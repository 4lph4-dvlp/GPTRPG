---
phase: 03-ai
reviewed: 2026-08-02T10:48:18Z
depth: standard
files_reviewed: 30
files_reviewed_list:
  - .gitignore
  - .importlinter
  - pyproject.toml
  - src/gptrpg/agents/action_classifier.py
  - src/gptrpg/agents/config.py
  - src/gptrpg/agents/context.py
  - src/gptrpg/agents/envelope.py
  - src/gptrpg/agents/__init__.py
  - src/gptrpg/agents/invoke.py
  - src/gptrpg/agents/master_gm.py
  - src/gptrpg/agents/prompt_assembly.py
  - src/gptrpg/agents/providers/anthropic_provider.py
  - src/gptrpg/agents/providers/base.py
  - src/gptrpg/agents/providers/gemini_provider.py
  - src/gptrpg/agents/providers/__init__.py
  - src/gptrpg/agents/providers/nim_provider.py
  - src/gptrpg/agents/providers/openai_provider.py
  - src/gptrpg/agents/providers/openrouter_provider.py
  - src/gptrpg/cli/main.py
  - src/gptrpg/cli/turn_flow.py
  - src/gptrpg/rulebooks/moves.py
  - tests/conftest.py
  - tests/test_action_classifier.py
  - tests/test_agent_config.py
  - tests/test_agents_retry.py
  - tests/test_cli.py
  - tests/test_master_gm.py
  - tests/test_providers.py
  - tests/test_session_actor.py
  - tests/test_turn_tracer.py
  - uv.lock
findings:
  critical: 1
  warning: 3
  info: 3
  total: 7
status: issues_found
---

# Phase 03-ai: Code Review Report

**Reviewed:** 2026-08-02T10:48:18Z
**Depth:** standard
**Files Reviewed:** 30
**Status:** issues_found

## Summary

This phase wires 5 LLM provider adapters and a classify/narrate loop behind
an explicit, well-documented timeout/retry contract (`invoke.py`, D-27/D-28)
and adds a stall watchdog to `narrate()` after a live-verification incident
(~22 min hang on a stalled stream). The overall shape is disciplined: the
D14 boundary (`agents` must never see `event_log`/`session_actor`/`sqlite3`)
is genuinely enforced, not just declared — `.importlinter` contract:3 is
live, and `tests/test_boundaries.py` proves the underlying mechanism
actually trips on a real violation (though only for contract:1, see WR-02).
JSON parsing for reasoning-model output and speaker-labeled context are both
solidly tested against the exact failure modes described in the phase
context.

The one finding that undermines the phase's central promise — bounded,
predictable call latency — is that none of the provider adapters disable
the underlying SDK's own automatic retries. `call_with_one_retry` documents
and tests "exactly one retry, no delay" as an explicit, locked contract
(D-28), but `anthropic.Anthropic(...)` and `openai.OpenAI(...)` are
constructed with their SDK defaults (`max_retries=2`, confirmed against the
installed versions in this venv), each with its own backoff delay. A single
"attempt" as `call_with_one_retry` sees it can silently balloon into up to
3 real network round-trips with growing backoff sleeps, before the app-level
retry logic ever gets a chance to run — precisely the class of hidden
unbounded-latency bug this phase already had to patch once for streaming.

## Critical Issues

### CR-01: Provider SDK clients default to their own internal retries, silently defeating the documented "exactly one retry, no delay" contract

**File:** `src/gptrpg/agents/providers/anthropic_provider.py:27`, `src/gptrpg/agents/providers/openai_provider.py:54` (transitively affects `nim_provider.py` and `openrouter_provider.py`, which delegate to `OpenAIProvider`)

**Issue:** `invoke.py`'s `call_with_one_retry` is explicitly documented and tested (D-28, `tests/test_agents_retry.py`) to call the provider exactly twice total, with **no delay between attempts** ("재시도 사이에 지연을 두지 않는다(즉시 재시도)"). This contract is only honored at the app layer. The underlying SDK clients are constructed with no `max_retries` override:

```python
# anthropic_provider.py
self._client = anthropic.Anthropic(api_key=api_key)

# openai_provider.py
self._client = OpenAI(api_key=api_key, base_url=base_url, default_headers=default_headers)
```

Both SDKs default `max_retries=2` (confirmed via `inspect.signature` against the versions pinned in `uv.lock`: `anthropic>=0.120.2`, `openai>=2.52.0`). On any retryable condition (timeouts, connection errors, 429, 5xx) — exactly the failure modes `call_with_one_retry` is designed to handle — the SDK itself silently retries up to 2 more times internally, each with exponential backoff, *before* the exception is ever raised to `call_with_one_retry`. The result:

