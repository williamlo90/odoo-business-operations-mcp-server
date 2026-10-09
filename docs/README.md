# Documentation

Choose a path through the project.

| Start with | What you will find |
| --- | --- |
| [Connected MCP journey](evidence/mcp-first-journey.md) | Actual synthetic source lookup, approval, execution, Odoo quotation and replay evidence |
| [Independent approval page](WEB-UI.md) | The current small human review surface; preparation and execution use MCP |
| [Phase 9A workspace](PHASE-9A.md) | Historical full browser checkpoint preserved at its Git tag |
| [Phase 9B checkpoint](PHASE-9B.md) | Why the current product boundary is MCP-first and the UI is approval-only |
| [Product walkthrough](demo/README.md) | Four visual scenes from the actual recorded quotation workflow |
| [Engineering case study](portfolio/CASE_STUDY.md) | Problem, design decisions, recovery and measured results |
| [Operator guide](USER-GUIDE.md) | Installation, daily use, approval and outcome handling |
| [Delivery acceptance](DELIVERY-ACCEPTANCE.md) | Expected and observed results for the recorded demo |
| [Local runbook](LOCAL-RUNBOOK.md) | Credentials, unknown writes, monitoring, restore and rollback |
| [Phase 9 release specification](RELEASE.md) | Frozen CLI delivery inputs, migrations and provenance |
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
