"""Regenerate Phase 3 schemas without database, network or model dependencies."""
import json
from pathlib import Path

from backend.assistant.contracts import Activity, Decision, Quote, Reconcile, Research, SkillResult, VERSION, provider_schema

ROOT = Path(__file__).resolve().parents[1]
MODELS = {'research_customer': Research, 'prepare_quote': Quote,
          'prepare_crm_activity': Activity, 'reconcile_odoo_write': Reconcile}


def artifacts():
    values = {'contracts/assistant/decision.schema.json': Decision.model_json_schema(),
              'contracts/assistant/provider.schema.json': provider_schema()}
    for name, model in MODELS.items():
        prefix = 'skills/' + name + '/'
        prepares = name in {'prepare_quote', 'prepare_crm_activity'}
        values[prefix + 'input.schema.json'] = model.model_json_schema()
        values[prefix + 'output.schema.json'] = SkillResult.model_json_schema()
        values[prefix + 'manifest.json'] = {
            'name': name, 'version': VERSION, 'owner': 'Odoo Business Operations project',
            'binding': 'backend.assistant.skills:execute_skill',
            'input_schema': 'input.schema.json', 'output_schema': 'output.schema.json',
            'role': ['operator'] if prepares else ['operator', 'approver', 'auditor'],
            'effect': 'application_proposal_only' if prepares else 'read_and_reconcile_audit' if name == 'reconcile_odoo_write' else 'read_only',
            'odoo_write': False, 'human_approval_before_odoo_write': True,
            'request_timeout_seconds': 10, 'task_timeout_seconds': 60,
            'max_domain_calls': 16, 'automatic_write_retries': 0,
            'compatibility': 'Phase 2 HTTP contract 1.0; assistant contract 0.3.0',
        }
    return values


if __name__ == '__main__':
    for relative, value in artifacts().items():
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + '\n', encoding='utf-8', newline='\n')
    print('Exported assistant and skill contracts')
