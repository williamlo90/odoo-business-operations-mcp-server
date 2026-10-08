# prepare_crm_activity

Version 0.3.0. Owner: Odoo Business Operations project.

Use to prepare a CRM follow-up with explicit opportunity ID, assignee ID, ISO date
and summary. Do not guess owners/dates or send notifications/email.

Preconditions: authenticated operator; all fields supplied; valid calendar date.
Binding and schemas: [manifest](manifest.json), [input](input.schema.json), [output](output.schema.json).

1. Validate identity, role and strict input contract.
2. Read `/v1/opportunities/{id}` and verify the returned record identity.
3. POST the supplied fields to `/v1/activities/prepare`; the domain enforces company
   scope, assignee eligibility and supported policy.
4. Verify proposal scope/payload/preview and return `awaiting_approval` with evidence.

Effect: application proposal only. Creation in Odoo requires human approval and
the existing approved-execute workflow. There are no automatic write retries.
Timeout after prepare is uncertain; inspect the application proposal/audit before
retrying manually. Cancellation does not imply server rollback.
Limits: 10 seconds/request, 60 seconds/task, 16 domain calls. No compensation needed
for an unexecuted proposal. Postcondition: matching preview, not a created activity.

Example: `{"skill":"prepare_crm_activity","opportunity_id":1,"assignee_id":5,"due_date":"2026-10-20","summary":"Follow up proposal"}`.
Valid preview, missing date, invalid date and malformed-output fixtures are in
`tests/assistant/test_core.py`. Changelog 0.3.0: initial HTTP implementation;
connected validation pending.
