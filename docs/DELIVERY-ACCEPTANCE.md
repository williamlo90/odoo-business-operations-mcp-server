# Delivery acceptance and recorded demonstration

Application source: Phase 8 `e42441a`; Phase 9 records the unchanged reference
CLI against real local synthetic Odoo. Execute `python -m deploy.record_demo`
with `ODOO_LIVE_TESTS=synthetic-sandbox` after the stack and client build exist.
It deliberately creates one draft per run. No hosted inference is requested.

| Case | Expected | Observed evidence |
| --- | --- | --- |
| Source selection | Scoped customer records, exact reference required | Recording stages 1–2; ambiguous name rejected |
| Quotation | 2 P1 + 1 P2 for A001, total IDR 250,000 | Stage 3 preview matches |
| Separation of duties | Operator cannot approve; approver can | Stages 4–5: 403 then approval receipt |
| Actual business result | One verified Odoo draft | Stage 6 plus SQL ledger/order counts 1/1 |
| Recovery | Saved operation ID resumes verified state | Stage 7 runs in a fresh CLI process |
| Replay | Original execution key does not create another draft | Stage 8 same operation/result; SQL count stays 1/1 |
| Isolation | Tenant B cannot read tenant A operation | Stage 9 returns 404 |
| Lost network response | Reconcile actual Odoo write without a second effect | Phase 8 connected `test_connected_lost_response_reconciles_without_second_write`; separate fault-injection evidence |
| Backup/rollback | Matching restore and image rollback/read-back | Phase 8 recovery evidence; unchanged application release |
| AI intent | Provider/model and outcome remain bounded | Phase 8 hosted/local canaries; Phase 7 historical frozen scores |

The [recorded session](demo/index.html) is a static HTML transcript generated
from actual CLI outputs, with durations and exit codes. Its [JSON recording](demo/recording.json)
contains the underlying receipts. It is not a screen-capture video. Approver
credentials are automated for this synthetic acceptance; human review effort
is not measured. The recovery scene is caller restart/resume, not a newly
injected network failure.

## Reviewer walkthrough

Open the HTML recording and follow the nine sections in order. Compare the
proposal's company, customer, product lines and total with the final receipt.
Observe the operator's denied approval and the foreign tenant's denied lookup.
Compare execution and replay operation IDs. For live reproduction, follow
`USER-GUIDE.md` and then the command above; allow old login-rate windows to expire
between repeated demos instead of disabling authentication limits.

## Delivery inventory

- Business purpose and validated results: `PROJECT-DELIVERY.md`.
- Installation, daily use, statuses and examples: `USER-GUIDE.md`.
- Failures, backup, restore and rollback: `LOCAL-RUNBOOK.md`.
- Versioned inputs, configuration and migration plan: `RELEASE.md`.
- Owner, operating cadence and backlog: `HANDOVER.md`.
- Proposed cloud topology, cost envelope and deployment gates: `AZURE-PLAN.md`.
- Recorded demo and sanitized release manifest: `demo/` and `evidence/phase9-manifest.json`.

Phase 9 acceptance covers this local delivery pack. Cloud deployment, image
registry publication, remote access and cloud alert/restore tests are pending
Phase 10; no Azure resource has been provisioned by this phase.
