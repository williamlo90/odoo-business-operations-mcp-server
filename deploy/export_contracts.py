"""Export a reviewable v1 contract snapshot; no database connection is made."""
import json
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
os.environ.setdefault('DATABASE_URL', 'postgresql://contract:unused@localhost/contract_export')
from backend.app import app
from backend.business import QuoteInput, ActivityInput, ApproveInput, ExecuteInput
from backend.contracts import ProposalOut, ApprovalOut, OperationOut

models = (QuoteInput, ActivityInput, ApproveInput, ExecuteInput, ProposalOut, ApprovalOut, OperationOut)
bundle = {'contract_version': '1.0', 'schemas': {model.__name__: model.model_json_schema() for model in models}}
target = root / 'contracts' / 'v1'
target.mkdir(parents=True, exist_ok=True)
(target / 'schemas.json').write_text(json.dumps(bundle, indent=2) + '\n', encoding='utf-8')
openapi = app.openapi()
openapi['paths'] = {key: value for key, value in openapi['paths'].items() if key.startswith('/v1/')}
(target / 'openapi.json').write_text(json.dumps(openapi, indent=2) + '\n', encoding='utf-8')
print('Exported v1 schemas and OpenAPI; review compatibility before committing')
