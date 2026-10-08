# prepare_quote

Version 0.3.0. Owner: Odoo Business Operations project.

Use to prepare a quotation preview for an exact customer reference and product
codes with positive integer quantities. Do not use to confirm orders, set prices,
grant approval, create invoices or execute Odoo writes.

Preconditions: authenticated operator; all required fields provided.
Binding and schemas: [manifest](manifest.json), [input](input.schema.json), [output](output.schema.json).

1. Validate identity and require the operator role.
2. Resolve the customer by exact reference using revision-bound pagination.
3. Read `/v1/catalog`; resolve each product code uniquely. Missing/ambiguous records
   return `needs_input` without a proposal. Duplicate products are rejected.
4. POST only customer/product IDs and quantities to `/v1/quotes/prepare`.
5. Validate returned scope, payload, line quantities and arithmetic. Return the
   domain proposal as `awaiting_approval`; prices and pricing policy belong to the domain.

Effect: creates an application proposal, not an Odoo quotation. Human approval and
approved execution use the existing Phase 2 client. Never automatically retry a
prepare request: a lost response is `proposal_outcome_unknown`. Inspect application
records/audit before preparing again. No automatic compensation or external write.
Limits: 10 seconds/request, 60 seconds/task, 16 domain calls. Cancellation stops
waiting but does not prove the server rolled back; resolve uncertain outcomes first.
Postcondition: a matching proposal preview, never a claim that an Odoo order exists.

Example: `{"skill":"prepare_quote","customer_reference":"OPS-A-001","items":[{"product_code":"OPS-A-P1","quantity":2}]}`.
Tests cover valid preview, ambiguous customer, invalid quantity, duplicate products,
scope/total mismatch, denied role and lost response in `tests/assistant/test_core.py`.
Changelog 0.3.0: initial HTTP implementation; live validation pending.
