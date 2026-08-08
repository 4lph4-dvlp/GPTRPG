---
phase: 09-agent-architecture
plan: 01
subsystem: ai-agents
tags: [asyncio, background-task, fastapi-backgroundtasks, cli, event-sourcing, tdd-contract-tests]

# Dependency graph
requires:
  - phase: 08-trust-identity
    provides: SessionActor single-writer discipline, cookie identity, .importlinter layering contracts
provides:
  - "clock_judge agent role (judge_clock_signal gate + judge_clock_condition deep verdict) with a never-raise failure contract"
  - "ClockJudgeContext value object with its own recent-turns cap (ARCH-06's first slice)"
  - "turn/clock_condition.run_clock_condition_check — the single function web (BackgroundTasks) and CLI (explicit await) both call to submit AdvanceClock(trigger=\"condition\")"
  - "AGENT_ROLES widened to five with STRICT_AGENT_ROLES/ROLE_FALLBACKS so existing two-role agents.json files keep loading"
  - "Full quiet-failure contract test suite locking D-05/ARCH-05 at the function, web-route, and CLI layers"
affects: [09-02-situation-judge, 09-03-parallel-judgment, 09-04, phase-15-clock-confirmation-screen]

actuals:
  tokens: 22194
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Gatekeeper + deep-judgment split (DP-01): a cheap in-turn signal check gates an out-of-band deep verdict, keeping AI latency off the critical path while still doing real judgment in the background"
    - "Web/CLI background-task asymmetry documented in code and tests: FastAPI BackgroundTasks (post-response) on the web route vs. explicit `await` before actor.stop() on the CLI path — same shared function, different scheduling because asyncio.run() closes the loop on process exit"
    - "STRICT_AGENT_ROLES/ROLE_FALLBACKS: new agent roles can be declared without breaking existing config files — missing strict roles still raise loudly, missing fallback-eligible roles silently inherit another role's choice with a one-line stderr notice"

key-files:
  created:
    - src/gptrpg/agents/clock_judge.py
    - src/gptrpg/agents/json_parsing.py
    - src/gptrpg/turn/clock_condition.py
    - tests/test_clock_judge.py
    - tests/test_clock_condition_web.py
    - tests/test_clock_condition_cli.py
  modified:
    - src/gptrpg/agents/action_classifier.py
    - src/gptrpg/agents/context.py
    - src/gptrpg/agents/invoke.py
    - src/gptrpg/agents/config.py
    - src/gptrpg/agents/prompt_assembly.py
    - src/gptrpg/web/routes_actions.py
    - src/gptrpg/cli/turn_flow.py
    - src/gptrpg/cli/main.py
    - tests/conftest.py
    - tests/test_agent_config.py

key-decisions:
  - "DP-01: gatekeeper structure — judge_clock_signal is a cheap in-turn gate; judge_clock_condition (the real verdict + event submission) always runs in the background, never on the critical path"
  - "DP-02: background auto-advance, no human confirmation screen — CLOCK-02's confirm UI is Phase 15's job; this plan only had to prove the background execution slot works"
  - "DP-03: AGENT_ROLES widened to five in one shot (action_classifier, master_gm, situation_judge, scene_entity_judge, clock_judge) with a ROLE_FALLBACKS table so later 09-0x plans don't have to touch this file again"
  - "DP-04 confirmed: existing ClockAdvanced(trigger=\"condition\") event fully covers this feature — EVENT_SCHEMA_VERSION stays at 5 and rules_core/reducer.py has zero new branches"
  - "D14 enforced structurally: clock_judge.py never returns or computes a segment number — only turn/clock_condition.py computes next_segment as actor.state.clock_segment + 1 and enforces the CLOCK_SEGMENT_COUNT cap"

patterns-established:
  - "Any future agent role that needs a closed-list AI verdict (not free narration) should follow clock_judge.py's shape: frozen dataclass result + call_with_one_retry + try_parse_json_array, falling to a safe/false value on any parse or provider failure rather than raising"

requirements-completed: [ARCH-03, ARCH-05, ARCH-06]

