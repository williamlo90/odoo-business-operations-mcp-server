"""Fixed JSON-2 capability allowlist; no caller-supplied model/method/URL."""
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

METHODS = frozenset({'info', 'customers', 'catalog', 'opportunities', 'opportunity', 'prepare', 'execute', 'status'})
KNOWN_ERRORS = frozenset({'forbidden', 'invalid_signature', 'scope_mismatch', 'self_approval',
    'invalid_input', 'record_not_found', 'catalog_limit', 'source_changed', 'unsupported_pricing',
    'unsupported_product', 'invalid_assignee', 'invalid_kind', 'idempotency_conflict',
    'approval_expired', 'stale_proposal', 'postcondition_failed'})


class PlatformError(Exception):
    def __init__(self, code: str, uncertain=False):
        self.code, self.uncertain = code, uncertain
        super().__init__(code)


class OdooAdapter:
    def __init__(self, tenant):
        path = os.environ.get('ODOO_CONFIG_PATH')
        if not path:
            raise PlatformError('odoo_not_configured')
        try:
            config = json.loads(Path(path).read_text())[str(tenant)]
            url = urlparse(config['url'])
            if url.scheme not in {'http', 'https'} or url.username or url.password or url.query or url.fragment:
                raise ValueError()
            if url.scheme == 'http' and url.hostname not in {'odoo', 'localhost', '127.0.0.1'}:
                raise ValueError()
            self.url = config['url'].rstrip('/')
            self.database, self.key = config['database'], config['api_key']
            self.company = int(config['company_id'])
            if not self.database or not self.key or self.company < 1:
                raise ValueError()
        except (KeyError, ValueError, OSError, TypeError):
            raise PlatformError('odoo_not_configured') from None

    def call(self, method, **payload):
        if method not in METHODS:
            raise PlatformError('tool_not_allowed')
        attempts = 1 if method == 'execute' else 3
        for attempt in range(attempts):
            try:
                with httpx.Client(timeout=httpx.Timeout(12, connect=3), follow_redirects=False, trust_env=False) as client:
                    with client.stream('POST', f'{self.url}/json/2/ops.bridge/{method}',
                            headers={'Authorization': f'Bearer {self.key}', 'X-Odoo-Database': self.database},
                            json=payload) as response:
                        raw = bytearray()
                        for chunk in response.iter_bytes():
                            raw.extend(chunk)
                            if len(raw) > 1_000_000:
                                raise PlatformError('platform_output_limit', uncertain=method == 'execute')
                        if response.status_code == 200:
                            try:
                                return json.loads(raw)
                            except ValueError:
                                raise PlatformError('platform_malformed', uncertain=method == 'execute') from None
                        if response.status_code == 401:
                            raise PlatformError('platform_credentials_expired')
                        if response.status_code in {429, 502, 503, 504}:
                            if attempt + 1 < attempts:
                                time.sleep(0.15 * 2 ** attempt)
                                continue
                            raise PlatformError('platform_rate_limited' if response.status_code == 429 else 'platform_unavailable', uncertain=method == 'execute')
                        # Only return allowlisted codes, never Odoo traceback/data.
                        match = re.search(r'OPS:([a-z_]+)', raw.decode(errors='replace'))
                        if match and match[1] in KNOWN_ERRORS:
                            raise PlatformError(match[1])
                        raise PlatformError('platform_rejected' if response.status_code < 500 else 'platform_unavailable', uncertain=method == 'execute')
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt + 1 < attempts:
                    time.sleep(0.15 * 2 ** attempt)
                    continue
                raise PlatformError('platform_timeout', uncertain=method == 'execute') from None


def adapter_for(tenant):
    return OdooAdapter(tenant)
