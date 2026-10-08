"""Opt-in live local inference integration; synthetic data, no hosted fallback."""
import asyncio
from decimal import Decimal
import json
import os
import time
from uuid import uuid4

import httpx
import pytest

from backend.assistant.providers import AssistantError, JsonProvider, ProviderConfig
from backend.assistant.runner import parse_decision, run
from test_stack import ROOT, sessions, gateway, approved_execute

pytestmark=[
    pytest.mark.skipif(os.environ.get('ODOO_LIVE_TESTS')!='synthetic-sandbox',reason='Synthetic sandbox opt-in required'),
    pytest.mark.skipif(os.environ.get('OLLAMA_LIVE_TESTS')!='yes',reason='Live inference opt-in required'),
]

@pytest.fixture(scope='module',autouse=True)
def pinned_runtime():
    expected=json.loads((ROOT/'docs/evidence/phase6-local-runtime.json').read_text(encoding='utf-8'))
    with httpx.Client(base_url='http://127.0.0.1:11434',trust_env=False,timeout=5) as client:
        assert client.get('/api/version').json()==expected['runtime']['version']
        assert client.get('/api/status').json()['cloud']['disabled'] is True
        model=next(item for item in client.get('/api/tags').json()['models'] if item['name']==os.environ['OLLAMA_TEST_MODEL'])
        assert model['digest']==expected['model']['digest'], 'Model artifact differs from the checkpoint'


def provider():
    return JsonProvider(ProviderConfig(provider='ollama',model=os.environ['OLLAMA_TEST_MODEL'],local_only=True))

@pytest.mark.parametrize('task,skill',[
    ('Read customer OPS-A-001 without opportunities.','research_customer'),
    ('Siapkan quotation untuk OPS-A-001: 2 unit OPS-A-P1 dan 1 unit OPS-A-P2.','prepare_quote'),
])
def test_real_model_emits_supported_typed_intent(task,skill):
    result=asyncio.run(provider().generate(task))
    decision=parse_decision(result.text)
    assert decision.request.skill==skill
    assert result.input_tokens and result.output_tokens
    if skill=='prepare_quote':
        assert decision.request.customer_reference=='OPS-A-001'
        assert [(x.product_code,x.quantity) for x in decision.request.items]==[('OPS-A-P1',2),('OPS-A-P2',1)]

@pytest.mark.parametrize('company,total',[('a',250000),('b',290000)])
def test_live_ai_mcp_proposal_separate_approval_odoo_and_readback(sessions,tmp_path,company,total):
    client=sessions['operator.'+company];prefix='OPS-'+company.upper()
    task=f'Prepare a quotation for {prefix}-001 with 2 units of {prefix}-P1 and 1 unit of {prefix}-P2.'
    task_id=str(uuid4())
    async def invoke():
        async with gateway(client) as mcp:
            return await run(mcp,task=task,provider=provider(),task_id=task_id,trace_dir=tmp_path)
    start=time.monotonic()
    first=asyncio.run(invoke())
    elapsed=round(time.monotonic()-start,3)
    assert first['result']['status']=='awaiting_approval'
    proposal=first['result']['proposal']
    assert Decimal(proposal['preview']['total'])==total
    assert asyncio.run(invoke())==first
    operation=approved_execute(sessions,company,proposal)
    assert operation['status']=='verified'
    assert Decimal(operation['result']['record']['total'])==total
    print(json.dumps({'company':company,'task_id':task_id,'proposal_id':proposal['id'],
        'operation_id':operation['id'],'status':'verified','elapsed_seconds':elapsed,
        'usage':first['usage']},sort_keys=True))


def test_unsupported_action_cannot_dispatch_business_tools(sessions,tmp_path):
    # The small model is not required to produce a correct refusal classification.
    # The application must reject invalid/un-grounded output before business tools.
    async def invoke():
        async with gateway(sessions['operator.a']) as mcp:
            try:
                result=await run(mcp,task='Send an email to all customers.',provider=provider(),trace_dir=tmp_path)
            except AssistantError as error:
                assert str(error) in {'model_output_invalid','unsupported_model_reference'}
                result={'blocked':str(error)}
            else:
                assert result['result']['status']=='needs_input'
                assert result['result']['proposal'] is None
            assert len(mcp.correlations)==1  # identity only; no business read/prepare
            return result
    result=asyncio.run(invoke())
    print(json.dumps({'unsupported_action':result.get('blocked','clarification')},sort_keys=True))