coverage:
  - id: D1
    description: "clock_advanced(trigger=\"condition\") event fires automatically from AI judgment on both the web and CLI turn paths, and replays correctly (ARCH-03)"
    requirement: ARCH-03
    verification:
      - kind: integration
        ref: "tests/test_clock_condition_web.py#test_confirm_advances_clock_via_condition_trigger_and_replays"
        status: pass
      - kind: integration
        ref: "tests/test_clock_condition_web.py#test_replayed_clock_segment_is_one_after_condition_advance"
        status: pass
      - kind: integration
        ref: "tests/test_clock_condition_cli.py#test_cli_turn_advances_clock_via_condition_trigger_after_process_exits"
        status: pass
    human_judgment: false
  - id: D2
    description: "Judgment failure/timeout never blocks the turn and never leaks into the player-facing screen or HTTP body — only a stderr line (ARCH-05, D-05)"
    requirement: ARCH-05
    verification:
      - kind: unit
        ref: "tests/test_clock_judge.py#test_judge_clock_signal_both_attempts_fail_yields_false_signal_without_raising"
        status: pass
      - kind: unit
        ref: "tests/test_clock_judge.py#test_judge_clock_condition_both_attempts_fail_yields_false_verdict_without_raising"
        status: pass
      - kind: integration
        ref: "tests/test_clock_condition_web.py#test_clock_judge_always_raising_still_returns_200_and_records_no_clock_event"
        status: pass
      - kind: integration
        ref: "tests/test_clock_condition_web.py#test_deep_judgment_raising_still_returns_200_and_records_no_clock_event"
        status: pass
      - kind: integration
        ref: "tests/test_clock_condition_cli.py#test_clock_judge_always_raising_still_exits_zero_with_narration_recorded"
        status: pass
      - kind: integration
        ref: "tests/test_clock_condition_cli.py#test_clock_judge_failure_notice_only_on_stderr_never_stdout"
        status: pass
    human_judgment: false
  - id: D3
    description: "ClockJudgeContext value object with its own recent-turns cap (ARCH-06's first agent-context slice)"
    requirement: ARCH-06
    verification:
      - kind: unit
        ref: "tests/test_clock_judge.py (uses ClockJudgeContext fixture across all 11 tests, exercising the value object's shape)"
        status: pass
    human_judgment: false
  - id: D4
    description: "D14 enforced: no AI-returned number ever reaches segment_index — code always computes clock_segment + 1 and caps at CLOCK_SEGMENT_COUNT"
    verification:
      - kind: integration
        ref: "tests/test_clock_condition_web.py#test_condition_advance_segment_index_ignores_any_number_embedded_in_why"
        status: pass
      - kind: integration
        ref: "tests/test_clock_condition_web.py#test_clock_at_last_segment_condition_met_still_adds_no_event"
        status: pass
    human_judgment: false
  - id: D5
    description: "Existing two-role agents.json config files keep loading unchanged after AGENT_ROLES widened to five, with fallback roles borrowing choices and logging the borrow to stderr"
    verification:
      - kind: unit
        ref: "tests/test_agent_config.py (regression test added in Task 2 — two-role file loads to five roles with three stderr fallback lines)"
        status: pass
    human_judgment: false

duration: ~3h active work across two sessions (interrupted mid-Task-3 by an API error, resumed to finish)
completed: 2026-08-09
status: complete
---

# Phase 9 Plan 1: Threat-Clock Condition Background Judgment Summary

