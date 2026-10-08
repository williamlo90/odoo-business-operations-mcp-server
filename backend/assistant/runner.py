"""One bounded model decision followed by one deterministic skill invocation."""
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
from uuid import UUID, uuid4

from pydantic import ValidationError

from backend.assistant.contracts import Activity, Decision, Quote, Reconcile, Research, VERSION, provider_schema
from backend.assistant.providers import AssistantError, PROMPT, PROMPT_VERSION
from backend.assistant.skills import SKILL_VERSION, execute_skill
from backend.assistant.journal import TaskJournal
from backend.assistant.costs import estimate


def parse_decision(text):
    def unique_object(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('duplicate_json_key')
            value[key] = item
        return value
    try:
        if len(text) > 16384:
            raise ValueError()
        return Decision.model_validate(json.loads(text, object_pairs_hook=unique_object))
    except (ValidationError, ValueError, TypeError, RecursionError):
        raise AssistantError('model_output_invalid') from None


def check_grounding(request, task):
    """Reject invented identifiers before any business retrieval or proposal."""
    references = []
    if isinstance(request, (Research, Quote)):
        references.append(request.customer_reference)
    if isinstance(request, Quote):
        references.extend(line.product_code for line in request.items)
    if isinstance(request, Activity):
        references.extend([str(request.opportunity_id), str(request.assignee_id), request.due_date])
    if isinstance(request, Reconcile):
        references.append(request.operation_id)
    for reference in references:
        if not re.search(r'(?<![\w-])' + re.escape(reference) + r'(?![\w-])', task, re.IGNORECASE):
            raise AssistantError('unsupported_model_reference')


class Trace:
    """A per-run, append-only local trace containing metadata, never task bodies."""
    def __init__(self, directory, task_id):
        Path(directory).mkdir(parents=True, exist_ok=True)
        self.path = Path(directory) / (task_id + '.jsonl')
        self.path.touch(exist_ok=True)

    def write(self, event, **fields):
        with self.path.open('a', encoding='utf-8', newline='\n') as file:
            file.write(json.dumps({'event': event, 'timestamp': datetime.now(timezone.utc).isoformat(),
                                   **fields}, ensure_ascii=True) + '\n')
            file.flush()
            os.fsync(file.fileno())


async def run(gateway, *, task=None, provider=None, decision=None,
              trace_dir='local/assistant-runs', timeout_seconds=60, task_id=None, rate=None):
    if (task is None) == (decision is None) or task is not None and provider is None:
        raise AssistantError('choose_task_or_decision')
    if not 0 < timeout_seconds <= 120:
        raise AssistantError('invalid_run_timeout')
    if task is not None and (not isinstance(task, str) or not 1 <= len(task) <= 4000 or not task.strip()):
        raise AssistantError('invalid_task')
    if decision is not None and not isinstance(decision, Decision):
        raise AssistantError('invalid_decision')
    try:
        task_id = str(UUID(task_id)) if task_id else str(uuid4())
    except (ValueError, TypeError, AttributeError):
        raise AssistantError('invalid_task_id') from None
    started = time.monotonic()
    trace = Trace(trace_dir, task_id)
    journal = TaskJournal(Path(trace_dir) / 'tasks.sqlite3')
    owner, stage = None, 'planning'
    fingerprint = hashlib.sha256(json.dumps({'task': task,
        'decision': decision.model_dump() if decision else None,
        'provider': provider.config.provider if provider else None,
        'model': provider.config.model if provider else None,
        'local_only': provider.config.local_only if provider else None,
        'rate': rate.model_dump() if rate else None, 'version': VERSION,
        'prompt': PROMPT_VERSION}, sort_keys=True).encode()).hexdigest()
    usage = {'input_tokens': None, 'output_tokens': None, 'cost_usd': None,
             'cost_status': 'not_estimated'}
    trace.write('started', task_id=task_id, contract_version=VERSION,
        skill_version=SKILL_VERSION, prompt_version=PROMPT_VERSION if provider else None,
        prompt_sha256=hashlib.sha256(PROMPT.encode()).hexdigest() if provider else None,
        schema_sha256=hashlib.sha256(json.dumps(provider_schema(), sort_keys=True).encode()).hexdigest(),
        provider=provider.config.provider if provider else None,
        model=provider.config.model if provider else None, caller='assistant' if task is not None else 'direct_skill')
    try:
        async with asyncio.timeout(timeout_seconds):
            identity = await gateway.authenticate()
            trace.write('authenticated', actor_id=identity['id'], tenant_id=identity['tenant_id'])
            claim = journal.claim(task_id, identity, fingerprint)
            if 'cached' in claim:
                trace.write('replayed', task_id=task_id)
                return claim['cached']
            owner = claim['owner']
            if 'decision' in claim:
                decision, usage = Decision.model_validate(claim['decision']), claim['usage']
            elif task is not None:
                model_started = time.monotonic()
                generation = await provider.generate(task)
                usage = estimate(provider.config, generation, rate)
                trace.write('model_returned', latency_ms=round((time.monotonic()-model_started)*1000, 2), **usage)
                decision = parse_decision(generation.text)
                check_grounding(decision.request, task)
            journal.checkpoint(task_id, owner, 'planned', decision=decision.model_dump(), usage=usage)
            trace.write('skill_started', skill=decision.request.skill)
            journal.checkpoint(task_id, owner, 'dispatching')
            stage = 'dispatching'
            result = await execute_skill(decision.request, gateway)
            output = {'task_id': task_id, 'contract_version': VERSION,
                      'result': result.model_dump(mode='json'), 'usage': usage}
            journal.checkpoint(task_id, owner, 'completed', result=output)
            stage = 'completed'
            trace.write('completed', status=result.status,
                        proposal_id=result.proposal['id'] if result.proposal else None,
                        operation_id=result.operation['id'] if result.operation else None,
                        latency_ms=round((time.monotonic()-started)*1000, 2), **usage)
            return output
    except asyncio.CancelledError:
        trace.write('cancelled', latency_ms=round((time.monotonic()-started)*1000, 2), **usage)
        raise
    except TimeoutError:
        trace.write('failed', code='task_timeout', latency_ms=round((time.monotonic()-started)*1000, 2), **usage)
        raise AssistantError('task_timeout') from None
    except AssistantError as exc:
        trace.write('failed', code=str(exc), latency_ms=round((time.monotonic()-started)*1000, 2), **usage)
        raise
    except (KeyError, TypeError, ValueError, ValidationError, AttributeError):
        trace.write('failed', code='domain_response_malformed', latency_ms=round((time.monotonic()-started)*1000, 2), **usage)
        raise AssistantError('domain_response_malformed') from None
    finally:
        if owner and stage != 'completed':
            state = 'review' if stage == 'dispatching' and isinstance(decision.request, (Quote, Activity)) else 'failed'
            journal.checkpoint(task_id, owner, state, usage=usage, error='interrupted_or_failed')
