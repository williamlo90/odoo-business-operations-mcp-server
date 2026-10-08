# Automation ownership

**Decision: use the standalone MCP server and Python worker. n8n is not selected.**
The implementation, connected workflow and local delivery gates pass without
n8n. Its absence is not a missing dependency or implementation failure.

The worker uses `backend.worker` and a local SQLite queue for orchestration.
Shared skills perform research, preparation and reconciliation. PostgreSQL/Odoo
remain authoritative for business outcomes. Queue state is not proof that a
remote write succeeded. Worker retry, lease and review semantics preserve this
boundary, including a process restart after dispatch.

## Optional future consumers

An n8n workflow could poll opportunity changes and ask the existing skill to
prepare an activity, or periodically request reconciliation of unknown
operations. That extension must explicitly assign ownership of retries,
approval state, scheduling and business state. It must not repeat a create just
because a workflow response was lost.

Approval remains bound to authenticated identity, tenant, payload and source
version. A callback containing the word approved is insufficient. All callers,
including direct API clients and future automation engines, use the same scope
and postcondition checks. The engine choice does not limit what n8n itself can do.

If an extension is requested, define its operator need, benefit, configuration,
cost and acceptance separately. Do not turn an optional integration into a
release prerequisite. See [worker implementation](docs/PHASE-5.md),
[operator guide](docs/USER-GUIDE.md) and [runbook](docs/LOCAL-RUNBOOK.md).
