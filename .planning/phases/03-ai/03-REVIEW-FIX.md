---
phase: 03-ai
fixed_at: 2026-08-02T11:02:22Z
review_path: .planning/phases/03-ai/03-REVIEW.md
iteration: 1
findings_in_scope: 7
fixed: 7
skipped: 0
status: all_fixed
---

# Phase 03-ai: Code Review Fix Report

**Fixed at:** 2026-08-02T11:02:22Z
**Source review:** .planning/phases/03-ai/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 7 (fix_scope=all — Critical, Warning, and Info)
- Fixed: 7
- Skipped: 0

**Isolation:** All fixes were made and verified in an isolated git worktree
(`/tmp/sv-03-reviewfix-*`, branch `gsd-reviewfix/03-*`), then fast-forwarded
onto `docs/m0-closeout`. Verification (full test suite, `lint-imports`,
`ruff check .`) ran inside that worktree after a fresh `uv sync`.

## Fixed Issues

### CR-01: Provider SDK clients default to their own internal retries, silently defeating the documented "exactly one retry, no delay" contract

**Files modified:** `src/gptrpg/agents/providers/anthropic_provider.py`, `src/gptrpg/agents/providers/openai_provider.py`, `tests/test_providers.py`
**Commit:** `7e25837`
**Applied fix:** Passed `max_retries=0` at SDK client construction in both `AnthropicProvider.__init__` and `OpenAIProvider.__init__` (the latter transitively fixes `NimProvider`/`OpenRouterProvider`, which delegate to it), so `call_with_one_retry` (D-28) is the single source of retry policy. Added a regression test (`_FakeOpenAIClient` now records the `max_retries` kwarg it was constructed with) asserting `max_retries == 0` for the Anthropic client and for all three OpenAI-compatible adapters (OpenAI, NIM, OpenRouter), so this can't silently regress. Ran the full test suite after this change per the orchestrator's request — 306/306 passed, no test in `test_providers.py` or elsewhere asserted on the old SDK-default retry behavior.

### WR-01: `_drain_with_stall_timeout`'s background pump thread is never cancelled on stall/retry, leaking a blocked thread per stalled attempt

**Files modified:** `src/gptrpg/agents/master_gm.py`
**Commit:** `1d374eb`
**Applied fix:** Added explicit inline comments at both spots the review flagged as under-documented — the `continue` branch in `narrate()`'s retry loop, and the fallthrough after the loop exits — explaining that a stalled attempt leaves its background pump thread blocked on the stuck network read with no way to cancel it, and that this is currently masked by one-shot CLI process teardown but becomes a real leak in any longer-lived process. This is a documentation-only fix (per the review's "at minimum" fix guidance) — no behavior change, since Python genuinely cannot forcibly interrupt a blocked thread; a structural fix (interruptible I/O primitive or thread tracking/joining) was noted as future work but out of scope for a doc-level fix.

### WR-02: D14 boundary trip-wire test only proves contract:1 (`rules_core`), not contract:3 (`agents`) — the exact boundary this review was asked to verify

**Files modified:** `tests/test_boundaries.py`
**Commit:** `76242c0`
**Applied fix:** Added `test_contract_3_actually_catches_an_agents_violation`, mirroring the existing `rules_core` probe test but targeting `gptrpg.agents`: it writes a temporary `_boundary_probe.py` under `src/gptrpg/agents/` containing `import sqlite3`, asserts `lint_imports(...)` returns `False` while the probe exists, then cleans up the probe file and its `__pycache__` artifacts in a `finally` block. Verified the new test actually catches the injected violation (ran in isolation, confirmed failure, confirmed cleanup left no stray probe file) before running the full suite.

### WR-03: `resolve_provider` is dead code — the real call path duplicates its logic instead of using it

**Files modified:** `src/gptrpg/cli/turn_flow.py`
**Commit:** `dd72949`
**Applied fix:** Replaced both direct `get_provider(choice.provider, os.environ)` call sites in `_turn_flow` (classifier and master_gm role resolution) with calls to `resolve_provider(role, {role: choice}, os.environ)`, removing the now-unused `get_provider` import from `turn_flow.py`. `resolve_provider` is no longer dead code — it is exercised by the real `turn` command path as well as its own unit test. Kept `resolve_provider`'s existing signature (`role, choices, env`) unchanged since it's covered by `tests/test_agent_config.py::test_resolve_provider_raises_missing_api_key_when_env_unset`; did not touch the bare-dict-index `KeyError` behavior the review flagged as a secondary, non-blocking style concern, to keep this fix narrowly scoped to the dead-code issue.

### IN-01: `CLASSIFIER_TIMEOUT_S = 5.0` is tight for the reasoning models this phase explicitly designed around

**Files modified:** `src/gptrpg/agents/invoke.py`
**Commit:** `15ce089`
**Applied fix:** Added an operator-facing note to the `CLASSIFIER_TIMEOUT_S` docstring explaining that NIM/Nemotron-style reasoning models can routinely hit both attempts' timeouts on ambiguous inputs, and that this is indistinguishable on screen from the model genuinely finding no match. Explicitly notes this is not a code defect (the value is a locked D-27 decision) — documentation only, no behavior change.

### IN-02: OpenRouter's `stream_options={"include_usage": True}` support is unverified

**Files modified:** `src/gptrpg/agents/providers/openrouter_provider.py`
**Commit:** `51a00ce`
**Applied fix:** Added a module-docstring note documenting that, unlike `nim_provider.py` (which claims live verification), OpenRouter's support for `stream_options={"include_usage": True}` has not been live-verified, and explaining the specific silent-failure mode (zero token counts landing in `RecordAiCall` under `ok=True`, indistinguishable in shape from the documented `ok=False` zero-token convention). Documentation only — a live smoke test against OpenRouter is out of scope for this fixer (no network access, and the review itself frames this as "worth a live smoke test" rather than a code change).

### IN-03: `_turn_flow`'s "several" tier records a `picked` move even on rejection

**Files modified:** `src/gptrpg/cli/turn_flow.py`
**Commit:** `ae38095`
**Applied fix:** Added a one-line comment at `picked = chosen if chosen is not None else suggestion` cross-referencing the `single`-tier precedent, explaining that `picked` is intentionally filled even on rejection because `ConfirmAction` needs a move/stat value and the actual gating on rejection happens later (`if not confirmed: return 0`), exactly as the review suggested.

## Skipped Issues

None — all findings were fixed.

## Verification

Ran inside the isolated worktree (`/tmp/sv-03-reviewfix-*`, `gsd-reviewfix/03-*` branch, fresh `uv sync`) after all 7 commits:

- `uv run pytest -q` → **307 passed** (up from the 302-test baseline; +5 net: 4 new regression tests for CR-01, 1 new probe test for WR-02)
- `uv run lint-imports` → **Contracts: 3 kept, 0 broken** (all three contracts, including the newly-probed contract:3, confirmed live)
- `uv run ruff check .` → **All checks passed**

These numbers are reproducible from the worktree environment described above; the worktree itself is torn down as part of this agent's cleanup, but the commits are on `docs/m0-closeout`.

---

_Fixed: 2026-08-02T11:02:22Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
