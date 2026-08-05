---
phase: 03-ai
fixed_at: 2026-08-02T16:00:18Z
review_path: .planning/phases/03-ai/03-REVIEW-gaps.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 03-ai: Code Review Fix Report (Gap-Closure Re-Review)

**Fixed at:** 2026-08-02T16:00:18Z
**Source review:** .planning/phases/03-ai/03-REVIEW-gaps.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (WR-01, WR-02, IN-01 — `fix_scope: all`)
- Fixed: 3
- Skipped: 0

**Verification environment:** all edits, syntax checks, `uv run pytest -q`, and
`uv run lint-imports` runs described below were executed inside the isolated
git worktree created for this fixer run (`/tmp/sv-03-reviewfix-*`, branch
`gsd-reviewfix/03-*`), not the main checkout. The worktree's commits were
fast-forwarded onto `docs/m0-closeout` as part of this run's cleanup, so the
numbers below are reproducible by re-running the same commands against the
current tip of that branch in the main checkout.

## Fixed Issues

### WR-01: Narration exception handler also swallows unrelated actor/store failures, mislabeling them as AI narration failures

**Files modified:** `src/gptrpg/cli/turn_flow.py`, `tests/test_turn_flow_failure.py`
**Commit:** `bce64ca`
**Applied fix:** Narrowed the `try/except` in `_turn_flow`'s narration section
(step ⑤) so it covers only the AI-facing calls — `narrate()` construction,
the first `next(narration_iter, ...)`, and subsequent `next(narration_iter)`
calls made through a manual `while True` loop (replacing the old `for
sentence in narration_iter:` loop, so each generator-advance can be guarded
independently of the `actor.submit(...)` call that follows it). Every
`await actor.submit(AppendNarration(...))` call (both the first-sentence
submit and the in-loop submit) now sits **outside** any try block in this
function, so an actor/store-layer failure (event-schema bug, `EventStore`
write failure, etc.) propagates as itself instead of being caught by the
`except Exception as exc: narration_error = exc` handler and mislabeled with
the "서사가 끝까지 나오지 못했다" (narration failed) message. Added a
regression test,
`test_actor_submit_failure_during_append_narration_propagates_undisguised`,
which monkeypatches `SessionActor.submit` to raise `CommandRejected` only for
`AppendNarration` commands (while narration itself streams two sentences
normally) and asserts the resulting stderr contains the actor's real error
message and does **not** contain the narration-mislabeled text.

### WR-02: The mandatory closing `RecordAiCall` submission is not covered by the "never let a raw exception escape" handler

**Files modified:** `src/gptrpg/cli/turn_flow.py`, `tests/test_turn_flow_failure.py`
**Commit:** `3d5c6a3`
**Applied fix:** Wrapped the closing, always-submitted `RecordAiCall` call
(step ⑥) in its own `try/except Exception`. On failure it now prints a
distinct, honestly-labeled message ("오류: 진행자 AI 호출 기록 제출이
실패했다 — {exc}") to stderr and returns `1`, instead of letting the
exception propagate unguarded out of `_turn_flow`/`run_turn` and surface as a
raw traceback in the CLI (the exact failure mode G-03-3 was written to
eliminate, one call later in the same function). Deliberately did **not**
fold this into the `narration_error` fallthrough path — it's a distinct
class of failure (record-submission failure vs. narration-stream failure)
and reusing the same message would repeat the WR-01 mislabeling pattern one
call downstream. Added a regression test,
`test_record_ai_call_submission_failure_after_successful_narration_degrades_gracefully`,
which monkeypatches `SessionActor.submit` to raise a plain `RuntimeError`
(deliberately **not** `CommandRejected`, since that type is already caught
generically by `main.py`'s `_cmd_turn` handler and would not have
distinguished pre-fix from post-fix behavior) only for the `master_gm`
`RecordAiCall` submission, after a fully successful two-sentence narration.
Confirmed this test reproduces a raw, unhandled `RuntimeError` escaping the
test (pytest failure) against the pre-fix code, and passes (exit code 1,
clear stderr message, both narration events still recorded) against the
fix.

### IN-01: No test drives a real production delegating adapter end-to-end through `narrate()`

**Files modified:** `tests/test_master_gm.py`
**Commit:** `b5c944d`
**Applied fix:** Added
`test_narrate_through_real_delegating_nim_provider_keeps_emitted_chunk_and_marks_failure`,
which constructs a real `NimProvider(_FAKE_KEY)` (wrapping a real, unmocked
`OpenAIProvider`) with only the `openai.OpenAI` SDK client constructor
monkeypatched to a network-free fake (`_FakeOpenAIClientStreamRaisesAfterOneChunk`,
following the same pattern as `tests/test_providers.py`'s `_no_network`
fixture). The fake's `chat.completions.create(stream=True)` yields one
streaming chunk and then raises `RuntimeError` mid-stream. The test drives
this real two-layer stack through `narrate()` and asserts the already-emitted
sentence is kept (`sentences == ["문이 삐걱거리며 열린다."]`) and that
`provider.last_result().ok is False` afterward — confirming the full
`NimProvider.note_result()` -> `OpenAIProvider.note_result()` ->
`OpenAIProvider._last_result` delegation chain is genuinely wired end to end
through the real classes, not just through the hand-built
`_DelegateShapedStallsForeverProvider`-style test doubles that were the
review's stated blind spot.

## Skipped Issues

None — all findings were fixed.

## Final Verification

Ran after all three commits, inside the isolated worktree:

- `uv run pytest -q` — **324 passed**, 0 failed (up from 322 passing before
  this run; +2 net new tests: 2 added for WR-01/WR-02, 1 added for IN-01,
  and none removed — the WR-02 regression test's temporary pre-fix
  intermediate state, where it failed on purpose to prove the bug, was not
  a separate commit).
- `uv run lint-imports` — **3 contracts kept, 0 broken** (unchanged).

---

_Fixed: 2026-08-02T16:00:18Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
