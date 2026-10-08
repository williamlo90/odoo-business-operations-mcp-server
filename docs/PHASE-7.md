# Phase 7 - Local quality evaluation

The selected hosted profile is GPT-4.1 mini `gpt-4.1-mini-2025-04-14`, prompt
`intent-v4-openai`, temperature 0, assistant contract `0.3.1`. It passed all 18
tasks in the frozen synthetic regression suite through the production assistant,
MCP subprocesses and local Odoo. This qualifies the profile for the tested local
scope; it is not an independent generalization or production-traffic claim.

Status: **Complete for the selected local regression qualification scope.**
Human time study and independent generalization claims are outside this result.

## Final results

| Frozen category | Typed reference | OpenAI | Qwen2.5 0.5B CPU |
| --- | ---: | ---: | ---: |
| Complete tasks | 8/8 | 8/8 | 6/8 |
| Clarification | 6/6 | 6/6 | 0/6 |
| Domain boundary | 4/4 | 4/4 | 1/4 |
| Correct tasks | 18/18 | 18/18 | 7/18 |
| Critical violations | 0 | 0 | 0 |
| Quality gate | Reference control | Pass | Fail: experimental only |

No cases were excluded from these final runs. The model-local failures are
available per case in the score report, including invalid model output, invented
references and an incorrect clarification. Application rejection prevented those
invalid plans from becoming business writes; it does not earn task-success credit.
Do not use the small local model as the quality-qualified natural-language default.

| Sequential observations | Typed reference | OpenAI | Local model |
| --- | ---: | ---: | ---: |
| Task sample count | 18 | 18 | 18 |
| Total task seconds | 15.966 | 40.086 | 57.482 |
| Median task seconds | 0.899 | 2.223 | 3.177 |
| Observed p95 task seconds, all statuses | 1.010 | 2.663 | 3.513 |
| Input / output tokens | Not applicable | 17,234 / 499 | 4,355 / 815 |

The successful-task p95 values are respectively 1.010 (N=18), 2.663 (N=18), and
3.513 seconds (N=7). Model time and total elapsed time are stored separately per
case. Runs were sequential on Windows with an Intel Core i7-13620H, CPU Ollama
and a shared Docker Desktop host. No controlled-load or human-time comparison
is implied by these observations.

Evidence: [OpenAI score records](evidence/phase7-openai.json),
[local-model score records](evidence/phase7-ollama.json),
[typed reference](evidence/phase7-reference.json).

## Scope and rubric

The [protocol](../evaluation/POLICY.md), [cases](../evaluation/regression-v2.json)
and [source/profile freeze](../evaluation/freeze-v3-final.json) define the run.
The 18 cases comprise 8 complete tasks across all four skills, 6 clarification
requests, and 4 missing-record/foreign-company cases. The threshold was fixed at
17/18 overall, 8/8 complete tasks, at least 5/6 clarification, 4/4 domain boundary,
and zero critical violations. No excluded cases, generation retries or corrections
are allowed in a completed final run. A critical violation stops the run and
leaves unrun cases explicitly counted against qualification.

Scoring compares exact typed decisions and independently checks customer identity,
source facts, requested opportunities, quotation quantities/prices/currency/total,
activity fields and operation status. Safe rejection of invalid model output
does not count as correct model understanding. All examples and platform data
are synthetic; a coding agent authored and ran the evaluation.

Cases used while debugging are regression cases. The final result is reported
on that basis, with a new untouched source-family set required before claiming
generalization for a future change. The original development cases, promoted
regressions and final frozen cases remain available for reproducibility. Raw
intermediate traces and experiments stay in ignored `local/evaluation/` and
`local/evaluation-history/`.

## Application behavior

Quotation quantities must appear explicitly as plain numeric integers in the
natural-language task. Digits inside a reference/product code cannot supply a
missing quantity. Negative values and decimal fragments cannot justify a positive
integer quantity in the tested rejection cases (`-1`, `1.5` and `1,5` incorrectly
reduced to `1`). Normal sentence punctuation is accepted. This guard checks
numeric presence, not the semantic association of every number with a product;
the approver must still review customer, line items, quantities and totals.

The OpenAI prompt checks unsupported actions first, requests all missing required
fields, treats identifiers as literal codes and distinguishes read-only operation
reconciliation from executing a write. Temperature 0 is configured only for the
validated GPT-4.1 mini snapshot; it does not guarantee deterministic model output.
Other model IDs retain their existing transport settings and need qualification.

The contract version changed to `0.3.1`, and the OpenAI prompt version changed to
`intent-v4-openai`. The journal binds both to task context, preventing replay of
an old cached plan under new behavior. Start a fresh task UUID after upgrading;
preserve old journals for audit. Skills and the domain API remain backward
compatible with typed request callers.

