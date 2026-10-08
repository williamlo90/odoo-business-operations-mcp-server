# Odoo Business Operations — delivery pack

Status: **Phases 0–9 and the Phase 9A browser workspace complete for the selected local scope. Azure deployment remains Phase 10.**

## Business brief

Sales operations needs reliable access to customer records and a controlled way
to prepare quotations and CRM follow-ups. This project gives an assistant four
typed skills through a scoped MCP server. It resolves source records, prepares
an immutable preview, requires a separate approver and verifies the final Odoo
record. The model cannot approve its own proposal or issue arbitrary database
commands. William owns this synthetic local demonstration and its operation.

The delivered interfaces are a [browser workspace](docs/WEB-UI.md) and reference
CLI, with reusable Python skills and a persistent worker. Natural-language
assistant requests use the CLI. The current pricing workflow
supports its explicit list-price/no-tax policy; unsupported pricing stops for
review. Company and role are loaded from authenticated identity, not model text.

## What has been demonstrated

Phase 8 passed 98 offline, 41 connected and 14 live checks. Its bounded 124-task
load produced 31 verified draft quotations without duplicate effects. Matching
backup/restore, database recovery, a local alert receiver and compatible image
rollback passed. These are synthetic local results, not production traffic or
human ROI. Phase 7's frozen OpenAI result was 18/18; the small local model scored
7/18 and remains experimental. The delivery demo separately records nine real
CLI stages and verifies exactly one Odoo draft.

## Start here

| Deliverable | Guide or evidence |
| --- | --- |
| Install, login, daily work and statuses | [Operator guide](docs/USER-GUIDE.md) |
| Actual normal, blocked and resumed workflow | [Recorded CLI demo](docs/demo/index.html), [receipts](docs/demo/recording.json) |
| Expected/observed acceptance | [Delivery acceptance](docs/DELIVERY-ACCEPTANCE.md) |
| Failure handling, backup and rollback | [Local runbook](docs/LOCAL-RUNBOOK.md) |
| Versions, secrets inventory and migration procedure | [Release specification](docs/RELEASE.md) |
| Ownership, cadence and improvement backlog | [Handover](docs/HANDOVER.md) |
| Cloud topology, budget proposal and deployment gates | [Azure design](docs/AZURE-PLAN.md) |
| Reproducible source/artifact hashes | [Release manifest](docs/evidence/phase9-manifest.json) |

All local delivery items above are complete. The demonstration uses a recorded
HTML terminal transcript rather than a screen-capture video. Human approval is
represented by a separate automated test identity; a real operator must still
review the preview. The worker and scheduler work without n8n. No n8n extension
was selected.

## Cloud handover boundary

Phase 9 supplies a design and cost proposal, not provisioned infrastructure.
Phase 10 requires approved account/region/budget/access, infrastructure as code,
immutable registry images, distinct credentials, HTTPS, delivered human alerts,
off-host restore/rollback and cloud-specific acceptance. No Azure cost was
incurred by provisioning in this phase. See the deployment gates before creating
any resources.
