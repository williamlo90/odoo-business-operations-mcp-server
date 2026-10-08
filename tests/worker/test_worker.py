import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys

import httpx
import pytest

from backend.assistant.contracts import Decision
from backend.assistant.gateway import DomainGateway
from backend.assistant.providers import AssistantError
from backend.worker.engine import run_once
from backend.worker.queue import Queue

ROOT=Path(__file__).resolve().parents[2]
IDENTITY={'id':'00000000-0000-0000-0000-000000000065','tenant_id':'00000000-0000-0000-0000-000000000001','role':'operator'}
OTHER={'id':'00000000-0000-0000-0000-0000000000c9','tenant_id':'00000000-0000-0000-0000-000000000002','role':'operator'}
RESEARCH=Decision(request={'skill':'research_customer','customer_reference':'OPS-A-001','include_opportunities':False})
QUOTE=Decision(request={'skill':'prepare_quote','customer_reference':'OPS-A-001','items':[{'product_code':'OPS-A-P1','quantity':2},{'product_code':'OPS-A-P2','quantity':1}]})
OPERATION=json.loads((ROOT/'tests/assistant/fixtures/operation.json').read_text(encoding='utf-8'))
RECONCILE=Decision(request={'skill':'reconcile_odoo_write','operation_id':OPERATION['id']})


class Source:
    def __init__(self):
        self.identity=IDENTITY
        self.fail=None
        self.effects=0
        self.status='verified'
        self.calls=[]

    def response(self,req):
        self.calls.append(req.url.path)
        path=req.url.path
        if path=='/me':
            return httpx.Response(200,json=self.identity)
        if self.fail=='read':
            raise httpx.ConnectError('private failure')
        if self.fail=='credentials':
            return httpx.Response(401,json={'error':'invalid_session'})
        if path=='/v1/customers':
            company=2 if self.identity==IDENTITY else 3
            return httpx.Response(200,json={'items':[{'id':7,'name':'Synthetic','reference':'OPS-A-001',
                'company_id':company,'version':'v1'}],'next_cursor':None,'revision':'a'*64})
        if path=='/v1/catalog':
            return httpx.Response(200,json={'items':[{'id':1,'code':'OPS-A-P1'},{'id':2,'code':'OPS-A-P2'}]})
        if path=='/v1/quotes/prepare':
            self.effects+=1
            if self.fail=='lost':
                raise httpx.ReadTimeout('lost response after committed proposal')
            return httpx.Response(201,json=json.loads((ROOT/'tests/assistant/fixtures/proposal.json').read_text(encoding='utf-8')))
        if path.startswith('/v1/operations/'):
            return httpx.Response(200,json={**OPERATION,'status':self.status,'result':OPERATION['result'] if self.status=='verified' else None})
        raise AssertionError('Forbidden route: '+path)

    def gateway(self):
        return DomainGateway('http://127.0.0.1:8020','synthetic-session',httpx.MockTransport(self.response))


def test_duplicate_event_and_worker_replay_do_not_duplicate_proposal(tmp_path):
    queue=Queue(tmp_path/'jobs.sqlite3');source=Source()
    job=queue.enqueue(IDENTITY,'event-1',QUOTE,now=100)
    assert queue.enqueue(IDENTITY,'event-1',QUOTE,now=101)==job
    first=asyncio.run(run_once(queue,source.gateway(),now=100))
    assert first['state']=='awaiting_approval'
    assert first['result']['proposal']['preview']['total']=='250000.0'
    assert asyncio.run(run_once(Queue(queue.path),source.gateway(),now=101))['state']=='idle'
    assert source.effects==1
    assert not any('/execute' in path or '/approve' in path for path in source.calls)


def test_changed_payload_cannot_reuse_event_key(tmp_path):
    queue=Queue(tmp_path/'jobs.sqlite3')
    queue.enqueue(IDENTITY,'event',QUOTE)
    with pytest.raises(AssistantError,match='event_conflict'):
        queue.enqueue(IDENTITY,'event',RESEARCH)


def test_two_claimers_get_only_one_lease(tmp_path):
    queue=Queue(tmp_path/'jobs.sqlite3')
    queue.enqueue(IDENTITY,'event',RESEARCH,now=100)
    with ThreadPoolExecutor(max_workers=2) as pool:
        values=list(pool.map(lambda _: Queue(queue.path).claim(IDENTITY,now=100),range(2)))
    assert sum(value is not None for value in values)==1


def test_tenant_and_actor_scopes_cover_queue_claim_inspection_and_schedule(tmp_path):
    queue=Queue(tmp_path/'jobs.sqlite3')
    job=queue.enqueue(IDENTITY,'same-key',RESEARCH,now=100)
    assert queue.claim(OTHER,now=100) is None
    with pytest.raises(AssistantError,match='job_not_found'):
        queue.inspect(OTHER,job)
    own=queue.enqueue(OTHER,'same-key',RESEARCH,now=100)
    assert own!=job
    source=Source();source.identity=OTHER
    result=asyncio.run(run_once(queue,source.gateway(),now=100))
    assert result['id']==own and result['result']['facts'][0]['record']['company_id']==3
    queue.add_schedule(IDENTITY,'daily',60,RESEARCH,now=100)
    assert queue.tick(OTHER,now=100)==[]


