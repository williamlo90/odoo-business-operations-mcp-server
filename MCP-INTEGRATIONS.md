# Custom MCP, API and database boundaries

Reference caller → TypeScript MCP server → Python domain API → PostgreSQL and
Odoo adapter. MCP does not bypass domain validation or expose arbitrary SQL,
model methods or caller-chosen URLs. Current transport is authenticated local
stdio; no remote MCP HTTP endpoint is claimed.

## Tool surface

| Tool | Capability |
| --- | --- |
| `odoo.identity` | Authenticate the current caller |
| `odoo.customer_search` | Search scoped customer records |
| `odoo.catalog` | Read the permitted catalog |
| `odoo.opportunity_list` | List scoped opportunities |
| `odoo.opportunity_get` | Read one opportunity |
| `odoo.quote_prepare` | Build a validated quotation proposal |
| `odoo.activity_prepare` | Build a CRM activity proposal |
| `odoo.proposal_get` | Read an existing proposal |
| `odoo.review_status` | Read approval ID and saved operation status after independent browser review; cannot approve |
| `odoo.execute_approved` | Execute with proposal, approval and idempotency key |
| `odoo.operation_status` | Reconcile/read a recorded operation |

The model and worker cannot create approval through this surface. The separate
approver uses the domain workflow. All routes enforce authenticated role,
company/record scope and applicable payload/version checks.

For a quotation, call `odoo.customer_search` and `odoo.catalog`, then
`odoo.quote_prepare` with exact IDs and quantities. Share the returned proposal
ID as `http://127.0.0.1:8020/#proposal/<proposal-id>` for human review.
After approval, `odoo.review_status` returns the approval ID. The original
operator calls `odoo.execute_approved` with a stable idempotency UUID and reads
`odoo.operation_status` to verify or reconcile the Odoo result. The
[connected synthetic transcript](docs/evidence/mcp-first-journey.md) records
this complete path.

Strict schemas, bounded output, stable error codes and correlation IDs are
part of the contract. SDK/protocol versions are pinned in the implementation.
Real stdio tests exercise schema rejection, expired sessions, tool injection,
cancellation, concurrency, replay and unknown outcomes. Connected acceptance
also verifies the downstream Odoo effects, not only tool responses.

PostgreSQL stores tenants, actors, proposals, approvals, operations and audit.
Constraints and transaction locks enforce identity and idempotency boundaries.
Odoo retains its own database and operation ledger. Cross-project consumers
should reuse the contract rather than copy the connector implementation.

[Protocol implementation](docs/PHASE-4.md) · [Domain contract](docs/CONTRACT-V1.md) ·
[Connected verification](docs/PHASE-8.md) · [Automation ownership](N8N-AUTOMATION.md)
