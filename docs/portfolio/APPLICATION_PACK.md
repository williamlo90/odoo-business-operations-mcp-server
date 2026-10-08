# Portfolio summary

## Short description

Built a custom MCP server for AI-assisted Odoo sales operations using TypeScript,
Python/FastAPI and PostgreSQL, with tenant isolation, source-bound proposals,
separate approval, idempotent execution and verified business outcomes.

## Evidence-backed resume bullets

- Implemented four reusable business skills and ten authenticated MCP tools for
  customer research, quotations, CRM activities and write reconciliation.
- Enforced role/tenant boundaries and proposal-bound approval through the domain
  service and an Odoo addon, with durable operation IDs and read-back checks.
- Validated 124 synthetic local workload tasks, including 31 draft writes with
  exactly one ledger entry and one order per operation across replay checks.
- Tested matching backup/restore, database outage recovery, local alert receipt
  and compatible image rollback; packaged operator guides and immutable learning
  checkpoints for reproducibility.

## Interview discussion

| Topic | Explain with |
| --- | --- |
| Why MCP rather than unrestricted API access? | Narrow capabilities, strict schemas, authenticated scope and bounded calls |
| What happens when a price changes after approval? | Fresh source checks at the Odoo write boundary; a new proposal is required |
| Why does a timeout not immediately trigger another create? | The remote write may already have committed; reconcile the operation first |
| How are model failures contained? | Typed intent, grounded identifiers/quantities, deterministic preview and separate approval |
| What was actually measured? | Named local test suites, workload sample counts, final effects and isolated recovery |
| What remains? | Cloud provisioning/acceptance, longer soak and optional browser-based natural-language assistance |

The project has a tested local release and an Azure design. It should not be
represented as an already deployed Azure service, a customer ROI study or a
production-scale performance benchmark. Use the [case study](CASE_STUDY.md) and
[walkthrough](../demo/README.md) as supporting artifacts.
