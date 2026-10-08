"""Domain failure injection with real PostgreSQL and a constrained platform fake."""
import copy
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend import odoo_adapter
from backend.business import fingerprint, matches
from backend.manage import admin_connection


class FakePlatform:
    company = 2
    version = 'v1'
    fault = None
    calls = 0

    def __init__(self):
        self.results = {}

    def call(self, method, **data):
        if method == 'prepare':
            payload = data['payload']
            return {'kind': 'quote', 'company_id': 2, 'customer_id': payload['customer_id'],
                    'currency': 'IDR', 'total': '250000', 'source_version': self.version,
                    'contract_version': '1.0', 'customer_name': 'Synthetic', 'pricelist_id': 3,
                    'pricing_policy': 'list-price-no-tax-v1',
                    'items': [{'product_id': 1, 'name': 'P1', 'quantity': 2, 'unit_price': '100000', 'subtotal': '200000'},
                              {'product_id': 2, 'name': 'P2', 'quantity': 1, 'unit_price': '50000', 'subtotal': '50000'}]}
        if method == 'status':
            if self.fault == 'readback_down':
                raise odoo_adapter.PlatformError('platform_timeout')
            result = copy.deepcopy(self.results.get(data['operation_id']))
            if result and self.fault == 'mismatch':
                result['record']['total'] = '1'
            return result
        if method == 'execute':
            self.calls += 1
            if self.fault == 'before_write':
                raise odoo_adapter.PlatformError('platform_timeout', uncertain=True)
            envelope = data['envelope']
            preview = self.call('prepare', payload=envelope['payload'])
            if fingerprint(preview) != envelope['payload_hash']:
                raise odoo_adapter.PlatformError('stale_proposal')
            record = {key: preview[key] for key in ('kind', 'company_id', 'customer_id', 'currency', 'total')}
            record.update(external_id=100, name='SYNTHETIC', state='draft',
                          items=[{k: v for k,v in line.items() if k != 'name'} for line in preview['items']])
            self.results[envelope['operation_id']] = {'operation_id': envelope['operation_id'],
                'payload_hash': envelope['payload_hash'], 'record': record}
            if self.fault == 'after_write':
                raise odoo_adapter.PlatformError('platform_timeout', uncertain=True)
            return self.results[envelope['operation_id']]
        raise AssertionError(method)


@pytest.fixture
def domain(server, monkeypatch):
    from backend.app import app
    fake = FakePlatform()
    monkeypatch.setenv('OPS_SIGNING_KEY', 'test-signing-key-' * 4)
    monkeypatch.setattr(odoo_adapter, 'adapter_for', lambda tenant: fake)
    with TestClient(app) as client:
        def headers(name):
            r = client.post('/auth/login', json={'username': name, 'password': os.environ['DEMO_PASSWORD']})
            assert r.status_code == 200
            return {'Authorization': 'Bearer ' + r.json()['access_token']}
        yield client, headers('operator.a'), headers('approver.a'), headers('operator.b'), fake


def prepared(domain):
    c, operator, approver, _, fake = domain
    p = c.post('/v1/quotes/prepare', headers=operator, json={'customer_id': 7,
        'items': [{'product_id': 1, 'quantity': 2}, {'product_id': 2, 'quantity': 1}]}).json()
    a = c.post(f"/v1/proposals/{p['id']}/approve", headers=approver, json={'payload_hash': p['payload_hash']})
    assert a.status_code == 201, a.text
    return p, {'approval_id': a.json()['id'], 'idempotency_key': str(uuid4())}


def test_approval_payload_role_tenant_and_actor_controls(domain):
    c, operator, approver, other, fake = domain
    p, body = prepared(domain)
    route = f"/v1/proposals/{p['id']}"
    assert c.post(route + '/approve', headers=operator, json={'payload_hash': p['payload_hash']}).status_code == 403
    assert c.post(route + '/approve', headers=approver, json={'payload_hash': '0' * 64}).status_code == 409
    assert c.get(route, headers=other).status_code == 404
    assert c.post(route + '/execute', headers=other, json=body).status_code == 404
    assert c.post(route + '/execute', headers=operator, json={**body, 'approval_id': str(uuid4())}).status_code == 403
    assert c.post(route + '/execute', headers=operator, json={**body, 'payload': {}}).status_code == 422
    assert fake.calls == 0


