# Phase 9 — Delivery and cloud preparation

Complete for the selected local delivery scope. The application remains exactly
at Phase 8 `e42441a`; this phase adds documentation, an actual CLI recording,
release verification and an Azure proposal. It creates no cloud resources.

The [delivery pack](../PROJECT-DELIVERY.md) links the English user guide,
acceptance checklist, local recovery runbook, migration/release specification,
owner handover and proposed cloud topology. The [recorded demo](demo/index.html)
contains nine actual CLI stages covering correct quotation, ambiguous selection,
unauthorized approval, verified write, caller restart/resume, replay and tenant
isolation. Direct Odoo queries confirmed one ledger entry and one draft order.
Recovery here means resume/replay; the separately recorded Phase 8 fault injection
covers lost downstream responses. No paid model call was needed for this demo.

The source manifest freezes all tracked release files except itself. The release
commit is resolved through the annotated `phase-9-delivery` tag. Run
`python deploy/check_release.py` to validate source hashes and unchanged qualified
application code. Dependencies remain locked; original image IDs and migration
checksums are preserved. There is no new schema change or model-quality score.

The [Azure proposal](AZURE-PLAN.md) uses one restricted synthetic-demo VM and
preserves private API/MCP paths. Linux B2ls v2 compute in Southeast Asia was quoted
at $0.0528/hour by the public Azure Retail Prices API. Other-service costs are
explicit planning allowances. Proposed budgets, subscription, network access,
domain and alert recipient require selection before Phase 10 provisioning.
IaC, registry publication, HTTPS and actual cloud acceptance belong to Phase 10.

Validation: the nine-stage connected CLI demo passed; release file hashes and
unchanged application source passed verification. Static HTML uses escaped
recorded output and no third-party script. No broad repetition of Phase 8 load,
model inference or recovery was necessary because runtime code did not change.
Phase 9 follows one phase = one commit and leaves the healthy local stack intact.
