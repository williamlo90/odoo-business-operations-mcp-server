"""Reusable deterministic skills. HTTP domain services remain authoritative."""
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError

from backend.assistant.contracts import Activity, Clarify, Fact, Quote, Reconcile, Research, SkillResult
from backend.assistant.providers import AssistantError
from backend.contracts import OperationOut, ProposalOut

SKILL_VERSION = '0.3.0'


def sourced(source, row, fields):
    try:
        return Fact(source=source, record={key: row[key] for key in fields})
    except (KeyError, TypeError):
        raise AssistantError('domain_response_malformed') from None


def customer_fact(row):
    return sourced('odoo:res.partner:' + str(row['id']), row,
                   ('id', 'name', 'reference', 'company_id', 'version'))


async def resolve_customer(gateway, reference):
    rows = await gateway.customers(reference)
    exact = [row for row in rows if row.get('reference') == reference]
    if len(exact) == 1:
        return exact[0], None
    return None, SkillResult(status='needs_input', reason='exact_customer_reference_required',
                             missing_information=['customer_reference'],
                             facts=[customer_fact(row) for row in rows[:20]])


def checked_proposal(data, gateway, kind, payload):
    try:
        proposal = ProposalOut.model_validate(data)
        if (str(proposal.tenant_id) != gateway.identity['tenant_id']
                or str(proposal.actor_id) != gateway.identity['id']
                or proposal.kind != kind or proposal.payload != payload
                or proposal.preview.kind != kind):
            raise ValueError()
        preview = proposal.preview.model_dump()
        if kind == 'quote':
            if preview['customer_id'] != payload['customer_id']:
                raise ValueError()
            actual = {line['product_id']: line['quantity'] for line in preview['items']}
            expected = {line['product_id']: line['quantity'] for line in payload['items']}
            if actual != expected or len(preview['items']) != len(payload['items']):
                raise ValueError()
            if any(Decimal(line['subtotal']) != Decimal(line['unit_price']) * line['quantity']
                   for line in preview['items']):
                raise ValueError()
            if Decimal(preview['total']) != sum(Decimal(line['subtotal']) for line in preview['items']):
                raise ValueError()
        elif any(preview[key] != value for key, value in payload.items()):
            raise ValueError()
        return proposal.model_dump(mode='json')
    except (ValidationError, ValueError, KeyError, TypeError, InvalidOperation):
        raise AssistantError('proposal_response_mismatch') from None


async def execute_skill(request, gateway) -> SkillResult:
    # Every caller, including a future worker, must use an authenticated gateway.
    if gateway.identity is None:
        await gateway.authenticate()
    if isinstance(request, Clarify):
        return SkillResult(status='needs_input', reason='required_information_missing',
                           missing_information=request.missing)
    if isinstance(request, (Quote, Activity)) and gateway.identity['role'] != 'operator':
        raise AssistantError('domain_access_denied')
    if isinstance(request, (Research, Quote)):
        customer, clarification = await resolve_customer(gateway, request.customer_reference)
        if clarification:
            return clarification
        facts = [customer_fact(customer)]
        if isinstance(request, Research):
            if request.include_opportunities:
                data = await gateway.opportunities()
                for row in data['items']:
                    if row['customer_id'] == customer['id']:
                        facts.append(sourced('odoo:crm.lead:' + str(row['id']), row,
                            ('id', 'company_id', 'name', 'customer_id', 'owner_id', 'stage', 'version')))
            return SkillResult(status='read', reason='source_records_retrieved', facts=facts)
        catalog = await gateway.catalog()
        items = []
        for line in request.items:
            matches = [item for item in catalog['items'] if item['code'] == line.product_code]
            if len(matches) != 1:
                return SkillResult(status='needs_input', reason='exact_product_code_required',
                                   missing_information=['product_code'], facts=facts)
            items.append({'product_id': matches[0]['id'], 'quantity': line.quantity})
        payload = {'customer_id': customer['id'], 'items': items}
        value = await gateway.prepare('quotes', payload)
        proposal = checked_proposal(value, gateway, 'quote', payload)
        return SkillResult(status='awaiting_approval', reason='human_approval_required',
                           facts=facts, proposal=proposal)
    if isinstance(request, Activity):
        lead = await gateway.opportunity(request.opportunity_id)
        if lead['id'] != request.opportunity_id:
            raise AssistantError('domain_response_malformed')
        payload = request.model_dump(exclude={'skill'})
        value = await gateway.prepare('activities', payload)
        proposal = checked_proposal(value, gateway, 'activity', payload)
        return SkillResult(status='awaiting_approval', reason='human_approval_required',
            proposal=proposal, facts=[sourced('odoo:crm.lead:' + str(lead['id']), lead,
                ('id', 'name', 'company_id', 'customer_id', 'owner_id', 'stage', 'version'))])
    if isinstance(request, Reconcile):
        try:
            operation = OperationOut.model_validate(await gateway.operation(request.operation_id))
            if str(operation.id) != request.operation_id or str(operation.tenant_id) != gateway.identity['tenant_id']:
                raise ValueError()
            if operation.status == 'verified' and (operation.result is None or operation.result.operation_id != operation.id):
                raise ValueError()
        except (ValidationError, ValueError):
            raise AssistantError('operation_response_mismatch') from None
        return SkillResult(status=operation.status, reason='domain_operation_status',
                           operation=operation.model_dump(mode='json'))
    raise AssistantError('invalid_skill')
