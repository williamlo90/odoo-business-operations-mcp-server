# Odoo Business Operations MCP Server

**AI-assisted sales operations with explicit approval and verified Odoo outcomes.**

Research customer records, prepare quotations and CRM activities, review the exact
proposal, and verify what Odoo actually created. A custom MCP server connects
bounded AI intent to authenticated business workflows.

![Odoo operations: source records, separate approval, verified outcome](docs/assets/overview.png)

[Product walkthrough](docs/demo/README.md) · [Engineering case study](docs/portfolio/CASE_STUDY.md) · [Operator guide](docs/USER-GUIDE.md) · [Documentation](docs/README.md)

## Why this project

A plausible AI response is not enough to create a business record. Customer names
can collide, product prices can change after a preview, and a network timeout can
hide a successful write. Retrying blindly can create a second quotation.

This project puts those operational problems inside the workflow: resolve the
source, bind approval to the proposal, execute with a durable operation ID, and
read the result back from Odoo before reporting success.

## Evidence at a glance

| Result | What was verified | Evidence |
| --- | --- | --- |
| **4 skills · 10 MCP tools** | Shared research, quotation, CRM activity and reconciliation workflows | [Skills](skills/README.md), [MCP server](docs/PHASE-4.md) |
| **153 checks passed** | 98 offline, 41 PostgreSQL/Odoo, 14 live checks in the local qualification | [Verification record](docs/evidence/phase8-controls.txt) |
| **124 workload tasks** | 93 correct reads and 31 verified drafts; zero errors or dropped tasks | [Reliability results](docs/PHASE-8.md) |
| **31 / 31 single effects** | Every load-run write had exactly one Odoo ledger entry and order, including replay | [Load evidence](docs/evidence/phase8-load.json) |
| **30.11 s restore** | Isolated matching database/filestore restore with authenticated business read-back | [Recovery evidence](docs/evidence/phase8-recovery.json) |

These are bounded synthetic local results. The application code remains the
qualified release; the nine-stage delivery demo is a separate recorded run.
[Versions and reproduction](docs/RELEASE.md).

## A quotation, from request to receipt

1. **Resolve** the exact customer and products within the caller's company.
2. **Prepare** an immutable preview with source version, line items and total.
3. **Review** with a separate approver; authorization is bound to the payload hash.
4. **Execute** using the approved proposal and a stable idempotency key.
5. **Verify** the actual Odoo record; reconcile uncertain outcomes before retrying.

<table>
<tr>
<td width="50%"><a href="docs/demo/README.md#1-prepare-the-correct-record"><img src="docs/assets/proposal.png" alt="Recorded quotation preview: company A, exact customer, IDR 250000"></a><br><strong>Source-bound proposal</strong><br>Review customer, quantities and total before any draft is created.</td>
<td width="50%"><a href="docs/demo/README.md#2-enforce-the-approval-boundary"><img src="docs/assets/approval.png" alt="Recorded operator approval denied with HTTP 403"></a><br><strong>Separate approval</strong><br>The operator cannot authorize their own proposal.</td>
</tr>
<tr>
<td width="50%"><a href="docs/demo/README.md#3-verify-the-odoo-result"><img src="docs/assets/receipt.png" alt="Recorded Odoo draft S00132 verified against the proposal"></a><br><strong>Verified business result</strong><br>A receipt points to the actual Odoo draft and its checked total.</td>
<td width="50%"><a href="docs/demo/README.md#4-resume-without-a-second-write"><img src="docs/assets/replay.png" alt="Recorded replay returns the same operation with one ledger entry and one order"></a><br><strong>Recover without duplication</strong><br>A fresh caller resumes from the saved operation ID.</td>
</tr>
</table>

The visuals summarize actual [CLI receipts](docs/demo/recording.json); they are
not screenshots of a web application. The reference interface is a CLI, with
Odoo's own interface available locally. [Full recorded walkthrough](docs/demo/README.md).

## Architecture and authority

![Architecture: caller and model, MCP tools, domain controls, separate approval, Odoo and read-back](docs/assets/architecture.png)

| Layer | Responsibility |
| --- | --- |
| AI assistant | Produce one bounded typed intent or request clarification |
| Custom MCP server | Expose allowlisted tools through authenticated stdio calls |
| FastAPI domain service | Enforce tenant/role scope, proposal freshness, approval and execution rules |
| Separate approver | Review and authorize the exact proposal version |
| Odoo + operation ledger | Apply the business action and provide read-back evidence |
| Persistent worker | Reuse skills with deduplication, leases and bounded recovery |

**Stack:** TypeScript MCP and reference client · Python/FastAPI · PostgreSQL ·
Odoo Community 19.0 / JSON-2 · SQLite orchestration journals · Docker Compose.
OpenAI is the tested hosted profile; Ollama is available for experimental
local-only use. [Model evaluation and scope](docs/PHASE-7.md).

## Try it locally

Requirements: Docker with Linux containers, Python 3.13 and Node.js 22+.
Start with credential-free checks from the repository root:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.lock
npm ci --prefix client
npm ci --prefix mcp-server
.venv/Scripts/python.exe deploy/check_offline.py
```

On Linux, use `.venv/bin/python`. This command builds the TypeScript packages
and runs the offline checks without Docker, provider keys or model inference.

For the full Odoo workflow, follow the [operator guide](docs/USER-GUIDE.md):
start the synthetic stack, prepare a quotation, approve with a separate account,
and inspect its verified receipt. The deterministic workflow needs no paid model.

## Explore the engineering

- [Case study](docs/portfolio/CASE_STUDY.md): architecture decisions, failure modes and measured outcomes.
- [Portfolio summary](docs/portfolio/APPLICATION_PACK.md): concise project description and interview talking points.
- [Reliability report](docs/PHASE-8.md): workload definitions, percentiles, resources and recovery.
- [Local runbook](docs/LOCAL-RUNBOOK.md): uncertain writes, credentials, backup and rollback.
- [Learning checkpoints](docs/LEARNING-PATH.md): one commit per completed phase, preserved tags.
- [Azure proposal](docs/AZURE-PLAN.md): restricted demo design and cost assumptions; deployment pending.

**Delivery status:** locally validated with a complete operator pack. Azure has
not been provisioned. There is no hosted application URL or customer ROI claim.
All documentation is indexed in [docs/README.md](docs/README.md).
