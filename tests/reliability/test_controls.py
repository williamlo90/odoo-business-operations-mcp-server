import asyncio
from concurrent.futures import ThreadPoolExecutor
import sqlite3

import pytest

from backend.assistant.contracts import Decision
from backend.assistant.providers import AssistantError
from backend.assistant.runner import check_grounding
from backend.monitor import Monitor, queue_metrics, probe
from backend.worker.queue import Queue

IDENTITY = {'id':'00000000-0000-0000-0000-000000000065','tenant_id':'00000000-0000-0000-0000-000000000001','role':'operator'}
READ = Decision(request={'skill':'research_customer','customer_reference':'OPS-A-001','include_opportunities':False})


@pytest.mark.parametrize('fragment,guessed', [('1,5',5),('1.5',5),('1/2',2),('-2',2),('\u22122',2),('2%',2),('2-P1',2),('2e3',2),('1,000',1)])
def test_quantity_fragment_cannot_become_integer(fragment,guessed):
    quote = Decision(request={'skill':'prepare_quote','customer_reference':'OPS-A-001',
        'items':[{'product_code':'OPS-A-P1','quantity':guessed}]})
    with pytest.raises(AssistantError,match='unsupported_model_quantity'):
        check_grounding(quote.request, 'Quote OPS-A-001 OPS-A-P1 quantity '+fragment)


def test_monitor_dedup_restart_recovery_and_receiver(tmp_path):
    path = tmp_path/'monitor.sqlite3'
    first = Monitor(path)
    assert first.sample('api_readiness',False,100)['transition'] is None
    assert first.sample('api_readiness',False,101)['transition'] == 'firing'
    restarted = Monitor(path)
    assert restarted.sample('api_readiness',False,102)['transition'] is None
    firing = restarted.receive(103)
    assert len(firing) == 1 and firing[0]['transition'] == 'firing'
    assert restarted.receive(104) == []
    restarted.sample('api_readiness',True,105)
    assert restarted.sample('api_readiness',True,106)['transition'] == 'recovered'
    recovered = restarted.receive(107)
    assert recovered[0]['incident'] == firing[0]['incident']


def test_monitor_rejects_foreign_db_and_external_probe(tmp_path):
    queue = Queue(tmp_path/'jobs.sqlite3')
    with pytest.raises(ValueError):
        Monitor(queue.path)
    for url in ['https://example.com','http://user@127.0.0.1:8020','http://127.0.0.1:8020/secret']:
        with pytest.raises(ValueError):
            probe(url)


def test_backlog_concurrent_drain_and_late_worker_are_fenced(tmp_path):
    queue = Queue(tmp_path/'jobs.sqlite3')
    for i in range(40):
        queue.enqueue(IDENTITY,'load-'+str(i),READ,now=100)
    def drain(_):
        results = []
        while job := queue.claim(IDENTITY,now=101):
            queue.dispatch(job,now=101)
            queue.finish(job,'completed',now=102)
            results.append(job['id'])
        return results
    with ThreadPoolExecutor(max_workers=4) as pool:
        completed = sum(pool.map(drain,range(4)),[])
    assert len(completed) == len(set(completed)) == 40
    assert queue_metrics(queue.path)['counts'] == {'completed':40}
    queue.enqueue(IDENTITY,'late',READ,now=200)
    old = queue.claim(IDENTITY,now=200)
    new = queue.claim(IDENTITY,now=291)
    with pytest.raises(AssistantError,match='job_lease_lost'):
        queue.finish(old,'completed',now=292)
    queue.finish(new,'completed',now=292)
    assert queue.inspect(IDENTITY,new['id'])['attempts'] == 2
