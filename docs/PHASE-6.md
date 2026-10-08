# Phase 6 â€” Connected integration

Status: **Complete for the selected local scope: Docker/Odoo, OpenAI and Ollama.**
Claude/Grok are optional adapters with offline contract coverage only; live
compatibility is unverified and is not a release gate for this scope.

## Connected results (2026-10-08)

- Rebuilt and started the isolated `odoo-ops-local` stack from the current source.
  PostgreSQL databases, Odoo and the domain API all became healthy.
- 38 regression tests passed, including 9 connected Odoo scenarios covering actual
  signed writes, replay/concurrency, stale sources and recovery. One existing
  Starlette/httpx deprecation warning was emitted.
- 7 new connected scenarios passed through actual host Python/TypeScript MCP
  subprocesses and the Docker API/Odoo stack: company A and B quotation workflows,
  company A and B scheduled worker reads, a worker-prepared CRM activity, and
  real CLI runs with dedicated automation profiles for both companies.
- Quote totals were IDR 250,000 (A) and IDR 290,000 (B). Preparation replay returned
  the same proposal; repeated approved execution returned the same verified
  operation/receipt. Foreign-tenant operation reads returned 404.
- Operator approval was denied. A separate synthetic approver account approved
  the test proposals. This is an automated role-separated approval test, not a
  claim that a human performed acceptance testing.
- Scheduled jobs and activity events used durable SQLite state and the same
  production skill handlers. Restart/replay did not enqueue or prepare twice.

The seven stack cases use typed decisions. An additional five live local AI
canaries use actual Qwen2.5 inference; results and limitations are recorded below.
These are integration cases, not a held-out model-quality evaluation.

## Reproduce

Use the existing private `.env` and synthetic Odoo connection configuration from
[Odoo setup](ODOO-LOCAL.md). `compose.resources.yaml` provides optional memory
limits for this project's services; other projects are untouched.

```powershell
docker compose -f compose.yaml -f compose.odoo.yaml -f compose.resources.yaml up --build -d --wait --wait-timeout 240 api
docker compose -f compose.test.yaml -f compose.connected.yaml build tests
docker compose -f compose.test.yaml -f compose.connected.yaml run --rm tests python -m pytest -q -o cache_dir=/tmp/pytest-cache tests/test_foundation.py tests/test_business.py tests/test_contracts.py tests/test_connected.py
docker compose -f compose.test.yaml -f compose.connected.yaml down
npm.cmd run build --prefix mcp-server
$env:ODOO_LIVE_TESTS = 'synthetic-sandbox'
.venv/Scripts/python.exe -m pytest -q --confcutdir=tests/live tests/live/test_stack.py
Remove-Item Env:ODOO_LIVE_TESTS
```

Run the two suites sequentially: the regression suite temporarily changes
synthetic source records to test stale approvals. The new suite requires explicit
opt-in and verifies that the local connection file names only `odoo_ops_sandbox`
at the expected local Docker Odoo URL. It creates synthetic draft quotations and
an activity and intentionally preserves their audit/operation records. Never
point this suite at real business data. No email is sent by the sandbox addon.

The normal API uses port 8020 and Odoo uses 8069, both loopback-only. The application
and Odoo volumes are preserved. To release resources when finished:

```powershell
docker compose -f compose.yaml -f compose.odoo.yaml -f compose.resources.yaml stop
```

## Selected integration scope

OpenAI, Ollama/local inference and dedicated automation accounts for both
companies are validated. Claude/Grok remain optional, unverified live integrations.
Enabling either later requires private credentials, an explicit model ID and its
own connected canary before use. Phase 7 evaluates the selected providers.

Evidence: [run summary](evidence/phase6-connected-tests.txt) and
[source manifest](evidence/phase6-source-manifest.json).

## Dedicated automation identities

```powershell
docker compose build migrate
.venv/Scripts/python.exe deploy/provision_worker.py a
.venv/Scripts/python.exe deploy/provision_worker.py b
```

Profiles are private ignored files in `local/worker-profiles/company-a.env` and
`company-b.env`. The helper runs only against `odoo_ops_local`, creates separate
synthetic operator identities and preserves matching credentials on repeated runs.
It refuses mismatching identities/credentials instead of rotating them silently.
The operator role supports preparation and approved execution; worker code itself
only reads/prepares/reconciles and has no approval or execution command. This is
not a new narrower API role. Use each profile with `backend.worker --env-file ...`.
The CLI tests prove actor/tenant binding and durable replay against actual Odoo.

## Local AI runtime setup

