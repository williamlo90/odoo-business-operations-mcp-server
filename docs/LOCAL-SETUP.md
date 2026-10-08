# Local setup and daily use

Phase 1 provides a local HTTP API, PostgreSQL database and TypeScript command-line
reference client. It records a customer research request and reads it back. All
customers are synthetic. Odoo, quotation approval, AI and MCP execution arrive in
later phases.

## Prerequisites

- Docker Engine with Linux containers and Docker Compose v2 or later (Docker
  Desktop with WSL2 on Windows is supported).
- Python 3.10+ for the credential-generation helper. Application Python runs in
  its container; a host Python environment is optional.
- Git. Node 22+ is optional if developing the client outside Docker.
- Free loopback port 8020. Change `API_PORT` in `.env` if occupied.

Run every command below from the project root. No cloud account or AI key is
required. The application database is not published to the host network.

## First installation

```sh
python deploy/setup_env.py
docker compose config --quiet
docker compose up --build -d --wait api
docker compose --profile client run --rm --build client
```

The helper creates random passwords in ignored `.env`, preserving an existing
file. Do not commit or share this file. `POSTGRES_PASSWORD` belongs only to the
migration/seed owner; `APP_DB_PASSWORD` belongs to the restricted runtime role.
`DEMO_PASSWORD` is shared by synthetic demo accounts only. Never use these accounts
for real users. Keep `.env` private to your local OS account.

Compose creates the project database, applies versioned migrations, then seeds
two companies, ten actors and four customers. Repeating startup preserves data.
An applied migration is immutable: a checksum mismatch aborts migration. Add a new
numbered migration for schema changes.

The CLI logs in as `operator.a`, selects the explicit reference `A-001`, creates a
local research request, reads it back, checks actor/tenant/customer/status, and
logs out. Successful output includes `result: passed` and `status: recorded_local`.
It never prints passwords or access tokens. This is a recorded local request,
not completed research or an Odoo quotation.

Health: `http://127.0.0.1:8020/health/ready`.
API documentation: `http://127.0.0.1:8020/docs`.

## Accounts and authorization

Each account exists with suffix `.a` and `.b` for separate tenants. Password is
the local `DEMO_PASSWORD` value. Scope is loaded from the database, never a header
or model-provided tenant ID.

| Account prefix | Phase 1 permissions |
| --- | --- |
| operator | Login, list own customers, record and read own-tenant research requests |
| approver | Login and read own-tenant data; approval workflow is not implemented yet |
| auditor | Login and read own-tenant data; no request creation |
| administrator | Login and inspect own identity; business record access is not implicitly granted |
| worker | Login and inspect own identity; no business action until skills are assigned |

Use `POST /auth/login` with JSON `username` and `password`; use the returned token
as `Authorization: Bearer ...`. Tokens expire after 30 minutes, are hashed in the
database, and are invalidated by `POST /auth/logout`. Deactivating an actor or
changing their role takes effect on the next request. Login limits are per
username, ten attempts per minute; this is a local baseline, not production edge
rate limiting. The API binds only to loopback and is not a cloud deployment.

## Daily commands

```sh
docker compose up -d --wait api
docker compose --profile client run --rm client
docker compose logs --tail 50 api
docker compose stop
```

API logs contain route templates, generated correlation IDs, status and duration.
They omit request bodies, URLs/query strings, authorization headers and credentials.
Record the response `X-Correlation-ID` when diagnosing a failed request.

## Automated checks and isolated reset

```sh
docker compose -f compose.test.yaml up --build --abort-on-container-exit --exit-code-from tests
docker compose -f compose.test.yaml down
```

The test Compose project is `odoo-ops-test`; its PostgreSQL uses tmpfs and the exact
database `odoo_ops_test`. Each suite resets only that test schema. The reset command
requires `APP_ENV=test`, `ALLOW_TEST_RESET=yes`, and the exact database name, verified
before any destructive statement. It refuses the local application database.
Tests run a real HTTP server against real PostgreSQL, including roles, tenant
isolation, sessions, audit persistence, migration/seed repeatability and sanitized
logs. No SQLite or mocked database is substituted.

For an explicit fresh test reset without running the suite:

```sh
docker compose -f compose.test.yaml run --rm tests python -m backend.manage reset-test
```

For client development:

```sh
cd client
npm ci
npm run build
```

To run the host CLI, set `DEMO_PASSWORD` in the process environment from your local
secret file, then `npm run demo`. Do not put passwords in command arguments or
paste them into chat. Docker is the default path to avoid this manual step.

## Troubleshooting and cleanup

- Docker connection error: start Docker Desktop and verify `docker version`
  includes a server. Wait for the Linux engine to be ready.
- API readiness 503: inspect `docker compose ps -a` and migration/seed logs. Check
  database connectivity and schema version. Error responses do not expose DB URLs.
- Login 401: check the username and existing seeded password. Re-seeding preserves
  credentials; changing `.env` alone does not rotate existing users/database passwords.
- Login 429: wait one minute before retrying that username.
- 403: the authenticated role does not permit the operation. 404 on a foreign
  record does not disclose whether it exists. 422: invalid or unexpected input.
- Stop/remove project containers while retaining data: `docker compose down`.
- To intentionally discard this project's synthetic database only, run
  `docker compose down --volumes`. This deletes the project's `pgdata` volume.
  Do not use global Docker prune or remove another project's volumes.

## Implementation boundaries

`backend/` owns auth, validation and database transactions; `client/` contains the
working TypeScript CLI; `tests/` contains HTTP/PostgreSQL checks; `deploy/` contains
the container build and local secret helper. `mcp-server/` and `skills/` document
later-phase boundaries without placeholder executable code.

Foundation choices were checked against [FastAPI security guidance](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
for password hashing and [Psycopg transaction documentation](https://www.psycopg.org/psycopg3/docs/basic/transactions.html).
Sessions here are revocable opaque bearer tokens rather than JWTs.
