# Model providers and local inference

All adapters share typed application contracts and deterministic business
controls. They use provider APIs, not consumer-chat UI automation. A request
uses one selected provider; switching providers never grants different authority.

| Profile | Implemented path | Verified scope |
| --- | --- | --- |
| OpenAI | Structured intent through the Responses API | Real local-stack canaries; frozen Phase 7 synthetic regression |
| Claude | Strict application output contract | Offline adapter tests; optional, not live-qualified |
| Grok | Strict application output contract | Offline adapter tests; optional, not live-qualified |
| Ollama | Native local inference and local-only checks | Pinned CPU runtime and real canaries; small model remains experimental |

The selected hosted profile is `gpt-4.1-mini-2025-04-14` with `intent-v4-openai`.
Phase 7 recorded 18/18 synthetic regression cases on its frozen contract 0.3.1
snapshot. Phase 8 contract 0.3.2 adds numeric grounding regressions and a separate
hosted canary. The optional Qwen2.5 0.5B profile scored 7/18 in Phase 7; it is not
promoted as a quality-equivalent default.

## Local runtime

Ollama 0.40.1 runs as a portable CPU runtime with Qwen2.5 0.5B Q4_K_M. Model
artifact digest, license hash, hardware and runtime settings are recorded in
[Phase 6 evidence](docs/evidence/phase6-local-runtime.json). Initial provisioning
requires downloads. Inference concurrency is bounded; hosted fallback is rejected
in local-only mode. Local inference does not make an internet-connected business
platform an offline application. This project has no embedding pipeline.

Tests cover malformed output, long/oversized responses, refusal, cancellation,
unavailable runtimes and unsafe provider routing. Host OOM injection was not
performed. Alternate runtimes such as llama.cpp or vLLM are not dependencies.

## Measurement and operation

Keep real-provider canaries, synthetic load and local-model evaluation separate.
Report exact model/prompt/runtime, sample counts, correctness, latency and usage.
Cost is unknown without a configured, versioned rate card; no savings claim is
inferred from local inference. Persist uncertain business state before changing
provider or retrying. Provider keys stay in private configuration.

Use a new task ID after changing model, prompt or contract. Follow the
[operator guide](docs/USER-GUIDE.md), [quality report](docs/PHASE-7.md) and
[rollback runbook](docs/LOCAL-RUNBOOK.md). Claude/Grok live canaries remain optional.
