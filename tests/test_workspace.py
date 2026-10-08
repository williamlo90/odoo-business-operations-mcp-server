"""Workspace read model: tenant/role isolation and safe saved-operation recovery."""
from uuid import uuid4

from tests.test_business import domain, prepared


def test_workspace_assets_and_headers(api):
    response = api.get('/')
    assert response.status_code == 200
    assert '<html lang="en">' in response.text
    assert "frame-ancestors 'none'" in response.headers['content-security-policy']
    assert "script-src 'self'" in response.headers['content-security-policy']
    assert response.headers['cache-control'] == 'no-store'
    assert api.get('/workspace/app.js').status_code == 200
    assert 'javascript' in api.get('/workspace/state.mjs').headers['content-type']
    assert api.get('/workspace/../config.py').status_code == 404
    assert api.get('/v1/workspace/proposals').status_code == 401


def test_workspace_scope_and_saved_receipt(domain):
    client, operator, approver, other, fake = domain
    p, body = prepared(domain)
    path = '/v1/workspace/proposals/' + p['id']
    assert client.get(path, headers=other).status_code == 404
    for headers in [operator, approver]:
        result = client.get(path, headers=headers).json()
        assert result['proposal']['id'] == p['id']
        assert result['approval']['id'] == body['approval_id']
        assert result['operation'] is None
        rows = client.get('/v1/workspace/proposals?limit=50', headers=headers).json()['items']
        assert any(row['id'] == p['id'] for row in rows)
    rows = client.get('/v1/workspace/proposals', headers=other).json()['items']
    assert not any(row['id'] == p['id'] for row in rows)
    execution = client.post('/v1/proposals/'+p['id']+'/execute', headers=operator, json=body).json()
    saved = client.get(path, headers=operator).json()['operation']
    assert saved['id'] == execution['id'] and saved['status'] == 'verified'
    assert 'signature' not in saved and 'envelope' not in saved
    assert fake.calls == 1  # Reading the workspace never dispatches an operation.


def test_workspace_pagination_and_input_bounds(domain):
    client, operator, _, _, _ = domain
    prepared(domain)
    prepared(domain)
    first = client.get('/v1/workspace/proposals?limit=1', headers=operator).json()
    assert first['next_offset'] == 1
    second = client.get('/v1/workspace/proposals?limit=1&offset=1', headers=operator).json()
    assert first['items'][0]['id'] != second['items'][0]['id']
    assert client.get('/v1/workspace/proposals?limit=1000', headers=operator).status_code == 422
    assert client.get('/v1/workspace/proposals?offset=-1', headers=operator).status_code == 422
    assert client.get('/v1/workspace/proposals/'+str(uuid4()), headers=operator).status_code == 404