- A single logical "attempt" from `call_with_one_retry`'s point of view can involve up to 3 real HTTP round-trips with backoff sleeps in between, directly contradicting "즉시 재시도" (immediate retry, no delay).
- Worst-case wall-clock time for a fully-failed `classify()` call is no longer bounded by `~2 × CLASSIFIER_TIMEOUT_S ≈ 10s` as the design intends — it can be several multiples higher.
- This is the exact same *class* of bug already found live for the streaming path (`GM_TIMEOUT_S` not bounding total stream duration, fixed with the 90s stall watchdog) — but here it's on the non-streaming `classify()` path, which currently has no equivalent safety net, and it was never addressed.
- `tests/test_providers.py`'s `_no_network` fixture monkeypatches the SDK client classes entirely, so this behavior is invisible to the test suite — nothing currently asserts `max_retries` is disabled.

**Fix:** Disable SDK-level retries explicitly so `call_with_one_retry` is the single source of truth for retry policy, as the docstrings already claim it is:

```python
# anthropic_provider.py
self._client = anthropic.Anthropic(api_key=api_key, max_retries=0)

# openai_provider.py
self._client = OpenAI(
    api_key=api_key, base_url=base_url, default_headers=default_headers, max_retries=0
)
```

Add a regression test in `test_providers.py` asserting the fake client constructors receive `max_retries=0` (or equivalent) so this can't silently regress.

## Warnings

### WR-01: `_drain_with_stall_timeout`'s background pump thread is never cancelled on stall/retry, leaking a blocked thread per stalled attempt

**File:** `src/gptrpg/agents/master_gm.py:34-72` (`_drain_with_stall_timeout`), used from `narrate()` at `src/gptrpg/agents/master_gm.py:144-165`

**Issue:** When a stream stalls, `_drain_with_stall_timeout` raises `TimeoutError` from the *consumer* side, but the daemon thread it spawned to pump `source` (the live `provider.stream()` generator) keeps running — it is blocked inside `for item in source: q.put(item)` on whatever network read is actually stuck, with no cancellation mechanism (Python cannot forcibly interrupt a blocked thread). `narrate()`'s retry loop (`MAX_ATTEMPTS = 2`) can trigger this twice in a row for the same logical call, leaving two orphaned pump threads blocked simultaneously. Being `daemon=True` only guarantees the process can still exit; it does not reclaim the thread or the (leaked) generator/socket it's holding open. In the current one-shot CLI (`gptrpg turn`, one process per invocation) this is masked by process teardown, but it is a real leak the moment this code runs inside any longer-lived process (test suite in the same interpreter, a future server/daemon mode, or a REPL).

