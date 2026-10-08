# research_customer

Version 0.3.0. Owner: Odoo Business Operations project.

Use to retrieve a customer's sourced profile and optionally their opportunities.
Do not use for editing records, approving proposals or unrestricted searches.

Preconditions: authenticated operator, approver or auditor; exact customer reference.
Binding and schemas: [manifest](manifest.json), [input](input.schema.json), [output](output.schema.json).

1. Validate the caller using `/me`; no scope comes from model output.
2. Read `/v1/customers` in revision-bound pages (100 records/page, at most 10 pages).
3. Require one exact reference. Otherwise return `needs_input` with bounded candidates.
4. If requested, read `/v1/opportunities` and retain this customer's records.
5. Return whitelisted fields and source record references; no model-authored factual summary.

Permissions: GET only. No Odoo side effects or approval step for this read.
Limits: 10 seconds/request, 60 seconds/task, at most 16 domain calls, no automatic retry.
Changed pagination revisions or malformed responses fail explicitly; cancellation
propagates to HTTP calls. Retry a read as a new task after resolving the cause.
Postcondition: every returned fact originates in the authenticated domain response.

Example: `{"skill":"research_customer","customer_reference":"OPS-A-001","include_opportunities":true}`.
Normal, ambiguous, source-injection and failure fixtures are covered in
`tests/assistant/test_core.py`. Changelog 0.3.0: initial HTTP implementation;
simulated transport validation, connected validation pending.
