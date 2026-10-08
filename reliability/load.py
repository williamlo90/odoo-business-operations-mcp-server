"""Bounded arrival-rate load against only the project's synthetic local stack."""
import asyncio
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time
from uuid import UUID, uuid4

import httpx

from evaluation.quality import BASE, ROOT, sessions, get_fixture


def docker(*args):
    result = subprocess.run(['docker',*args],cwd=ROOT,capture_output=True,timeout=30)
    if result.returncode:
        raise RuntimeError('docker_read_failed')
    return result.stdout.decode()


def distribution(values):
    values = sorted(values)
    return {'n':len(values), **{f'p{p}':round(values[math.ceil(p/100*len(values))-1],4) if values else None
                              for p in (50,90,95,99)}}


async def workload(spec, clients, fixture, policy):
    rows, calls = [], []
    slots = asyncio.Semaphore(spec['concurrency'])
    start = time.monotonic()
    failures = 0
    async with httpx.AsyncClient(base_url=BASE,trust_env=False,follow_redirects=False,timeout=15) as http:
        async def request(stage,method,path,role='operator',body=None,params=None):
            began = time.monotonic()
            response = await http.request(method,path,headers={'Authorization':clients[role+'.a'].headers['Authorization']},json=body,params=params)
            duration = time.monotonic()-began
            calls.append({'stage':stage,'status':response.status_code,'elapsed_seconds':duration,
                          'downstream_seconds':float(response.headers.get('X-Downstream-Duration-Ms',0))/1000,
                          'correlation_id':response.headers.get('X-Correlation-ID')})
            response.raise_for_status()
            return response.json()

        async def task(index,scheduled):
            nonlocal failures
            kind = 'write' if index%4 == 3 else 'read'
            async with slots:
                began = time.monotonic()
                wait = began-scheduled
                if wait > policy['max_queue_wait_seconds'] or failures >= policy['stop_after_failures']:
                    rows.append({'kind':kind,'state':'dropped','queue_seconds':wait,'elapsed_seconds':0})
                    return
                row = {'kind':kind,'state':'failed','queue_seconds':wait}
                try:
                    async with asyncio.timeout(policy['max_task_seconds']):
                        if kind == 'read':
                            data = await request('customer_search','GET','/v1/customers',params={'query':'OPS-A-001','limit':100})
                            assert len(data['items']) == 1
                            customer = data['items'][0]
                            assert customer['id'] == fixture['customers']['OPS-A-001']['id'] and customer['company_id'] == fixture['company_id']
                            row['state'] = 'correct_read'
                        else:
                            proposal = await request('prepare','POST','/v1/quotes/prepare',body={
                                'customer_id':fixture['customers']['OPS-A-001']['id'],
                                'items':[{'product_id':fixture['products']['OPS-A-P1']['id'],'quantity':2}]})
                            assert Decimal(proposal['preview']['total']) == 200000
                            approval = await request('approve','POST','/v1/proposals/'+proposal['id']+'/approve',
                                                     role='approver',body={'payload_hash':proposal['payload_hash']})
                            payload = {'approval_id':approval['id'],'idempotency_key':str(uuid4())}
                            operation = await request('execute_ack','POST','/v1/proposals/'+proposal['id']+'/execute',body=payload)
                            assert operation['status'] == 'verified'
                            verified = await request('readback','GET','/v1/operations/'+operation['id'])
                            assert verified['status'] == 'verified' and Decimal(verified['result']['record']['total']) == 200000
                            replay = await request('execute_replay','POST','/v1/proposals/'+proposal['id']+'/execute',body=payload)
                            assert replay['id'] == verified['id'] and replay['result'] == verified['result']
                            row.update(state='verified',operation_id=operation['id'])
                except (httpx.HTTPError,AssertionError,KeyError,ValueError,TimeoutError):
                    failures += 1
                row['elapsed_seconds'] = time.monotonic()-began
                row['total_seconds'] = row['queue_seconds']+row['elapsed_seconds']
                rows.append(row)

        tasks = []
        for index in range(spec['count']):
            scheduled = start+index/spec['rate_per_second']
            await asyncio.sleep(max(0,scheduled-time.monotonic()))
            tasks.append(asyncio.create_task(task(index,scheduled)))
        await asyncio.gather(*tasks)
    wall = time.monotonic()-start
    states = dict(Counter(row['state'] for row in rows))
    per_kind = {kind:distribution([row['elapsed_seconds'] for row in rows if row['kind']==kind and row['state']!='dropped']) for kind in ['read','write']}
    passed = states.get('failed',0) == states.get('dropped',0) == 0
    passed &= all(per_kind[k]['p95'] is not None and per_kind[k]['p95'] <= spec[k+'_p95_seconds'] for k in per_kind)
    return {'spec':spec,'rows':rows,'http_calls':calls,'wall_seconds':wall,'states':states,'per_kind_seconds':per_kind,
            'queue_seconds':distribution([r['queue_seconds'] for r in rows]),
            'total_seconds':distribution([r['total_seconds'] for r in rows if 'total_seconds' in r]),
            'per_stage_seconds':{stage:distribution([x['elapsed_seconds'] for x in calls if x['stage']==stage]) for stage in sorted({x['stage'] for x in calls})},
            'downstream_per_stage_seconds':{stage:distribution([x['downstream_seconds'] for x in calls if x['stage']==stage]) for stage in sorted({x['stage'] for x in calls})},
            'achieved_correct_tasks_per_second':(states.get('correct_read',0)+states.get('verified',0))/wall,
            'verified_operations_per_minute':states.get('verified',0)/wall*60,
            'error_rate':states.get('failed',0)/spec['count'],'dropped':states.get('dropped',0),'passed':bool(passed)}


