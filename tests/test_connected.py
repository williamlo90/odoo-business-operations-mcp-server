"""Connected Odoo tests; only the dedicated synthetic sandbox is allowed."""
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
import psycopg
from psycopg.conninfo import conninfo_to_dict

from backend.manage import admin_connection
from backend import odoo_adapter

pytestmark = pytest.mark.skipif(os.environ.get('CONNECTED_TESTS') != 'yes', reason='Requires local Odoo sandbox')


def sandbox_db():
    uri = os.environ['ODOO_TEST_DATABASE_URL']
    assert conninfo_to_dict(uri)['dbname'] == 'odoo_ops_sandbox'
    conn = psycopg.connect(uri)
    assert conn.execute('SELECT current_database()').fetchone()[0] == 'odoo_ops_sandbox'
    return conn


@pytest.fixture
def connected(api, login):
    operator, approver = login(), login('approver.a')
    info = api.get('/v1/odoo/info', headers=operator)
    assert info.status_code == 200 and info.json()['api'] == 'JSON-2'
    adapter = odoo_adapter.OdooAdapter('00000000-0000-0000-0000-000000000001')
    assert adapter.database == 'odoo_ops_sandbox'
    customers = api.get('/v1/customers', headers=operator).json()
    catalog = api.get('/v1/catalog', headers=operator).json()['items']
    customer = next(r for r in customers['items'] if r['reference'] == 'OPS-A-001')
    products = {r['code']: r['id'] for r in catalog}
    return operator, approver, customer, products


def quote(api, connected):
    operator, approver, customer, products = connected
    response = api.post('/v1/quotes/prepare', headers=operator, json={'customer_id': customer['id'],
        'items': [{'product_id': products['OPS-A-P1'], 'quantity': 2}, {'product_id': products['OPS-A-P2'], 'quantity': 1}]})
    assert response.status_code == 201, response.text
    p = response.json()
    assert Decimal(p['preview']['total']) == 250000
    a = api.post(f"/v1/proposals/{p['id']}/approve", headers=approver, json={'payload_hash': p['payload_hash']})
    assert a.status_code == 201, a.text
    return p, {'approval_id': a.json()['id'], 'idempotency_key': str(uuid4())}


def test_connected_quote_concurrency_and_direct_replay(api, connected):
    operator = connected[0]
    p, body = quote(api, connected)
    route = f"/v1/proposals/{p['id']}/execute"
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: api.post(route, headers=operator, json=body), range(4)))
    assert all(r.status_code == 200 for r in responses), [r.text for r in responses]
    ids = {r.json()['id'] for r in responses}
    assert len(ids) == 1
    ident = ids.pop()
    r = api.get('/v1/operations/' + ident, headers=operator).json()
    assert r['status'] == 'verified', r
    assert Decimal(r['result']['record']['total']) == 250000
    with admin_connection() as conn:
        envelope, signature = conn.execute('SELECT envelope,signature FROM operations WHERE id=%s', (ident,)).fetchone()
    adapter = odoo_adapter.OdooAdapter('00000000-0000-0000-0000-000000000001')
    with ThreadPoolExecutor(max_workers=3) as pool:
        receipts = list(pool.map(lambda _: adapter.call('execute', envelope=envelope, signature=signature), range(3)))
    assert {item['record']['external_id'] for item in receipts} == {r['result']['record']['external_id']}
    with sandbox_db() as conn:
        assert conn.execute('SELECT count(*) FROM ops_operation WHERE operation_id=%s', (ident,)).fetchone()[0] == 1
        assert conn.execute('SELECT count(*) FROM sale_order WHERE client_order_ref=%s', ('ops:' + ident,)).fetchone()[0] == 1
    print(json.dumps({'case': 'connected_quote_concurrent_replay', 'operation_id': ident,
                      'external_id': r['result']['record']['external_id'], 'total': '250000', 'status': 'verified'}))


