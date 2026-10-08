"""Explicit versioned rate cards; never invent a current provider price."""
from decimal import Decimal

from pydantic import Field

from backend.assistant.contracts import Strict


class RateCard(Strict):
    provider: str
    model: str
    version: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=500)
    input_usd_per_million: str = Field(pattern=r'^\d+(\.\d+)?$')
    output_usd_per_million: str = Field(pattern=r'^\d+(\.\d+)?$')


def estimate(config, generation, rate=None):
    result = {'input_tokens': generation.input_tokens, 'output_tokens': generation.output_tokens,
              'cost_usd': None, 'cost_status': 'not_estimated', 'rate_version': None}
    if rate is None:
        return result
    if (rate.provider, rate.model) != (config.provider, config.model):
        result['cost_status'] = 'rate_mismatch'
    elif generation.input_tokens is None or generation.output_tokens is None:
        result['cost_status'] = 'usage_missing'
    else:
        amount = (generation.input_tokens * Decimal(rate.input_usd_per_million)
                  + generation.output_tokens * Decimal(rate.output_usd_per_million)) / 1000000
        result.update(cost_usd=str(amount), cost_status='estimated_uncached', rate_version=rate.version)
    return result
