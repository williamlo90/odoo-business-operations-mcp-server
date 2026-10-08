# Phase 5 — Offline automation and recovery

Status: implementation complete. The worker uses the same deterministic skill
handlers as the assistant. Validation uses temporary SQLite databases and simulated
domain HTTP, including real CLI/MCP subprocesses. Live PostgreSQL/Odoo integration,
provider canaries and local inference remain Phase 6.

## Ownership and boundaries

`backend.worker` owns event deduplication, schedules, leases, checkpoints and job
outcomes. SQLite is a single-host orchestration store; the domain backend,
PostgreSQL and Odoo remain authoritative for business records and operations.
No new Python dependencies are required. n8n is not required.

The worker accepts typed skill requests, reads records and prepares proposals.
It never grants approval or executes an Odoo write. A human follows the Phase 2
approval and execution workflow. `awaiting_approval` completes the preparation job;
it does not mean that an Odoo record was created. Reconciliation only reads an
existing operation and checks its receipt.

## Configuration

Use Python dependencies from `backend/requirements.lock`, and install/build the pinned MCP
dependencies with `npm ci --prefix mcp-server` and `npm run build --prefix mcp-server`.
The following operational commands need a running domain API; they are instructions
for Phase 6, not commands used to start Docker during Phase 5.

Configure an ignored local environment file:

```dotenv
API_URL=http://127.0.0.1:8020
WORKER_USERNAME=operator.a
WORKER_PASSWORD=<local password>
WORKER_TENANT_ID=<tenant UUID returned by /me>
WORKER_TRANSPORT=mcp
```

Use an authorized operator for proposal preparation, or an authorized reader
(operator, approver or auditor) for reads. The seeded `worker` role has no business
permissions; this implementation does not elevate that role. Provisioning a
dedicated least-privilege account and validating it on the real stack belongs to
Phase 6. The configured tenant must match authenticated `/me` before any job action.
For company B, use its own credentials and tenant UUID in a separate ignored profile.

The default queue is `local/worker/jobs.sqlite3` (ignored by Git). For actual use,
choose a local, non-synchronized path such as
`--queue "$env:LOCALAPPDATA/OdooOps/jobs.sqlite3"` on Windows. Do not share this file
over OneDrive or across hosts. Its requests and results contain business data;
protect the file with the operating-system account permissions. Credentials are
not stored in the queue. Scope checks also bind each job to its actor and tenant.

## Event and schedule commands

Save a request to `local/research.json`:

```json
{"request":{"skill":"research_customer","customer_reference":"OPS-A-001","include_opportunities":false}}
```

From the project root and activated virtual environment:

```powershell
python -m backend.worker --env-file .env enqueue customer-review-001 local/research.json
python -m backend.worker --env-file .env run-once
python -m backend.worker --env-file .env inspect <job-id>
python -m backend.worker --env-file .env schedule customer-review 300 local/research.json
python -m backend.worker --env-file .env --max-ticks 12 --poll-seconds 5 run
python -m backend.worker --env-file .env disable-schedule customer-review
```

Place global options before the command. `enqueue` is the event ingestion interface;
there is no exposed webhook or background service installed. An upstream caller
supplies a stable event key. Repeating the same tenant/key/actor/request returns the
same job; changing the payload or actor for that key is rejected.

The explicitly started worker loop owns schedule ticks. Intervals are 60–86400
seconds, at most 20 schedules per identity. The first tick is due immediately;
missed intervals coalesce into the latest time bucket, avoiding a catch-up burst.
Each bucket has a deterministic event key. Schedule definitions are immutable;
disable an old definition and use a new name for changed input. Disabling stops
future enqueueing, but does not cancel jobs already queued. Each tick claims at
most one eligible job. `run` is bounded (default 12 ticks, maximum 1000), logs in
again each tick and exits on configuration/authentication failure.

## Recovery

| State | Meaning and action |
| --- | --- |
| `queued` / `running` | Waiting or held under a 90-second lease; handler timeout is at most 60 seconds |
| `retry_wait` | Transient read failure or unresolved operation; backoff 5 then 10 seconds, at most three attempts |
| `awaiting_approval` | Proposal available; use the human approval workflow |
| `completed` | Read or verified reconciliation finished; stored results describe that observation |
| `review` | Inspect the job and domain records before deciding what to do next |
| `dead` | Attempts exhausted or terminal failure; investigate the cause before submitting new work |

Atomic claims prevent concurrent ownership. Checkpoints are written before skill
dispatch. A process crash before dispatch may be recovered after lease expiry;
an interrupted dispatched prepare job enters `review`. Lost prepare responses and
prepare timeouts also enter `review`, with no automatic resubmission. Old lease
owners cannot commit a result after recovery. Known pre-write transient failures
may retry; uncertain writes cannot. Reads of unresolved operations end in `review`
after three attempts instead of replaying the underlying write.

Use `inspect` to see the job result, sanitized error and event history. For an
uncertain proposal, inspect existing proposals/audit records in the domain before
submitting anything with a new event key. There is intentionally no blind reset or
retry command. A completed job replay does not refresh its business data; use a
new event key for a new observation. Database schema/application identifiers reject
unrelated or incompatible queue files. Stop workers before backing up the queue;
restore/production capacity testing remains a later reliability gate.

## Verification

Run `.venv/Scripts/python.exe deploy/check_offline.py` on Windows (or the equivalent
virtual-environment Python elsewhere). It performs lightweight gates sequentially:
49 assistant tests, 16 worker tests, 2 TypeScript client tests and 8 MCP scenarios,
including both TypeScript builds. Tests use synthetic records and no live AI calls.

Worker cases cover duplicate events, conflicting keys, concurrent claims, tenant
isolation, bounded backoff, lost writes, expired credentials, unknown operations,
schedule deduplication, a real child-process crash, lease fencing, timeout handling
and rejection of unrelated databases. The MCP suite also launches separate worker
CLI processes and verifies durable replay with exactly one prepared proposal.

Evidence: [test output](evidence/phase5-offline-tests.txt) and
[source manifest](evidence/phase5-source-manifest.json). Checkpoint: `phase-5-code`.
