# Local operations and recovery runbook

Applies to the synthetic `odoo-ops-local` environment and the local reference
client/MCP/worker. William is the local owner of credentials, approvals,
backup files and incident decisions. Cloud deployment and human paging are
not configured. Do not apply these commands to production data.

## Readiness and monitoring

From the repository root, with its virtual environment active:

```powershell
python -m backend.monitor check --samples 2 --interval 5
python -m backend.monitor receive
```

The first command samples API/database readiness; two consecutive failures
create one durable incident. Two successes close it. The second command is a
local receiver that acknowledges queued transitions. It does not send a message
to a person. Restarting the monitor preserves incident state. Run the check
periodically while operating this sandbox; no background scheduler is installed.
After receipt, the local operator must inspect the incident and act on it.

To include an existing worker queue:

```powershell
python -m backend.monitor check --queue local/worker/jobs.sqlite3 --samples 2
```

A wait over 300 seconds or any `review`/`dead` job makes this check unhealthy.
Only pass an existing worker database; an unrelated SQLite file is rejected.
The monitor does not automatically check Odoo, provider credentials, model
quality or spend. Check `/v1/odoo/info` with a scoped session and inspect task
receipts when readiness is green but a business task fails.

Authenticated operators, approvers and auditors can read `GET /v1/metrics`:
operation counts by status, proposal count and oldest unresolved operation age,
all restricted to their tenant. `administrator` and the unassigned `worker`
role do not receive business access. Monitor unresolved-age trends; this metric
is time since the last operation update, not time since original dispatch.

HTTP responses carry `X-Correlation-ID` and `X-Downstream-Duration-Ms`.
Structured API logs connect this ID to allowlisted Odoo method, status and
duration. MCP receipts carry MCP/domain correlation IDs; assistant traces carry
task/version, model latency and outcome. Durations exclude human approval time.
Use `docker compose -f compose.yaml -f compose.odoo.yaml logs --tail 100 api`
locally; share only sanitized relevant events.

## Failure handling

| Symptom | Operator action |
| --- | --- |
| Provider timeout, refusal or malformed output | Inspect the sanitized task error. Fix the provider configuration or wait for service recovery, then submit a new task ID. Never convert a failed model response into a guessed proposal. Local-only tasks cannot fall back to a hosted provider. |
| `platform_credentials_expired` | Stop relevant producers. Rotate the connector API key through the project setup procedure, update ignored `local/odoo-config/connections.json`, restart the API and verify scoped `/v1/odoo/info`. Do not paste credentials into traces or issues. |
| `source_changed` / stale approval | Refresh source records and prepare a new proposal. A separate approver must approve its current hash. The previous approval cannot be repurposed. |
| `unknown`, interrupted dispatch or missing receipt | Preserve operation/task/job IDs. Reconcile the existing operation through `odoo.operation_status` or the reconciliation skill. Do not create a second write or a new idempotency key to make the status green. Escalate persistent uncertainty to the local owner. |
| Worker `review` / `dead` | Inspect the job and its event history. Confirm the remote effect before considering a new event. Reads retry at most three attempts; uncertain preparation is not automatically repeated. There is no blanket reset-to-queued command. |
| Worker stopped while leased | Restart the same scoped queue/identity. Expired read leases may recover; a dispatched preparation moves to review. The old owner cannot commit a late completion. Do not edit lease state by hand. |
| API readiness fails | Inspect this project's API and database health, disk space and memory caps. Restore connectivity before resuming work. Successful HTTP health alone does not prove Odoo business correctness. |
| Duplicate incident | Compare the incident ID and receipt. The spool deduplicates repeated unhealthy samples; a new incident after a completed recovery is intentional. Receipts prove local consumption, not human acknowledgement. |
| Suspected duplicate business effect | Stop writes for the affected workflow, retain IDs and inspect the Odoo operation ledger and draft order reference. Do not delete audit history. Resolve with the local owner before restarting. |