def test_expired_and_revoked_approval(domain):
    c, operator, _, _, fake = domain
    p, body = prepared(domain)
    with admin_connection() as conn:
        conn.execute("UPDATE approvals SET expires_at=now()-interval '1 second' WHERE id=%s", (body['approval_id'],))
    r = c.post(f"/v1/proposals/{p['id']}/execute", headers=operator, json=body)
    assert r.status_code == 409 and r.json()['error'] == 'approval_expired'
    p, body = prepared(domain)
    with admin_connection() as conn:
        conn.execute("UPDATE actors SET active=false WHERE username='approver.a'")
    try:
        assert c.post(f"/v1/proposals/{p['id']}/execute", headers=operator, json=body).status_code == 403
    finally:
        with admin_connection() as conn:
            conn.execute("UPDATE actors SET active=true WHERE username='approver.a'")
    assert fake.calls == 0


def test_stale_after_approval_is_failed(domain):
    c, operator, _, _, fake = domain
    p, body = prepared(domain)
    fake.version = 'v2'
    result = c.post(f"/v1/proposals/{p['id']}/execute", headers=operator, json=body).json()
    assert result['status'] == 'failed' and result['error_code'] == 'stale_proposal'
    assert not fake.results


@pytest.mark.parametrize('fault', ['after_write', 'before_write', 'readback_down', 'mismatch'])
def test_unknown_and_mismatch_recovery(domain, fault):
    c, operator, _, _, fake = domain
    p, body = prepared(domain)
    fake.fault = fault
    result = c.post(f"/v1/proposals/{p['id']}/execute", headers=operator, json=body).json()
    assert result['status'] == ('review' if fault == 'mismatch' else 'unknown')
    fake.fault = None
    status = c.get('/v1/operations/' + result['id'], headers=operator).json()
    if fault == 'before_write':
        assert status['status'] == 'unknown'
        status = c.post('/v1/operations/' + result['id'] + '/retry', headers=operator).json()
    assert status['status'] == 'verified'
    assert fake.calls == (2 if fault == 'before_write' else 1)
    assert len(fake.results) == 1


def test_replay_and_conflicting_key(domain):
    c, operator, _, _, fake = domain
    p, body = prepared(domain)
    route = f"/v1/proposals/{p['id']}/execute"
    one = c.post(route, headers=operator, json=body).json()
    two = c.post(route, headers=operator, json=body).json()
    assert one['id'] == two['id'] and two['status'] == 'verified' and fake.calls == 1
    assert c.post(route, headers=operator, json={**body, 'idempotency_key': str(uuid4())}).status_code == 409


def test_malformed_and_injection_input(domain):
    c, operator, _, _, fake = domain
    for payload in ({'customer_id': 7, 'items': [{'product_id': 1, 'quantity': 0}]},
                    {'customer_id': 7, 'items': [], 'model': 'res.users'},
                    {'customer_id': 7, 'items': [{'product_id': 1, 'quantity': True}]},
                    {'customer_id': 7, 'items': [{'product_id': 1, 'quantity': 1, 'price': 1}]}):
        assert c.post('/v1/quotes/prepare', headers=operator, json=payload).status_code == 422
    assert not matches({}, {}, uuid4(), 'bad')


def test_adapter_read_retry_bounded_and_no_write_retry(monkeypatch, tmp_path):
    import httpx
    path = tmp_path / 'connections.json'
    path.write_text('{"test":{"url":"http://odoo:8069","database":"sandbox","company_id":2,"api_key":"not-a-real-key"}}')
    monkeypatch.setenv('ODOO_CONFIG_PATH', str(path))
    counter = []
    real_client = httpx.Client
    def handler(request):
        counter.append(request.url.path)
        return httpx.Response(429, json={'error': 'limited'})
    monkeypatch.setattr(odoo_adapter.httpx, 'Client', lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    adapter = odoo_adapter.OdooAdapter('test')
    with pytest.raises(odoo_adapter.PlatformError) as error:
        adapter.call('catalog')
    assert error.value.code == 'platform_rate_limited' and len(counter) == 3
    counter.clear()
    with pytest.raises(odoo_adapter.PlatformError) as error:
        adapter.call('execute')
    assert error.value.uncertain and len(counter) == 1
    with pytest.raises(odoo_adapter.PlatformError, match='tool_not_allowed'):
        adapter.call('unlink')
