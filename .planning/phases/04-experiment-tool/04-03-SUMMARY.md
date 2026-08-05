---
phase: 04-experiment-tool
plan: 03
subsystem: rules-core, session-actor, web
tags: [tdd, reducer, session-actor, auto-advance, meas-03, rig-04, fastapi, typescript]

requires:
  - phase: 01-rules-core
    provides: "GameState reducer / apply_event with six event types, frozen dataclass discipline"
  - phase: 04-01
    provides: "gptrpg.web FastAPI package, GameStateView/PollResponse, session_view.ts renderHeader (co-equal cli|web layer)"
  - phase: 04-02
    provides: "session_actor/report.py build_report/write_report/DEFAULT_REPORTS_DIR/UnsafeSessionId — the shared aggregation module both cli and web can reach"
provides:
  - "GameState.fails_since_clock: int — resets to 0 on any clock_advanced event, independent of the never-resetting failure_count"
  - "SessionActor(clock_id='threat', report_dir=None) auto-advance hook — recursive _process call inside the single-consumer queue, atomic under concurrent submits"
  - "SessionActor._write_report_snapshot() — write_report called after every processed command (D-44), OSError/UnsafeSessionId caught to a one-line stderr warning"
  - "AUTO_ADVANCE_FAILURE_THRESHOLD = 3 (session_actor.actor) — single source of truth imported by web/routes_events.py, never hardcoded"
  - "GameStateView.fails_since_clock / .auto_advance_threshold in the poll response"
  - "renderHeader failure counter line ('실패 카운터 M/3') next to the clock line, no destructive color, no urgency copy"
affects: [04-04, 04-05, 04-06, 05-experiment-run, 06-hypothesis-verdict]

actuals:
  tokens: 7100
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Auto-triggered follow-up commands recurse directly into the single-consumer _process() rather than re-entering the asyncio.Queue, so they stay atomic with the command that triggered them even under concurrent submits from multiple players"
    - "Side-effect hooks (report auto-save) that must never block the source-of-truth write (event append) catch their own exception classes narrowly and degrade to a one-line stderr warning"
    - "A threshold/constant that both a UI display and a backend rule depend on is declared once (session_actor.actor.AUTO_ADVANCE_FAILURE_THRESHOLD) and imported everywhere it's shown, never re-typed as a literal"

key-files:
  created:
    - tests/test_reducer_fails_since_clock.py
    - tests/test_session_actor_auto_advance.py
  modified:
    - src/gptrpg/rules_core/reducer.py
    - src/gptrpg/session_actor/actor.py
    - src/gptrpg/web/routes_events.py
    - frontend/src/session_view.ts
    - tests/test_web_events.py

key-decisions:
  - "clock_id is bound at SessionActor/SessionRegistry construction time (default \"threat\") rather than looked up from the last ClockAdvanced event, because GameState never retains the last clock_id used — matches the plan's stated approach and cli/turn_flow.py's existing \"threat\" convention, avoids a chicken-and-egg lookup for the very first auto-trigger"
  - "_maybe_auto_advance recurses directly into _process() instead of re-queuing AdvanceClock — this keeps the auto-generated clock_advanced event atomic with the triggering check_resolved event inside the single-consumer queue; the recursive call's return value is discarded so submit() always returns the seq of the command the caller actually submitted"
  - "_write_report_snapshot runs unconditionally at the end of _process (both the outer call and any recursive auto-advance call), meaning a clock-advancing command writes the report file twice in a row — harmless since both writes reflect the same already-updated self.state, and simpler than threading a \"skip on recursion\" flag through the hot path"
  - "report_dir defaults to session_actor.report.DEFAULT_REPORTS_DIR (not a locally re-declared constant) — SessionActor already imports write_report from the same module, so importing the default path alongside it avoids a second definition of the same value"

requirements-completed: [RIG-04, MEAS-01, MEAS-03]

