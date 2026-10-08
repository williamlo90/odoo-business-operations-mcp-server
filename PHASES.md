# Delivery roadmap and acceptance gates

**Phases 0–9 are complete for the selected local scope. Phase 10 cloud deployment
is pending.** The sequence is 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10.
Authorization and tests accompany each feature; Phase 8 consolidates reliability
verification. Each implementation phase has a learning commit and fixed tag.
Documentation-only portfolio updates do not rewrite those checkpoints.

## Phase 0 — Inventory and scope

- [x] Identify reusable/new components, current source state and dependencies.
- [x] Define the owner, three user journeys, V1 action boundaries and expected outcomes.
- [x] Record sandbox, credential, hardware, license and API requirements.
- [x] Select standalone MCP/Python automation; n8n is not required.

Gate: scope, inventory, 20 acceptance cases and dependency register exist.
[Scope](docs/PHASE-0.md) · [Acceptance](docs/ACCEPTANCE-CASES.md) · [Dependencies](docs/DEPENDENCIES.md).
This checkpoint made no application-test or connected-validation claim.

## Phase 1 — Local foundation

- [x] Git, FastAPI, TypeScript client, PostgreSQL migrations and Linux Docker Compose.
- [x] Authentication, role/tenant context, validated configuration, private secrets,
  health/readiness and sanitized logs.
- [x] Synthetic seed, isolated test reset, installation and automated smoke tests.

Gate: an authorized user completes a persisted local flow; unauthorized access
is rejected. 17 PostgreSQL tests, fresh-volume install and outage recovery passed.
[Phase 1](docs/PHASE-1.md).

## Phase 2 — Deterministic Odoo workflows

- [x] Fix the Odoo edition/API, source mapping and supported business policy.
- [x] Separate read, prepare, approval, execute and read-back.
- [x] Bind approval to identity, tenant, payload and source version.
- [x] Handle pagination, stale records, timeouts, retries and idempotency at the
  actual transaction boundary; publish versioned contracts and fixtures.

Gate: normal, negative and recovery paths have reference outcomes independent
of model quality. 38 tests including nine actual Odoo cases passed.
[Phase 2](docs/PHASE-2.md) · [Contract](docs/CONTRACT-V1.md).

## Phase 3 — Assistant and reusable skills

- [x] Four executable skills, typed contracts, retrieval and output validation.
- [x] OpenAI, Claude, Grok and Ollama adapters with refusal/timeout/local-only tests.
- [x] TypeScript reference client, durable tasks, replay/version binding and traces.

Gate: production code paths pass offline transport tests; real model acceptance
is deferred to Phase 6. 49 Python and two client tests passed at this checkpoint.
[Phase 3](docs/PHASE-3.md).

## Phase 4 — Custom MCP server

- [x] Pin SDK/protocol and build scoped read, prepare, approved-execute and verify tools.
- [x] Connect the client/assistant through actual stdio processes.
- [x] Test identity, tenant, schema, cancellation, limits, replay and unknown results.

Gate: seven protocol scenarios pass with simulated downstream HTTP. Actual Odoo
acceptance follows in Phase 6. [Phase 4](docs/PHASE-4.md).

## Phase 5 — Persistent automation

- [x] Shared worker/scheduler handlers with jobs, deduplication, leases and checkpoints.
- [x] Bounded retries, review/dead states and interruption recovery.
- [x] Separate automation from approval and document company-specific configuration.

Gate: 16 worker and eight MCP tests pass, including process restart and scoped
reuse. SQLite is orchestration state, not business truth. [Phase 5](docs/PHASE-5.md).

## Phase 6 — Connected integration

- [x] Run the project's bounded Docker stack without disrupting other projects.
- [x] Connect Odoo/PostgreSQL, assistant, MCP and dedicated company A/B workers.
- [x] Pin/provision local inference; run actual Ollama and OpenAI canaries.
- [x] Verify approval, writes, read-back, stale sources, replay and reuse.

Gate: selected real integrations pass. Claude/Grok are optional and not
live-qualified. [Phase 6](docs/PHASE-6.md).

## Phase 7 — Quality evaluation

- [x] Freeze datasets, labels, profiles, rubric and thresholds before scoring.
- [x] Treat debugging cases as regression data rather than independent holdout.
- [x] Compare typed reference and assisted outcomes on the same synthetic tasks.
- [x] Record quality, latency, usage and critical failures without claiming human ROI.

Gate: selected hosted profile passed 18/18 frozen regression cases; typed
reference passed 18/18. Local Qwen2.5 0.5B passed 7/18 and remains experimental.
86 offline, 20 live and 38 PostgreSQL/Odoo checks passed at this checkpoint.
[Phase 7](docs/PHASE-7.md). The score belongs to its exact source snapshot.

## Phase 8 — Local reliability and security

- [x] Verify API/client/MCP/worker roles, tenant boundaries, bypass and injection cases.
- [x] Test concurrency, worker interruption, lost response, late completion, retries,
  unknown outcomes, backlog, database recovery and isolated backup/restore.
- [x] Measure per-operation and total percentiles with sample counts, achieved
  throughput, dropped work, resources and final effects.
- [x] Separate queue, HTTP, inference and downstream timing; use fixed bounded
  normal/peak/soak workloads and separate real-provider canaries.
- [x] Prove local alert receipt, image rollback and recovery procedures.

Gate: local release candidate passes the selected tests and workload. 98 offline,
41 connected and 14 live checks; 124 load tasks; 31 verified single-effect writes.
No browser UI or async callback endpoint exists. Cloud and human paging remain
pending. [Phase 8](docs/PHASE-8.md) · [Runbook](docs/LOCAL-RUNBOOK.md).

## Phase 9 — Delivery pack

- [x] English installation, daily use, approval, failure handling and support guides.
- [x] Actual recorded CLI demo with normal, blocked and resumed outcomes.
- [x] Frozen release inputs, dependency/migration/rollback/configuration inventory.
- [x] Azure design, cost proposal, access, secrets, alerts, backups and teardown plan.
- [x] Named owner, operating cadence and improvement backlog.

Gate: the local product can be understood and operated from the delivery pack;
cloud prerequisites are explicit. No Azure provisioning was performed.
[Phase 9](docs/PHASE-9.md) · [Delivery](PROJECT-DELIVERY.md) · [Azure design](docs/AZURE-PLAN.md).

## Phase 10 — Azure deployment and runtime acceptance

- [ ] Confirm subscription, budget, region, access method and alert recipient.
- [ ] Validate IaC/what-if, provision isolated resources and deploy immutable images.
- [ ] Apply migrations, secrets/network controls and distinct business credentials.
- [ ] Repeat connected correctness, authorization and workload gates in Azure.
- [ ] Prove delivered human alerts, off-host restore, rollback and safe teardown.
- [ ] Record actual costs, retained resources, release provenance and cloud handover.
- [ ] Establish ongoing incident response and pre-change quality review.

Final gate: the chosen cloud deployment is verified in its own environment.
Local evidence is not relabeled as cloud proof. Until then, status is
local-ready/cloud-pending. Infrastructure planning and hosted model API calls
from a local client do not count as cloud application deployment.