**Fix:** At minimum, document the leak explicitly at the call site (currently only described in the module docstring, not at the two spots where it actually happens — the `continue` and the fallthrough after the `for _attempt` loop). Where possible, prefer an interruptible I/O primitive over a bare thread (e.g., have the provider's underlying HTTP client enforce its own per-chunk read timeout so the pump thread unblocks on its own), or track+join spawned pump threads with a bounded timeout at process/session teardown so they don't silently accumulate across turns in a long-lived process.

### WR-02: D14 boundary trip-wire test only proves contract:1 (`rules_core`), not contract:3 (`agents`) — the exact boundary this review was asked to verify

**File:** `tests/test_boundaries.py:23-34`, `.importlinter:33-41` (contract:3)

**Issue:** `.importlinter` correctly declares contract:3 ("agents는 사건 저장소를 모른다" — `gptrpg.agents` forbidden from importing `gptrpg.event_log`, `gptrpg.session_actor`, `sqlite3`), and running `lint-imports` right now confirms all three contracts are currently kept (`Contracts: 3 kept, 0 broken`). However, `test_contract_actually_catches_a_violation` — the test whose entire purpose is to prove the checker isn't just "returning 0 for a no-op" — only injects a violation into `rules_core` (contract:1, by writing `import random` into a `_boundary_probe.py` file). There is no equivalent probe that injects `import gptrpg.event_log` (or `sqlite3`) into `gptrpg.agents` to prove contract:3 specifically would actually fire. Both contracts use the same import-linter `forbidden` mechanism, so this is a reasonable inference rather than a broken guarantee — but it is exactly the kind of "looks enforced, never actually verified for this specific boundary" gap the review was asked to check for.

**Fix:** Add a second violation-probe test mirroring the existing one, targeting `gptrpg.agents` (e.g., a temporary `_boundary_probe.py` under `src/gptrpg/agents/` that does `import sqlite3`), asserting `lint_imports(...)` returns `False` while the probe file exists.

### WR-03: `resolve_provider` is dead code — the real call path duplicates its logic instead of using it

**File:** `src/gptrpg/agents/config.py:93-100` vs `src/gptrpg/cli/turn_flow.py:146-158, 213, 294`

**Issue:** `config.py` defines and documents `resolve_provider(role, choices, env)` as "그 역할의 저장된 제공자를 실제로 만든다" (turns a role's stored choice into an actual provider), and it has its own unit test (`tests/test_agent_config.py::test_resolve_provider_raises_missing_api_key_when_env_unset`). But the actual production call site, `turn_flow.py::_resolve_role_choice` + its callers, never imports or calls it — it calls `get_provider(choice.provider, os.environ)` directly (`turn_flow.py:213`, `:294`) after resolving the choice inline. `resolve_provider` is therefore exercised only by its own test and never runs in the real `turn` command path. This isn't wrong today (the duplicated logic is correct), but it's dead production code that will silently drift from the real call path over time, and its `choices[role]` uses a bare dict index (a raw `KeyError` on a missing role) rather than the module's own stated "fail loud with a readable exception" philosophy that `ConfigNotFound`/`InvalidAgentConfig` otherwise follow.

**Fix:** Either wire `turn_flow._resolve_role_choice` through `resolve_provider` (removing the duplication), or remove `resolve_provider` if `_resolve_role_choice`'s inline approach is the intended long-term shape.

## Info

### IN-01: `CLASSIFIER_TIMEOUT_S = 5.0` is tight for the reasoning models this phase explicitly designed around

**File:** `src/gptrpg/agents/invoke.py:26-27`, `src/gptrpg/agents/action_classifier.py:82-96`

`action_classifier.py`'s own docstring extensively documents that reasoning models (NIM's Nemotron family) take noticeably longer and wrap output in `<think>...</think>` blocks, precisely because "애매한 문장일수록... 모델이 더 오래 '생각'하고" (the more ambiguous the sentence, the longer the model "thinks"). `CLASSIFIER_TIMEOUT_S` is locked at 5.0s by D-27 and this phase correctly doesn't revisit that number, but it's worth flagging for operator awareness: an operator running NIM/Nemotron as the classifier can hit both attempts' timeouts routinely on exactly the ambiguous inputs where 2-3 candidates matter most, silently degrading to the "무브 없음" screen every time — indistinguishable on screen from the model genuinely finding no match. Not a code defect given the locked decision, but worth surfacing since it directly affects the reliability of the tier-selection UX this phase built.

### IN-02: OpenRouter's `stream_options={"include_usage": True}` support is unverified

**File:** `src/gptrpg/agents/providers/openrouter_provider.py`, `src/gptrpg/agents/providers/openai_provider.py:108`

`OpenRouterProvider` delegates to `OpenAIProvider.stream()`, which always passes `stream_options={"include_usage": True}`. The module docstring for `nim_provider.py` states this parameter was live-verified against NIM's backend, but no equivalent verification is claimed for OpenRouter. If OpenRouter's OpenAI-compatible surface ignores or rejects this option, the failure mode is soft — `narrate()`'s broad `except Exception` would catch an outright rejection and retry/fail gracefully, but silent non-support would just leave `prompt_tokens`/`completion_tokens` at 0 in the final `AgentResult`, which then gets written into `RecordAiCall` as a false "zero-cost" call — indistinguishable from the documented `ok=False` failure-envelope zero-token convention, but here it would be attached to `ok=True`. Worth a live smoke test against OpenRouter before relying on its token/cost numbers.

### IN-03: `_turn_flow`'s "several" tier records a `picked` move even on rejection

**File:** `src/gptrpg/cli/turn_flow.py:256-272`

When the player rejects a multi-candidate proposal with `n`, `picked` falls back to `suggestion` (the first candidate) and the `ConfirmAction` event is still submitted with that move/stat, just with `player_confirmed=False`. This mirrors the intentional `single`-tier rejection behavior and downstream code correctly gates on `confirmed` before resolving a check, so it is not a functional bug — flagging only because a reader unfamiliar with the `single`-tier precedent could easily mistake this for "recording a move the player never picked." Consider a one-line comment at `picked = chosen if chosen is not None else suggestion` cross-referencing the `single`-tier rationale for consistency of intent, since the code itself doesn't currently explain *why* a rejected pick still needs a `move`/`stat` value.

---

_Reviewed: 2026-08-02T10:48:18Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