coverage:
  - id: D1
    description: "GameState.fails_since_clock increments alongside failure_count on a failing check_resolved (both v2 counts_as_failure and legacy v1 grade-name paths), resets to 0 on any clock_advanced regardless of trigger, and is untouched by the other four event types"
    requirement: RIG-04
    verification:
      - kind: unit
        ref: "tests/test_reducer_fails_since_clock.py (7 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "SessionActor auto-advances the clock exactly once when fails_since_clock reaches AUTO_ADVANCE_FAILURE_THRESHOLD (3), tagged trigger=fail_counter with caused_by_seq pointing at the triggering check, atomically under the single-consumer queue, and never on success checks"
    requirement: RIG-04
    verification:
      - kind: unit
        ref: "tests/test_session_actor_auto_advance.py::test_two_failures_do_not_trigger_clock_advance"
        status: pass
      - kind: unit
        ref: "tests/test_session_actor_auto_advance.py::test_third_failure_triggers_exactly_one_clock_advanced_with_fail_counter_trigger"
        status: pass
      - kind: unit
        ref: "tests/test_session_actor_auto_advance.py::test_submit_returns_the_check_seq_not_the_auto_generated_clock_seq"
        status: pass
      - kind: unit
        ref: "tests/test_session_actor_auto_advance.py::test_after_auto_advance_fails_since_clock_resets_and_can_trigger_again"
        status: pass
      - kind: unit
        ref: "tests/test_session_actor_auto_advance.py::test_success_checks_never_advance_the_clock"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every processed command triggers a report snapshot write (D-44); an unwritable report_dir degrades to a stderr warning and never blocks submit() or event recording"
    requirement: "MEAS-01, MEAS-03"
    verification:
      - kind: unit
        ref: "tests/test_session_actor_auto_advance.py::test_report_snapshot_updates_after_each_submitted_command"
        status: pass
      - kind: unit
        ref: "tests/test_session_actor_auto_advance.py::test_unwritable_report_dir_does_not_block_submit_or_event_recording"
        status: pass
      - kind: manual
        ref: "live smoke: three failing ResolveCheck submits against a real SessionActor + EventStore, read back .gptrpg/reports/{session_id}.json — clock_advances == 1, failure_count == 3"
        status: pass
    human_judgment: false
  - id: D4
    description: "Poll response state carries fails_since_clock and auto_advance_threshold (imported from AUTO_ADVANCE_FAILURE_THRESHOLD, never a re-typed literal); header renders both numbers with no destructive color or urgency copy"
    requirement: RIG-04
    verification:
      - kind: unit
        ref: "tests/test_web_events.py::test_poll_response_state_has_fails_since_clock_matching_failure_count"
        status: pass
      - kind: unit
        ref: "tests/test_web_events.py::test_poll_response_auto_advance_threshold_matches_actor_constant"
        status: pass
      - kind: static
        ref: "grep -c 'DC2626' frontend/src/session_view.ts == 0; grep -rn innerHTML frontend/src/ == 0; npx tsc --noEmit == 0"
        status: pass
    human_judgment: true
    rationale: "The plan's own Flagged Assumptions section requires a human to confirm RIG-04's acceptance directly against .planning/REQUIREMENTS.md and ROADMAP.md Phase 4 success criterion 3 — specifically whether \"실패 3회\" means since-last-clock-advance (this plan's reading) or strictly-consecutive (a success would reset the counter). This plan implemented the since-last-advance reading per its own explicit statement; the alternative reading is a one-line change (reset fails_since_clock on success too) if a human decides otherwise."

duration: ~55min
completed: 2026-08-03
status: complete
---

# Phase 4 Plan 3: 위협 시계 자동 진행 + 실패 카운터 Summary

**`GameState.fails_since_clock`이 판정 실패마다 오르고 시계가 돌 때마다 0으로 돌아가는 새 칸으로 리듀서에 들어갔고, `SessionActor`가 이 값이 3에 닿으면 큐를 다시 타지 않고 스스로 `AdvanceClock(trigger="fail_counter")`를 처리하며, 명령마다 04-02의 집계 파일을 자동 저장하고, 화면 머리띠에 두 숫자가 재촉·경고 없이 나란히 뜬다.**

## Performance

- **Duration:** ~55 min (3 TDD-style tasks: reducer field, actor auto-advance hook, web+frontend surfacing)
- **Completed:** 2026-08-03
- **Tasks:** 3
- **Commits:** 5 (RED/GREEN pairs for Task 1 and Task 2, single feat commit for Task 3 which was not TDD-flagged)
- **Files modified:** 5 source files + 3 test files (2 new, 1 extended)

## Accomplishments

