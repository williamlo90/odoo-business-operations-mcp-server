"""Twelve actual MCP/Odoo reads, two worker consumers, persistent scoped queue."""
import asyncio
import json
import os
import time
from uuid import uuid4

from dotenv import dotenv_values
import httpx

from backend.assistant.contracts import Decision
from backend.assistant.mcp_gateway import McpGateway
from backend.worker.engine import run_once
from backend.worker.queue import Queue
from backend.monitor import queue_metrics
from reliability.load import ROOT, distribution


async def main():
    assert os.environ.get('ODOO_LIVE_TESTS')=='synthetic-sandbox'
    profile = dotenv_values(ROOT/'local/worker-profiles/company-a.env')
    # Only the existing project-specific automation identity may run this drill.
    assert profile['WORKER_USERNAME']=='automation.a'
    base = 'http://127.0.0.1:8020'
    with httpx.Client(base_url=base,trust_env=False,timeout=15) as client:
        response = client.post('/auth/login',json={'username':profile['WORKER_USERNAME'],'password':profile['WORKER_PASSWORD']})
        response.raise_for_status()
        token = response.json()['access_token']
        client.headers['Authorization'] = 'Bearer '+token
        try:
            identity = client.get('/me').json()
            assert identity['role']=='operator' and identity['tenant_id']=='00000000-0000-0000-0000-000000000001'
            queue = Queue(ROOT/'local/phase8-worker/jobs.sqlite3')
            assert not any(queue_metrics(queue.path)['counts'].get(s,0) for s in ['queued','running','retry_wait'])
            run_id = str(uuid4())
            decision = Decision(request={'skill':'research_customer','customer_reference':'OPS-A-001','include_opportunities':True})
            jobs = []
            start = time.monotonic()
            for index in range(12):
                key = run_id+':'+str(index)
                job = queue.enqueue(identity,key,decision)
                assert queue.enqueue(identity,key,decision)==job
                jobs.append(job)
            before = queue_metrics(queue.path)
            results = []
            async def consume():
                while True:
                    # Call budgets belong to one job, just as in the worker CLI.
                    async with McpGateway(base,token) as gateway:
                        result = await run_once(Queue(queue.path),gateway)
                        if result['state']=='idle':
                            return
                        assert result['state']=='completed'
                        assert result['result']['facts'][0]['record']['reference']=='OPS-A-001'
                        results.append(result)
            await asyncio.gather(consume(),consume())
            elapsed = time.monotonic()-start
            assert sorted(x['id'] for x in results)==sorted(jobs)
            waits, processing, total = [], [], []
            for job in jobs:
                value = Queue(queue.path).inspect(identity,job)
                events = {e['event']:e['at'] for e in value['events']}
                assert value['attempts']==1
                waits.append(events['claimed']-events['enqueued'])
                processing.append(events['completed']-events['claimed'])
                total.append(events['completed']-events['enqueued'])
            assert max(total)<60 and not any(queue_metrics(queue.path)['counts'].get(s,0) for s in ['queued','running','retry_wait'])
            report = {'run_id':run_id,'passed':True,'tasks':12,'consumers':2,'completed':12,'duplicates':0,
                      'scope':'Actual dedicated worker identity, MCP stdio and synthetic Odoo reads; no model inference',
                      'queue_before':before,'queue_wait_seconds':distribution(waits),'processing_seconds':distribution(processing),
                      'end_to_end_seconds':distribution(total),'achieved_tasks_per_second':12/elapsed,'elapsed_seconds':elapsed}
            (ROOT/'local/phase8-worker.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            print(json.dumps(report))
        finally:
            client.post('/auth/logout')


if __name__=='__main__':
    asyncio.run(main())
