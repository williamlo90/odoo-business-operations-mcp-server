# Business API contract 1.0

The producer owns [OpenAPI](../contracts/v1/openapi.json),
[JSON schemas](../contracts/v1/schemas.json) and
[consumer fixtures](../contracts/v1/consumer-fixtures.json). The snapshot is checked
against executable Pydantic contracts in the test suite. Regenerate with
`python deploy/export_contracts.py`, then review the diff; changing the snapshot is
not permission to silently break consumers. Breaking changes require a new major
version/path, with migration notes and compatibility tests. Additive capabilities
require an explicit minor contract revision and fixtures.

Consumers 04/05/08 call this domain contract and later its MCP wrapper, rather than
copying the connector. Invoice and purchase writes for project 05 are not supplied
by this release. MCP transport/protocol verification remains Phase 4.

| Capability | Endpoint | Allowed role |
| --- | --- | --- |
| Connection identity | GET `/v1/odoo/info` | Operator, approver, auditor |
| Customer search | GET `/v1/customers?query=&after=&limit=&revision=` | Reader roles |
| Product catalog | GET `/v1/catalog` | Reader roles |
| Opportunity list/detail | GET `/v1/opportunities`, GET `/v1/opportunities/{id}` | Reader roles |
| Quote proposal | POST `/v1/quotes/prepare` | Operator |
| Activity proposal | POST `/v1/activities/prepare` | Operator |
| Preview | GET `/v1/proposals/{id}` | Reader roles, same tenant |
| Approval | POST `/v1/proposals/{id}/approve` with preview hash | Separate approver, same tenant |
| Approved execution | POST `/v1/proposals/{id}/execute` with approval ID and idempotency UUID | Original proposing operator |
| Read-back/reconciliation | GET `/v1/operations/{id}` | Reader roles, same tenant |
| Explicit recovery retry | POST `/v1/operations/{id}/retry` | Original operator, valid approval |

Authentication is the Phase 1 bearer session. Identity, tenant and role always come
from server records. Tenant, role, price, Odoo model, method and URL are not accepted
as proposal fields. The app's tenant UUID maps to a fixed Odoo company ID and
company-scoped connector identity in private configuration. Odoo record IDs are
scoped by that connection; they are not globally meaningful identifiers.

All money is returned as decimal strings. Odoo is authoritative for customer,
catalog, opportunity and final document fields. The domain service independently
checks quantity/price arithmetic and preview identity. A source fingerprint
includes relevant record versions and pricing values. Application proposals,
approvals, operation status and audit are authoritative in the application DB.

## Transaction boundary and approval binding

1. Prepare reads Odoo and persists an immutable proposal with actor, tenant, input,
   full preview, source fingerprint, SHA256 preview hash, contract version and expiry.
2. Approval requires a different active approver, the exact preview hash and a fresh
   source check. One proposal has at most one approval.
3. Execute validates actor and active approver, expiry/hash and idempotency. A short
   tenant advisory lock serializes creation of one durable operation per proposal.
   Its signed envelope is persisted before external dispatch.
4. The Odoo addon validates the scoped service identity and HMAC signature. It opens
   a dedicated READ COMMITTED cursor, acquires source-table locks, rechecks source
   state, creates the draft/activity, checks draft postconditions and records the
   unique operation ID in that same transaction. Its commit is independent of the
   outer JSON-2 response transaction, so losing that response still requires lookup.
5. The backend performs a separate read-back. Only a matching receipt becomes
   `verified`; missing/uncertain results become `unknown`, differences become `review`.

The service account has no generic create permission on sale orders and no direct
ACL on binding/ledger models. The addon's private methods use narrowly scoped
elevated ORM operations after authorization; they are not exposed as tools. Runtime
database connections cannot modify proposal/approval rows. Signed envelopes and
platform credentials are omitted from API responses and application logs.

For V1, source table locks are deliberately conservative and can serialize unrelated
company writes while the short transaction executes. Lock acquisition times out
after three seconds; platform calls have bounded timeouts. This is a verified local
correctness design, not a high-throughput production claim. Row-level optimization
must preserve the race test before any later change.

Business rejections use stable codes such as `valid_approval_required`,
`proposal_actor_mismatch`, `idempotency_conflict`, `approval_expired`,
`stale_proposal`, `unsupported_pricing`, `source_changed`, `readback_mismatch` and
`platform_timeout`. Failure details never contain Odoo debug traces or credentials.
Domain audit records include preparation, approvals, dispatch, outcomes, retries and
execution denials. HTTP correlation IDs link requests to sanitized route logs.

Reference decisions were checked against the official [Odoo JSON-2 API documentation](https://www.odoo.com/documentation/19.0/developer/reference/external_api.html)
and the pinned image's installed Odoo source. JSON-2 does not combine multiple HTTP
calls into one transaction; the addon supplies the required atomic operation.
