# Phase 8 - Local reliability, security and performance

Status: **Complete for the selected local release candidate scope.**
The final image passed 124 bounded workload tasks, including 31 verified Odoo
draft quotations with exactly one ledger entry and one order each. Isolated
restore, database recovery, delivered local alerts and image rollback passed.
This is synthetic, single-host evidence; cloud validation remains Phase 10.

## Implementation and controls

Tenant-scoped `/v1/metrics` exposes operation status counts, proposal count and
age since the last unresolved-operation update. API/Odoo timing shares the
request correlation ID; the response reports downstream duration without
record payloads or credentials. The local monitor persists incident transitions
and receiver acknowledgements across restarts.

Assistant contract `0.3.2` rejects integer fragments taken from decimals,
fractions, negative quantities, percentages, scientific notation and product
codes. Numeric presence remains a syntactic check; a separate human approver
must confirm each product/quantity association. Provider/prompt configuration
is unchanged. Phase 7's 18/18 result belongs to its frozen `0.3.1` snapshot;
its artifacts are preserved. This phase adds targeted regression and canary
evidence, not a new held-out model-quality score.

| Check | Result and scope |
| --- | --- |
| Offline | 98 passed: 6 evaluator, 54 assistant, 16 worker, 12 reliability, 2 client, 8 MCP; both TypeScript builds passed |
| PostgreSQL/Odoo | 41 passed, including three new metrics/correlation cases; one existing Starlette/httpx deprecation warning |
| Live | 14 passed: 7 stack/MCP/worker, 5 local inference, 1 local quantity regression, 1 bounded hosted quotation canary |
| Worker backlog | 12 real MCP/Odoo reads, two consumers, one completion per job; 1.846 tasks/s; processing p95 0.1763 s, queue p95 5.5366 s, end-to-end p95 5.6755 s |
| Queue concurrency/fencing | 40 queued jobs drained by four claimers; no duplicate claims; stale worker completion rejected after lease transfer |
| Secret checks | Changed public files and current structured API logs checked against locally configured credential values; no matches |

The worker drill includes MCP process startup in queue/end-to-end time and has
a 60-second completion bound. It is separate from the HTTP load queue gate.
Worker preparation remains approval-pending; it never creates human approval
or automatically executes an Odoo write.

Security coverage includes direct API role/tenant spoofing, changed approval
payloads, connector signature bypass, MCP tool/schema injection, sensitive error
redaction and assistant source injection. The reference interface is a CLI;
there is no browser UI to test. Existing production-path fault injection proves
bounded read retries, no blind write retries, real-process worker interruption,
late completion fencing, unknown outcomes and lost responses after an actual
Odoo write. Connected concurrent execution verifies the final effect count.
There is no asynchronous callback endpoint; no callback-specific test is claimed.

## Fixed workload and observed performance

The [workload](../reliability/workload.json) was set before measurement and its
SHA-256 is recorded in the report. Each fourth task runs prepare, approval by
a separate account, execute, actual read-back and replay; the rest read the
exact expected customer/company. Approval is automated with separate test
credentials, not a measurement of human review time. Synthetic load uses real
HTTP/PostgreSQL/Odoo paths without a model or simulated downstream service.

| Workload | Tasks / concurrency / offered rate | Read p95 / limit | Write p95 / limit | Achieved tasks/s | Verified operations/min |
| --- | --- | --- | --- | --- | --- |
| Normal | 24 / 2 / 1 per s | 0.1636 / 2 s | 0.3875 / 5 s | 1.026 | 15.396 |
| Peak | 40 / 4 / 4 per s | 0.0753 / 5 s | 0.4362 / 10 s | 3.930 | 58.949 |
| Bounded soak | 60 / 2 / 0.5 per s | 0.0741 / 3 s | 0.5216 / 7 s | 0.507 | 7.602 |

All three runs had zero errors and dropped tasks. In total, 93 sourced reads
and 31 writes were correct. Every write also passed replay and direct SQL
ledger/order-count verification. Maximum load queue wait was below 0.21 seconds,
against a five-second gate. The schedules lasted 23.38, 10.18 and 118.39 seconds;
the short soak does not establish long-duration leak resistance.

The [load evidence](evidence/phase8-load.json) includes sample counts,
nearest-rank p50/p90/p95/p99 by task kind and by HTTP stage, downstream spans,
queue waits, total durations, response status, resource samples and final
effect counts. Write duration includes verification and replay. HTTP execute
acknowledgement is synchronous after dispatch/read-back, not an accepted-only
response counted as completion. With only 6/10/15 writes per workload, p99 is
effectively the maximum observation, not a production tail guarantee.

