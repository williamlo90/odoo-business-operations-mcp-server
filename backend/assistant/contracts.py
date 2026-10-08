"""Versioned application contracts. Model output never carries authorization."""
from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

VERSION = '0.3.0'


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, hide_input_in_errors=True)


class Research(Strict):
    skill: Literal['research_customer']
    customer_reference: str = Field(min_length=1, max_length=100)
    include_opportunities: bool


class Line(Strict):
    product_code: str = Field(min_length=1, max_length=100)
    quantity: int = Field(ge=1, le=1000)


class Quote(Strict):
    skill: Literal['prepare_quote']
    customer_reference: str = Field(min_length=1, max_length=100)
    items: list[Line] = Field(min_length=1, max_length=20)

    @model_validator(mode='after')
    def unique_products(self):
        if len({line.product_code for line in self.items}) != len(self.items):
            raise ValueError('duplicate_product')
        return self


class Activity(Strict):
    skill: Literal['prepare_crm_activity']
    opportunity_id: int = Field(gt=0)
    assignee_id: int = Field(gt=0)
    due_date: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    summary: str = Field(min_length=1, max_length=120, pattern=r'^[^<>]+$')

    @field_validator('due_date')
    @classmethod
    def calendar_date(cls, value):
        date.fromisoformat(value)
        return value

    @field_validator('summary')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('empty_summary')
        return value


class Reconcile(Strict):
    skill: Literal['reconcile_odoo_write']
    operation_id: str = Field(pattern=r'^[0-9a-fA-F-]{36}$')

    @field_validator('operation_id')
    @classmethod
    def valid_uuid(cls, value):
        return str(UUID(value))


class Clarify(Strict):
    skill: Literal['clarify']
    missing: list[Literal['customer_reference', 'product_code', 'quantity',
                         'opportunity_id', 'assignee_id', 'due_date', 'summary',
                         'operation_id', 'supported_task']] = Field(min_length=1, max_length=9)


class Decision(Strict):
    # A nested anyOf is portable across hosted JSON-schema output interfaces.
    request: Research | Quote | Activity | Reconcile | Clarify


class Fact(Strict):
    source: str
    record: dict


class SkillResult(Strict):
    status: Literal['read', 'needs_input', 'awaiting_approval', 'verified',
                    'unknown', 'failed', 'review', 'dispatched']
    reason: str
    facts: list[Fact] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    proposal: dict | None = None
    operation: dict | None = None


def provider_schema():
    """Keep transport schemas conservative; validate all constraints locally."""
    def portable(value):
        if isinstance(value, list):
            return [portable(item) for item in value]
        if not isinstance(value, dict):
            return value
        omitted = {'title', 'minLength', 'maxLength', 'minimum', 'maximum',
                   'exclusiveMinimum', 'pattern', 'minItems', 'maxItems'}
        result = {key: portable(item) for key, item in value.items() if key not in omitted}
        if 'const' in result:
            result['enum'] = [result.pop('const')]
        return result
    return portable(Decision.model_json_schema())
