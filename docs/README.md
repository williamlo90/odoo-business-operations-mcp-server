# Documentation

Choose a path through the project.

| Start with | What you will find |
| --- | --- |
| [Browser workspace](WEB-UI.md) | Login, quotation/CRM preparation, approval and verified receipts in the web UI |
| [Web UI acceptance](PHASE-9A.md) | Browser and API checks for the pre-cloud workspace checkpoint |
| [Product walkthrough](demo/README.md) | Four visual scenes from the actual recorded quotation workflow |
| [Engineering case study](portfolio/CASE_STUDY.md) | Problem, design decisions, recovery and measured results |
| [Portfolio summary](portfolio/APPLICATION_PACK.md) | Concise project pitch and evidence-backed interview points |
| [Operator guide](USER-GUIDE.md) | Installation, daily use, approval and outcome handling |
| [Delivery acceptance](DELIVERY-ACCEPTANCE.md) | Expected and observed results for the recorded demo |
| [Local runbook](LOCAL-RUNBOOK.md) | Credentials, unknown writes, monitoring, restore and rollback |
| [Release specification](RELEASE.md) | Locked inputs, immutable migrations and release provenance |
| [Owner handover](HANDOVER.md) | Operating cadence, retention and improvement backlog |
| [Azure proposal](AZURE-PLAN.md) | Proposed topology and cost assumptions; no deployment yet |

## Technical contracts

- [Domain API](CONTRACT-V1.md), [acceptance cases](ACCEPTANCE-CASES.md) and [dependencies](DEPENDENCIES.md).
- [Assistant design](../AI-AGENTS.md), [reusable skills](../REUSABLE-SKILLS.md) and [MCP integration](../MCP-INTEGRATIONS.md).
- [Odoo integration](../BUSINESS-PLATFORM.md), [model profiles](../LOCAL-AI-AND-PROVIDERS.md) and [worker ownership](../N8N-AUTOMATION.md).
- [Security and evidence policy](../SECURITY-TESTING-MONITORING.md).

## Evidence and learning

[Quality](PHASE-7.md), [reliability](PHASE-8.md) and [delivery](PHASE-9.md)
reports describe separate runs and their scope. Raw sanitized evidence lives in
`evidence/`; recorded CLI receipts live in `demo/recording.json`.

The [learning path](LEARNING-PATH.md) maps every completed phase to its immutable
Git tag. The [roadmap](../PHASES.md) tracks delivery gates. Historical evaluation
and release manifests are checked at their tagged source snapshots; current
portfolio documentation can evolve without rewriting those artifacts.