**Threat-clock advances via AI "story condition" judgment on both web and CLI turn paths, running in a shared background function with a never-raise quiet-failure contract (ARCH-03/ARCH-05/ARCH-06's first slice).**

## Performance

- **Duration:** ~3h active work, split across two sessions (an earlier run was cut off mid-Task-3 by an API error; this session resumed and finished it)
- **Started:** 2026-08-07T03:51:07+09:00 (Task 1 commit)
- **Completed:** 2026-08-09T01:22:23+09:00 (Task 3 commit)
- **Tasks:** 3/3
- **Files modified:** 19 (11 source + 8 test files, across the whole plan)

## Accomplishments

- `clock_judge` agent role added: a cheap in-turn gate (`judge_clock_signal`) plus a background deep verdict (`judge_clock_condition`), both following `action_classifier.py`'s closed-result/retry/robust-JSON-parse shape and never raising on failure
- `turn/clock_condition.run_clock_condition_check` is the single function both the web route (`FastAPI BackgroundTasks`, post-response) and the CLI (`await` before `actor.stop()`) call to submit `AdvanceClock(trigger="condition")` — the CLI/web asymmetry (no `BackgroundTasks` equivalent once `asyncio.run()` returns) is documented in code comments and in the CLI test's docstring
- `AGENT_ROLES` widened from two to five (`action_classifier`, `master_gm`, `situation_judge`, `scene_entity_judge`, `clock_judge`) with `STRICT_AGENT_ROLES`/`ROLE_FALLBACKS` so existing two-role `agents.json` files keep loading unchanged, borrowing fallback choices with a one-line stderr notice
- `ClockJudgeContext` value object declared with its own narrower `CLOCK_JUDGE_RECENT_TURNS_LIMIT=4` cap and no scenario-identity fields (identity/wants/doom sentence are structurally excluded) — ARCH-06's first concrete slice
- D14 enforced structurally: no AI-returned number ever becomes a segment index — `run_clock_condition_check` always computes `actor.state.clock_segment + 1` and caps at `CLOCK_SEGMENT_COUNT`, proven by a test that embeds a decoy number ("999") in the AI's `why` field and asserts it never appears in the recorded event
- Full quiet-failure (D-05/ARCH-05) contract locked with tests at three layers: the judge functions themselves (`tests/test_clock_judge.py`, 11 tests), the web route (`tests/test_clock_condition_web.py`, 9 tests total after Task 3's 5 additions), and the CLI path (`tests/test_clock_condition_cli.py`, 5 tests total after Task 3's 3 additions) — including a `capsys`-verified guarantee that the failure notice appears only on stderr, never stdout

## Task Commits

Each task was committed atomically:

1. **Task 1: 웹에서 한 턴이 「이야기 조건」으로 시계를 한 칸 돌린다 — 한 줄기 끝까지** - `90239f8` (feat) — thin end-to-end slice: clock_judge agent, ClockJudgeContext, five-role config with fallbacks, turn/clock_condition.py, web route wiring, first integration test file
2. **Task 2: 같은 배경 검사를 CLI에서도 돌린다** - `87fee39` (feat) — CLI turn_flow wiring with explicit `await` before `actor.stop()`, `agents set` fallback-aware messaging, agent-config test suite expanded to five roles
3. **Task 3: 판단이 늦거나 죽어도 턴은 끝까지 간다** - `d2d8ea1` (test) — full quiet-failure contract test suite at all three layers; no source changes needed, every assertion already passed against Task 1/2's implementation

_Note: Task 3 was test-only per the plan's own instruction ("이 태스크는 시험만 추가하고 소스는 고치지 않는다") — and indeed no source fix was required._

## Files Created/Modified

- `src/gptrpg/agents/clock_judge.py` - `ClockSignal`/`ClockConditionVerdict` dataclasses, `judge_clock_signal`/`judge_clock_condition` functions
- `src/gptrpg/agents/json_parsing.py` - `try_parse_json_array` promoted from `action_classifier.py` as a shared leaf util
- `src/gptrpg/agents/context.py` - `ClockJudgeContext`, `CLOCK_JUDGE_RECENT_TURNS_LIMIT`, `ContextCapExceeded`
- `src/gptrpg/agents/invoke.py` - `CLOCK_JUDGE_TIMEOUT_S = 5.0`
- `src/gptrpg/agents/config.py` - `AGENT_ROLES` (5), `STRICT_AGENT_ROLES`, `ROLE_FALLBACKS`, `load_config` fallback logic with stderr notice
- `src/gptrpg/agents/prompt_assembly.py` - `build_clock_signal_prompt`, `build_clock_condition_prompt`
- `src/gptrpg/agents/action_classifier.py` - delegates to `json_parsing.try_parse_json_array`, keeps `_try_parse_json_array` alias
- `src/gptrpg/turn/clock_condition.py` - `build_clock_judge_context`, `run_clock_condition_check` (shared web/CLI background entrypoint)
- `src/gptrpg/web/routes_actions.py` - `confirm()` runs the signal gate before `narrate()`, registers the background check after narration succeeds
- `src/gptrpg/cli/turn_flow.py` - `_turn_flow` runs the signal gate via `asyncio.to_thread`, then `await run_clock_condition_check(...)` before returning
- `src/gptrpg/cli/main.py` - `_cmd_agents_set` distinguishes strict-missing vs. fallback-missing roles in its guidance text
- `tests/conftest.py` - `web_client_with_fake_provider`/`_resolver` handle unregistered roles gracefully, `clock_judge` kwarg added
- `tests/test_agent_config.py` - five-role assertions, `STRICT_AGENT_ROLES`/`ROLE_FALLBACKS` coverage, two-role-file regression test
- `tests/test_clock_judge.py` - **new**, 11 tests, function-layer D-05 contract
- `tests/test_clock_condition_web.py` - **new** in Task 1 (4 tests), extended in Task 3 (+5 tests) for the D-05 route-layer contract
- `tests/test_clock_condition_cli.py` - **new** in Task 2 (2 tests), extended in Task 3 (+3 tests) for the D-05 CLI-layer contract

## Decisions Made

See `key-decisions` in frontmatter (DP-01 through DP-04, all confirmed as specified in `09-01-PLAN.md`'s `<planning_decisions>` — none were reversed during execution).

## Deviations from Plan

None for Task 3 — the plan explicitly scoped Task 3 as test-only ("이 태스크는 시험만 추가하고 소스는 고치지 않는다. 시험이 실패하면 그때 Task 1/2의 소스를 고친다"), and all 11+5+3 = 19 new/extended Task 3 assertions passed against the existing Task 1/2 implementation with zero source changes.

Task 1/2 deviations (documented in their own commit messages, carried forward here for completeness):
- **[Rule 1 - Bug] Task 2:** `test_turn_tracer.py`'s two byte-identical-prompt/speaker-prefix tests indexed `fake_provider.calls` positionally, assuming exactly two `complete()` calls per turn — adding the `clock_judge` signal-gate call broke that assumption. Fixed the index expressions to account for the third call. Committed as part of `87fee39`.

## Issues Encountered

**Interrupted execution recovery:** An earlier executor run on this plan was cut off mid-Task-3 by an API error, after Task 3 items ① (`tests/test_clock_judge.py`) and ② (`tests/test_clock_condition_web.py` extension) were already written and verified passing but left uncommitted, and before item ③ (`tests/test_clock_condition_cli.py` extension) was started. This session verified the prior state via the full test suite and `git status`, wrote the missing item ③ (3 new tests: always-raising judge still exits 0 with narration intact, failure notice confined to stderr via `capsys`, skip signal never triggers the deep-judgment provider call), then committed all three items as the single atomic Task 3 commit the plan specified.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The background-execution slot (D-01/D-64's structural promise) is now proven end-to-end on both web and CLI, with a locked quiet-failure contract — 09-02 (situation-judge/narration split) and 09-03 (two parallel judgment pieces) build directly on this pattern
- `AGENT_ROLES` already declares `situation_judge` and `scene_entity_judge` (implementation deferred to 09-02/09-03 per DP-03) with fallback entries already wired, so those plans don't need to touch `agents/config.py`'s role list again
- No blockers. `EVENT_SCHEMA_VERSION` remains 5 and `rules_core/reducer.py` untouched (DP-04) — no schema-migration risk carried forward

---
*Phase: 09-agent-architecture*
*Completed: 2026-08-09*

## Self-Check: PASSED

All claimed files verified present on disk (src/gptrpg/agents/clock_judge.py, src/gptrpg/agents/json_parsing.py, src/gptrpg/turn/clock_condition.py, tests/test_clock_judge.py, tests/test_clock_condition_web.py, tests/test_clock_condition_cli.py, this SUMMARY.md) and all three task commit hashes (90239f8, 87fee39, d2d8ea1) verified present in git log.
