# Independent approval page

The current browser has one job: let a separate person inspect and approve an exact MCP-prepared proposal. It does not search customers, build quotations, schedule activities, dispatch Odoo writes, or retry operations. Those actions remain in the MCP client and domain service. [The earlier Phase 9A workspace](PHASE-9A.md) is preserved as a tagged learning checkpoint.

![Actual synthetic approval page before the human decision](assets/approval-review.png)

## Use the page

1. The operator prepares a proposal through `odoo.quote_prepare` or `odoo.activity_prepare` and sends its ID or local review link: `http://127.0.0.1:8020/#proposal/<proposal-id>`.
2. A separate approver signs in, checks company, target, line items or activity details, source version, total, expiry and payload hash, then explicitly approves.
3. The operator calls `odoo.review_status` with the proposal ID to retrieve the approval ID. The original operator then calls `odoo.execute_approved` using that ID and a stable idempotency UUID, followed by `odoo.operation_status`.
4. The approval page can be refreshed to display the saved outcome. The actual quotation or activity is inspected in Odoo.

The page also accepts a proposal ID after sign-in when a full review link is unavailable. An operator may read a proposal and its saved status, but only an approver account can approve. A creator cannot approve their own proposal; cross-company reads return no detail. Backend checks, not hidden buttons, enforce these rules.

## Local operation and recovery

Follow the [operator guide](USER-GUIDE.md) to start the synthetic stack. The page is served at [localhost:8020](http://127.0.0.1:8020/). Use the private `DEMO_PASSWORD` from `.env` for local synthetic accounts `operator.a`, `approver.a` and their `.b` equivalents. The page stores the bearer token only in memory; reload requires sign-in again. Source values are escaped, responses are `no-store`, and a same-origin CSP with frame denial protects the surface.

Approval is tied to a payload hash and expiry. A stale source or expired proposal must be prepared again. When execution has an uncertain response, the operator reads `odoo.review_status` and `odoo.operation_status` and reuses the original idempotency key. Do not create a new proposal to guess whether the first write succeeded. No retry is initiated from this page.

The connected browser test exercises MCP preparation, separate approval, MCP execution/status/replay and company denial. Run `npm test --prefix tests/web` with the local stack active. It creates a synthetic Odoo draft and saves raw outputs in ignored `local/web-acceptance/`. See the [recorded journey](evidence/mcp-first-journey.md).