The [hosted canary](evidence/phase8-canary.json) measured 3.6454 seconds of model
inference and 4.5933 seconds from assistant entry to proposal, then verified
approval/execute/read-back. It used `gpt-4.1-mini-2025-04-14` with
`intent-v4-openai`: 941 input and 45 output tokens. N=1 is not a throughput or
percentile result. Dollar cost is unknown without a configured rate card.
Local Qwen2.5 0.5B remains experimental; Claude/Grok remain optional/unverified.

## Environment and recovery

Windows host: Intel Core i7-13620H, 10 cores/16 logical processors, approximately
15.71 GiB physical memory; Docker Linux containers. No host-wide stress or OOM
injection was performed. Admission/output limits and bounded queue behavior
are tested separately. Sampled Docker usage during load was:

| Service | Memory cap MiB | Maximum sampled MiB | Maximum sampled CPU % |
| --- | --- | --- | --- |
| API | 256 | 66.52 | 53.41 |
| Application PostgreSQL | 192 | 26.04 | 12.66 |
| Odoo | 768 | 129.20 | 20.58 |
| Odoo PostgreSQL | 256 | 71.95 | 5.27 |

There were 22 samples per container, with approximately five seconds between
sampling calls plus collection overhead. No tested container was OOM-killed or
stopped. These are sampled container observations, not whole-host maxima.

The [recovery evidence](evidence/phase8-recovery.json) records:

- Matching application/Odoo dumps and filestore, backed up while source API/Odoo
  were stopped. Seven application and ten Odoo tables matched after restore;
  filestore content matched and two SQLite snapshots passed integrity checks.
- Restore and authenticated business read-back in **30.11 seconds**, below the
  predeclared 180-second bound. Restored sessions were invalidated and restored
  worker jobs were not automatically replayed.
- Isolated application-database outage, one firing alert received, no duplicate
  receipt, then one recovery transition for the same incident. Readiness
  recovered in **1.26 seconds**, below the 60-second bound.
- Rollback to the captured compatible baseline API image and rollforward to
  the candidate, each verified by actual image ID and Odoo operation read-back.
  This tests a schema-compatible image change, not a destructive migration.
- Removal of only the run-owned drill containers/volumes and verified restart
  of the source stack. Other projects were not stopped or modified.

Image IDs, table/file hashes and run IDs are in the evidence. The baseline is
the captured previous runtime image; it is not claimed to have been built from
the Phase 7 commit. The final candidate image matches the tested backend files.
Private dumps/configuration remain under ignored `local/recovery`.

Alert receipt means a durable local SQLite receiver acknowledgement. No email,
Slack, human paging, automatic disaster promotion, production SLO or cloud
readiness is claimed. Monitoring does not automatically cover spend or model
quality drift. Follow the [local runbook](LOCAL-RUNBOOK.md) for those limits and
operational recovery.

## Reproduction and learning checkpoint

Use the `phase-8-reliability` tag with the existing Phase 6 local setup. The
source/artifact [manifest](evidence/phase8-manifest.json) records the parent
revision, source hashes and runtime IDs. Exactly one commit represents this phase.

1. Run `python deploy/check_offline.py` in the provisioned virtual environment.
2. Build the test image with `docker compose -f compose.test.yaml -f compose.connected.yaml build tests`.
   Run the five root test modules `test_foundation.py`, `test_business.py`,
   `test_contracts.py`, `test_connected.py`, `test_observability.py` using that
   Compose test service and `python -m pytest -q`; then remove the test project
   with the same two files and `down`.
3. Build/start the source API with `compose.yaml`, `compose.odoo.yaml` and
   `compose.resources.yaml`. Never run connected mutation tests concurrently
   with load or recovery.
4. Set `ODOO_LIVE_TESTS=synthetic-sandbox`. Run `python -m reliability.load` and
   `python -m reliability.worker_drill` sequentially. The worker requires the
   dedicated Company A profile. Each load run intentionally creates 31 sandbox
   drafts; do not use production data.
5. Run the selected live tests listed in [control evidence](evidence/phase8-controls.txt).
   Set `OPENAI_LIVE_TESTS=yes` only for the single paid hosted canary, and
   `OLLAMA_LIVE_TESTS=yes`, `OLLAMA_TEST_MODEL=qwen2.5:0.5b` for the pinned local
   runtime. These calls are excluded from load measurements.
6. Follow the runbook to stop producers, retain a baseline image and run
   `python -m deploy.recovery_drill`. Inspect both pass and source-resumed flags.

The Phase 7 frozen evaluator intentionally refuses modified source. Reproduce
its score at `phase-7-quality` in a separate checkout/environment; do not
overwrite its freeze file to make it accept Phase 8. Phase 9 completes the
delivery pack and deployment preparation; it has not been started here.
