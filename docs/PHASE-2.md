# Phase 2 — Deterministic Odoo workflow delivery

Date: 2026-10-08 (Asia/Jakarta). Run ID: `phase2-20261008-01`.
Status: **Phase 2 gate passed on a local synthetic Odoo sandbox**.

## Delivered

The TypeScript reference client can search customers, inspect sales opportunities,
prepare a quotation or CRM activity, display the proposal, accept a separate
approver's explicit approval, execute, and read back the result. No LLM is required.
The live quotation example is **2 × IDR 100,000 + 1 × IDR 50,000 = IDR 250,000**.

The API separates read, prepare, approve, execute and status/retry capabilities.
Proposals are immutable; approval binds the preview hash, source versions, actor,
tenant and expiry. Source changes invalidate approval. A durable application
operation and an Odoo transaction ledger prevent repeated effects. Outcome
uncertainty is represented explicitly and reconciled before a bounded retry.

Odoo **Community 19.0-20260926**, Contacts/CRM/Sales, JSON-2, and the custom
`ops_bridge` addon were exercised. The image is pinned to
`sha256:dd9013e669caaa23d26765dc55814655eaeecca7cfc2c265dbabae913bce22fd`.
Two distinct Odoo companies, service identities and pricing configurations are
connected to the two application tenants. Company B's equivalent quotation totals
IDR 290,000 and uses the same implementation.

## Verification and evidence

| Verification | Result |
| --- | --- |
| Full foundation/business/contracts/connected suite | **38 passed**, 10.58 seconds; one test-client deprecation warning |
| Actual Odoo connected cases | 9 cases, including quote/activity, duplicate dispatch, direct addon replay, price-update race, changed pagination, altered read-back, invalid credentials and access bypass |
| Failure injection with real application PostgreSQL | 10 cases, including expired/revoked approval, unknown outcome before/after write, read-back outage/mismatch and bounded read retries |
| Foundation regression | 17 existing checks passed |
| Consumer compatibility | 2 schema/fixture checks passed |
| TypeScript client | Build passed; preview → approver → execute produced a verified draft |
| Fresh-volume installation | New application and Odoo DB volumes, addon initialization and CLI quotation workflow passed; temporary resources removed |

Evidence: [test transcript](evidence/phase2-test-run.txt),
[proposal](evidence/phase2-proposal.json), [approval](evidence/phase2-approval.json),
[receipt](evidence/phase2-receipt.json), [fresh install](evidence/phase2-clean-install.txt),
[fresh-install receipt](evidence/phase2-clean-receipt.json), and
[source manifest](evidence/phase2-source-manifest.json).
Fresh installation was replayed on this machine with Docker image/build caches;
it was not a second physical machine test.

The concurrency case sends four HTTP execution requests and three additional
direct addon replays, then counts **one ledger row and one sale order** for that
operation in Odoo. The race case commits a price update while execute is waiting;
the signed operation is rejected as stale and creates **zero** drafts. The lost
response test performs a real Odoo write, drops its result at the adapter boundary,
then recovers the existing external ID without another write. Activity creation
is checked not to add mail queue records.

## Acceptance coverage

The original expected outcomes in [ACCEPTANCE-CASES.md](ACCEPTANCE-CASES.md) remain
the V1 specification. Phase 2 exercises A01–A17/A19/A20 at the relevant HTTP/domain
and Odoo boundaries; this is not a claim that every later-phase channel is tested.
In particular:

- A03/A14 include direct HTTP, connector, allowlist and company checks; MCP-channel
  checks wait for Phase 4 and AI prompt-injection evaluation waits for Phase 3/6.
- A09 includes a real concurrent product-price edit; exhaustive source/policy
  mutation combinations remain regression expansion, not a universal guarantee.
- A12 combines real invalid-credential rejection with mocked rate-limit and
  transport failures. A17 combines real altered-draft detection and fake outages.
- A18 worker restart is not implemented/tested: worker automation belongs to
  Phase 5 and comprehensive interrupted-worker tests to Phase 7. Durable operation
  persistence and cross-request reconciliation are present now.
- A20 proves a second company/pricing configuration; reusable AI skill packages
  themselves remain Phase 3.

## Boundaries and next phase

Pricing supports only the documented IDR/no-tax/no-discount policy. Source table
locks prioritize local correctness and can serialize other writes briefly; no
production throughput claim is made. Draft confirmation, invoice/payment/stock
actions and external email are excluded. No cloud resources were deployed.

Business API contracts are versioned at 1.0, with OpenAPI, input/output schemas and
consumer fixtures for 04/05/08. This provides reusable connector contracts, not
completed consumer integrations. No invoice/purchase capability is implied for 05.

Next: Phase 3 adds the AI assistant, executable business skills and provider/local
inference integration on top of these deterministic rules. MCP protocol integration
remains Phase 4; connected automation and broader platform resilience remain Phase 5.

Operator guide: [Odoo local workflow](ODOO-LOCAL.md).
Engineering contract: [Business API v1](CONTRACT-V1.md).