def test_connected_activity(api, connected):
    operator, approver, _, _ = connected
    with sandbox_db() as conn:
        mail_count = conn.execute('SELECT count(*) FROM mail_mail').fetchone()[0]
    lead = api.get('/v1/opportunities', headers=operator).json()['items'][0]
    r = api.post('/v1/activities/prepare', headers=operator, json={'opportunity_id': lead['id'],
        'assignee_id': lead['owner_id'], 'due_date': '2026-12-01', 'summary': 'Synthetic follow-up ' + str(uuid4())[:8]})
    assert r.status_code == 201, r.text
    p = r.json()
    a = api.post(f"/v1/proposals/{p['id']}/approve", headers=approver, json={'payload_hash': p['payload_hash']})
    assert a.status_code == 201, a.text
    result = api.post(f"/v1/proposals/{p['id']}/execute", headers=operator,
        json={'approval_id': a.json()['id'], 'idempotency_key': str(uuid4())}).json()
    assert result['status'] == 'verified', result
    assert result['result']['record']['opportunity_id'] == lead['id']
    repeated = api.get('/v1/operations/' + result['id'], headers=operator).json()
    assert repeated['result']['record']['external_id'] == result['result']['record']['external_id']
    with sandbox_db() as conn:
        assert conn.execute('SELECT count(*) FROM ops_operation WHERE operation_id=%s', (result['id'],)).fetchone()[0] == 1
        assert conn.execute('SELECT count(*) FROM mail_mail').fetchone()[0] == mail_count


def test_connected_ambiguity_pagination_and_other_company(api, connected, login):
    operator = connected[0]
    first = api.get('/v1/customers', headers=operator, params={'limit': 1}).json()
    assert first['ambiguous'] and len(first['items']) == 1
    second = api.get('/v1/customers', headers=operator, params={'limit': 1, 'after': first['next_cursor'], 'revision': first['revision']}).json()
    assert second['items'][0]['id'] != first['items'][0]['id'] and second['next_cursor'] is None
    other = login('operator.b')
    foreign = api.get('/v1/opportunities', headers=other).json()['items'][0]
    assert api.get('/v1/opportunities/' + str(foreign['id']), headers=operator).status_code == 404
    products = api.get('/v1/catalog', headers=other).json()['items']
    customer = api.get('/v1/customers', headers=other).json()['items'][0]
    p = api.post('/v1/quotes/prepare', headers=other, json={'customer_id': customer['id'],
        'items': [{'product_id': products[0]['id'], 'quantity': 2}, {'product_id': products[1]['id'], 'quantity': 1}]}).json()
    assert Decimal(p['preview']['total']) == 290000
    ap = login('approver.b')
    approval = api.post(f"/v1/proposals/{p['id']}/approve", headers=ap, json={'payload_hash': p['payload_hash']}).json()
    result = api.post(f"/v1/proposals/{p['id']}/execute", headers=other,
                     json={'approval_id': approval['id'], 'idempotency_key': str(uuid4())}).json()
    assert result['status'] == 'verified' and Decimal(result['result']['record']['total']) == 290000
    assert api.get('/v1/operations/' + result['id'], headers=operator).status_code == 404


def test_connected_price_update_race_invalidates_approval(api, connected):
    operator = connected[0]
    p, body = quote(api, connected)
    product = connected[3]['OPS-A-P1']
    with sandbox_db() as conn:
        template, old_price = conn.execute('''SELECT t.id,t.list_price FROM product_template t
            JOIN product_product p ON p.product_tmpl_id=t.id WHERE p.id=%s''', (product,)).fetchone()
    try:
        with sandbox_db() as mutation:
            mutation.execute('UPDATE product_template SET list_price=%s,write_date=now() WHERE id=%s', (old_price + 1, template))
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(api.post, f"/v1/proposals/{p['id']}/execute", headers=operator, json=body)
                time.sleep(0.3)
                assert not future.done(), 'Execution should wait behind the source update transaction'
                mutation.commit()
                response = future.result(timeout=20)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result['status'] == 'failed' and result['error_code'] == 'stale_proposal', result
        with sandbox_db() as conn:
            assert conn.execute('SELECT count(*) FROM sale_order WHERE client_order_ref=%s', ('ops:' + result['id'],)).fetchone()[0] == 0
    finally:
        with sandbox_db() as conn:
            conn.execute('UPDATE product_template SET list_price=%s,write_date=now() WHERE id=%s', (old_price, template))


def test_connected_changed_pagination_detected(api, connected):
    operator, _, customer, _ = connected
    page = api.get('/v1/customers', headers=operator, params={'limit': 1}).json()
    with sandbox_db() as conn:
        conn.execute('UPDATE res_partner SET write_date=now() WHERE id=%s', (customer['id'],))
    result = api.get('/v1/customers', headers=operator, params={'after': page['next_cursor'], 'revision': page['revision']})
    assert result.status_code == 409 and result.json()['error'] == 'source_changed'


def test_connected_readback_detects_changed_draft(api, connected):
    p, body = quote(api, connected)
    op = connected[0]
    result = api.post(f"/v1/proposals/{p['id']}/execute", headers=op, json=body).json()
    assert result['status'] == 'verified', result
    ident = result['result']['record']['external_id']
    with sandbox_db() as conn:
        conn.execute('UPDATE sale_order SET amount_total=amount_total+1 WHERE id=%s', (ident,))
    status = api.get('/v1/operations/' + result['id'], headers=op).json()
    assert status['status'] == 'review' and status['error_code'] == 'readback_mismatch'