def test_transient_reads_back_off_and_exhaust_into_dead_letter(tmp_path):
    queue=Queue(tmp_path/'jobs.sqlite3');source=Source();source.fail='read'
    job=queue.enqueue(IDENTITY,'read',RESEARCH,now=100)
    first=asyncio.run(run_once(queue,source.gateway(),now=100))
    assert first['state']=='retry_wait' and first['available']==105
    assert asyncio.run(run_once(queue,source.gateway(),now=104))['state']=='idle'
    second=asyncio.run(run_once(queue,source.gateway(),now=105))
    assert second['available']==115
    third=asyncio.run(run_once(queue,source.gateway(),now=115))
    assert third['state']=='dead' and third['attempts']==3
    assert 'private failure' not in json.dumps(queue.inspect(IDENTITY,job))


def test_lost_prepare_never_automatically_retries(tmp_path):
    queue=Queue(tmp_path/'jobs.sqlite3');source=Source();source.fail='lost'
    job=queue.enqueue(IDENTITY,'lost',QUOTE,now=100)
    result=asyncio.run(run_once(queue,source.gateway(),now=100))
    assert result['state']=='review' and result['error']=='proposal_outcome_unknown'
    assert asyncio.run(run_once(queue,source.gateway(),now=1000))['state']=='idle'
    assert source.effects==1


def test_expired_credentials_route_to_review(tmp_path):
    queue=Queue(tmp_path/'jobs.sqlite3');source=Source();source.fail='credentials'
    queue.enqueue(IDENTITY,'auth',RESEARCH,now=100)
    result=asyncio.run(run_once(queue,source.gateway(),now=100))
    assert result['state']=='review' and result['error']=='domain_access_denied'


def test_unknown_operation_polling_is_bounded_and_can_recover(tmp_path):
    queue=Queue(tmp_path/'jobs.sqlite3');source=Source();source.status='unknown'
    queue.enqueue(IDENTITY,'operation',RECONCILE,now=100)
    assert asyncio.run(run_once(queue,source.gateway(),now=100))['state']=='retry_wait'
    source.status='verified'
    assert asyncio.run(run_once(queue,source.gateway(),now=105))['state']=='completed'
    assert source.effects==0


def test_persistent_unknown_operation_requires_manual_review(tmp_path):
    queue=Queue(tmp_path/'jobs.sqlite3');source=Source();source.status='unknown'
    queue.enqueue(IDENTITY,'operation',RECONCILE,now=100)
    for now in [100,105,115]:
        result=asyncio.run(run_once(queue,source.gateway(),now=now))
    assert result['state']=='review' and result['attempts']==3


def test_schedule_deduplicates_ticks_coalesces_missed_intervals_and_disables(tmp_path):
    queue=Queue(tmp_path/'jobs.sqlite3')
    queue.add_schedule(IDENTITY,'customer-research',60,RESEARCH,now=100)
    assert len(queue.tick(IDENTITY,now=100))==1
    assert queue.tick(IDENTITY,now=110)==[]
    assert len(Queue(queue.path).tick(IDENTITY,now=600))==1
    queue.disable_schedule(IDENTITY,'customer-research')
    assert queue.tick(IDENTITY,now=660)==[]


def test_real_process_crash_after_dispatch_enters_review_without_replay(tmp_path):
    queue=Queue(tmp_path/'jobs.sqlite3')
    job=queue.enqueue(IDENTITY,'crash',QUOTE,now=100)
    code='''import json,os,sys
from backend.worker.queue import Queue
queue=Queue(sys.argv[1]); identity=json.loads(sys.argv[2])
job=queue.claim(identity,now=100); queue.dispatch(job,now=100)
os._exit(23)
'''
    child=subprocess.run([sys.executable,'-c',code,str(queue.path),json.dumps(IDENTITY)],cwd=ROOT,capture_output=True,timeout=10)
    assert child.returncode==23
    assert Queue(queue.path).claim(IDENTITY,now=191) is None
    assert queue.inspect(IDENTITY,job)['state']=='review'


def test_crash_before_dispatch_recovers_with_new_owner_and_fences_old_worker(tmp_path):
    queue=Queue(tmp_path/'jobs.sqlite3')
    queue.enqueue(IDENTITY,'crash-read',RESEARCH,now=100)
    old=queue.claim(IDENTITY,now=100)
    current=Queue(queue.path).claim(IDENTITY,now=191)
    assert current['id']==old['id'] and current['owner']!=old['owner']
    with pytest.raises(AssistantError,match='job_lease_lost'):
        queue.finish(old,'completed',now=191)
    queue.finish(current,'completed',now=191)


def test_worker_uses_same_skill_postconditions_and_read_only_roles(tmp_path):
    queue=Queue(tmp_path/'jobs.sqlite3')
    with pytest.raises(AssistantError,match='job_permission_denied'):
        queue.enqueue({**IDENTITY,'role':'auditor'},'write',QUOTE)
    with pytest.raises(AssistantError,match='invalid_job'):
        queue.enqueue(IDENTITY,'clarify',Decision(request={'skill':'clarify','missing':['supported_task']}))


@pytest.mark.parametrize('decision,state', [(RESEARCH,'retry_wait'),(QUOTE,'review')])
def test_timeout_preserves_write_uncertainty(tmp_path,monkeypatch,decision,state):
    queue=Queue(tmp_path/'jobs.sqlite3'); source=Source()
    queue.enqueue(IDENTITY,'timeout',decision,now=100)
    async def slow(*args):
        await asyncio.sleep(10)
    monkeypatch.setattr('backend.worker.engine.execute_skill',slow)
    result=asyncio.run(run_once(queue,source.gateway(),now=100,timeout_seconds=0.01))
    assert result['state']==state and result['error']=='worker_timeout'


def test_unrelated_sqlite_database_is_rejected_without_changes(tmp_path):
    import sqlite3
    path=tmp_path/'unrelated.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE unrelated(value TEXT)')
    with pytest.raises(AssistantError,match='incompatible_queue_database'):
        Queue(path)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()==[('unrelated',)]
