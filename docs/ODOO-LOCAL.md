# Odoo sandbox and deterministic workflow

This Phase 2 reference client uses explicit commands and the domain API. It does
not need an LLM. All seeded data belongs to the local synthetic sandbox.

## Install or resume

From the project root, with Docker's Linux engine running:

```sh
python deploy/setup_env.py
python deploy/setup_odoo_env.py
docker compose -f compose.yaml -f compose.odoo.yaml build
docker compose -f compose.yaml -f compose.odoo.yaml up -d --wait api
docker compose -f compose.yaml -f compose.odoo.yaml --profile client build client
```

Initial Odoo module installation can take a few minutes. Keep the `.env` file and
`local/odoo-config/connections.json` private; both are ignored by Git. Do not copy
API keys into chat or public evidence. The setup scripts preserve existing secrets.
Two Odoo connector accounts are bound to one company each. API keys expire after
90 days; expiration returns `platform_credentials_expired`. Re-provision their
keys through the controlled seed command after securely moving the old connection
file aside, then restart the API. Existing approvals must be reviewed if company
bindings change.

Odoo is at `http://127.0.0.1:8069`; backend documentation is at
`http://127.0.0.1:8020/docs`. Odoo administrator login is `admin`, with the local
`ODOO_ADMIN_PASSWORD`. The backend uses its separate seeded accounts and
`DEMO_PASSWORD`. No Odoo database or credentials are exposed by the business API.

The runtime is Odoo Community 19.0, pinned by image digest in `odoo/Dockerfile`,
with Contacts, CRM, Sales and the `ops_bridge` addon. Integration uses JSON-2 at
`/json/2/ops.bridge/<allowlisted-method>`. No legacy XML-RPC fallback is enabled.
Odoo owns its separate PostgreSQL cluster and volume; the application never writes
directly to its tables. Tests may mutate only the named synthetic sandbox to
simulate external edits.

## Inspect and prepare a quotation

```sh
docker compose -f compose.yaml -f compose.odoo.yaml run --rm --no-deps client node dist/index.js customers
docker compose -f compose.yaml -f compose.odoo.yaml run --rm --no-deps client node dist/index.js catalog
docker compose -f compose.yaml -f compose.odoo.yaml run --rm --no-deps client node dist/index.js quote OPS-A-001 OPS-A-P1:2,OPS-A-P2:1
```

Two customers intentionally share a name. Choose their exact reference or record
ID. The reference CLI does not choose the first name match. The expected preview
for company A is IDR 250,000; company B's P1 costs IDR 120,000, giving IDR 290,000
for the same quantities. No Odoo draft exists at the prepare step.

Keep the returned proposal `id` and `payload_hash`. The proposal is immutable and
expires after 30 minutes. To inspect it again:

```sh
docker compose -f compose.yaml -f compose.odoo.yaml run --rm --no-deps client node dist/index.js preview PROPOSAL_ID
```

## Approve, execute and verify

After reviewing customer, company, items and total, use the separate approver:

```sh
docker compose -f compose.yaml -f compose.odoo.yaml run --rm --no-deps -e DEMO_USERNAME=approver.a client node dist/index.js approve PROPOSAL_ID PAYLOAD_HASH
```

Keep the returned approval `id`. As the original operator, execute with a UUID
chosen once for this operation (`python -c "import uuid; print(uuid.uuid4())"`):

```sh
docker compose -f compose.yaml -f compose.odoo.yaml run --rm --no-deps client node dist/index.js execute PROPOSAL_ID APPROVAL_ID IDEMPOTENCY_UUID
docker compose -f compose.yaml -f compose.odoo.yaml run --rm --no-deps client node dist/index.js status OPERATION_ID
```

Reuse the same key if the execute response is lost. Changing the key or approval
for a proposal that already has an operation returns `idempotency_conflict`.
`verified` requires a separate Odoo read-back matching customer/company/currency,
line items, quantities, prices, total and draft state. The receipt includes the
external Odoo ID. It does not confirm or send the quotation.

For company B, use `-e DEMO_USERNAME=operator.b` / `approver.b` and references
`OPS-B-001`, `OPS-B-P1`, `OPS-B-P2`. No code changes are needed.

## Opportunity and follow-up activity

```sh
docker compose -f compose.yaml -f compose.odoo.yaml run --rm --no-deps client node dist/index.js opportunities
docker compose -f compose.yaml -f compose.odoo.yaml run --rm --no-deps client node dist/index.js activity OPPORTUNITY_ID OWNER_ID 2026-12-01 "Synthetic follow-up"
```

Review, approve and execute using the same proposal workflow. The assignee must be
an active internal Odoo user in the same company. Dates are calendar dates, not
timestamps. The addon suppresses assignment email notifications; Odoo cron workers
are disabled in this sandbox. No outbound email capability is part of V1.

## Recovery and supported limits

| Status/code | Meaning and next action |
| --- | --- |
| `dispatched` | Durable operation exists, but the result is not yet verified; request status |
| `unknown` | Outcome is uncertain; request status to find the operation in Odoo |
| `verified` | A read-back matched the approved proposal at that time |
| `review` | Read-back is malformed or disagrees with the proposal; inspect the record, do not create another blindly |
| `failed` | A definite validation/permission rejection; fix the cause and prepare a new proposal |
| `stale_proposal` | Source changed; create a new preview and approval |
| `source_changed` | Customer pagination source changed; restart pagination |
| `approval_expired` | Prepare and approve again; an existing external receipt may still be reconciled |
| `platform_credentials_expired` | Restore scoped platform credentials before retrying |

If status confirms no external receipt and the operation is `unknown`, the original
operator may run `retry OPERATION_ID`. The server first looks up the outcome,
checks approval validity, then resends the same signed operation ID, at most three
dispatches total. The addon deduplicates inside Odoo. A transport error never
triggers an automatic second create. Read calls retry at most three times with
bounded backoff; write calls make one HTTP attempt per dispatch.

V1 pricing is explicit list price, IDR, positive integer quantities up to 1,000,
at most 20 distinct products, no tax, no discount, no fiscal position or custom
pricelist rules. Unsupported policy is rejected. Customer pages are capped at 100,
with a 1,000-customer sandbox source limit; product/opportunity lists are capped at
100. There is no general ERP query executor or unrestricted model/URL input.

## Tests and maintenance

With the normal sandbox running:

```sh
docker compose -f compose.test.yaml -f compose.connected.yaml up --build --abort-on-container-exit --exit-code-from tests
docker compose -f compose.test.yaml -f compose.connected.yaml down
```

The test application database is disposable and separate. Connected cases create
synthetic drafts/activities in this Odoo sandbox and temporarily edit synthetic
source prices to test races. Do not point them at a real tenant. Other tests use
a constrained fake for specific transport and malformed-result failures. A
Starlette/httpx deprecation warning is currently emitted by in-process test clients;
the tests pass. The normal backend and client use actual HTTP.

Addon Python changes: rebuild `odoo`, then recreate its service. Addon schema/XML
changes: stop only this project's Odoo service, rebuild `odoo-init`, `odoo-seed` and
`odoo`, run `docker compose -f compose.yaml -f compose.odoo.yaml run --rm --no-deps odoo-init upgrade`,
then start Odoo again. Addons are copied into `/opt/ops-addons` so an inherited
anonymous addons volume cannot mask a new image's code.

Stop while preserving volumes: `docker compose -f compose.yaml -f compose.odoo.yaml stop`.
Never globally prune Docker to reset this project. Cloud deployment is still Phase 9.