Use the official portable Windows archive for [Ollama 0.40.1](https://github.com/ollama/ollama/releases/tag/v0.40.1).
Extract `ollama.exe` and its `lib/ollama` tree into `local/ollama-portable/`.
The validated runtime uses the CPU backend, with GPU backends disabled. The runtime is a project-started process, not an installed host service.

```powershell
./deploy/start_ollama.ps1
./local/ollama-portable/ollama.exe pull qwen2.5:0.5b
$env:ODOO_LIVE_TESTS = 'synthetic-sandbox'
$env:OLLAMA_LIVE_TESTS = 'yes'
$env:OLLAMA_TEST_MODEL = 'qwen2.5:0.5b'
.venv/Scripts/python.exe -m pytest -q -s --confcutdir=tests/live tests/live/test_local_ai.py
```

The startup helper configures localhost-only port 11434, cloud disabled, CPU inference,
one loaded model/request, a 4096-token context and immediate unloading. It changes
only that process's environment. Models persist outside OneDrive under
`%LOCALAPPDATA%/OdooOps/ollama-models`; process identity and logs are in ignored
`local/ollama-runtime/`. The provider verifies runtime/cloud and GGUF metadata
before sending a task and has no external fallback.

Initial runtime/model downloads need internet access. Stop the specific project
runtime after testing with `./deploy/stop_ollama.ps1`; this preserves artifacts and
checks process identity before stopping anything. The Odoo Docker stack is separate.

Validated integration model: Qwen2.5 0.5B Q4_K_M (~398 MB), Apache-2.0.
The runtime executable hash is checked before startup; canaries check the exact
runtime version and model manifest digest from the evidence file.
References: [cloud disable configuration](https://docs.ollama.com/faq#how-do-i-disable-ollama-cloud-features),
[model metadata](https://ollama.com/library/qwen2.5:0.5b), and
[upstream license](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/blob/main/LICENSE).

## Live local inference results

Five canaries passed on the final CPU configuration:

- A real model selected customer research from an English request.
- A real model extracted exact product codes and quantities from an Indonesian quotation request.
- For each of company A/B, a model-generated quotation flowed through MCP, separate
  approver credentials, idempotent execution and matching Odoo read-back.
- An unsupported email request was rejected before any business tool call.

**Model limitation:** the unsupported request produced an invalid intent, not a
correct refusal/clarification. The application validator rejected it with
`model_output_invalid`; the test verifies safe rejection, not model correctness.
This 0.5B model is an integration baseline and is not approved as a production
quality default. Larger-model comparison and broader intent/ambiguity coverage
belong to Phase 7. GPU acceleration is not part of the validated configuration.

The final quotation cases took 4.324 and 4.102 seconds from assistant start to
proposal, each reporting 226 input and 61 output tokens. These are two observed
integration timings, not latency percentiles or throughput claims. Costs remain
unknown (`not_estimated`); these local canaries made no hosted API calls.

The actual TypeScript assistant CLI also returned sourced Odoo customer data after
local inference. A stopped runtime returned `provider_unavailable` without hosted
fallback; restarting it restored the CLI flow. `/api/ps` confirmed the model was
unloaded after the task. Missing-model preflight also failed before generation.

Evidence: [local canaries](evidence/phase6-local-ai-tests.txt),
[client and recovery](evidence/phase6-local-client.json),
[runtime/model artifact hashes](evidence/phase6-local-runtime.json).

## OpenAI live validation

The selected canary snapshot is `gpt-4.1-mini-2025-04-14`, using Responses API
Structured Outputs and `store=false`. Four live tests passed: unsupported actions
and incomplete inputs returned clarification without business tool dispatch;
company A/B quotations passed MCP preparation, separate approver credentials,
Odoo execution, read-back and replay. The actual TypeScript client also completed
a sourced customer read through OpenAI, MCP and Odoo.

OpenAI uses prompt profile `intent-v2-openai`, which explicitly requires the
clarify branch instead of partially filled requests. Ollama retains its validated
`intent-v1` profile. Both share the same typed contracts, grounding, authorization
and approval rules. Traces hash the actual provider prompt, and the task journal
binds replay to its version. Use a fresh task UUID when switching prompt profiles;
reusing an old OpenAI task UUID with changed context is rejected.

```powershell
$env:ODOO_LIVE_TESTS = 'synthetic-sandbox'
$env:OPENAI_LIVE_TESTS = 'yes'
.venv/Scripts/python.exe -m pytest -q -s --confcutdir=tests/live tests/live/test_openai.py
```

This command makes four paid API generations, at most 500 output tokens each,
without automatic generation retries. It loads `OPENAI_API_KEY` from the process
or ignored `.env`. For the reference client, select `ASSISTANT_PROVIDER=openai`,
`ASSISTANT_MODEL=gpt-4.1-mini-2025-04-14`, `ASSISTANT_LOCAL_ONLY=0`, and
`ASSISTANT_ENV_FILE=.env`; then run `node client/dist/index.js assistant "Read customer OPS-A-001 without opportunities."`.
The client uses the existing bounded provider defaults. Keys stay in local config.

Evidence: [OpenAI canaries](evidence/phase6-openai-tests.txt),
[actual client](evidence/phase6-openai-client.json).
References: [model documentation](https://developers.openai.com/api/docs/models/gpt-4.1-mini),
[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).
These cases establish integration behavior only; broader quality evaluation is Phase 7.
