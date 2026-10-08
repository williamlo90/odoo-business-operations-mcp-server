# Phase 4 - Custom MCP implementation

Status: **offline implementation complete**. Real stdio protocol/process tests
use a loopback domain fixture. Odoo/PostgreSQL/provider validation is Phase 6.

## Runtime and boundaries

Node 22+, TypeScript 5.9.3, `@modelcontextprotocol/server` and `client` 2.3.1.
The reference client explicitly pins protocol **2026-07-28**, with no automatic
version fallback. Dependencies are locked in `mcp-server/package-lock.json`.
The server uses the official SDK's stdio transport; no HTTP MCP server is exposed.

One server process represents one existing domain session, supplied through
`ODOO_OPS_TOKEN`. Every tool rechecks `/me`, roles and session validity. Tenant
is never a tool argument. The domain service remains authoritative for record
scope, approval binding, expiry, stale source checks and idempotency.

Tools: `odoo.identity`, `odoo.customer_search`, `odoo.catalog`,
`odoo.opportunity_list`, `odoo.opportunity_get`, `odoo.quote_prepare`,
`odoo.activity_prepare`, `odoo.proposal_get`, `odoo.execute_approved`,
`odoo.operation_status`. There is no tool to create approvals or issue blind retries.
Inputs and outputs use closed JSON schemas; proposal/operation schemas are loaded
from the existing version 1 contract. Reads return bounded source fields.

## Build and test without Docker

```powershell
npm.cmd ci --prefix mcp-server --ignore-scripts
npm.cmd run build --prefix mcp-server
npm.cmd run build --prefix client
npm.cmd test --prefix mcp-server
```

Seven protocol scenarios pass, covering discovery/schema rejection, preparation,
approved replay/concurrency, expired identity, stale approval, cross-tenant scope,
uncertain writes, malformed receipts, request limits, cancellation, and the
TypeScript client -> Python skill -> MCP -> HTTP path. See
[protocol evidence](evidence/phase4-protocol-tests.txt). The original Phase 3
49 Python and 2 client tests also pass. The domain fixture's effects are simulated;
this is not a new claim of Odoo connected acceptance.

## Use with the local stack later

After the Phase 6 stack is available, use the TypeScript assistant command from
[Phase 3](PHASE-3.md). The Python CLI now defaults to `ASSISTANT_TRANSPORT=mcp`.
`ASSISTANT_TRANSPORT=http` retains the Phase 3 direct-domain route for diagnosis.
Both paths invoke the same skill implementation, with no change to approval rules.

For human-operated protocol calls (Node loads the ignored local environment):

```powershell
node --env-file=.env mcp-server/dist/cli.js list
node --env-file=.env mcp-server/dist/cli.js odoo.customer_search '{"query":"OPS-A-001"}'
```

The CLI logs in, starts its scoped MCP connection and logs out afterward. Use the
existing Phase 2 approver client to approve a reviewed proposal. Then an operator
may call `odoo.execute_approved` with `proposal_id`, `approval_id` and a stable
`idempotency_key`. Reconcile with `odoo.operation_status` after uncertain results.
The AI skill allowlist cannot invoke approved execution; that remains a deliberate
human/client step. No arbitrary URL, SQL or Odoo method is available.

## Resource and recovery policy

- At most four active tool requests per process; excess requests fail explicitly.
- Domain calls have a bounded timeout (default 10 seconds) and 256 KiB response cap.
- Cancellation is forwarded to HTTP and propagated on connection teardown.
  Cancellation after dispatch does not prove rollback.
- No automatic write retry. A lost/invalid POST response is `write_outcome_unknown`.
- `verified` requires an authoritative, schema-valid operation with a receipt.
- Output correlation IDs link assistant traces to MCP requests and domain response
  IDs. Server stderr logs only tool names, IDs and durations, never tokens/bodies.
- Local URLs are allowlisted and redirects rejected. Remote authenticated MCP,
  production load and real downstream recovery are later gates.

Checkpoint: `phase-4-code`, one implementation commit on `learning-phases`.

Implementation references: [official SDK v2](https://ts.sdk.modelcontextprotocol.io/v2/),
[stdio lifecycle](https://ts.sdk.modelcontextprotocol.io/v2/serving/stdio.html),
[cancellation](https://ts.sdk.modelcontextprotocol.io/v2/servers/logging-progress-cancellation.html).
