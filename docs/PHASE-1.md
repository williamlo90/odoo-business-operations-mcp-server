# Phase 1 — Local foundation delivery

Date: 2026-10-08 (Asia/Jakarta). Run ID: `phase1-20261008-01`.
Status: **passed for the Phase 1 local foundation gate**.

## Delivered behavior

An authorized operator logs in, selects an explicit synthetic customer reference,
records a research request, reads back its persisted tenant/actor/customer/status,
and logs out. Creation and its audit event share one PostgreSQL transaction.
Anonymous users and unauthorized roles cannot create requests; cross-tenant records
are rejected without revealing whether they exist.

The backend uses FastAPI, Argon2 password hashes, revocable opaque bearer sessions,
database-backed actor/role checks, strict input models, bounded pagination and
sanitized structured request logs. PostgreSQL composite foreign keys prevent
cross-tenant relationships. The runtime database role has no schema creation or
actor-management privileges. Migration credentials are confined to management jobs.

The TypeScript CLI is the Phase 1 reference client. It uses HTTP; the MCP protocol
implementation remains Phase 4. No empty executable placeholders were created.
Structure and future boundaries are documented in `mcp-server/` and `skills/`.

## Verification

| Check | Result / evidence |
| --- | --- |
| Real PostgreSQL + HTTP automated suite | **17 passed**, 2.39 seconds; [test run](evidence/phase1-test-run.txt) |
| Containerized TypeScript client | **passed**; [receipt](evidence/phase1-client.json) |
| Independent installation with empty volume | **passed**, dedicated `odoo-ops-phase1-clean` Compose project; [install transcript](evidence/phase1-clean-install.txt) |
| Database outage and recovery | Readiness 200 → 503 → 200, liveness remains 200; [recovery evidence](evidence/phase1-recovery.json) |
| Dependency/install checks | `npm ci`, TypeScript build and Python `pip check` passed |
| Secrets | Generated in ignored `.env`; Git ignore verified; API validation and logs tested for secret/token reflection |
| Isolated reset | Dedicated test DB on tmpfs; rejects local environment or a non-test database name; repeatable migration and seed checked |

The suite covers role denial, tenant isolation, forged context, persisted audit,
session logout/expiry/deactivation, live role changes, input validation, pagination,
login rate limit, log redaction, database constraints and migration/seed repeatability.
These are Phase 1 cases; the 20 V1 acceptance cases remain future implementation
targets, and are not reported as passed.

The installation replay used new containers and an empty project volume on this
machine with Docker's image/build cache available. It was not tested on a second
physical machine. Its resources and the isolated test project were removed after
verification. The normal local API and database remain available on loopback port
8020, with their synthetic data preserved.

## Runtime versions

Docker Engine 29.8.0, Compose 5.5.1; container Python 3.13.16, PostgreSQL 17.11,
Node 22.23.3; TypeScript 5.9.3; FastAPI 0.142.4, Psycopg 3.3.6.
Python dependencies are pinned in `backend/requirements.lock`, client dependencies
in `client/package-lock.json`, and container bases by SHA256 digest in Dockerfiles
and Compose. Application source hashes/revision are recorded in
[source manifest](evidence/phase1-source-manifest.json).

## Environment recovery

Docker Desktop initially failed to start because its Secrets Engine could not
rename a stale socket. Its stopped/failed processes were restarted after preserving
the socket directory at
`C:\Users\William\AppData\Local\docker-secrets-engine-phase1-backup-20261008`.
No existing container images or volumes were deleted. Docker may auto-start other
pre-existing containers according to their existing restart policies.

## Limits and next work

Phase 1 creates local work requests only. Each demo invocation creates a new local
request; it does not claim business-operation idempotency. Odoo connectivity,
quotations, approval binding, external-write deduplication, skills and AI remain
scheduled work. No provider credentials, Odoo tenant or cloud resources were used.

Phase 2 adds deterministic business workflows, reference outcomes and the Odoo
adapter contract, including pricing, approval/version rules and retry/reconciliation.
The Odoo API/version and atomic write design must be validated before connected
write claims. MCP SDK/protocol versions will be pinned when its implementation
begins; there is no unused SDK dependency in Phase 1.

Operator instructions: [Local setup and daily use](LOCAL-SETUP.md).
