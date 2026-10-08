"""Reuse deterministic skills via a real TypeScript MCP client/server connection."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import UUID

from backend.assistant.gateway import DomainGateway
from backend.assistant.providers import AssistantError


class McpGateway(DomainGateway):
    async def __aenter__(self):
        root = Path(__file__).resolve().parents[2]
        bridge = root / 'mcp-server/dist/bridge.js'
        if not bridge.is_file():
            raise AssistantError('mcp_build_required')
        env = {key: os.environ[key] for key in ('PATH','Path','SystemRoot','SYSTEMROOT','TEMP','TMP') if key in os.environ}
        env.update(API_URL=self._base_url, ODOO_OPS_TOKEN=self._token)
        self._process = await asyncio.create_subprocess_exec('node', str(bridge), cwd=root, env=env,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            limit=524288, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        self._sequence = 0
        self.correlations = []
        return self

    async def __aexit__(self, *args):
        process = self._process
        if process.returncode is None:
            process.stdin.close()
            try:
                await asyncio.wait_for(process.wait(), 3)
            except TimeoutError:
                process.kill()
                await process.wait()

    async def _request(self, method, path, *, params=None, body=None):
        self._remaining -= 1
        if self._remaining < 0:
            raise AssistantError('domain_call_limit')
        routes = {'/me':'odoo.identity','/v1/customers':'odoo.customer_search',
                  '/v1/catalog':'odoo.catalog','/v1/opportunities':'odoo.opportunity_list'}
        if method == 'GET' and path in routes:
            tool, arguments = routes[path], params or {}
        elif method == 'GET' and path.startswith('/v1/opportunities/'):
            tool, arguments = 'odoo.opportunity_get', {'opportunity_id':int(path.rsplit('/',1)[1])}
        elif method == 'GET' and path.startswith('/v1/operations/'):
            tool, arguments = 'odoo.operation_status', {'operation_id':path.rsplit('/',1)[1]}
        elif method == 'POST' and path in {'/v1/quotes/prepare','/v1/activities/prepare'}:
            tool = 'odoo.quote_prepare' if '/quotes/' in path else 'odoo.activity_prepare'
            arguments = body
        else:
            raise AssistantError('mcp_tool_not_allowed')
        self._sequence += 1
        try:
            packet = json.dumps({'id':self._sequence,'tool':tool,'arguments':arguments})+'\n'
            self._process.stdin.write(packet.encode())
            await self._process.stdin.drain()
            raw = await asyncio.wait_for(self._process.stdout.readline(), 20)
            reply = json.loads(raw)
            if reply.get('id') != self._sequence or 'result' not in reply:
                raise ValueError()
            result = reply['result']
            if result.get('isError'):
                # Classify only known transport/domain codes; never emit raw tool text.
                code = json.loads(result['content'][0]['text']).get('error')
                if code in {'write_outcome_unknown','request_cancelled'} and method == 'POST':
                    raise AssistantError('proposal_outcome_unknown')
                if code in {'access_denied','invalid_session','role_not_permitted','authentication_required'}:
                    raise AssistantError('domain_access_denied')
                if code in {'domain_unavailable','request_limit'}:
                    raise AssistantError('mcp_unavailable')
                raise AssistantError('domain_request_rejected')
            wrapped = result.get('structuredContent')
            if wrapped is None:
                wrapped = json.loads(result['content'][0]['text'])
            if wrapped.get('contract_version') != '1.0' or not isinstance(wrapped.get('data'),dict):
                raise ValueError()
            self.correlations.append({'mcp':str(UUID(wrapped['correlation_id'])),
                                      'domain':[str(UUID(value)) for value in wrapped.get('domain_correlation_ids',[])]})
            return wrapped['data']
        except (OSError, ValueError, KeyError, IndexError, TypeError, TimeoutError):
            raise AssistantError('proposal_outcome_unknown' if method == 'POST' else 'mcp_unavailable') from None
