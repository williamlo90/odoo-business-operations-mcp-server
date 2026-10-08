# Reusable business skills

These are executable application capabilities shared by the assistant and
worker, not a collection of prompts or an assumption that an editor skill is
installed. Each package under `skills/` documents its contract, allowed tools,
preconditions, implementation binding and recovery behavior.

| Skill | Input | Outcome | Action boundary |
| --- | --- | --- | --- |
| `research_customer` | Exact customer reference | Source-backed customer facts | Read-only |
| `prepare_quote` | Customer and product quantities | Validated quotation preview | Deterministic prices; approval required before write |
| `prepare_crm_activity` | Opportunity, assignee, date and summary | CRM activity preview | Approval required before write |
| `reconcile_odoo_write` | Operation ID | Verified, unknown or failed outcome | Lookup before retry |

## Package and reuse contract

A skill has a business purpose, owner, typed versioned input/output, minimum
permissions, declared side effects and a Python handler binding. Timeouts,
retries, cancellation, idempotency and postcondition checks are explicit.
Fixtures include normal, ambiguous and failure cases with independently defined
expected results. Application rules stay in authoritative services rather than
being duplicated in prompts.

The assistant and worker call the same `execute_skill` implementation. Company
A/B configuration exercises the same logic against different data. Provider
selection cannot change permission or approval rules. Missing information or
uncertain outcomes produce explicit states, not guessed success.

[Skill packages](skills/README.md) · [Worker reuse](docs/PHASE-5.md) ·
[Connected evidence](docs/PHASE-6.md) · [Reliability](docs/PHASE-8.md)
