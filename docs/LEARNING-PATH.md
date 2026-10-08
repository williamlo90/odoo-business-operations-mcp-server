# Learning checkpoints

Each fixed tag preserves a reproducible learning snapshot. The default branch,
`learning-phases`, presents the current product and its phase-oriented development
history. The older `main` branch is retained. Portfolio documentation updates do
not rewrite earlier phase tags.

| Tag | Learning focus | Guide |
| --- | --- | --- |
| `phase-0` | Scope, inventory, dependencies and reference acceptance | [Phase 0](PHASE-0.md) |
| `phase-1` | FastAPI, PostgreSQL, authentication, roles and tenant scope | [Phase 1](PHASE-1.md) |
| `phase-2` | Odoo preview, approval, draft creation and verification | [Phase 2](PHASE-2.md) |
| `phase-3-code` | Assistant, providers, shared skills and task journal | [Phase 3](PHASE-3.md) |
| `phase-4-code` | MCP stdio, strict schemas and scoped tools | [Phase 4](PHASE-4.md) |
| `phase-5-code` | Persistent worker, scheduling, leases and recovery | [Phase 5](PHASE-5.md) |
| `phase-6-integration` | Docker/Odoo, real MCP/worker and selected model canaries | [Phase 6](PHASE-6.md) |
| `phase-7-quality` | Frozen synthetic evaluation and quantity grounding | [Phase 7](PHASE-7.md) |
| `phase-8-reliability` | Telemetry, bounded load, security, restore and rollback | [Phase 8](PHASE-8.md) |
| `phase-9-delivery` | Operator pack, recorded demo, release verification and Azure design | [Phase 9](PHASE-9.md) |
| `phase-9a-web-ui` | Browser workspace, scoped read models, role separation and browser recovery acceptance | [Phase 9A](PHASE-9A.md) |

## Study one stage

```bash
git clone https://github.com/williamlo90/odoo-business-operations-mcp-server.git
cd odoo-business-operations-mcp-server
git switch --detach phase-4-code
git show phase-4-code
git diff phase-3-code phase-4-code
```

Return with `git switch learning-phases`, or create an exercise branch from a checkpoint:
`git switch -c exercise-phase-4 phase-4-code`. Use separate databases/volumes for
old versions: changing Git source does not downgrade the database schema.
Credentials are generated privately by setup, not included in the repository.

Phase 0 is a planning snapshot assembled from retained artifacts. Phases 1–2
reference verified implementation commits. Each subsequent completed phase has
one learning commit. The roadmap moved resource-heavy connected work after the
Phase 3–5 implementation checkpoints. Earlier commits and tags remain intact.

A module can introduce the goal, prerequisites, workflow, tagged implementation,
verification and a follow-up exercise. This document is the module map, not a
complete course. Start with `deploy/check_offline.py` in the prepared environment
for the current offline checks; it starts no Docker or model inference.

## Reproduce frozen evidence

Phase 7's quality evaluator is tied to `phase-7-quality` and its contract 0.3.1.
Phase 8 changes numeric grounding to 0.3.2 and records separate controls/canaries.
Run the Phase 9 full-file verifier at `phase-9-delivery`, where its manifest was
frozen. Current documentation can differ without changing the qualified
application. Do not regenerate old evaluation or release manifests merely to
make them accept a newer checkout.
