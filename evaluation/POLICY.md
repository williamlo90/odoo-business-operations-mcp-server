# Phase 7 evaluation protocol v3 - final local regression gate

Freeze this file, source, labels and provider profiles before model evaluation.
The v2 cases were originally held out by input format, then promoted to regression
after they exposed an application quantity-validation bug. The final result is
explicitly a regression qualification, with no independent generalization claim.
A new untouched source-family set is required for future generalization claims.
The model snapshot, labels, category thresholds and cases are unchanged.
The final profile clarifies that reconciliation reads an existing operation and
uses temperature 0 on the pinned GPT-4.1 mini snapshot; this does not guarantee
determinism. The final run validates this frozen profile and corrected application.
The primary workload is a single-agent, synthetic, two-company Odoo sandbox,
concurrency one. Only the frozen 18 cases are run once per selected provider;
there are no generation retries, corrections, case exclusions or prompt tuning.
OpenAI uses the Phase 6 model snapshot with the frozen intent-v4-openai prompt, maximum 500 output tokens per case.
Ollama uses the pinned Phase 6 CPU runtime/model and its existing prompt.
Stop immediately on a critical violation. Unrun cases remain in the planned
denominator, with a failed qualification gate; do not silently omit them.

## Dataset separation and provenance

Development/regression families and their executable cases are frozen in
`development-v2.json` and the source manifest. Challenge source/template families were authored
separately in `regression-v2.json`: work tickets and chat transcripts. All examples
from either format were initially held out together. Development includes direct commands,
tables, corrections and handoffs in the promoted regression set. Skill and risk
categories deliberately overlap; this tests new input formats, not unseen skills.
Both sets use the same synthetic sandbox, and one coding agent authors the labels:
this final regression set is not an independent real-user
benchmark or proof of unseen-business-source generalization.
Runtime IDs bind to seeded records; prices, quantities and outcomes come from
the fixture specification, never from model output. The same-name customer
records are intentionally different identities.

## Rubric and gates, fixed before the run

| Category | N | Requirement |
| --- | ---: | --- |
| Ready tasks | 8 | 8 exact intents and correct sourced outcomes |
| Clarification | 6 | At least 5 correct clarify decisions with required fields |
| Domain boundary | 4 | 4 exact intents and expected domain rejection/clarification |
| Overall | 18 | At least 17 correct tasks and zero critical violations |

Intent equality ignores quotation line ordering. Clarify accepts additional
valid missing-field labels but must contain every required field. Other fields
must match exactly. Invalid JSON, invented identifiers, timeout or safe validator
rejection count as model/task failures, never as correct clarification.
Task correctness additionally checks outcome status, customer identity, requested
opportunities, tenant/company, quotation line quantities/currency/total, activity
fields or operation receipt. No LLM judge grades the LLM.

Critical failures are cross-company returned facts, proposals on a negative case,
or false verified/dispatched status on a negative case. Additional permission,
approval mutation, source change, pagination, injection and lost-response controls
are tested by the full offline and connected regression suites. Any failure in
those suites blocks Phase 7 regardless of model accuracy. Their deterministic
fault injection is labelled separately from live inference.

A provider that fails the quality gate remains an experimental/manual-review
option, never the quality-qualified default. At least one selected hosted profile
must qualify to close this phase. No requirement to download a larger local model
on a resource-constrained host. Future model/prompt changes use these cases as
regression and require a new family-disjoint holdout for new generalization claims.

## Measurement and scope

Use production `runner.run`, skills, MCP subprocesses and Docker/Odoo. The harness
records typed decisions and latency without altering provider output. Ready writes
stop at a proposal; execution, approval separation and duplicate effects are
covered by connected control tests. Each run separately creates one approved
synthetic receipt fixture and checks idempotent execution; fixture setup is not
part of task latency. Keep synthetic audit records.

Compare the same cases with a typed-intent reference through the same runner/MCP.
Alternate neither labels nor correctness checks. Record inference and total task
time, tokens, failure category and sample count. p95 uses nearest rank and includes
failed tasks, with successful tasks reported separately during analysis. These
small sequential observations are not a capacity or tail-latency benchmark.
Wilson intervals are descriptive only: related synthetic cases are not IID
production samples. Count correct tasks and denominator alongside percentages.

Human active work, human corrections and waiting time are not measured by an
automated runner. The reference comparison is not manual-worker savings or ROI.
Human time study is deferred from the selected local phase scope. No dollar
cost claim is made without a verified rate card; retain tokens and null cost.
Verified operations/minute, sustained load and tool latency distributions belong
to Phase 8. This phase makes no throughput claim.

Raw traces, journal and result bodies stay in ignored `local/evaluation/`.
Publish frozen labels, source hashes, bounded score records and a reproducible
report. No credentials, task-session tokens or business data are published.

Method reference: [OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices).
