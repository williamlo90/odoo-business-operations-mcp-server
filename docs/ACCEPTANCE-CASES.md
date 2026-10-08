# V1 acceptance cases

Specification v0.1, established on 2026-10-08 before implementation. These are
business reference cases, not the Phase 7 model-quality dataset.

The synthetic fixture has companies A/B, separate business roles, same-name
customers and scoped opportunities/products. Company A P1 costs IDR 100,000 and
P2 IDR 50,000 without tax/discount: two P1 plus one P2 must total IDR 250,000.
Company B has separate pricing. Expected results come from source rules.

| ID | Condition | Required outcome |
| --- | --- | --- |
| A01 | Unique permitted customer | Correct ID/company/source; no write |
| A02 | Same-name customers | Require explicit selection; no automatic quotation |
| A03 | Cross-company access | Reject at service/API/MCP; no foreign data |
| A04 | Valid opportunity | Source-matching customer, stage and owner; no write |
| A05 | Prepare two P1 and one P2 | Correct IDR 250,000 preview; no Odoo draft yet |
| A06 | Authorized approval and execution | One matching draft, receipt and read-back |
| A07 | Missing/expired approval or wrong role | Reject before write; record reason |
| A08 | Modified payload/tenant/actor | Reject old approval; require matching context |
| A09 | Source/pricing changes after preview or during execution | Refresh preview and approval before writing |
| A10 | Replay/concurrent execution | One effect and consistent outcome; count final records |
| A11 | Response times out after a draft is created | Unknown until lookup/read-back; no blind create retry |
| A12 | Failure before write, rate limit or expired credentials | Classified error, safe bounded retry, no false success |
| A13 | Multi-page retrieval | No missing/duplicate records on fixed fixture; detect revisions |
| A14 | Forbidden model/field/URL injection | Reject without leakage or side effects |
| A15 | Invalid quantity, inactive product or unsupported pricing | Reject preparation; no approval/write |
| A16 | Valid follow-up and approval | One activity with correct opportunity/company/assignee/date; read-back |
| A17 | Missing or mismatched read-back | Unknown/review rather than verified; retain recovery path |
| A18 | Worker restart after dispatch | Reconcile durable state; no second draft |
| A19 | Unauthenticated request or prompt-forged scope | Reject; derive authority from authenticated identity |
| A20 | Second company configuration | Reuse skills with different data/policy |

Record case/revision/fixture identifiers, expected/actual results, pass/fail,
correlation/approval/operation/external IDs, effect counts and sanitized evidence.
A06/A09/A10/A11/A16 require actual Odoo evidence; fakes support fault injection
but do not replace connected acceptance.

Critical permission, stale-approval, duplicate-effect and false-success cases
must pass. Model-quality and workload thresholds are separate. The final Phase 7
score is synthetic regression, not independent holdout. See [Phase 8](PHASE-8.md)
for the current verification scope.
