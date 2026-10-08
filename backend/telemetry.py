"""Request-local, bounded telemetry. Never records task or credential values."""
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass
class RequestTiming:
    correlation_id: str
    downstream_ms: float = 0


request_timing = ContextVar('request_timing', default=None)
