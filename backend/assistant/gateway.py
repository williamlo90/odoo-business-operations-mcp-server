"""Fixed Phase 2 HTTP capabilities, bound to a caller's existing session."""
import json
from urllib.parse import urlsplit
from uuid import UUID

import httpx

from backend.assistant.providers import AssistantError


class DomainGateway:
    def __init__(self, base_url: str, token: str, transport=None):
        url = urlsplit(base_url)
        if (url.scheme != 'http' or url.hostname not in {'127.0.0.1', 'localhost'}
                or url.username or url.password or url.query or url.fragment or url.path not in {'', '/'}):
            raise AssistantError('local_domain_url_required')
        if not token or len(token) > 256:
            raise AssistantError('session_required')
        self._base_url, self._token, self._transport = base_url.rstrip('/'), token, transport
        self._remaining = 16
        self.identity = None

    async def _request(self, method, path, *, params=None, body=None):
        self._remaining -= 1
        if self._remaining < 0:
            raise AssistantError('domain_call_limit')
        try:
            async with httpx.AsyncClient(transport=self._transport, trust_env=False,
                                         timeout=10, follow_redirects=False) as client:
                async with client.stream(method, self._base_url + path, params=params, json=body,
                                         headers={'Authorization': 'Bearer ' + self._token}) as response:
                    if response.status_code in {401, 403}:
                        raise AssistantError('domain_access_denied')
                    if response.status_code != (201 if method == 'POST' else 200):
                        # POST may have committed before an upstream/server error.
                        if method == 'POST' and response.status_code >= 500:
                            raise AssistantError('proposal_outcome_unknown')
                        raise AssistantError('domain_request_rejected')
                    raw = bytearray()
                    async for chunk in response.aiter_bytes():
                        raw.extend(chunk)
                        if len(raw) > 262144:
                            raise AssistantError('domain_response_too_large')
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError()
            return value
        except httpx.HTTPError:
            raise AssistantError('proposal_outcome_unknown' if method == 'POST' else 'domain_unavailable') from None
        except (ValueError, TypeError):
            raise AssistantError('proposal_outcome_unknown' if method == 'POST' else 'domain_response_malformed') from None

    async def authenticate(self):
        identity = await self._request('GET', '/me')
        try:
            self.identity = {'id': str(UUID(identity['id'])),
                             'tenant_id': str(UUID(identity['tenant_id'])), 'role': identity['role']}
            if self.identity['role'] not in {'operator', 'approver', 'auditor'}:
                raise AssistantError('domain_access_denied')
        except (ValueError, KeyError, TypeError, AttributeError):
            raise AssistantError('domain_response_malformed') from None
        return self.identity

    async def customers(self, query):
        rows, seen, after, revision = [], set(), 0, None
        for _ in range(10):
            params = {'query': query, 'after': after, 'limit': 100}
            if revision is not None:
                params['revision'] = revision
            page = await self._request('GET', '/v1/customers', params=params)
            if (not isinstance(page.get('revision'), str) or len(page['revision']) != 64
                    or revision is not None and revision != page['revision']
                    or not isinstance(page.get('items'), list) or len(page['items']) > 100):
                raise AssistantError('domain_response_malformed')
            revision = page['revision']
            for item in page['items']:
                ident = item.get('id') if isinstance(item, dict) else None
                if type(ident) is not int or ident <= after or ident in seen:
                    raise AssistantError('domain_response_malformed')
                seen.add(ident)
                rows.append(item)
            cursor = page.get('next_cursor')
            if cursor is None:
                return rows
            if type(cursor) is not int or cursor <= after or not page['items'] or cursor != page['items'][-1]['id']:
                raise AssistantError('domain_response_malformed')
            after = cursor
        raise AssistantError('retrieval_limit')

    async def catalog(self):
        return await self._request('GET', '/v1/catalog')

    async def opportunities(self):
        return await self._request('GET', '/v1/opportunities')

    async def opportunity(self, ident: int):
        return await self._request('GET', f'/v1/opportunities/{ident}')

    async def prepare(self, kind, payload):
        if not self.identity or self.identity['role'] != 'operator':
            raise AssistantError('domain_access_denied')
        if kind not in {'quotes', 'activities'}:
            raise AssistantError('invalid_skill')
        return await self._request('POST', '/v1/' + kind + '/prepare', body=payload)

    async def operation(self, ident: str):
        return await self._request('GET', '/v1/operations/' + str(UUID(ident)))
