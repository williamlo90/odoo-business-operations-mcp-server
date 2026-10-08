"""Opt-in synthetic Odoo integration. No provider calls or model inference."""
import asyncio
from decimal import Decimal
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4

from dotenv import dotenv_values
import httpx
import pytest

from backend.assistant.contracts import Decision
from backend.assistant.mcp_gateway import McpGateway
from backend.assistant.runner import run
from backend.worker.engine import run_once
from backend.worker.queue import Queue

ROOT=Path(__file__).resolve().parents[2]
pytestmark=pytest.mark.skipif(os.environ.get('ODOO_LIVE_TESTS')!='synthetic-sandbox',reason='Explicit synthetic sandbox opt-in required')
BASE='http://127.0.0.1:8020'

@pytest.fixture(scope='module')
def sessions():
    config=json.loads((ROOT/'local/odoo-config/connections.json').read_text(encoding='utf-8'))
    assert all(c['database']=='odoo_ops_sandbox' and c['url']=='http://odoo:8069' for c in config.values())
    password=dotenv_values(ROOT/'.env')['DEMO_PASSWORD']
    clients={}
    try:
        for name in ['operator.a','approver.a','operator.b','approver.b']:
            client=httpx.Client(base_url=BASE,trust_env=False,follow_redirects=False,timeout=30)
            clients[name]=client
            response=client.post('/auth/login',json={'username':name,'password':password})
            assert response.status_code==200
            client.headers['Authorization']='Bearer '+response.json()['access_token']
            if name.startswith('operator'):
                info=client.get('/v1/odoo/info')
                assert info.status_code==200 and info.json()['api']=='JSON-2'
        yield clients
    finally:
        for client in clients.values():
            if 'Authorization' in client.headers:client.post('/auth/logout')
            client.close()

def gateway(client):
    return McpGateway(BASE,client.headers['Authorization'].removeprefix('Bearer '))

def assistant(client,request,state,task_id=None):
    async def invoke():
        async with gateway(client) as mcp:
            return await run(mcp,decision=Decision(request=request),trace_dir=state,task_id=task_id)
    return asyncio.run(invoke())

def tool(client,name,args):
    env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','TEMP','TMP'}}
    env.update(API_URL=BASE,ODOO_OPS_TOKEN=client.headers['Authorization'].removeprefix('Bearer '))
    process=subprocess.run(['node','mcp-server/dist/bridge.js'],cwd=ROOT,env=env,input=json.dumps({'id':1,'tool':name,'arguments':args})+'\n',text=True,capture_output=True,timeout=35)
    assert process.returncode==0
    reply=json.loads(process.stdout)['result']
    assert not reply.get('isError'), 'MCP tool rejected connected request'
    return reply['structuredContent']['data']

def approved_execute(sessions,company,proposal):
    operator=sessions['operator.'+company]
    approver=sessions['approver.'+company]
    denied=operator.post('/v1/proposals/'+proposal['id']+'/approve',json={'payload_hash':proposal['payload_hash']})
    assert denied.status_code==403
    approved=approver.post('/v1/proposals/'+proposal['id']+'/approve',json={'payload_hash':proposal['payload_hash']})
    assert approved.status_code==201
    args={'proposal_id':proposal['id'],'approval_id':approved.json()['id'],'idempotency_key':str(uuid4())}
    first=tool(operator,'odoo.execute_approved',args)
    replay=tool(operator,'odoo.execute_approved',args)
    assert first['id']==replay['id'] and first['status']==replay['status']=='verified'
    assert first['result']==replay['result']
    foreign=sessions['operator.'+('b' if company=='a' else 'a')]
    assert foreign.get('/v1/operations/'+first['id']).status_code==404
    return first

