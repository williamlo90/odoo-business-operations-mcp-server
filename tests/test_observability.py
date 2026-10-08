import json
from test_business import domain, prepared


def test_metrics_never_count_another_tenants_operation(domain):
    client, operator, _, foreign, _ = domain
    before_a = client.get('/v1/metrics',headers=operator).json()
    before_b = client.get('/v1/metrics',headers=foreign).json()
    proposal, body = prepared(domain)
    response = client.post('/v1/proposals/'+proposal['id']+'/execute',headers=operator,json=body)
    assert response.status_code in {200,201} and response.json()['status']=='verified'
    after = client.get('/v1/metrics',headers=operator).json()
    assert after['operations']['verified']==before_a['operations']['verified']+1
    assert after['proposals']==before_a['proposals']+1
    assert client.get('/v1/metrics',headers=foreign).json()==before_b


def test_metrics_are_authenticated_scoped_and_no_record_data(api,login):
    assert api.get('/v1/metrics').status_code == 401
    assert api.get('/v1/metrics',headers=login('worker.a')).status_code == 403
    headers = login('auditor.b')
    response = api.get('/v1/metrics',headers=headers)
    assert response.status_code == 200
    assert set(response.json()) == {'operations','proposals','oldest_unresolved_seconds'}
    assert set(response.json()['operations']) == {'dispatched','unknown','verified','failed','review'}
    assert float(response.headers['X-Downstream-Duration-Ms']) == 0
    assert 'tenant_id' not in response.text and 'password' not in response.text


def test_downstream_timing_has_matching_sanitized_correlation(api,login,server):
    import os
    import pytest
    if os.environ.get('CONNECTED_TESTS') != 'yes':
        pytest.skip('Actual downstream span requires connected sandbox')
    response = api.get('/v1/catalog',headers=login())
    assert response.status_code == 200
    assert float(response.headers['X-Downstream-Duration-Ms']) > 0
    correlation = response.headers['X-Correlation-ID']
    events = []
    for line in server['log'].read_text().splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if value.get('correlation_id') == correlation:
            events.append(value)
    assert any(e['event']=='odoo_call' and e['method']=='catalog' for e in events)
    assert all(not {'payload','token','url','customer','signature'}.intersection(e) for e in events)
