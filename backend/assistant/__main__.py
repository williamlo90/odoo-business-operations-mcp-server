"""Host-side reference CLI. Does not start Docker, download models or load .env implicitly."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
from typing import Literal

import httpx
from dotenv import load_dotenv
from pydantic import Field, ValidationError, model_validator

from backend.assistant.contracts import Decision, Strict
from backend.assistant.costs import RateCard
from backend.assistant.gateway import DomainGateway
from backend.assistant.providers import AssistantError, JsonProvider, ProviderConfig
from backend.assistant.runner import parse_decision, run


class ClientPacket(Strict):
    task: str | None = Field(default=None, min_length=1, max_length=4000)
    request: Decision | None = None
    provider: Literal['openai', 'claude', 'grok', 'ollama'] = 'ollama'
    model: str | None = None
    local_only: bool = False
    task_id: str | None = None

    @model_validator(mode='after')
    def one_input(self):
        if (self.task is None) == (self.request is None):
            raise ValueError('one_input_required')
        return self


async def main(args):
    if args.env_file:
        load_dotenv(args.env_file, override=False)
    provider = None
    if args.task:
        names = {'openai': 'OPENAI_API_KEY', 'claude': 'ANTHROPIC_API_KEY', 'grok': 'XAI_API_KEY'}
        provider = JsonProvider(ProviderConfig(provider=args.provider, model=args.model or '',
            api_key=os.environ.get(names.get(args.provider, 'UNUSED_LOCAL_PROVIDER_KEY')),
            local_only=args.local_only))
    decision = getattr(args, 'decision', None)
    if args.request_file:
        path = Path(args.request_file)
        if path.stat().st_size > 16384:
            raise AssistantError('model_output_invalid')
        decision = parse_decision(path.read_text(encoding='utf-8'))
    rate = None
    if args.rate_file:
        path = Path(args.rate_file)
        if path.stat().st_size > 16384:
            raise AssistantError('invalid_rate_file')
        rate = RateCard.model_validate_json(path.read_text(encoding='utf-8'))
    base = os.environ.get('API_URL', 'http://127.0.0.1:8020').rstrip('/')
    DomainGateway(base, 'validate-url-before-login')
    password = os.environ.get('DEMO_PASSWORD')
    if not password:
        raise AssistantError('demo_password_required')
    async with httpx.AsyncClient(base_url=base, trust_env=False, follow_redirects=False, timeout=10) as client:
        try:
            response = await client.post('/auth/login', json={
                'username': os.environ.get('DEMO_USERNAME', 'operator.a'), 'password': password})
            if response.status_code != 200:
                raise AssistantError('login_failed')
            token = response.json()['access_token']
            try:
                value = await run(DomainGateway(base, token), task=args.task, provider=provider,
                                  decision=decision, task_id=args.task_id, rate=rate,
                                  trace_dir=os.environ.get('ASSISTANT_STATE_DIR', 'local/assistant-runs'))
                print(json.dumps(value, ensure_ascii=True, indent=2))
            finally:
                logout = await client.post('/auth/logout', headers={'Authorization': 'Bearer ' + token})
                if logout.status_code != 204:
                    raise AssistantError('logout_failed')
        except httpx.HTTPError:
            raise AssistantError('domain_unavailable') from None
        except (ValueError, KeyError, TypeError):
            raise AssistantError('domain_response_malformed') from None


def cli():
    parser = argparse.ArgumentParser(description='Phase 3 assistant: read or prepare, then review using the existing client.')
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--stdio', action='store_true', help='One bounded client JSON packet on stdin')
    inputs.add_argument('--task', help='Natural-language request; explicit --provider and --model required')
    inputs.add_argument('--request-file', help='JSON Decision contract for deterministic skill invocation')
    parser.add_argument('--provider', choices=['openai', 'claude', 'grok', 'ollama'], default='ollama')
    parser.add_argument('--model', help='Explicit model identifier; no unverified model default')
    parser.add_argument('--local-only', action='store_true')
    parser.add_argument('--env-file', help='Explicit local dotenv path; values are never printed')
    parser.add_argument('--task-id', help='Stable UUID for safe replay; use the same input/context')
    parser.add_argument('--rate-file', help='Optional explicit versioned rate card JSON')
    args = parser.parse_args()
    try:
        if args.stdio:
            raw = sys.stdin.buffer.read(16385)
            if len(raw) > 16384:
                raise AssistantError('client_input_too_large')
            packet = ClientPacket.model_validate_json(raw)
            args.task, args.decision = packet.task, packet.request
            args.provider, args.model = packet.provider, packet.model
            args.local_only, args.task_id = packet.local_only, packet.task_id
        asyncio.run(main(args))
    except AssistantError as exc:
        if args.stdio:
            print(json.dumps({'error': str(exc)}))
            raise SystemExit(1)
        parser.exit(1, str(exc) + '\n')
    except ValidationError:
        parser.exit(1, 'invalid_client_configuration\n')
    except OSError:
        parser.exit(1, 'local_file_unavailable\n')
    except KeyboardInterrupt:
        parser.exit(130, 'cancelled\n')


if __name__ == '__main__':
    cli()
