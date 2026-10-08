# Phase 9A — Browser workspace

Status: completed locally before Azure. Learning checkpoint: `phase-9a-web-ui`.
One implementation commit follows the portfolio documentation commit
`862effa`. Existing phase commits and tags remain unchanged; Azure remains Phase 10.

## Delivered behavior

- English responsive login and role-aware workspace with company identity.
- Saved proposal queue, pagination, direct proposal links and company totals.
- Source-backed customer/product selection and quotation preparation.
- CRM opportunity, assignee, due date and activity preparation.
- Explicit independent approval and original-operator execution confirmations.
- Verified Odoo receipts, status reconciliation and bounded safe retry.
- Recovery after page reload, reauthentication and a lost execution response.

The static UI runs inside the existing API container. Two additive, scoped
read endpoints expose saved proposal state without signed dispatch envelopes.
The domain service and Odoo addon retain write authority. No new database
migration, MCP tool, cloud resource or model dependency was introduced.

## Acceptance

| Check | Result | Scope |
| --- | --- | --- |
| Offline gate | 102 passed | Existing 98 Python/TypeScript checks plus four browser-state unit tests |
| Complete container test suite | 132 passed, 20 skipped | Real isolated application PostgreSQL, synthetic Odoo connection and existing unit suites; one existing TestClient deprecation warning |
| Browser workflow | 13 acceptance checks passed | Real Chromium, local API and Odoo; quotation and CRM activity, separate accounts, reload and lost-response recovery, company denial, mobile layout and logout |
| Screenshots | Desktop and 390px mobile inspected | Actual synthetic application screens, not mockups |

The container skips are opt-in live-provider/host-stack cases without their
required profiles. This phase does not claim a fresh model evaluation or repeat
the Phase 8 load/recovery benchmark. Offline and container suites overlap; their
counts must not be added into a single independent test total.

The full-suite log-schema assertion now recognizes both bounded HTTP events
and existing Odoo telemetry events while continuing to scan the entire log
for credentials. This makes the test independent of connected-test ordering.

[Sanitized browser results and source hashes](evidence/phase9a-web.json)
record the tested inputs and outcomes. The browser simulates losing the execute
response after the real server request completes; the saved operation and Odoo
receipt are then recovered without another create action.

## Reproduction and handover

```powershell
.venv/Scripts/python.exe deploy/check_offline.py
docker compose -f compose.test.yaml -f compose.connected.yaml up --build --abort-on-container-exit --exit-code-from tests
npm ci --prefix tests/web
npm exec --prefix tests/web -- playwright install chromium
npm test --prefix tests/web
```

The container suite uses its explicitly disposable test application database.
Browser acceptance uses the running synthetic local sandbox and creates test
business records. Use the [web UI guide](WEB-UI.md) for installation, accounts,
screenshots and daily operation.

The Phase 9 full-file release manifest still applies only to its original
`phase-9-delivery` checkout. Deploy the newer web checkpoint with its own image
and evidence; do not relabel the older frozen manifest as this UI release.
Cloud acceptance, HTTPS, individual credentials and delivered human alerts
remain pending. No Azure resources were provisioned in this phase.
