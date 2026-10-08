# Assistant design

The reference assistant helps sales operations research Odoo records and prepare
business changes through bounded skills. The local implementation and connected
workflow are complete; cloud deployment remains pending.

## Behavior contract

The caller supplies a task ID and authenticates. The server determines role,
tenant and permitted scope; prompt text cannot expand them. One bounded model
decision selects a typed skill or asks for clarification. Deterministic handlers
retrieve source records and return facts, missing information, proposals or
operation outcomes. Model confidence does not authorize execution.

- Read, prepare, approval and execution are distinct capabilities.
- Business rules, arithmetic, permissions and state transitions live in Python
  services and the Odoo transaction boundary.
- Approval binds actor, company, payload hash, source version and expiry.
- Requests have step/call limits, timeouts, cancellation and terminal states.
- Credentials are excluded from prompts; retrieved text cannot become instructions.
- Success requires the target record to match the intended outcome. Uncertain
  writes remain unknown until reconciliation.
- One orchestrator and shared deterministic skills are the implemented design;
  no multi-agent performance claim is made.

## Delivered components

Typed contracts, a durable task journal, hosted/local adapters, a TypeScript
reference client, four executable skills and sanitized traces are implemented.
Tests cover ambiguity, refusal, malformed output, injection, cancellation,
source changes and tool failures. Traces retain version, identity, correlation,
latency and usage metadata; monetary cost stays unknown without a rate card.

The custom MCP server works independently of n8n. Interactive callers and the
worker reuse the same handlers. See [skills](REUSABLE-SKILLS.md),
[MCP](MCP-INTEGRATIONS.md), [quality](docs/PHASE-7.md),
[reliability](docs/PHASE-8.md) and the [operator guide](docs/USER-GUIDE.md).
