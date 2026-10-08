# Phase 0 — Scope and implementation decisions

Date: 2026-10-08 (Asia/Jakarta). Run: `phase0-20261008-01`.
This is the initial planning checkpoint. See [the phase map](../PHASES.md)
for current implementation status.

## Outcome and ownership

Help sales operations prepare correct Odoo transactions through previews, human
approval and verified receipts. William owns the local project and sandbox.
Operator and approver use separate test accounts, even in a single-person demo.
No external customer business owner was assigned at this checkpoint.

The first agreed workflow was customer lookup → quotation proposal → preview →
approval → one draft quotation → read-back and receipt.

## V1 user journeys

| Journey | Expected result | Boundary |
| --- | --- | --- |
| J1: customer research | Source-backed record ID, company and profile; explicit selection for ambiguous matches | Read-only; server-enforced company scope |
| J2: opportunity review and follow-up | Opportunity context and an activity with the correct owner, date and target | Creation requires approval; implemented after the quotation flow |
| J3: quotation preparation | Customer, company, currency, items, prices and total, followed by one approved Odoo draft | No order confirmation or outbound quotation email |

All four [shared skills](../REUSABLE-SKILLS.md) remain in scope. Prioritizing J3
does not remove J1, J2 or later acceptance gates.

## Business rules

- Use synthetic local data and explicitly isolated Companies A and B. Initial
  fixtures exclude shared cross-company customer records.
- Operators read and prepare proposals. Separate approvers authorize scoped
  writes. Configuration administrators do not automatically receive approval rights.
- Calculate prices deterministically from supported catalog and policy data.
  Initial fixtures use IDR, positive quantities, active products and no tax or
  discount. Reject unsupported pricing configurations explicitly.
- Odoo owns business records and final quotations. The application database owns
  proposals, approvals, operations, idempotency and audit records. Application
  services do not write directly to Odoo's database.
- Bind approval to the actor, tenant/company, payload hash, source version,
  expiry and policy. Relevant changes require a new preview and approval.
  Transaction-time race protection was a Phase 2 implementation and testing gate.
- Duplicate or concurrent requests must produce one effect. Treat uncertain
  post-write timeouts as unknown until reconciliation; never blindly recreate.
- Exclude order confirmation, invoices, payments, stock movements, record
  deletion, outbound email and arbitrary SQL, model methods or URLs from V1.
  Cloud delivery follows local validation and release preparation.

## Initial technical decisions

| Area | Decision at Phase 0 |
| --- | --- |
| Platform | Odoo Community 19.0 with Contacts, CRM and Sales; JSON-2 API, with actual methods and permissions to be verified |
| Runtime | Linux containers through Docker Compose; Windows/WSL2 development host |
| Services | Python/FastAPI domain service, TypeScript MCP server and reference client, PostgreSQL |
| Dependencies | Pin runtime versions, images and dependencies during compatibility work |
| MCP | Local stdio transport; remote transport deferred to deployment design |
| Automation | Python worker using shared services and skills; n8n not selected |
| AI | One orchestrator; hosted-provider adapters and optional Ollama; model choice requires evaluation |
| Resources | Start inference concurrency at one; measure memory before qualifying a local model |

References: [Odoo JSON-2 API](https://www.odoo.com/documentation/19.0/developer/reference/external_api.html),
[source installation](https://www.odoo.com/documentation/19.0/administration/on_premise/source.html)
and [Community source license](https://github.com/odoo/odoo/blob/19.0/LICENSE).
The local Community choice does not imply free hosted Odoo Online API access.

## Inventory and handoff

The initial folder contained ten planning documents and no executable project
source. Git, Python, Node, Docker and WSL CLIs were found; the Docker engine was
not yet connected. The sandbox, API accounts, services, migrations, skills,
worker and evaluation harness required implementation. No other project's
working tree was imported or modified. Downstream consumer projects were not
prerequisites for building this producer.

Planning evidence: [acceptance cases](ACCEPTANCE-CASES.md),
[dependency register](DEPENDENCIES.md), [baseline manifest](evidence/phase0-baseline.json)
and [original environment inspection](evidence/phase0-environment.md).
The original tag preserves the exact initial document versions.

Phase 0 completed scope and inventory with recorded dependencies. Phase 1 would
establish Git, pinned dependencies, authentication, PostgreSQL, synthetic seeds
and a local smoke test. Provider keys were not required for the deterministic
foundation. No application tests were claimed at the Phase 0 checkpoint.
