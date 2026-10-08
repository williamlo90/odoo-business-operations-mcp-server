import json
from pathlib import Path

from backend.business import QuoteInput, ActivityInput, ApproveInput, ExecuteInput
from backend.contracts import ProposalOut, ApprovalOut, OperationOut


def test_v1_schema_compatibility_snapshot():
    path = Path(__file__).parents[1] / 'contracts/v1/schemas.json'
    expected = json.loads(path.read_text())
    assert expected['contract_version'] == '1.0'
    models = (QuoteInput, ActivityInput, ApproveInput, ExecuteInput, ProposalOut, ApprovalOut, OperationOut)
    assert expected['schemas'] == {model.__name__: model.model_json_schema() for model in models}


def test_consumer_fixtures_use_supported_inputs():
    path = Path(__file__).parents[1] / 'contracts/v1/consumer-fixtures.json'
    fixtures = json.loads(path.read_text())
    assert len(fixtures['consumers']) == 3
    QuoteInput.model_validate(fixtures['quote_request'])
    ActivityInput.model_validate(fixtures['activity_request'])
    assert int(fixtures['expected_synthetic_company_a_total']) == 2 * 100000 + 50000