Claude/Grok are optional adapters with offline coverage only. Ollama remains an
explicit experimental option; integration success alone does not qualify its
small model for unrestricted natural-language business tasks. The normal CLI
still requires an explicit model selection and does not silently send local-only
tasks to a hosted provider.

## Reproduce

Start the synthetic stack and local runtime using [Phase 6](PHASE-6.md). Use the
project virtual environment and built TypeScript client/MCP packages. Never run
the connected fault suite concurrently with evaluation; it changes synthetic
source records temporarily.

```powershell
.venv/Scripts/python.exe deploy/check_offline.py
$env:ODOO_LIVE_TESTS = 'synthetic-sandbox'
.venv/Scripts/python.exe -m evaluation.quality run --provider reference
$env:OPENAI_LIVE_TESTS = 'yes'
.venv/Scripts/python.exe -m evaluation.quality run --provider openai
.venv/Scripts/python.exe -m evaluation.quality run --provider ollama
```

The OpenAI evaluation makes exactly 18 bounded paid generations for a full run,
each with at most 500 output tokens and no automatic generation retries. The
runner verifies frozen source/data hashes before generation. It also checks
Ollama runtime/cloud configuration and the pinned model digest. The key is loaded
from ignored `.env` or environment, never from a dataset or report.

Each invocation creates a fresh run directory with a report, score records,
traces and journal. It creates one approved synthetic receipt fixture for the
reconciliation case and verifies replay; task preparation itself does not execute
business writes. Separate connected control tests verify execution and read-back.

For final-profile development and connected regressions:

```powershell
$env:OLLAMA_LIVE_TESTS = 'yes'
$env:OLLAMA_TEST_MODEL = 'qwen2.5:0.5b'
.venv/Scripts/python.exe -m pytest -q --confcutdir=tests/live tests/live
docker compose -f compose.test.yaml -f compose.connected.yaml build tests
docker compose -f compose.test.yaml -f compose.connected.yaml run --rm tests python -m pytest -q -o cache_dir=/tmp/pytest-cache tests/test_foundation.py tests/test_business.py tests/test_contracts.py tests/test_connected.py
docker compose -f compose.test.yaml -f compose.connected.yaml down
```

The full live suite includes seven paid OpenAI generations (four integration
canaries and three development regressions); local inference is separate.

## Measurement limits

The reference run supplies a known typed decision through the same assistant/MCP
path. Its comparison measures software waiting time, not manual human labor.
Human active time, corrections and ROI remain unmeasured and outside this phase's
selected claim. A human time study can be added separately without blocking local
quality qualification.

Report latency with N and status distribution. Nearest-rank p95 for 18 sequential
cases is only a small sample observation; it is not a load/throughput guarantee.
Confidence intervals in the score files are descriptive Wilson intervals, not
production confidence bounds: synthetic cases are related and not IID.
Token counts are recorded, while dollar cost remains null without a verified
rate card. Sustained throughput, per-tool latency, backup/recovery and resource
stress testing belong to Phase 8.

Method references: [evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices),
[Responses sampling parameter](https://developers.openai.com/api/reference/python/resources/responses/methods/create).

## Control verification

All final checks passed: 86 offline tests (6 evaluator, 54 assistant, 16 worker,
2 client, 8 MCP), 20 live tests, and 38 PostgreSQL/Odoo regression tests. Both
TypeScript builds passed. The Docker suite emitted one existing Starlette/httpx
deprecation warning. Its isolated test database/container/network were removed;
the normal Odoo stack and its audit records were preserved.

| Required failure scenario | Evidence in the passing suites |
| --- | --- |
| Same-name customer ambiguity | `test_ambiguous_customer_requires_exact_reference`; connected ambiguity/pagination case |
| Cross-company isolation | Foundation tenant tests, connected company case, final Q17/Q18 |
| Approval reused with modified payload | `test_approval_payload_role_tenant_and_actor_controls`; MCP wrong-role/stale/tenant checks |
| Source changes after preview | `test_connected_price_update_race_invalidates_approval` |
| Response lost after a real draft write | `test_connected_lost_response_reconciles_without_second_write` (response-drop fault injection after actual Odoo write) |
| Missing/duplicate/changed pagination | Connected pagination tests and assistant revision validation |
| Forbidden model/field/tool injection | Domain malformed-input tests, MCP schema-injection tests, final Q14 |

Concurrent and repeated approved writes also verify a single Odoo operation and
sales-order effect in the connected suite. Model calls prepare only; they do not
approve or execute. The live suite verifies real MCP/worker reuse and separate
approver identities for both companies. These finite cases do not replace the
broader security, recovery and load work in Phase 8.

Evidence: [verification summary](evidence/phase7-controls.txt),
[source and artifact manifest](evidence/phase7-manifest.json).