Inspect an individual worker job using its own profile and queue:

```powershell
python -m backend.worker --env-file local/worker-profiles/company-a.env --queue local/worker/jobs.sqlite3 inspect JOB_UUID
```

## Backup and isolated recovery drill

Take a matching backup before upgrades and after material sandbox changes.
Stop all host workers, scheduled producers and load scripts first. The drill
stops only this project's API/Odoo while preserving its database volumes.
Allow approximately two minutes of local service interruption. It backs up:

- Application and Odoo databases, plus matching Odoo filestore.
- Connector configuration and required infrastructure keys in private files.
- Existing standard assistant/worker SQLite stores using SQLite's backup API.

Custom queue/trace locations require separate backup; the script's fixed path
list is explicit. Hosted provider keys are not included in the backup. Retain
access to those separately in the owner's secret store.

Before an upgrade, capture the running compatible API and Odoo image IDs in
ignored `local/phase8-baseline.json` with the keys `api` and `odoo`. Use
`docker compose ... ps -q SERVICE` followed by
`docker inspect --format '{{.Image}}' CONTAINER_ID`; do not export full inspect
output, which contains environment secrets. Keep these images available.
Build/start the candidate using the three Compose files below. A baseline from
before an incompatible schema migration requires its matching database restore;
an image switch alone is not a migration rollback.

```powershell
$env:ODOO_LIVE_TESTS='synthetic-sandbox'
$env:RECOVERY_QUIESCE_CONFIRMED='yes'
python -m deploy.recovery_drill
```

The script refuses existing `odoo-ops-drill` resources or an occupied port 8021.
It verifies snapshot hashes, restores into new isolated volumes, compares
critical table content and filestore hashes, invalidates restored sessions,
then authenticates and reads back an existing verified Odoo operation. Restored
job stores are integrity-checked but never automatically replayed. It tests a
database outage, local alert receipt/recovery, rollback to the recorded API
image and rollforward. Cleanup checks this run's container labels, removes only
drill resources, restarts the source and verifies its business read-back.

Check `local/phase8-recovery.json` for `passed` and `source_resumed`, and keep
the corresponding private `local/recovery/RUN_UUID` backup. A failed drill
must not be promoted over the source. If interrupted outside Python cleanup,
inspect project labels before removing anything, then restore the source with:

```powershell
docker compose -f compose.yaml -f compose.odoo.yaml -f compose.resources.yaml up -d --no-deps --wait --wait-timeout 90 odoo api
```

No automatic disaster promotion is implemented. Actual data-loss recovery must
first repeat the isolated drill with the chosen backup, validate tenant scope,
reconcile pending operations and invalidate sessions before any cutover.

## Rollback, retention and support

For a model/prompt rollback, choose an approved pinned profile, restart the
caller and use a new task ID. Never reuse cached evidence from a different
contract/model fingerprint. Phase 7's frozen quality reproduction uses its own
`phase-7-quality` source snapshot; Phase 8 contract `0.3.2` has stronger numeric
grounding. New model/prompt changes require new evaluation before promotion.

Store `.env`, profiles, SQLite task data, dumps and filestore under the owner's
restricted local account. This workspace is inside OneDrive: ignored Git files
may still sync through OneDrive. Keep real secrets/backups only in an
owner-approved private location with appropriate sync and access settings.
Do not upload private backups or raw task payloads to the repository.

For this sandbox, retain the latest two verified backups and the last 30 days
of sanitized diagnostic logs/acknowledged alert history; the owner performs
retention manually after confirming a usable newer backup. Unresolved incident
evidence and business audit records remain until resolved; there is no automatic
purge or database audit deletion. Public evidence contains synthetic IDs,
aggregate metrics and hashes, not keys or session tokens.

Escalate persistent uncertainty, authentication failures or failed restore to
the local owner. Review the regression cases and operational limits before
every release. Phase 9 supplies the complete delivery pack; Phase 10 must prove
cloud alerts, backup access and recovery again in its own environment.
