import hashlib
import hmac
import json
import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from psycopg.types.json import Jsonb

from backend.db import connection
from backend import odoo_adapter
from backend.contracts import ProposalOut, ApprovalOut, OperationOut, Receipt
from pydantic import ValidationError


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def fail(code, status=409):
    raise HTTPException(status, code)


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Item(Strict):
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=1000)


class QuoteInput(Strict):
    customer_id: int = Field(gt=0)
    items: list[Item] = Field(min_length=1, max_length=20)


class ActivityInput(Strict):
    opportunity_id: int = Field(gt=0)
    assignee_id: int = Field(gt=0)
    due_date: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    summary: str = Field(min_length=1, max_length=120, pattern=r'^[^<>]+$')


class ApproveInput(Strict):
    payload_hash: str = Field(pattern=r'^[a-f0-9]{64}$')


class ExecuteInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    approval_id: UUID
    idempotency_key: UUID


def audit(conn, current, event, resource=None):
    conn.execute('INSERT INTO business_events(id,tenant_id,actor_id,event,resource_id) VALUES (%s,%s,%s,%s,%s)',
                 (uuid4(), current['tenant_id'], current['id'], event, resource))


def denied(current, code, status=409):
    # Separate transaction survives rollback of the rejected business request.
    with connection() as conn:
        audit(conn, current, 'execution.denied_' + code)
    fail(code, status)


def proposal(conn, ident, current):
    row = conn.execute('SELECT * FROM proposals WHERE id=%s AND tenant_id=%s', (ident, current['tenant_id'])).fetchone()
    if not row:
        fail('proposal_not_found', 404)
    return row


def operation(conn, ident, current):
    row = conn.execute('SELECT * FROM operations WHERE id=%s AND tenant_id=%s', (ident, current['tenant_id'])).fetchone()
    if not row:
        fail('operation_not_found', 404)
    return row


def public_operation(row):
    return {key: value for key, value in row.items() if key not in {'envelope', 'signature'}}


def matches(preview, receipt, operation_id, payload_hash):
    try:
        if receipt['operation_id'] != str(operation_id) or receipt['payload_hash'] != payload_hash:
            return False
        record = receipt['record']
        if record['company_id'] != preview['company_id'] or record['kind'] != preview['kind']:
            return False
        if preview['kind'] == 'quote':
            if record['state'] != 'draft' or record['customer_id'] != preview['customer_id'] or record['currency'] != preview['currency']:
                return False
            if Decimal(record['total']) != Decimal(preview['total']) or len(record['items']) != len(preview['items']):
                return False
            expected = sorted(preview['items'], key=lambda line: line['product_id'])
            actual = sorted(record['items'], key=lambda line: line['product_id'])
            return all(a['product_id'] == b['product_id'] and all(Decimal(str(a[field])) == Decimal(str(b[field]))
                for field in ('quantity', 'unit_price', 'subtotal')) for a, b in zip(expected, actual))
        return all(record[key] == preview[key] for key in ('opportunity_id', 'assignee_id', 'due_date', 'summary'))
    except (KeyError, TypeError, ValueError, InvalidOperation):
        return False


def reconcile(row, current, adapter):
    try:
        receipt = adapter.call('status', operation_id=str(row['id']))
        state, error = ('unknown', 'awaiting_platform_result') if receipt is None else ('verified', None)
        if receipt is not None:
            try:
                Receipt.model_validate(receipt)
            except ValidationError:
                receipt, state, error = None, 'review', 'readback_malformed'
        if receipt is not None:
            with connection() as conn:
                p = proposal(conn, row['proposal_id'], current)
            if not matches(p['preview'], receipt, row['id'], p['payload_hash']):
                state, error = 'review', 'readback_mismatch'
    except odoo_adapter.PlatformError as exc:
        state, error, receipt = 'unknown', exc.code, None
    with connection() as conn:
        row = conn.execute('''UPDATE operations SET status=%s,error_code=%s,result=%s,updated_at=now()
            WHERE id=%s AND tenant_id=%s RETURNING *''',
            (state, error, Jsonb(receipt) if receipt else None, row['id'], current['tenant_id'])).fetchone()
        audit(conn, current, 'operation.' + state, row['id'])
    return public_operation(row)


def dispatch(row, current, adapter):
    try:
        adapter.call('execute', envelope=row['envelope'], signature=row['signature'])
    except odoo_adapter.PlatformError as exc:
        with connection() as conn:
            row = conn.execute('''UPDATE operations SET status=%s,error_code=%s,updated_at=now()
                WHERE id=%s RETURNING *''', ('unknown' if exc.uncertain else 'failed', exc.code, row['id'])).fetchone()
            audit(conn, current, 'operation.' + row['status'], row['id'])
        return public_operation(row)
    return reconcile(row, current, adapter)


