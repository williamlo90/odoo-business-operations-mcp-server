"""Frozen, bounded synthetic evaluation through the production assistant and MCP."""
import argparse
import asyncio
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
from string import Template
import time
from uuid import uuid4

from dotenv import dotenv_values
import httpx

from backend.assistant.contracts import Decision
from backend.assistant.mcp_gateway import McpGateway
from backend.assistant.providers import AssistantError, JsonProvider, ProviderConfig, prompt_for, prompt_version_for
from backend.assistant.runner import parse_decision, run

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8020'
MODELS = {'openai': 'gpt-4.1-mini-2025-04-14', 'ollama': 'qwen2.5:0.5b'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(request):
    value = json.loads(json.dumps(request))
    if value and value.get('skill') == 'prepare_quote':
        value['items'] = sorted(value['items'], key=lambda x: x['product_code'])
    return value


def decision_matches(expected, actual):
    if not actual:
        return False
    if expected['skill'] == 'clarify':
        return actual.get('skill') == 'clarify' and set(expected['missing']) <= set(actual.get('missing', []))
    return canonical(expected) == canonical(actual)


def grade(case, actual, result, error, fixture):
    """A safe validation error is not a correct model decision or completed task."""
    result = result or {}
    status = error or result.get('status')
    intent = decision_matches(case['expected'], actual)
    outcome = status == case['status']
    facts = result.get('facts', [])
    company = fixture['company_id']
    critical = any(f['record'].get('company_id', company) != company for f in facts)
    proposal = result.get('proposal')
    if case['category'] != 'ready':
        critical |= proposal is not None or result.get('status') in {'verified', 'dispatched'}
    if case.get('no_facts'):
        critical |= bool(facts)
    if case['status'] == 'needs_input':
        required = case.get('missing', case['expected'].get('missing', []))
        outcome &= set(required) <= set(result.get('missing_information', [])) and proposal is None
    expected = case['expected']
    if case['status'] == 'read':
        ref = expected['customer_reference']
        customer = fixture['customers'][ref]
        outcome &= bool(facts) and facts[0]['record'] == {k: customer[k] for k in ('id','name','reference','company_id','version')}
        wanted = [facts[0]] if facts else []
        if expected['include_opportunities']:
            wanted += [{'source': 'odoo:crm.lead:'+str(x['id']), 'record': {k:x[k] for k in
                ('id','company_id','name','customer_id','owner_id','stage','version')}}
                for x in fixture['opportunities'] if x['customer_id'] == customer['id']]
        outcome &= facts == wanted and all(f['source'].startswith('odoo:') for f in facts)
    if case['status'] == 'awaiting_approval':
        outcome &= proposal is not None
        if proposal:
            preview = proposal['preview']
            outcome &= preview['company_id'] == company and proposal['tenant_id'] == fixture['tenant_id']
            if expected['skill'] == 'prepare_quote':
                wanted = {fixture['products'][x['product_code']]['id']: x['quantity'] for x in expected['items']}
                outcome &= preview['customer_id'] == fixture['customers'][expected['customer_reference']]['id']
                outcome &= {x['product_id']: x['quantity'] for x in preview['items']} == wanted
                outcome &= Decimal(preview['total']) == Decimal(case['total']) and preview['currency'] == 'IDR'
            else:
                outcome &= all(preview[k] == v for k, v in expected.items() if k != 'skill')
    if case['status'] == 'verified':
        operation = result.get('operation') or {}
        outcome &= operation.get('id') == expected['operation_id'] and operation.get('tenant_id') == fixture['tenant_id']
        outcome &= operation.get('result') is not None
    return {'intent_correct': bool(intent), 'outcome_correct': bool(outcome),
            'task_correct': bool(intent and outcome and not critical), 'critical_violation': bool(critical)}


def wilson(passed, count):
    if not count:
        return None
    z = 1.96
    p = passed / count
    denominator = 1 + z*z/count
    center = (p + z*z/(2*count))/denominator
    margin = z*math.sqrt(p*(1-p)/count + z*z/(4*count*count))/denominator
    return [round(center-margin, 4), round(center+margin, 4)]


def summarize(rows):
    categories = {}
    for category in ('ready', 'clarify', 'domain'):
        selected = [r for r in rows if r['category'] == category]
        passed = sum(r['task_correct'] for r in selected)
        categories[category] = {'passed': passed, 'count': len(selected), 'wilson_95_descriptive': wilson(passed, len(selected))}
    critical = sum(r['critical_violation'] for r in rows)
    passed = sum(r['task_correct'] for r in rows)
    times = sorted(r['elapsed_seconds'] for r in rows)
    return {'passed': passed, 'count': len(rows), 'planned_count': 18, 'not_run': 18-len(rows),
            'critical_violations': critical, 'categories': categories,
            'qualified': len(rows) == 18 and passed >= 17 and categories['ready']['passed'] == 8
                and categories['clarify']['passed'] >= 5 and categories['domain']['passed'] == 4 and critical == 0,
            'elapsed_total_seconds': round(sum(times), 3),
            'p95_task_seconds_nearest_rank': times[math.ceil(.95*len(times))-1] if times else None,
            'latency_sample_count': len(times), 'failures_in_latency_denominator': True,
            'cost_per_correct_task_usd': None, 'cost_status': 'rate_card_not_configured',
            'human_active_seconds': None, 'human_corrections': None}


@contextmanager
def sessions():
    config = json.loads((ROOT/'local/odoo-config/connections.json').read_text())
    if not config or not all(x['database'] == 'odoo_ops_sandbox' and x['url'] == 'http://odoo:8069' for x in config.values()):
        raise RuntimeError('Synthetic sandbox required')
    password = dotenv_values(ROOT/'.env')['DEMO_PASSWORD']
    clients = {}
    try:
        for company in ('a', 'b'):
            for role in ('operator', 'approver'):
                name = role+'.'+company
                client = clients[name] = httpx.Client(base_url=BASE, trust_env=False, timeout=30)
                response = client.post('/auth/login', json={'username': name, 'password': password})
                response.raise_for_status()
                client.headers['Authorization'] = 'Bearer '+response.json()['access_token']
        yield clients
    finally:
        for client in clients.values():
            try:
                if 'Authorization' in client.headers:
                    client.post('/auth/logout')
            finally:
                client.close()


def get_fixture(client):
    def get(path):
        response = client.get(path)
        response.raise_for_status()
        return response.json()
    customers = get('/v1/customers')['items']
    return {'customers': {x['reference']: x for x in customers},
            'products': {x['code']: x for x in get('/v1/catalog')['items']},
            'opportunities': get('/v1/opportunities')['items'],
            'company_id': customers[0]['company_id'], 'tenant_id': get('/me')['tenant_id']}


def operation_fixture(clients, fixture):
    """One explicit approved synthetic write, replayed with the same key."""
    client = clients['operator.b']
    payload = {'customer_id': fixture['customers']['OPS-B-001']['id'],
               'items': [{'product_id': fixture['products']['OPS-B-P1']['id'], 'quantity': 1}]}
    response = client.post('/v1/quotes/prepare', json=payload)
    response.raise_for_status()
    proposal = response.json()
    response = clients['approver.b'].post('/v1/proposals/'+proposal['id']+'/approve', json={'payload_hash': proposal['payload_hash']})
    response.raise_for_status()
    body = {'approval_id': response.json()['id'], 'idempotency_key': str(uuid4())}
    response = client.post('/v1/proposals/'+proposal['id']+'/execute', json=body)
    response.raise_for_status()
    operation = response.json()
    replay = client.post('/v1/proposals/'+proposal['id']+'/execute', json=body)
    replay.raise_for_status()
    assert operation['status'] == replay.json()['status'] == 'verified' and operation['id'] == replay.json()['id']
    assert Decimal(operation['result']['record']['total']) == 120000
    return operation['id']


class ObservedProvider:
    def __init__(self, provider):
        self.inner, self.config = provider, provider.config
        self.decision = None
        self.model_seconds = None
        self.usage = None

    async def generate(self, task):
        start = time.monotonic()
        generation = await self.inner.generate(task)
        self.model_seconds = round(time.monotonic()-start, 3)
        self.usage = {'input_tokens': generation.input_tokens, 'output_tokens': generation.output_tokens}
        try:
            self.decision = parse_decision(generation.text).request.model_dump()
        except AssistantError:
            pass
        return generation


async def evaluate(case, client, fixture, provider, directory):
    observed = ObservedProvider(provider) if provider else None
    result, error = None, None
    task_id = str(uuid4())
    start = time.monotonic()
    async with McpGateway(BASE, client.headers['Authorization'].removeprefix('Bearer ')) as gateway:
        try:
            kwargs = {'task': case['task'], 'provider': observed} if observed else {'decision': Decision(request=case['expected'])}
            output = await run(gateway, **kwargs, trace_dir=directory, task_id=task_id)
            result = output['result']
        except AssistantError as exc:
            error = str(exc)
        calls = len(gateway.correlations)
    elapsed = round(time.monotonic()-start, 3)
    actual = observed.decision if observed else case['expected']
    row = {'case_id': case['id'], 'family': case['family'], 'category': case['category'], 'task_id': task_id,
           'expected_decision': case['expected'], 'observed_decision': actual,
           'expected_status': case['status'], 'observed_status': error or result['status'],
           'elapsed_seconds': elapsed, 'model_seconds': observed.model_seconds if observed else None,
           'usage': observed.usage if observed else None, 'successful_mcp_calls': calls,
           **grade(case, actual, result, error, fixture)}
    # Raw synthetic results remain local; publication uses a bounded score record.
    (directory/(case['id']+'-result.json')).write_text(json.dumps({'result': result, 'error': error}, indent=2)+'\n')
    return row


def frozen_files():
    paths = ['evaluation/regression-v2.json', 'evaluation/development-v2.json', 'evaluation/POLICY.md',
             'evaluation/quality.py', 'evaluation/regression-v1.json', 'tests/evaluation/test_quality.py',
             'tests/assistant/test_core.py', 'tests/live/test_quality_regression.py',
             'docs/evidence/phase6-local-runtime.json']
    tracked = subprocess.check_output(['git', 'ls-files', 'backend', 'tests/live', 'mcp-server/src',
                                      'backend/requirements.lock', 'mcp-server/package-lock.json'], cwd=ROOT, text=True).splitlines()
    return {p: sha(ROOT/p) for p in sorted(set(paths+tracked))}


def freeze():
    path = ROOT/'evaluation/freeze-v3-final.json'
    if path.exists():
        raise SystemExit('Freeze already exists; create a new dataset version for a new final evaluation.')
    path.write_text(json.dumps({'frozen_at': datetime.now(timezone.utc).isoformat(),
        'base_revision': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'files': frozen_files(), 'model_profiles': {p: {'model': m, 'prompt_version': prompt_version_for(p),
        'prompt_sha256': hashlib.sha256(prompt_for(p).encode()).hexdigest()} for p,m in MODELS.items()}}, indent=2)+'\n')


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['freeze', 'run'])
    parser.add_argument('--provider', choices=['reference', 'openai', 'ollama'])
    args = parser.parse_args()
    if args.action == 'freeze':
        freeze()
        return
    if os.environ.get('ODOO_LIVE_TESTS') != 'synthetic-sandbox' or not args.provider:
        raise SystemExit('Set ODOO_LIVE_TESTS=synthetic-sandbox and --provider')
    if args.provider == 'openai' and os.environ.get('OPENAI_LIVE_TESTS') != 'yes':
        raise SystemExit('Set OPENAI_LIVE_TESTS=yes for 18 paid calls, no retries, max 500 output tokens each')
    frozen = json.loads((ROOT/'evaluation/freeze-v3-final.json').read_text())
    if frozen['files'] != frozen_files():
        raise SystemExit('Frozen source/data changed; do not reuse this holdout for tuning')
    if args.provider == 'ollama':
        evidence = json.loads((ROOT/'docs/evidence/phase6-local-runtime.json').read_text())
        with httpx.Client(base_url='http://127.0.0.1:11434', trust_env=False, timeout=10) as client:
            assert client.get('/api/version').json()['version'] == evidence['version']
            assert client.get('/api/status').json()['cloud']['disabled'] is True
            model = next(x for x in client.get('/api/tags').json()['models'] if x['name'] == MODELS['ollama'])
            assert model['digest'] == evidence['model']['digest']
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+args.provider+'-'+str(uuid4())[:8]
    directory = ROOT/'local/evaluation'/run_id
    directory.mkdir(parents=True)
    provider = None
    if args.provider != 'reference':
        key = None
        if args.provider == 'openai':
            key = os.environ.get('OPENAI_API_KEY') or dotenv_values(ROOT/'.env').get('OPENAI_API_KEY')
        provider = JsonProvider(ProviderConfig(args.provider, MODELS[args.provider], api_key=key,
            local_only=args.provider == 'ollama', max_output_tokens=500))
    rows = []
    with sessions() as clients:
        fixtures = {c: get_fixture(clients['operator.'+c]) for c in ('a','b')}
        bindings = {f'{k}_{c}': fixtures[c]['opportunities'][0][field] for c in ('a','b')
                    for k,field in [('lead','id'),('owner','owner_id')]}
        bindings['operation_b'] = operation_fixture(clients, fixtures['b'])
        data = json.loads(Template((ROOT/'evaluation/regression-v2.json').read_text()).substitute(bindings))
        for case in data['cases']:
            if 'total' in case:
                catalog = fixtures[case['company']]['products']
                expected_total = sum(Decimal(catalog[x['product_code']]['unit_price'])*x['quantity']
                                     for x in case['expected']['items'])
                assert expected_total == Decimal(case['total']), 'Fixture prices differ from frozen specification'
        for case in data['cases']:
            if case['expected']['skill'] == 'prepare_crm_activity':
                for field in ('opportunity_id', 'assignee_id'):
                    case['expected'][field] = int(case['expected'][field])
            row = await evaluate(case, clients['operator.'+case['company']], fixtures[case['company']], provider, directory)
            rows.append(row)
            with (directory/'scores.jsonl').open('a') as file:
                file.write(json.dumps(row)+'\n')
            print(json.dumps({'case': row['case_id'], 'correct': row['task_correct'], 'status': row['observed_status']}), flush=True)
            if row['critical_violation']:
                print('Critical violation: stopped remaining cases', flush=True)
                break
    report = {'run_id': run_id, 'provider': args.provider, 'model': MODELS.get(args.provider),
              'freeze_sha256': sha(ROOT/'evaluation/freeze-v3-final.json'), 'dataset_sha256': sha(ROOT/'evaluation/regression-v2.json'),
              'base_revision': frozen['base_revision'], 'source_manifest': frozen['files'],
              'profile': frozen['model_profiles'].get(args.provider),
              'environment': {'system': platform.system(), 'release': platform.release(), 'python': platform.python_version(),
                              'processor': platform.processor(), 'execution': 'single-agent synthetic sandbox, concurrency=1'},
              'bindings': bindings, 'summary': summarize(rows), 'rows': rows,
              'excluded_cases': [x['id'] for x in data['cases'][len(rows):]],
              'human_time_comparison': 'not measured; reference is automated typed intent, not human manual work'}
    path = directory/'report.json'
    path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'report': str(path), 'summary': report['summary']}), flush=True)


if __name__ == '__main__':
    asyncio.run(main())
