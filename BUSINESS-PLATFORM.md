# Odoo business integration

The target is local Odoo Community 19.0, with Contacts, CRM, Sales and the
`ops_bridge` addon. JSON-2 exposes fixed business capabilities. Hosted Odoo
account/plan access is not assumed. The complete connected workflow is locally
validated; [Azure deployment](docs/AZURE-PLAN.md) is still a proposal.

## Authoritative records

Odoo owns customers, opportunities, products and resulting business records.
The application database owns proposals, approvals, operation state and audit.
The application never writes directly to Odoo tables. Synthetic company A/B
fixtures exercise distinct references, same-name ambiguity and different prices.

Read and prepare happen before approval, write and verification. The supported
quotation policy uses positive quantities, active products, list prices and no
tax or discount. Unsupported pricing is rejected. Approval becomes invalid when
relevant source data or payload changes. Signed envelopes, source locking and a
unique Odoo operation ledger protect the write boundary.

## Failure handling and evidence

Pagination/revision changes, rate limits, expired credentials, missing records,
stale previews, timeouts and mismatched read-back are classified explicitly.
Reads have bounded retries; uncertain writes are reconciled by operation ID
before another action. There is no asynchronous webhook/callback endpoint in
this release. Any future webhook must authenticate its source and reject replay.

Evidence retains sanitized references, source versions, approval/operation IDs,
expected/observed fields and final record counts. Concurrent/replayed execution
and response loss after an actual write are covered by connected tests.
Draft creation does not imply order confirmation, email, invoice or payment.

[Local setup and mapping](docs/ODOO-LOCAL.md) · [API contract](docs/CONTRACT-V1.md) ·
[Acceptance cases](docs/ACCEPTANCE-CASES.md) · [Recorded walkthrough](docs/demo/README.md)