def build_router(actor, reader, operator):
    router = APIRouter(prefix='/v1', tags=['business-v1'])

    def approver(current=Depends(actor)):
        if current['role'] != 'approver':
            with connection() as conn:
                audit(conn, current, 'approval.denied_role')
            fail('role_not_permitted', 403)
        return current

    @router.get('/odoo/info')
    def info(current=Depends(reader)):
        return odoo_adapter.adapter_for(current['tenant_id']).call('info')

    @router.get('/customers')
    def customers(current=Depends(reader), query: str = Query(default='', max_length=100),
                  after: int = Query(default=0, ge=0), limit: int = Query(default=20, ge=1, le=100),
                  revision: str | None = Query(default=None, pattern=r'^[a-f0-9]{64}$')):
        return odoo_adapter.adapter_for(current['tenant_id']).call('customers', query=query, after=after, limit=limit, revision=revision)

    @router.get('/catalog')
    def catalog(current=Depends(reader)):
        return odoo_adapter.adapter_for(current['tenant_id']).call('catalog')

    @router.get('/opportunities')
    def opportunities(current=Depends(reader)):
        return odoo_adapter.adapter_for(current['tenant_id']).call('opportunities')

    @router.get('/opportunities/{opportunity_id}')
    def opportunity(opportunity_id: int, current=Depends(reader)):
        return odoo_adapter.adapter_for(current['tenant_id']).call('opportunity', opportunity_id=opportunity_id)

    def prepare(kind, payload, current):
        adapter = odoo_adapter.adapter_for(current['tenant_id'])
        preview = adapter.call('prepare', kind=kind, payload=payload)
        if not isinstance(preview, dict) or preview.get('kind') != kind or preview.get('company_id') != adapter.company:
            fail('invalid_platform_preview', 502)
        # Independently validate arithmetic; the model never supplies price or total.
        if kind == 'quote':
            try:
                total = sum(Decimal(line['unit_price']) * line['quantity'] for line in preview['items'])
                expected_items = sorted((line['product_id'], line['quantity']) for line in payload['items'])
                actual_items = sorted((line['product_id'], line['quantity']) for line in preview['items'])
                if (total != Decimal(preview['total']) or expected_items != actual_items
                        or preview['customer_id'] != payload['customer_id'] or preview['currency'] != 'IDR'
                        or any(Decimal(line['subtotal']) != Decimal(line['unit_price']) * line['quantity'] for line in preview['items'])):
                    fail('invalid_platform_total', 502)
            except (KeyError, TypeError, InvalidOperation):
                fail('invalid_platform_preview', 502)
        elif any(preview.get(key) != value for key, value in payload.items()):
            fail('invalid_platform_preview', 502)
        with connection() as conn:
            row = conn.execute('''INSERT INTO proposals(id,tenant_id,actor_id,kind,payload,preview,payload_hash,contract_version,expires_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,'1.0',%s) RETURNING *''',
                (uuid4(), current['tenant_id'], current['id'], kind, Jsonb(payload), Jsonb(preview), fingerprint(preview),
                 datetime.now(timezone.utc) + timedelta(minutes=30))).fetchone()
            audit(conn, current, 'proposal.prepared', row['id'])
        return row

    @router.post('/quotes/prepare', status_code=201, response_model=ProposalOut)
    def quote(data: QuoteInput, current=Depends(operator)):
        return prepare('quote', data.model_dump(), current)

    @router.post('/activities/prepare', status_code=201, response_model=ProposalOut)
    def activity(data: ActivityInput, current=Depends(operator)):
        try:
            date.fromisoformat(data.due_date)
        except ValueError:
            fail('invalid_due_date', 422)
        return prepare('activity', data.model_dump(), current)

    @router.get('/proposals/{proposal_id}', response_model=ProposalOut)
    def get_proposal(proposal_id: UUID, current=Depends(reader)):
        with connection() as conn:
            return proposal(conn, proposal_id, current)

    @router.post('/proposals/{proposal_id}/approve', status_code=201, response_model=ApprovalOut)
    def approve(proposal_id: UUID, data: ApproveInput, current=Depends(approver)):
        with connection() as conn:
            p = proposal(conn, proposal_id, current)
        error = None
        if p['actor_id'] == current['id']:
            error = 'self_approval'
        elif data.payload_hash != p['payload_hash']:
            error = 'payload_mismatch'
        elif p['expires_at'] <= datetime.now(timezone.utc):
            error = 'proposal_expired'
        else:
            fresh = odoo_adapter.adapter_for(current['tenant_id']).call('prepare', kind=p['kind'], payload=p['payload'])
            if fingerprint(fresh) != p['payload_hash']:
                error = 'stale_proposal'
        if error:
            with connection() as conn:
                audit(conn, current, 'approval.denied_' + error, p['id'])
            fail(error)
        with connection() as conn:
            row = conn.execute('''INSERT INTO approvals(id,tenant_id,proposal_id,approver_id,payload_hash,expires_at)
                VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (proposal_id) DO NOTHING RETURNING *''',
                (uuid4(), current['tenant_id'], p['id'], current['id'], p['payload_hash'], p['expires_at'])).fetchone()
            if not row:
                row = conn.execute('SELECT * FROM approvals WHERE proposal_id=%s', (p['id'],)).fetchone()
            audit(conn, current, 'approval.granted', p['id'])
        return row

    @router.post('/proposals/{proposal_id}/execute', response_model=OperationOut)
    def execute(proposal_id: UUID, data: ExecuteInput, current=Depends(operator)):
        adapter = odoo_adapter.adapter_for(current['tenant_id'])
        with connection() as conn:
            # Serialize creation of a single durable operation per proposal.
            conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))', (str(current['tenant_id']),))
            p = proposal(conn, proposal_id, current)
            if p['actor_id'] != current['id']:
                denied(current, 'proposal_actor_mismatch', 403)
            existing = conn.execute('SELECT * FROM operations WHERE proposal_id=%s', (p['id'],)).fetchone()
            if existing:
                if existing['idempotency_key'] != data.idempotency_key or existing['approval_id'] != data.approval_id:
                    denied(current, 'idempotency_conflict')
                return public_operation(existing)
            approval = conn.execute('''SELECT ap.* FROM approvals ap JOIN actors a ON a.id=ap.approver_id
                WHERE ap.id=%s AND ap.proposal_id=%s AND ap.tenant_id=%s AND a.active AND a.role='approver' ''',
                (data.approval_id, p['id'], current['tenant_id'])).fetchone()
            if not approval or approval['payload_hash'] != p['payload_hash'] or approval['approver_id'] == current['id']:
                denied(current, 'valid_approval_required', 403)
            if approval['expires_at'] <= datetime.now(timezone.utc):
                denied(current, 'approval_expired')
            if conn.execute('SELECT 1 FROM operations WHERE tenant_id=%s AND idempotency_key=%s',
                            (current['tenant_id'], data.idempotency_key)).fetchone():
                denied(current, 'idempotency_conflict')
            ident = uuid4()
            envelope = {'contract_version': '1.0', 'operation_id': str(ident), 'tenant': str(current['tenant_id']),
                'company_id': adapter.company, 'actor_id': str(current['id']), 'approver_id': str(approval['approver_id']),
                'approval_id': str(approval['id']), 'payload_hash': p['payload_hash'], 'kind': p['kind'], 'payload': p['payload'],
                'expires_at': approval['expires_at'].timestamp()}
            key = os.environ.get('OPS_SIGNING_KEY', '')
            if len(key) < 32:
                fail('signing_not_configured', 503)
            signature = hmac.new(key.encode(), canonical(envelope).encode(), hashlib.sha256).hexdigest()
            row = conn.execute('''INSERT INTO operations(id,tenant_id,proposal_id,approval_id,idempotency_key,envelope,signature,status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,'dispatched') RETURNING *''',
                (ident, current['tenant_id'], p['id'], approval['id'], data.idempotency_key, Jsonb(envelope), signature)).fetchone()
            audit(conn, current, 'operation.dispatched', ident)
        return dispatch(row, current, adapter)

    @router.get('/operations/{operation_id}', response_model=OperationOut)
    def status(operation_id: UUID, current=Depends(reader)):
        with connection() as conn:
            row = operation(conn, operation_id, current)
        if row['status'] == 'failed':
            return public_operation(row)
        return reconcile(row, current, odoo_adapter.adapter_for(current['tenant_id']))

    @router.post('/operations/{operation_id}/retry', response_model=OperationOut)
    def retry(operation_id: UUID, current=Depends(operator)):
        adapter = odoo_adapter.adapter_for(current['tenant_id'])
        with connection() as conn:
            row = operation(conn, operation_id, current)
            p = proposal(conn, row['proposal_id'], current)
            if p['actor_id'] != current['id']:
                fail('proposal_actor_mismatch', 403)
            if row['status'] in {'failed', 'review'}:
                return public_operation(row)
        outcome = reconcile(row, current, adapter)
        if outcome['status'] != 'unknown' or outcome['error_code'] != 'awaiting_platform_result':
            return outcome
        with connection() as conn:
            approval = conn.execute('''SELECT ap.id FROM approvals ap JOIN actors a ON a.id=ap.approver_id
                WHERE ap.id=%s AND ap.expires_at>now() AND a.active AND a.role='approver' ''', (row['approval_id'],)).fetchone()
            if not approval:
                fail('valid_approval_required', 403)
            row = conn.execute('''UPDATE operations SET status='dispatched',attempts=attempts+1,updated_at=now()
                WHERE id=%s AND status='unknown' AND attempts<3 RETURNING *''', (row['id'],)).fetchone()
            if not row:
                fail('retry_limit_or_in_progress')
            audit(conn, current, 'operation.retried', row['id'])
        return dispatch(row, current, adapter)

    return router
