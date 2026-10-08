# Release specification — Phase 9

This specification describes the immutable CLI delivery checkpoint. The current
browser workspace is a subsequent application revision documented in
[Phase 9A](PHASE-9A.md); its evidence is separate from this frozen manifest.

Release checkpoint: `phase-9-delivery` on `learning-phases`. Resolve the exact
commit with `git rev-parse phase-9-delivery^{commit}`. The accompanying manifest
hashes the release's files; a file cannot embed its own final Git commit hash.
The application source is frozen at `e42441aee2b06483e7158f8ccc4ecc0e632a6041`
(Phase 8). Phase 9 adds delivery documentation, recording and release checks;
it does not change backend, client, MCP, Odoo addon or model behavior.

## Reproducible inputs

Use `pip install -r backend/requirements.lock` and `npm ci` against the two
package-lock files. Docker base images are pinned in `deploy/Dockerfile`,
`client/Dockerfile`, `odoo/Dockerfile` and Compose. The release manifest includes
their hashes and the locally tested API/Odoo/PostgreSQL image IDs. Local image
IDs are not remote registry digests: publish to a private registry and record
immutable registry digests in Phase 10 before deploying. Do not deploy a mutable
`latest` reference and call it this release.

Assistant contract: 0.3.2. Domain/MCP contract: 1.0. The selected hosted profile
is `gpt-4.1-mini-2025-04-14`, `intent-v4-openai`. The Phase 7 frozen evaluation
remains its own historical snapshot; Phase 8 control/canary coverage applies to
0.3.2. No new model-quality score is claimed in this delivery phase.

Ollama 0.40.1 / Qwen2.5 0.5B Q4_K_M is optional, local and experimental. The model
artifact digest and captured license hash are preserved in
`docs/evidence/phase6-local-runtime.json`; the recorded model license is
Apache-2.0. Keep the runtime's bundled third-party notices if redistributing it.
This private repository contains no general open-source license grant for the
project itself. Cloud deployment does not bundle hosted OpenAI weights. Review
upstream notices/terms before distributing images or binaries to others.

## Configuration inventory

| Configuration | Owner / location / use |
| --- | --- |
| PostgreSQL owner/runtime passwords | William; ignored `.env`; migration owner separate from restricted API user |
| Odoo database/admin password and signing key | William; ignored `.env`; Odoo setup/signature verification |
| Company-bound Odoo API keys | Ignored `local/odoo-config/connections.json`; read-only mount into API |
| Synthetic account password | Ignored `.env`; local test accounts only |
| Hosted model keys | Owner's private environment; host assistant only, not Odoo or MCP tool output |
| Worker identity/tenant | Ignored per-company profiles; no shared multi-tenant queue identity |
| Task/queue databases | Ignored local paths; durable IDs needed for recovery |
| Cloud values | Proposed architecture in `AZURE-PLAN.md`; subscription, region, domain, budget and recipient unresolved |

## Migrations and upgrades

Migrations `001_foundation.sql` and `002_business_workflow.sql` are immutable
checksummed inputs. Phase 9 has no schema migration. Stop producers, take a
matching verified database/filestore/SQLite backup, capture the current image
IDs, verify the release manifest, then build/start the candidate. The migration
service runs before seed/API and must succeed before traffic is accepted.
Never repair a checksum mismatch by changing the migration ledger. Add a new
numbered migration with its own tests for future schema changes.

Run readiness plus a scoped customer read and the normal/negative acceptance
flow. Review source hashes and image IDs before resuming workers. If an upgrade
fails, use the compatible image rollback demonstrated in Phase 8. For an
incompatible future migration, restore the matching backup in isolation first;
changing an image alone does not reverse database mutations. Recovery jobs must
be reconciled against Odoo before any replay. See `LOCAL-RUNBOOK.md`.

## Verification and release boundaries

Run `python deploy/check_release.py` from the fixed `phase-9-delivery` checkout
with dependencies installed. Later portfolio documentation updates are outside
that frozen full-file manifest; do not regenerate it for a newer checkout.
It checks committed/staged file hashes, unchanged application source,
locked inputs and matching Phase 8 runtime evidence; it makes no network calls.
The recorded CLI demonstration has nine checked stages and a direct Odoo
ledger/order count of 1/1. Earlier release controls: 98 offline, 41 connected,
14 live tests plus 124 workload tasks. These are separate runs, not one quality
percentage. See `DELIVERY-ACCEPTANCE.md` and `phase9-manifest.json`.

This release is local-ready with cloud design prepared. Azure IaC/runtime,
HTTPS, restricted remote access, distinct real-user credentials and delivered
human alerts must be implemented and tested in Phase 10. No production,
cloud-performance or high-availability claim is made.
