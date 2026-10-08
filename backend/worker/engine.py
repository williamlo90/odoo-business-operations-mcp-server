"""A bounded worker tick. It never creates approvals or executes external writes."""
import asyncio

from backend.assistant.contracts import Decision
from backend.assistant.providers import AssistantError
from backend.assistant.skills import execute_skill
from backend.worker.queue import WRITE_SKILLS


async def run_once(queue, gateway, *, now=None, timeout_seconds=60):
    if not 0<timeout_seconds<=60:
        raise AssistantError('invalid_worker_timeout')
    identity = await gateway.authenticate()
    queue.tick(identity,now)
    job=queue.claim(identity,now)
    if job is None:
        return {'state':'idle'}
    dispatched=False
    try:
        decision=Decision.model_validate_json(job['request'])
        if (job['actor'],job['tenant']) != (identity['id'],identity['tenant_id']):
            raise AssistantError('job_scope_mismatch')
        queue.dispatch(job,now)
        dispatched=True
        async with asyncio.timeout(timeout_seconds):
            result=await execute_skill(decision.request,gateway)
        if result.status in {'read','verified'}:
            state='completed'
        elif result.status=='awaiting_approval':
            state='awaiting_approval'
        elif result.status in {'unknown','dispatched'}:
            state='retry_wait' if job['attempts']<3 else 'review'
        elif result.status in {'needs_input','review'}:
            state='review'
        else:
            state='dead'
        queue.finish(job,state,result=result.model_dump(mode='json'),now=now)
    except asyncio.CancelledError:
        state='review' if dispatched and job['skill'] in WRITE_SKILLS else 'retry_wait' if job['attempts']<3 else 'dead'
        queue.finish(job,state,error='worker_cancelled',now=now)
        raise
    except (AssistantError, TimeoutError) as exc:
        code=str(exc) if isinstance(exc,AssistantError) else 'worker_timeout'
        if code=='job_lease_lost':
            raise
        if code in {'proposal_outcome_unknown','proposal_response_mismatch'} or isinstance(exc,TimeoutError) and job['skill'] in WRITE_SKILLS:
            state='review'
        elif code in {'domain_unavailable','mcp_unavailable','worker_timeout'}:
            state='retry_wait' if job['attempts']<3 else 'dead'
        else:
            state='review'
        queue.finish(job,state,error=code,now=now)
    except Exception:
        queue.finish(job,'review',error='worker_internal_error',now=now)
    return queue.inspect(identity,job['id'])