- `GameState.fails_since_clock`: new frozen-dataclass field, distinct from the never-resetting `failure_count`. Docstring pins down why the two must stay separate — one is RIG-04's display counter (resets), the other is MEAS-03's ratio numerator (never resets). The legacy v1 grade-name interpretation path (`_legacy_v1_counts_as_failure`) increments it identically to the v2 `counts_as_failure` signal path — no new branch was introduced.
- `SessionActor.AUTO_ADVANCE_FAILURE_THRESHOLD = 3` and two new constructor args (`clock_id="threat"`, `report_dir=None`), both defaulted so existing callers (`cli/main.py`, `cli/turn_flow.py`, `SessionRegistry.get_or_create`) needed zero changes.
- `_maybe_auto_advance`: recurses directly into `_process()` (not the queue) when a `check_resolved` event pushes `fails_since_clock` to the threshold — this keeps the auto-generated `clock_advanced` event atomic with its trigger even if four players submit concurrently. `submit()` always returns the seq of the command the caller actually sent; the recursive auto-advance seq is discarded.
- `_write_report_snapshot`: calls `session_actor.report.write_report` after every processed command (D-44), catching `OSError`/`UnsafeSessionId` into a one-line stderr warning — a broken report directory never blocks event recording, verified both by a `tmp_path`-as-a-file unit test and a live smoke run.
- `web/routes_events.py`'s `GameStateView` gained `fails_since_clock` and `auto_advance_threshold` (the latter imported from `AUTO_ADVANCE_FAILURE_THRESHOLD`, never re-typed as `3`).
- `frontend/src/session_view.ts`'s `renderHeader` now renders "실패 카운터 M/3" next to "위협 시계 N/6" (8px flex gap, both `.text-heading`, `textContent` only) — no destructive color token, no color change by value, no urgency copy, matching D-10's rejection of pressure devices.

## Task Commits

Each task was committed atomically (RED/GREEN split for the two `tdd="true"` tasks):

1. **Task 1: 초기화되는 실패 카운터를 리듀서에 새 칸으로 만든다**
   - `40e72bc` (test, RED) — `tests/test_reducer_fails_since_clock.py`, confirmed failing via `AttributeError` before the field existed
   - `9420b17` (feat, GREEN) — `src/gptrpg/rules_core/reducer.py`
2. **Task 2: 실패 3회에 액터가 스스로 시계를 돌리고 집계를 남긴다**
   - `c049198` (test, RED) — `tests/test_session_actor_auto_advance.py`, confirmed failing via `ImportError` before `AUTO_ADVANCE_FAILURE_THRESHOLD` existed
   - `799f5d2` (feat, GREEN) — `src/gptrpg/session_actor/actor.py` (+ one test-only bug fix found during GREEN, see Deviations)
3. **Task 3: 두 숫자를 상태 응답과 화면 머리띠에 올린다**
   - `0e6c15a` (feat) — `src/gptrpg/web/routes_events.py`, `frontend/src/session_view.ts`, `tests/test_web_events.py` (not TDD-flagged in the plan, implemented + tested together)

_Note: this is a worktree-isolated parallel agent run — the plan-metadata commit (this SUMMARY.md + REQUIREMENTS.md) is made separately by the execute-plan workflow after this file is written; STATE.md/ROADMAP.md are updated centrally by the orchestrator after all wave agents complete._

## Files Created/Modified

- `src/gptrpg/rules_core/reducer.py` - `GameState.fails_since_clock` field, `check_resolved`/`clock_advanced` branches updated
- `src/gptrpg/session_actor/actor.py` - `AUTO_ADVANCE_FAILURE_THRESHOLD`, `SessionActor(clock_id=, report_dir=)`, `_maybe_auto_advance`, `_write_report_snapshot`, `SessionRegistry` threads the same two args
- `src/gptrpg/web/routes_events.py` - `GameStateView.fails_since_clock`/`.auto_advance_threshold`, import of `AUTO_ADVANCE_FAILURE_THRESHOLD`
- `frontend/src/session_view.ts` - `GameStateView` TS interface widened, `renderHeader` renders the failure counter line
- `tests/test_reducer_fails_since_clock.py` - 7 tests covering all `<behavior>` items
- `tests/test_session_actor_auto_advance.py` - 9 tests (7 behavior items + threshold constant + regression-safe rejected-command check)
- `tests/test_web_events.py` - 2 new tests appended to the 04-01 file

