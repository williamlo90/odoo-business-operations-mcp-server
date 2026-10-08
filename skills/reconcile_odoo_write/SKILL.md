# reconcile_odoo_write

Version 0.3.0. Owner: Odoo Business Operations project.

Use to inspect an existing operation by UUID. Do not use to execute or retry writes,
infer success from a model statement, or search arbitrary Odoo models.

Preconditions: authenticated operator, approver or auditor; operation UUID provided.
Binding and schemas: [manifest](manifest.json), [input](input.schema.json), [output](output.schema.json).

1. Validate the session and operation ID.
2. GET `/v1/operations/{id}`; the domain performs reconciliation and audit as defined
   in Phase 2, without creating another Odoo record.
3. Check returned operation/tenant IDs. `verified` requires a matching receipt ID.
4. Preserve the authoritative domain state, including `unknown`, `review`, `failed`
   and `dispatched`. Return structured evidence; never upgrade an uncertain state.

Effect: Odoo read plus application reconciliation/audit updates. Approval is not
required for status lookup; any later retry remains in the approved domain workflow.
Limits: 10 seconds/request, 60 seconds/task, 16 domain calls; no automatic retry.
On failure, report the error and inspect/retry status manually. Cancellation stops
the caller's wait; subsequent status lookup is the recovery path.

Example: `{"skill":"reconcile_odoo_write","operation_id":"e43442d8-eaaa-4426-9f1a-4d00945bf6db"}`.
All five domain states and no-write behavior are tested in `tests/assistant/test_core.py`.
Changelog 0.3.0: initial HTTP implementation; connected validation pending.
