# Operator guide — local release

This application helps sales operations research customers and prepare quotations
or CRM activities. The assistant proposes; a separate approver authorizes; Odoo
read-back establishes the outcome. The interface is a reference command-line
client. This release has no chat website or browser dashboard.

## Install and resume

Use the `phase-9-delivery` Git tag. Install Docker Desktop with Linux containers,
Python 3.13 and Node.js 22 or newer. Keep ports 8020 and 8069 free. From the project
root, create a Python environment and install the locked dependencies:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.lock
npm ci --prefix client
npm ci --prefix mcp-server
npm run build --prefix client
npm run build --prefix mcp-server
.venv/Scripts/python.exe deploy/setup_env.py
.venv/Scripts/python.exe deploy/setup_odoo_env.py
docker compose -f compose.yaml -f compose.odoo.yaml -f compose.resources.yaml build
docker compose -f compose.yaml -f compose.odoo.yaml -f compose.resources.yaml up -d --wait --wait-timeout 300 api
docker compose -f compose.yaml -f compose.odoo.yaml --profile client build client
```

The setup helpers preserve existing credentials. Initial migrations and synthetic
Odoo initialization run through Compose dependencies. Existing data is preserved.
Linux users substitute `.venv/bin/python` for the Windows Python path.
Do not use this shared-password synthetic seed for real users or public access.

Open `http://127.0.0.1:8020/health/ready` and check `ready`. Odoo's local interface
is `http://127.0.0.1:8069`; its administrator password is `ODOO_ADMIN_PASSWORD`
in your private `.env`. Business accounts use the separate `DEMO_PASSWORD`.
Read [ODOO-LOCAL](ODOO-LOCAL.md) for connector rotation and pricing restrictions.

## A daily quotation

Use these commands from the repository root. The Docker client loads its login
configuration through Compose, so no password needs to appear in command history.

```powershell
docker compose -f compose.yaml -f compose.odoo.yaml run --rm --no-deps client node dist/index.js customers
docker compose -f compose.yaml -f compose.odoo.yaml run --rm --no-deps client node dist/index.js catalog
docker compose -f compose.yaml -f compose.odoo.yaml run --rm --no-deps client node dist/index.js quote OPS-A-001 OPS-A-P1:2,OPS-A-P2:1
```

Expect a proposal with company A, the exact customer reference, two P1 and one P2,
and total IDR 250,000. A proposal is not an Odoo draft. Save its `id` and
`payload_hash`. Check the company, customer, quantity, unit price, total, currency
and source freshness before approval. Same-name customers require exact references.

The following uppercase values are placeholders from the preceding receipts:

```powershell
docker compose -f compose.yaml -f compose.odoo.yaml run --rm --no-deps client node dist/index.js preview PROPOSAL_ID
docker compose -f compose.yaml -f compose.odoo.yaml run --rm --no-deps -e DEMO_USERNAME=approver.a client node dist/index.js approve PROPOSAL_ID PAYLOAD_HASH
docker compose -f compose.yaml -f compose.odoo.yaml run --rm --no-deps client node dist/index.js execute PROPOSAL_ID APPROVAL_ID IDEMPOTENCY_UUID
docker compose -f compose.yaml -f compose.odoo.yaml run --rm --no-deps client node dist/index.js status OPERATION_ID
```

Generate the idempotency UUID once with `[guid]::NewGuid().ToString()` and save it.
Replaying execution uses exactly the same proposal, approval and UUID. Success is
`verified` with the expected Odoo draft record and total. It does not mean the
quotation was emailed, confirmed as a sale or invoiced. Approval expires and is
bound to its original payload; prepare again if the source changes.

In this sandbox, automated acceptance uses both roles with separate identities.
In real operations, the approver is a separate person with distinct credentials.
Company B uses `.b` accounts and `OPS-B-*` references; the same example totals
IDR 290,000. The server derives tenant scope from the authenticated account.

## Optional natural-language assistant

Configure the existing private `.env` with the provider key, then on the host:

```powershell
$env:ASSISTANT_ENV_FILE='.env'
$env:ASSISTANT_PROVIDER='openai'
$env:ASSISTANT_MODEL='gpt-4.1-mini-2025-04-14'
$env:ASSISTANT_LOCAL_ONLY='0'
node client/dist/index.js assistant "Prepare a quotation for OPS-A-001: 2 units of OPS-A-P1 and 1 unit of OPS-A-P2."
```

This makes a paid provider request. Review the returned `result.proposal` using
the same approval workflow above. Explicit numeric quantities are required;
unsupported or incomplete requests stop for clarification. Do not put secrets
or unnecessary personal data in prompts. Save the task UUID printed by the client.
Set `ASSISTANT_TASK_ID` only when deliberately replaying the same task/context;
use a new UUID after changing task, identity, model or contract.

For local-only experiments, follow [Phase 6](PHASE-6.md) to start the pinned
Ollama runtime, then set `ASSISTANT_PROVIDER=ollama`, `ASSISTANT_MODEL=qwen2.5:0.5b`
and `ASSISTANT_LOCAL_ONLY=1`. Its measured quality remains experimental.
Claude and Grok adapters are optional and not live-qualified.

## Interpret outcomes

| State | Meaning and next action |
| --- | --- |
| `read` | Sourced facts returned; no business write |
| `needs_input` | Supply exact missing identifiers/quantities; do not guess |
| `awaiting_approval` | Review the preview with a separate approver |
| `verified` | Odoo read-back matches the intended operation |
| `dispatched` / `unknown` | Keep IDs and reconcile; do not send a new write |
| `review` | Stop automated continuation and ask the local owner to investigate |
| `failed` | Read the sanitized reason; correct source/configuration before a new proposal |

A missing receipt is not evidence that the write failed. Resume with `status
OPERATION_ID`. The [recorded demo](demo/index.html) shows the actual normal,
blocked and resumed workflow, with [machine-readable receipts](demo/recording.json).
It is a saved CLI recording, not a video or live control panel.

## Workers, shutdown and support

Provision each automation identity explicitly with `python deploy/provision_worker.py a`
or `b` in the environment. Follow [Phase 5](PHASE-5.md) for scoped enqueue,
schedules and bounded worker ticks. Worker commands reuse the same skills;
they do not approve or execute business writes. n8n is not required.

Stop host worker producers before shutdown. Preserve Docker volumes:

```powershell
docker compose -f compose.yaml -f compose.odoo.yaml -f compose.resources.yaml stop api odoo db odoo-db
```

Resume with the earlier `up` command. For container/network cleanup, use the same
Compose files with `down`, without `--volumes`. Before an intentional uninstall,
verify a backup and enumerate this project's volumes; data deletion is a separate
owner decision. Do not delete volumes belonging to other projects.

For backup, credential rotation, stuck jobs or unknown writes, follow the
[local runbook](LOCAL-RUNBOOK.md). William owns local support; include sanitized
operation/task/correlation IDs and the version, never credentials.
