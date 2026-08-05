# Phase 3 — External API Coverage Matrix

**Produced:** 2026-08-02 (plan time, `/gsd-plan-phase 3`)
**External APIs in scope:** Anthropic Claude, OpenAI, Google Gemini, Nvidia NIM, OpenRouter — five LLM provider APIs, reached through three official SDKs (`anthropic`, `openai`, `google-genai`; NIM and OpenRouter ride the `openai` client with `base_url` swapped, per 03-RESEARCH.md § Standard Stack).

> **Detector note.** `bin/lib/api-coverage.cjs` returned `{"detected": false}` on this phase's scope. Its signal-term lists are English-only and this phase's ROADMAP section and CONTEXT.md are written in Korean, so the deterministic scan cannot fire here — the same language limitation that made the edge-probe engine return `unclassified` for all four requirement texts. The phase manifestly integrates five external LLM APIs, so this matrix is produced anyway. A valid matrix always passes the seal-time gate; a false-negative detection must not become a silent hole.

## Capability surface

The capability surface is the same for all five providers (each exposes a chat-completions-shaped API plus a models endpoint), so one matrix covers all five. Where a capability's availability differs per provider, the difference is noted.

| capability | decision | reason |
|---|---|---|
| `list_models` (live model catalog query) | INTEGRATE | D-31 explicitly requires querying each chosen provider's live model list at selection time. Built in 03-01 (Anthropic) and 03-02 (the other four). |
| `chat_completion` (non-streaming) | INTEGRATE | `action_classifier` needs one short request/response per turn (RIG-01). |
| `streaming_completion` | INTEGRATE | RIG-03 requires narration to stream out sentence by sentence. |
| `token_usage_reporting` | INTEGRATE | `AiInvoked.prompt_tokens`/`completion_tokens` must carry real counts (MEAS-02, D-30); MEAS-01 in Phase 4 aggregates them. |
| `request_timeout` | INTEGRATE | D-27 (5s classifier) and the already-locked 15s GM ceiling are enforced through each SDK's timeout parameter (03-03). |
| `prompt_caching` | INTEGRATE | The phase's stated hidden requirement — cache hit/miss is a 3.7x cost swing. Anthropic: explicit `cache_control` breakpoints at the permanent and session boundaries. OpenAI: automatic on a byte-identical prefix, no code-level breakpoint exists, so the ordering discipline in `prompt_assembly.py` is the whole integration. Gemini: implicit caching, on by default, same prefix rule. |
| `structured_output` (constrained response shape) | INTEGRATE | Implemented provider-agnostically at the prompt level — the classifier's instruction asks for move ids drawn from the closed catalog, and `classify` validates every returned name against `rulebooks/moves.py`, raising `UnknownMove` on a miss. Not implemented via each provider's proprietary JSON-mode API. |
| `custom_base_url` | INTEGRATE | The integration path for Nvidia NIM (`https://integrate.api.nvidia.com/v1`) and OpenRouter (`https://openrouter.ai/api/v1`) — both document themselves as OpenAI-compatible. |
| `custom_request_headers` | INTEGRATE | OpenRouter's `HTTP-Referer`/`X-Title` attribution headers are attached defensively (03-RESEARCH.md Open Question 1 could not confirm whether they are required for the models endpoint). |
| `tool_use` / `function_calling` | OPT-OUT | Not needed — D-16 confines the LLM to picking from a closed list and narrating. A tool-call round trip buys nothing over validating a returned move id against the catalog. |
| `explicit_prompt_cache_objects` (Gemini `caches.create` + TTL) | OPT-OUT | Not needed — Gemini's implicit caching is on by default and keyed on the same stable-prefix rule the phase already enforces; explicit cache creation costs an extra round trip per scene. Revisit at Phase 6 only if the cost re-calculation shows implicit caching is not hitting. |
| `extended_thinking` / reasoning-effort controls | OPT-OUT | Not needed yet — M0 fixes the top-tier model to measure the quality ceiling, not to tune cost. Latency/cost tuning is Phase 6's question, after the numbers exist. |
| `logprobs` / token-probability access | OPT-OUT | Explicitly out of scope — D-16 killed the confidence-threshold concept platform-wide and D-37 forbids showing a confidence number. UI intensity is derived from candidate count, so no probability signal is needed. |
| `moderation` / safety-classification endpoints | OPT-OUT | Explicitly out of scope — REQUIREMENTS.md lists safety-layer UI as replaced by verbal agreement for the experiment; the real safety layer is M1-05. |
| `vision` / image input | OPT-OUT | Not needed — the experiment is text-only; there is no image surface anywhere in M0. |
| `audio` / speech input or output | OPT-OUT | Not needed — voice is explicitly out of scope (REQUIREMENTS.md: party chat and voice happen in an external messenger). |
| `embeddings` | OPT-OUT | Explicitly out of scope — REQUIREMENTS.md rules out retrieval-based memory injection ("검색 품질이라는 실패 지점을 추가하면 재미있나를 못 잰다"). Memory injection is the four fixed items in `TurnContext`. |
| `batch` / asynchronous bulk completion | OPT-OUT | Not needed — this is an interactive turn loop where the player is waiting; batching is structurally inapplicable. |
| `files` / document upload | OPT-OUT | Not needed yet — rulebook file upload and parsing is M1-04. This phase's rulebooks are hand-written Python data declarations. |
| `fine_tuning` | OPT-OUT | Not needed yet — the labeled data this phase produces (MEAS-04) is scored in Phase 6, not trained on. Any training use would also breach this phase's recorded prohibition on exporting player sentences beyond the provider call. |
| `assistants` / stateful server-side threads | OPT-OUT | Not needed — conversation state lives in this project's own event log (RIG-06, the one irreversible M0 decision). A provider-held thread would duplicate and contradict it. |
| `rate_limit_headers` / retry-after handling | OPT-OUT | Not needed — D-28 caps retries at exactly one, with no backoff math. Honoring a retry-after hint would require the retry policy D-28 deliberately cut. |
| `usage`/`billing` admin endpoints | OPT-OUT | Not needed — MEAS-01 (Phase 4) computes spend from the token counts already recorded in `AiInvoked`, not from provider billing APIs, so the number stays reproducible from the event log alone. |
| `embedded_web_search` / provider-side retrieval tools | OPT-OUT | Explicitly out of scope — same reason as embeddings; adding a retrieval failure point would confound the fun measurement (HYP-01). |

## Second-integration note

D-31 asks for five providers against the same need. Per the coverage rule, each provider starts from the **same** full-coverage baseline — the opt-outs above are decided once for the capability surface itself, not carried over asymmetrically from whichever provider was integrated first. Concretely: Anthropic is integrated first (03-01, the tracer) but gains no capability the other four are denied. The one asymmetry that does exist is a provider-side fact, not a decision: Anthropic exposes explicit cache breakpoints while OpenAI and Gemini cache automatically, so `prompt_caching` is INTEGRATE for all five with a different mechanism per provider rather than INTEGRATE for one and OPT-OUT for four.
