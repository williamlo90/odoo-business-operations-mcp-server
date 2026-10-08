# Phase 3 - AI assistant and reusable skills

Status: **offline implementation complete** under the revised Phase 0–10 roadmap.
Live provider/Odoo/model validation belongs to Phase 6 and has not been run here.

## Implemented

- An importable Python assistant core and host-side CLI in `backend/assistant/`.
- A single bounded model decision selects a typed skill request or clarification.
  No model decision can approve or execute an Odoo write.
- HTTP adapters for OpenAI Responses, Claude Messages, Grok Chat Completions,
  and Ollama native chat. Model IDs must be explicitly configured.
- Four executable [business skills](../skills/README.md) with manifests, input/output
  schemas, documented recovery and shared deterministic handlers.
- Exact customer/product resolution, revision-bound customer pagination, sourced
  customer/opportunity facts, and proposal/operation response checks. Prices come
  from the domain service. Unsupported identifiers and extra model-authored facts
  are rejected. Quantity/summary intent still needs human preview review.
- Local metadata traces with task/actor/tenant IDs, schema/prompt hashes, versions,
  latency, token usage when supplied, proposal/operation IDs and terminal events.
  Task bodies, model text, credentials and source record contents are not logged.
  An explicit versioned rate card can estimate uncached token cost; missing usage
  remains unknown. No current model prices are assumed.

The model receives the operator's task, not retrieved Odoo text. Deterministic
skills retrieve the relevant source records after intent extraction and return
them as structured evidence. There is no free-form model factual summary,
embedding index or claim of completed retrieval-quality evaluation.

## Run lightweight tests

From the project root, using the existing Python virtual environment:

```powershell
.venv/Scripts/python.exe -m pytest -q --confcutdir=tests/assistant tests/assistant
```

Linux equivalent: `.venv/bin/python -m pytest -q --confcutdir=tests/assistant tests/assistant`.
Install `backend/requirements.lock` in a virtual environment if needed. No new
Python dependencies were added. `--confcutdir` excludes the parent PostgreSQL test
fixtures; this suite needs no Docker, database, API keys, network or model runtime.

Latest result: **49 Python tests and 2 TypeScript/Python process integration tests passed** using simulated provider/domain HTTP transports.
See [test evidence](evidence/phase3-offline-tests.txt). Coverage includes all four
provider request formats, all four skills, malformed/unsupported output, ambiguous
customers, wrong role/scope, changed pagination, lost prepare responses, refusal,
truncation, rate limits, missing usage, cancellation and local-cloud rejection.
This tests transport/application behavior, not model task quality or live compatibility.

Regenerate schema artifacts with:

```powershell
.venv/Scripts/python.exe -m deploy.export_assistant_contracts
```

## Run against the local stack later

First start the verified Phase 2 stack using [ODOO-LOCAL.md](ODOO-LOCAL.md). The
assistant runs on the host and reaches the API at `http://127.0.0.1:8020`; it does
not start Docker or download models. Use the generated local `.env` for login.

For hosted inference, set the relevant key in your shell or an ignored dotenv
file: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `XAI_API_KEY`. Select one provider and
an explicitly chosen model supporting that provider's structured output contract.
The placeholder below must be replaced before running:

```powershell
.venv/Scripts/python.exe -m backend.assistant --env-file .env --provider openai --model YOUR_MODEL_ID --task "Siapkan quotation OPS-A-001: 2 OPS-A-P1 dan 1 OPS-A-P2"
```

The CLI authenticates using `DEMO_USERNAME` (default `operator.a`) and `DEMO_PASSWORD`,
runs one task, then revokes its session. It loads dotenv only with `--env-file`;
existing shell variables take precedence. Do not put secrets in the task text.
Review the returned proposal using the existing TypeScript `preview`, `approve`
and `execute` commands. The TypeScript reference client invokes the Python assistant over bounded stdio:

```powershell
npm.cmd run build --prefix client
$env:ASSISTANT_ENV_FILE = '.env'
$env:ASSISTANT_PROVIDER = 'openai'
$env:ASSISTANT_MODEL = 'YOUR_MODEL_ID'
node client/dist/index.js assistant "Siapkan quotation OPS-A-001: 2 OPS-A-P1 dan 1 OPS-A-P2"
```

The client prints a task UUID before starting. To replay the original outcome,
set `ASSISTANT_TASK_ID` to that UUID and submit the identical task/configuration.
Use a new UUID for fresh source reads or fresh operation reconciliation. Replay
returns the original observation, not a newly validated business state.
`ASSISTANT_STATE_DIR` selects the local state directory (default
`local/assistant-runs/`). Keep it on local disk and protect it with host account
permissions; it contains structured decisions and results, not credentials.