@pytest.mark.parametrize('company,total',[('a',250000),('b',290000)])
def test_assistant_mcp_quote_approval_execute_readback_and_replay(sessions,tmp_path,company,total):
    client=sessions['operator.'+company];prefix='OPS-'+company.upper()
    request={'skill':'prepare_quote','customer_reference':prefix+'-001','items':[{'product_code':prefix+'-P1','quantity':2},{'product_code':prefix+'-P2','quantity':1}]}
    task_id=str(uuid4())
    first=assistant(client,request,tmp_path,task_id)
    assert first['result']['status']=='awaiting_approval'
    assert assistant(client,request,tmp_path,task_id)==first
    proposal=first['result']['proposal']
    assert Decimal(proposal['preview']['total'])==total
    operation=approved_execute(sessions,company,proposal)
    reconciled=assistant(client,{'skill':'reconcile_odoo_write','operation_id':operation['id']},tmp_path)
    assert reconciled['result']['status']=='verified'
    assert Decimal(reconciled['result']['operation']['result']['record']['total'])==total

@pytest.mark.parametrize('company',['a','b'])
def test_worker_schedule_dedup_restart_and_tenant_scope_on_real_odoo(sessions,tmp_path,company):
    client=sessions['operator.'+company];identity=client.get('/me').json()
    queue=Queue(tmp_path/'jobs.sqlite3')
    request=Decision(request={'skill':'research_customer','customer_reference':'OPS-'+company.upper()+'-001','include_opportunities':True})
    queue.add_schedule(identity,'connected-research',300,request,now=100)
    async def tick():
        async with gateway(client) as mcp:
            return await run_once(Queue(queue.path),mcp,now=100)
    first=asyncio.run(tick())
    assert first['state']=='completed' and first['result']['status']=='read'
    assert first['result']['facts'][0]['record']['reference']==request.request.customer_reference
    assert asyncio.run(tick())['state']=='idle'
    foreign=sessions['operator.'+('b' if company=='a' else 'a')].get('/me').json()
    assert queue.claim(foreign,now=100) is None


def test_activity_skill_and_worker_proposal_on_real_odoo(sessions,tmp_path):
    client=sessions['operator.a'];identity=client.get('/me').json()
    lead=client.get('/v1/opportunities').json()['items'][0]
    request=Decision(request={'skill':'prepare_crm_activity','opportunity_id':lead['id'],'assignee_id':lead['owner_id'],'due_date':'2026-12-01','summary':'Synthetic Phase 6 integration'})
    queue=Queue(tmp_path/'activity.sqlite3');key='phase6-'+str(uuid4())
    job=queue.enqueue(identity,key,request)
    assert queue.enqueue(identity,key,request)==job
    async def tick():
        async with gateway(client) as mcp:
            return await run_once(Queue(queue.path),mcp)
    result=asyncio.run(tick())
    assert result['state']=='awaiting_approval'
    assert asyncio.run(tick())['state']=='idle'
    operation=approved_execute(sessions,'a',result['result']['proposal'])
    assert operation['result']['record']['summary']==request.request.summary


@pytest.mark.parametrize('company',['a','b'])
def test_dedicated_worker_profile_cli_persists_scoped_research(sessions,tmp_path,company):
    import sys
    profile=ROOT/'local/worker-profiles'/('company-'+company+'.env')
    if not profile.exists():
        pytest.skip('Provision dedicated worker profile first')
    request=tmp_path/'request.json'
    request.write_text(json.dumps({'request':{'skill':'research_customer','customer_reference':'OPS-'+company.upper()+'-001','include_opportunities':False}}),encoding='utf-8')
    env={k:v for k,v in os.environ.items() if not k.startswith('WORKER_')}
    def invoke(*args):
        process=subprocess.run([sys.executable,'-m','backend.worker','--env-file',str(profile),'--queue',str(tmp_path/'cli.sqlite3'),*args],cwd=ROOT,env=env,text=True,capture_output=True,timeout=35)
        assert process.returncode==0, 'Dedicated worker command failed'
        return json.loads(process.stdout)
    first=invoke('enqueue','connected-cli',str(request))
    assert invoke('enqueue','connected-cli',str(request))==first
    completed=invoke('run-once')
    assert completed['state']=='completed' and completed['id']==first['job_id']
    assert completed['result']['facts'][0]['record']['reference']=='OPS-'+company.upper()+'-001'
    assert invoke('inspect',first['job_id'])==completed
    assert invoke('run-once')['state']=='idle'
