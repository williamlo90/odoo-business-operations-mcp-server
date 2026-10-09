# Connected MCP → approval → MCP → Odoo journey

Recorded on 2026-10-09 against the local synthetic Odoo 19 sandbox. The browser and MCP calls used the current Phase 9B source in this repository. No model request or customer data was involved. The screenshots below are captures from the actual local Odoo and approval UI, not mockups.

![Odoo draft quotation S00150 created by this run](../assets/odoo-quotation-s00150.png)

![The separate approver reviewing the exact proposal before approval](../assets/approval-review.png)

## Sanitized connected transcript

| Step | Caller and tool/action | Relevant input → observed result |
| --- | --- | --- |
| 1 | Operator · `odoo.customer_search` | `query=OPS-A-001` → scoped customer `#7`, company `#2`; source page carried a revision token. |
| 2 | Operator · `odoo.catalog` | Catalog read → `OPS-A-P1` at IDR 100,000 and `OPS-A-P2` at IDR 50,000. |
| 3 | Operator · `odoo.quote_prepare` | Customer `#7`, product `#1 × 2`, product `#2 × 1` → proposal `d7a03ef2-22cc-4ee5-8b9d-b3880d936459`, total IDR 250,000. No Odoo order yet. |
| 4 | Approver · browser `POST /v1/proposals/{id}/approve` | Separate `approver.a` reviewed company, customer, lines, source version and expiry → approval `9caba731-e397-483d-9e73-b94f241d7912`. The browser had no execute control. |
| 5 | Operator · `odoo.review_status` | Proposal ID → same approval ID; this read tool cannot authorize or dispatch. |
| 6 | Operator · `odoo.execute_approved` | Proposal ID + approval ID + stable idempotency UUID → verified operation `1f1ddcc0-0c35-4f57-bb57-c2c836dc821c`, Odoo `sale.order` `#150` / `S00150`. |
| 7 | Operator · `odoo.execute_approved` replay; `odoo.operation_status` | Same idempotency UUID returned the same operation; status remained `verified` with Odoo read-back: draft, company `#2`, customer `#7`, two matching lines and IDR 250,000. |
| 8 | Other company · approval-page read | `operator.b` opening the review link received `proposal_not_found`; no proposal detail was shown. |

The proposal source version was `d9a951d2ac6394a530263d6585ceea4312305edf5b7026597c57803d02622b03`; its payload hash was `b1008042757281306567d79d8c9c7d30205a1754006cd108b52d1c30f092d918`. The approval binds to that hash. The Odoo read-back verified a **draft quotation**, not a confirmed sale.

After replay, a direct query against the local application and Odoo PostgreSQL databases returned `1|1`: one `ops_operation` row for the operation ID and one `sale_order` whose `client_order_ref` is `ops:1f1ddcc0-0c35-4f57-bb57-c2c836dc821c`. The browser acceptance wrote its raw synthetic result and screenshots to ignored `local/web-acceptance/`; the two presentation screenshots above were copied from that run.

Reproduce with the [local stack](../USER-GUIDE.md) running and private `.env` configured:

```powershell
npm ci --prefix client
npm run build --prefix client
npm ci --prefix mcp-server
npm run build --prefix mcp-server
npm ci --prefix tests/web
npm test --prefix tests/web
```

The test creates a new draft on each run. The numeric Odoo name and IDs above are evidence for this recorded run and will differ when reproduced.