Run the process-boundary tests after building with
`node --test client/tests/assistant.test.mjs`. They start only a tiny loopback HTTP
fixture and short-lived Python processes, not Docker or AI inference.

For a deterministic caller, save a Decision JSON in an ignored local file:

```json
{"request":{"skill":"research_customer","customer_reference":"OPS-A-001","include_opportunities":true}}
```

Then use `--env-file .env --request-file local/research.json` instead of `--task`.
Both entry paths invoke the same skill handler. The tests demonstrate this reuse;
an actual automation worker has not been connected yet.

## Local inference policy

The Ollama adapter connects only to `127.0.0.1:11434`, with proxy inheritance and
redirects disabled. It first requires `/api/status` to report cloud disabled and
`/api/show` to describe a local GGUF model with no remote host/model. Unsupported
runtime versions fail closed before receiving the task. Runtime compatibility
must be checked during the later live setup.

Configure `OLLAMA_NO_CLOUD=1` on the Ollama **server**, restart it, and use a
downloaded local model. `--local-only` rejects hosted provider selection. There
is no external fallback. Requests use one generation, a 4,096-token context,
bounded output and `keep_alive: 0`. No model has been selected, downloaded,
benchmarked or certified to fit this machine during this checkpoint.

## Limits and recovery

- One model generation per task, 30-second provider request timeout, 60-second
  total task timeout, 10-second domain request timeout, at most 16 domain calls.
- No implicit provider or prepare retry. A lost prepare response is uncertain;
  it may have created an application proposal, never an Odoo order via this skill.
- Reconciliation preserves the domain status and never calls the retry endpoint.
- Cancellation stops the client's wait; it does not imply remote rollback.
- Traces are appended under ignored `local/assistant-runs/`. A completed proposal
  remains durable in the existing domain database. The SQLite task journal fences concurrent callers, binds replay to actor/tenant
  and input fingerprint, and caches completed results. Only an expired `planned`
  checkpoint resumes automatically (lease 300 seconds, task timeout at most 120).
  Interrupted planning/dispatch requires review; uncertain prepare is never retried.
  Do not delete active state. After task resolution, retain local state only as long
  as needed for development/audit; archive/delete the whole inactive state directory
  under the host owner's policy. This journal is not a distributed job database.
- The CLI is for trusted local operators, not an exposed multi-user assistant API.

## Deferred to Phase 6 and later

1. Run real-provider canaries for each available credential and report status per
   provider. No provider is currently live-validated for this implementation.
2. Provision/pin Ollama runtime and model artifacts, record licensing/hardware,
   run actual inference, quality/latency/resource evaluation and failure recovery.
3. Run the AI-to-Odoo workflow through human approval, execution and verified
   read-back on the live sandbox; rerun the existing regression suite.
4. Verify multi-tenant/reuse behavior with real Odoo and the worker, measure quality
   on frozen datasets in Phase 7, then harden/load-test in Phase 8. Custom MCP
   transport remains Phase 4; worker integration remains Phase 5.

## Rate cards and accounting

An optional `--rate-file` (Python) or `ASSISTANT_RATE_FILE` (TypeScript) points to
JSON with `provider`, `model`, `version`, `source`, `input_usd_per_million` and
`output_usd_per_million`. Rate numbers are decimal strings. The model/provider
must match exactly. Estimates are labeled `estimated_uncached`; they do not claim
invoice accuracy or account for cache discounts, tools, taxes or local electricity.
Without rates/usage, cost is null. Test rates are synthetic and are not price advice.

## Learning checkpoint

This phase is one commit on `learning-phases`, based on the Phase 2 learning-path
commit. It incorporates the earlier partial assistant work without rewriting
published `main` history. Phase completion here means the revised offline gate;
no live-model quality or connected Phase 6 result is implied.

## Adapter references

Checked on 2026-10-08. Payloads follow official documentation; live validation is
still needed for the chosen model and runtime versions.

- [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)
- [Claude structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [Grok structured outputs](https://docs.x.ai/developers/model-capabilities/text/structured-outputs)
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs)
- [Ollama local-only server configuration](https://docs.ollama.com/faq#how-do-i-disable-ollama-cloud-features)
- [Ollama status/show client contracts](https://github.com/ollama/ollama/blob/main/api/client.go)
