# Access control, testing and monitoring

## Authority and tenant scope

| Role | Business authority |
| --- | --- |
| Operator | Read scoped records, run the assistant and prepare proposals |
| Approver | Review and authorize an eligible proposal bound to its payload/version |
| Administrator | Manage configuration; no implicit business approval privilege |
| Auditor | Read permitted records/evidence; no write authority |
| Worker identity | Only assigned tenant and skills; no autonomous approval |

Enforce record/tenant scope at API, MCP, worker, retrieval and cached-result
boundaries. Separate proposer and approver. Synthetic tests use the project's
sandbox; destructive database tests use disposable targets.

## Required scenario coverage

Same-name customers, cross-company records, modified approval payloads, changed
Odoo sources, response loss after a committed draft, changed pagination and
forbidden tool/model/field access are covered. The [Phase 7 mapping](docs/PHASE-7.md)
identifies individual cases; [Phase 8](docs/PHASE-8.md) consolidates reliability.

Verification layers include rules/schema unit tests, provider/MCP contracts,
real PostgreSQL/Odoo integration, reference-client workflows, bounded model
regression, worker process interruption and load/recovery tests. The browser
workspace adds role/tenant isolation, reload recovery, lost-response and
responsive-layout acceptance in [Phase 9A](docs/PHASE-9A.md).
Request/output/queue limits and memory caps are tested without
forcing whole-host OOM. Lost response and late completion cover the applicable
recovery paths; there is no callback endpoint.

## Measurement rules

Report code and dirty-diff identity, dataset/profile hashes, environment,
workload, sample counts, durations, exclusions and expected/observed outcomes.
Keep different suites separate instead of constructing a combined quality score.
Freeze workload thresholds and stop conditions before the run. Include
p50/p90/p95/p99, achieved throughput, dropped work, errors and final effect counts.
Separate queue wait, HTTP acknowledgement, inference, downstream work and verified
completion. A quick failed response is not a successful business operation.

## Implemented monitoring

- Correlation IDs connect API/MCP requests to bounded Odoo method/status/duration
  logs. Sensitive bodies, credentials and model text are excluded.
- Assistant traces record version, latency, usage and outcome. Dollar cost remains
  unknown without a rate card.
- Tenant-scoped metrics report operation states, proposal counts and age since
  the latest unresolved-operation update. Worker queue counts/age are available.
- An isolated database outage generated firing/recovery transitions consumed by
  the durable SQLite receiver. This is local receipt, not email or human paging.
- The [runbook](docs/LOCAL-RUNBOOK.md) covers credentials, stale sources, uncertain
  writes, stuck jobs, restoration, image/model rollback and duplicate incidents.

Automatic spend/quality-drift monitoring and cloud alerts are not implemented.
Private backups and task data stay outside Git; public evidence is sanitized.
The runbook defines owner access and manual retention.

## Acceptance gate

The named critical suite requires no permission bypass, cross-tenant leakage,
duplicate effects or false success. Zero in finite synthetic tests is not a
universal production guarantee. Thresholds must not be relaxed after observing
failures. Fix the issue or explicitly revise and validate scope.

The local qualification recorded 98 offline, 41 connected and 14 live checks.
Cloud runtime evidence belongs to Phase 10. n8n is not required; any future
consumer must meet its own scope and outcome checks.
