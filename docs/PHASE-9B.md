# Phase 9B — MCP-first product boundary

This checkpoint narrows the Phase 9A full workspace into an independent approval page. Customer lookup, catalog read, quotation or CRM preparation, execution and reconciliation belong to the MCP client. The browser displays one proposal and records only a human decision. The earlier `phase-9a-web-ui` tag remains a complete learning snapshot of the broader UI.

The implementation adds `odoo.review_status`, a read-only MCP tool that returns the approval ID and saved operation status for a scoped proposal. It does not create approval. The operator can therefore resume the original MCP conversation after a separate approver acts in the browser. Existing tenant, role, payload-hash, source-freshness, expiry and idempotency rules remain in the domain service and Odoo addon.

The [connected synthetic journey](evidence/mcp-first-journey.md) records source lookup → proposal → browser approval → MCP execution → Odoo read-back, replay, cross-company denial and one final database effect. The README uses actual screenshots of the approval page and resulting Odoo quotation. The [approval guide](WEB-UI.md) explains local use and recovery.

To reproduce: start the local sandbox using the [operator guide](USER-GUIDE.md), build the client and MCP packages, then run `npm test --prefix tests/web`. Offline checks use `deploy/check_offline.py`. The connected test creates a new draft and needs no model request.