async def main():
    if os.environ.get('ODOO_LIVE_TESTS') != 'synthetic-sandbox':
        raise SystemExit('Explicit synthetic sandbox opt-in required')
    policy_path = ROOT/'reliability/workload.json'
    policy = json.loads(policy_path.read_text())
    ids = docker('compose','-f','compose.yaml','-f','compose.odoo.yaml','ps','-q').splitlines()
    inspected = json.loads(docker('inspect',*ids))
    services = {}
    for value in inspected:
        labels = value['Config']['Labels']
        assert labels['com.docker.compose.project'] == 'odoo-ops-local'
        name = labels['com.docker.compose.service']
        if name in policy['memory_limits_mib']:
            assert value['State']['Running'] and not value['State']['OOMKilled']
            assert value['HostConfig']['Memory'] == policy['memory_limits_mib'][name]*1024*1024
            services[value['Id']] = name
    assert len(services) == 4
    resources, stop = [], asyncio.Event()
    async def sample():
        while not stop.is_set():
            raw = await asyncio.to_thread(docker,'stats','--no-stream','--format','{{json .}}',*services)
            resources.extend(json.loads(line) for line in raw.splitlines())
            try:
                await asyncio.wait_for(stop.wait(),5)
            except TimeoutError:
                pass
    sampling = asyncio.create_task(sample())
    try:
        with sessions() as clients:
            fixture = get_fixture(clients['operator.a'])
            reports = []
            for spec in policy['workloads']:
                report = await workload(spec,clients,fixture,policy)
                reports.append(report)
                print(json.dumps({'workload':spec['name'],'passed':report['passed'],'states':report['states'],
                                  'per_kind_seconds':report['per_kind_seconds']}),flush=True)
                if not report['passed']:
                    break
            metrics = clients['operator.a'].get('/v1/metrics')
            metrics.raise_for_status()
            business_metrics = metrics.json()
    finally:
        stop.set()
        await sampling
    operation_ids = [str(UUID(r['operation_id'])) for report in reports for r in report['rows'] if 'operation_id' in r]
    effects = []
    # UUID validation above is mandatory before formatting these local SQL literals.
    for operation in operation_ids:
        sql = "SELECT (SELECT count(*) FROM ops_operation WHERE operation_id='"+operation+"'),(SELECT count(*) FROM sale_order WHERE client_order_ref='ops:"+operation+"');"
        value = docker('compose','-f','compose.yaml','-f','compose.odoo.yaml','exec','-T','odoo-db',
                       'psql','-U','odoo','-d','odoo_ops_sandbox','-At','-c',sql).strip()
        effects.append({'operation_id':operation,'ledger_and_order_count':value})
    final = json.loads(docker('inspect',*services))
    passed = len(reports)==len(policy['workloads']) and all(x['passed'] for x in reports)
    passed &= all(x['ledger_and_order_count']=='1|1' for x in effects)
    passed &= all(x['State']['Running'] and not x['State']['OOMKilled'] for x in final)
    output = {'run_id':datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
              'workload_sha256':hashlib.sha256(policy_path.read_bytes()).hexdigest(),
              'base_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'passed':bool(passed),'workloads':reports,'resources':resources,'final_effect_counts':effects,
              'business_metrics':business_metrics,'inference_seconds':None,'inference_scope':'No model calls in load',
              'http_ack_semantics':'Synchronous execution reply after dispatch/readback; no asynchronous accepted-only result counted',
              'application_images':{x['Config']['Labels']['com.docker.compose.service']:x['Image'] for x in final}}
    target = ROOT/'local/phase8-load.json'
    target.write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':bool(passed),'report':str(target),'verified_effects':len(effects)}))
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    asyncio.run(main())
