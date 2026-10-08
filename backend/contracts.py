"""Version 1 response contracts shared by HTTP clients and future MCP consumers."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid')


class PreviewLine(Contract):
    product_id: int
    name: str
    quantity: int
    unit_price: str
    subtotal: str


class QuotePreview(Contract):
    kind: Literal['quote']
    company_id: int
    customer_id: int
    customer_name: str
    currency: Literal['IDR']
    pricelist_id: int
    pricing_policy: Literal['list-price-no-tax-v1']
    items: list[PreviewLine]
    total: str
    source_version: str
    contract_version: Literal['1.0']


class ActivityPreview(Contract):
    kind: Literal['activity']
    company_id: int
    opportunity_id: int
    assignee_id: int
    due_date: str
    summary: str
    source_version: str
    contract_version: Literal['1.0']


class ProposalOut(Contract):
    id: UUID
    tenant_id: UUID
    actor_id: UUID
    kind: Literal['quote', 'activity']
    payload: dict
    preview: QuotePreview | ActivityPreview = Field(discriminator='kind')
    payload_hash: str
    contract_version: Literal['1.0']
    created_at: datetime
    expires_at: datetime


class ApprovalOut(Contract):
    id: UUID
    tenant_id: UUID
    proposal_id: UUID
    approver_id: UUID
    payload_hash: str
    expires_at: datetime
    created_at: datetime


class QuoteLine(Contract):
    product_id: int
    quantity: float
    unit_price: str
    subtotal: str


class QuoteRecord(Contract):
    kind: Literal['quote']
    external_id: int
    name: str
    state: str
    company_id: int
    customer_id: int
    currency: str
    total: str
    items: list[QuoteLine]


class ActivityRecord(Contract):
    kind: Literal['activity']
    external_id: int
    company_id: int
    opportunity_id: int
    assignee_id: int
    due_date: str
    summary: str


class Receipt(Contract):
    operation_id: UUID
    payload_hash: str
    record: QuoteRecord | ActivityRecord = Field(discriminator='kind')


class OperationOut(Contract):
    id: UUID
    tenant_id: UUID
    proposal_id: UUID
    approval_id: UUID
    idempotency_key: UUID
    status: Literal['dispatched', 'unknown', 'verified', 'failed', 'review']
    result: Receipt | None
    error_code: str | None
    attempts: int
    created_at: datetime
    updated_at: datetime