## TDD Gate Compliance

Both `tdd="true"` tasks followed the RED→GREEN gate correctly:
- Task 1: `40e72bc` (test, confirmed failing via `AttributeError`) → `9420b17` (feat, all green)
- Task 2: `c049198` (test, confirmed failing via `ImportError`) → `799f5d2` (feat, all green)

No REFACTOR commit was needed for either — the implementation matched the plan's `<action>` text closely enough that no separate cleanup pass was warranted.

## Decisions Made

See `key-decisions` in frontmatter. Summary: `clock_id` bound at construction time (no chicken-and-egg lookup), auto-advance recurses directly into `_process()` for atomicity under the single-consumer queue (not re-queued), report snapshot writes unconditionally on every `_process()` call including the recursive one (double-write on advance is harmless), `report_dir` default sourced from `session_actor.report.DEFAULT_REPORTS_DIR` rather than re-declared.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test read events after closing the store**
- **Found during:** Task 2 GREEN verification (`uv run pytest tests/test_session_actor_auto_advance.py`)
- **Issue:** `test_after_auto_advance_fails_since_clock_resets_and_can_trigger_again` called `store.read_events("s1")` after the `finally` block had already called `store.close()`, raising `RuntimeError: EventStore.initialize()를 먼저 불러야 한다`. This was a bug in the test I wrote for this plan, not in the implementation.
- **Fix:** Moved the `store.read_events("s1")` call inside the `try` block, before `finally` closes the store.
- **Files modified:** `tests/test_session_actor_auto_advance.py`
- **Committed in:** `799f5d2` (bundled with the GREEN implementation commit since both touch the same test file in the same task)

### Environment Setup (not a deviation, but worth recording)

`frontend/node_modules/` was absent in this fresh worktree checkout (gitignored, not shared across worktrees). Ran `npm install` before `npx tsc --noEmit` could resolve the local `typescript` package — without it, `npx` silently substitutes an unrelated placeholder `tsc` package from the registry and reports a misleading error banner instead of type-checking. No code or config change was needed; this is purely a per-worktree setup step already covered by 04-01's environment availability notes.

---

**Total deviations:** 1 auto-fixed (Rule 1, test-only bug found during GREEN), no scope creep, no architectural changes.

## Issues Encountered

- `npx tsc --noEmit` in a freshly created worktree resolves to npm's unrelated placeholder `tsc@2.0.4` package if `frontend/node_modules/` doesn't exist yet — `npm install` must run first in each new worktree before this verification command means what it looks like it means. Worth a note for 04-04's sibling worktree if it also runs `tsc --noEmit`.

## User Setup Required

None - no external service configuration required. All changes are pure Python/TypeScript with defaulted constructor arguments; no new dependencies, no new environment variables.

## Next Phase Readiness

- RIG-04's core mechanism (auto-advancing threat clock + display counter) is proven end-to-end: reducer field → actor hook → web response → frontend render, all covered by automated tests plus one live smoke run.
- **Flagged for human review (carried from the plan's own Flagged Assumptions section, not resolved by this plan):** whether "실패 3회" means since-last-clock-advance (this plan's implementation) or strictly-consecutive-with-success-resetting-the-counter — a human needs to confirm against `.planning/REQUIREMENTS.md` and `ROADMAP.md` Phase 4 success criterion 3 before the first real experiment session runs, per the plan's own reversibility note (`costly`, not `one-way`, but the event record is append-only so a wrong auto-advance rule leaves permanent `clock_advanced` events in any session played before the correction).
- No clock segment upper bound exists yet (also flagged by the plan as unresolved) — `clock_segment` can climb past a scenario's declared segment count with no code-level stop. Scenario data doesn't exist until EXP-01/M1, so this remains open by design.
- 04-05's narrator-agent call (which will consume `TurnContext.clock_state`) can now read `fails_since_clock` alongside `clock_segment` if a future plan wants the narration to know "how close" the clock is to auto-advancing — not used in this plan, no new coupling introduced.

---
*Phase: 04-experiment-tool*
*Completed: 2026-08-03*

## Self-Check: PASSED

All 8 files found on disk (5 modified source files, 2 new test files, this SUMMARY.md).
All 5 commit hashes (`40e72bc`, `9420b17`, `c049198`, `799f5d2`, `0e6c15a`) found in `git log`.
