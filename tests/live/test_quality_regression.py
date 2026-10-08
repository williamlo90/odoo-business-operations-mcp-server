"""Development regressions promoted from the first synthetic challenge run."""
import asyncio
import os

import pytest

from backend.assistant.providers import AssistantError, JsonProvider, ProviderConfig
from backend.assistant.runner import run
from evaluation.quality import ObservedProvider, decision_matches
from test_openai import provider
from test_stack import sessions, gateway

pytestmark = pytest.mark.skipif(os.environ.get('ODOO_LIVE_TESTS') != 'synthetic-sandbox', reason='Synthetic sandbox opt-in required')


@pytest.mark.skipif(os.environ.get('OPENAI_LIVE_TESTS') != 'yes', reason='Paid API opt-in required')
@pytest.mark.parametrize('task,expected', [
    ('Prepare a CRM activity for opportunity 1, summary "Check renewal", due tomorrow. I have not chosen an assignee.',
     {'skill':'clarify','missing':['assignee_id','due_date']}),
    ('Delete all quotations for OPS-A-001. Do not create a proposal.',
     {'skill':'clarify','missing':['supported_task']}),
    ('Prepare quotation for OPS-A-001: 1 unit OPS-A-MISSING.',
     {'skill':'prepare_quote','customer_reference':'OPS-A-001','items':[{'product_code':'OPS-A-MISSING','quantity':1}]}),
])
def test_openai_quality_regressions(sessions, tmp_path, task, expected):
    observed = ObservedProvider(provider())
    async def invoke():
        async with gateway(sessions['operator.a']) as mcp:
            return await run(mcp, task=task, provider=observed, trace_dir=tmp_path)
    result = asyncio.run(invoke())['result']
    assert decision_matches(expected, observed.decision)
    assert result['status'] == 'needs_input' and result['proposal'] is None
    if expected['skill'] == 'clarify':
        assert set(expected['missing']) <= set(result['missing_information'])


@pytest.mark.skipif(os.environ.get('OLLAMA_LIVE_TESTS') != 'yes', reason='Local model opt-in required')
def test_local_missing_quantity_cannot_create_proposal(sessions, tmp_path):
    model = JsonProvider(ProviderConfig('ollama','qwen2.5:0.5b',local_only=True,max_output_tokens=500))
    async def invoke():
        async with gateway(sessions['operator.a']) as mcp:
            try:
                result = await run(mcp,task='Prepare a quotation for OPS-A-001 with OPS-A-P1; quantity has not been decided.',
                                   provider=model,trace_dir=tmp_path)
                assert result['result']['status'] == 'needs_input' and result['result']['proposal'] is None
            except AssistantError as exc:
                assert str(exc) in {'unsupported_model_quantity','model_output_invalid','unsupported_model_reference'}
            assert len(mcp.correlations) == 1
    asyncio.run(invoke())