def test_connected_connector_cannot_bypass_or_forge_signature(api, connected):
    adapter = odoo_adapter.OdooAdapter('00000000-0000-0000-0000-000000000001')
    with httpx.Client(timeout=10, trust_env=False) as client:
        headers = {'Authorization': 'Bearer ' + adapter.key, 'X-Odoo-Database': adapter.database}
        response = client.post(adapter.url + '/json/2/sale.order/create', headers=headers,
                               json={'vals_list': [{'partner_id': connected[2]['id']}]})
        assert response.status_code != 200
        private = client.post(adapter.url + '/json/2/ops.bridge/_execute_atomic', headers=headers,
                              json={'envelope': {}, 'signature': '0' * 64})
        assert private.status_code != 200
    with pytest.raises(odoo_adapter.PlatformError, match='invalid_signature'):
        adapter.call('execute', envelope={}, signature='0' * 64)
    adapter.key = 'invalid-test-credential'
    with pytest.raises(odoo_adapter.PlatformError, match='platform_credentials_expired'):
        adapter.call('info')


def test_connected_unsupported_pricing_and_inactive_product(api, connected):
    operator, _, customer, products = connected
    product = products['OPS-A-P1']
    payload = {'customer_id': customer['id'], 'items': [{'product_id': product, 'quantity': 1}]}
    with sandbox_db() as conn:
        template = conn.execute('SELECT product_tmpl_id FROM product_product WHERE id=%s', (product,)).fetchone()[0]
        plist, currency = conn.execute('''SELECT p.id,p.currency_id FROM product_pricelist p JOIN ops_connection c
            ON c.pricelist_id=p.id WHERE c.tenant=%s''', ('00000000-0000-0000-0000-000000000001',)).fetchone()
        foreign_currency = conn.execute("SELECT id FROM res_currency WHERE name='EUR'").fetchone()[0]
        conn.execute('UPDATE product_pricelist SET currency_id=%s WHERE id=%s', (foreign_currency, plist))
    try:
        response = api.post('/v1/quotes/prepare', headers=operator, json=payload)
        assert response.status_code == 422 and response.json()['error'] == 'unsupported_pricing'
    finally:
        with sandbox_db() as conn:
            conn.execute('UPDATE product_pricelist SET currency_id=%s WHERE id=%s', (currency, plist))
    with sandbox_db() as conn:
        conn.execute('UPDATE product_product SET active=false WHERE id=%s', (product,))
    try:
        response = api.post('/v1/quotes/prepare', headers=operator, json=payload)
        assert response.status_code in {404, 422}
    finally:
        with sandbox_db() as conn:
            conn.execute('UPDATE product_product SET active=true WHERE id=%s', (product,))


def test_connected_lost_response_reconciles_without_second_write(server, monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app import app
    original = odoo_adapter.OdooAdapter.call
    writes = []
    def dropped(self, method, **kwargs):
        result = original(self, method, **kwargs)
        if method == 'execute':
            writes.append(result)
            raise odoo_adapter.PlatformError('platform_timeout', uncertain=True)
        return result
    with TestClient(app) as c:
        def login(name):
            return {'Authorization': 'Bearer ' + c.post('/auth/login', json={'username': name, 'password': os.environ['DEMO_PASSWORD']}).json()['access_token']}
        op, ap = login('operator.a'), login('approver.a')
        customer = c.get('/v1/customers', headers=op).json()['items'][0]
        catalog = c.get('/v1/catalog', headers=op).json()['items']
        p = c.post('/v1/quotes/prepare', headers=op, json={'customer_id': customer['id'], 'items': [{'product_id': catalog[0]['id'], 'quantity': 1}]}).json()
        a = c.post(f"/v1/proposals/{p['id']}/approve", headers=ap, json={'payload_hash': p['payload_hash']}).json()
        monkeypatch.setattr(odoo_adapter.OdooAdapter, 'call', dropped)
        r = c.post(f"/v1/proposals/{p['id']}/execute", headers=op, json={'approval_id': a['id'], 'idempotency_key': str(uuid4())}).json()
        assert r['status'] == 'unknown', r
        recovered = c.get('/v1/operations/' + r['id'], headers=op).json()
        assert recovered['status'] == 'verified' and len(writes) == 1
        assert recovered['result']['record']['external_id'] == writes[0]['record']['external_id']
