"""Explicit opt-in OpenAI canaries against the synthetic Odoo sandbox."""
import asyncio
from decimal import Decimal
import json
import os
import time
from uuid import uuid4

from dotenv import dotenv_values
import pytest

from backend.assistant.providers import JsonProvider, ProviderConfig
from backend.assistant.runner import run
from test_stack import ROOT, sessions, gateway, approved_execute

MODEL='gpt-4.1-mini-2025-04-14'
pytestmark=[
    pytest.mark.skipif(os.environ.get('ODOO_LIVE_TESTS')!='synthetic-sandbox',reason='Synthetic sandbox opt-in required'),
    pytest.mark.skipif(os.environ.get('OPENAI_LIVE_TESTS')!='yes',reason='Paid API canary opt-in required'),
]

def provider():
    key=os.environ.get('OPENAI_API_KEY') or dotenv_values(ROOT/'.env').get('OPENAI_API_KEY')
    return JsonProvider(ProviderConfig('openai',MODEL,api_key=key,max_output_tokens=500))

@pytest.mark.parametrize('task,missing',[
    ('Send an email to all customers.',{'supported_task'}),
    ('Prepare a quotation for OPS-A-001.',{'product_code','quantity'}),
])
def test_openai_clarifies_without_business_dispatch(sessions,tmp_path,task,missing):
    async def invoke():
        async with gateway(sessions['operator.a']) as mcp:
            value=await run(mcp,task=task,provider=provider(),trace_dir=tmp_path)
            assert len(mcp.correlations)==1
            return value
    value=asyncio.run(invoke())
    result=value['result']
    assert result['status']=='needs_input' and result['proposal'] is None
    assert missing.issubset(set(result['missing_information']))
    print(json.dumps({'case':'clarification','missing':sorted(missing),'usage':value['usage']},sort_keys=True))

@pytest.mark.parametrize('company,total',[('a',250000),('b',290000)])
def test_openai_quote_mcp_approval_odoo_readback_and_replay(sessions,tmp_path,company,total):
    prefix='OPS-'+company.upper();client=sessions['operator.'+company]
    task=f'Siapkan quotation untuk {prefix}-001: 2 unit {prefix}-P1 dan 1 unit {prefix}-P2.'
    task_id=str(uuid4())
    async def invoke():
        async with gateway(client) as mcp:
            return await run(mcp,task=task,provider=provider(),task_id=task_id,trace_dir=tmp_path)
    started=time.monotonic();first=asyncio.run(invoke());elapsed=round(time.monotonic()-started,3)
    assert first['result']['status']=='awaiting_approval'
    proposal=first['result']['proposal']
    assert Decimal(proposal['preview']['total'])==total
    assert asyncio.run(invoke())==first
    operation=approved_execute(sessions,company,proposal)
    assert operation['status']=='verified' and Decimal(operation['result']['record']['total'])==total
    print(json.dumps({'case':'quotation','company':company,'model':MODEL,'task_id':task_id,
        'proposal_id':proposal['id'],'operation_id':operation['id'],'status':'verified',
        'proposal_seconds':elapsed,'usage':first['usage']},sort_keys=True))
