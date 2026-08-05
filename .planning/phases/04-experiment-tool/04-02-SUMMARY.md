---
phase: 04-experiment-tool
plan: 02
subsystem: measurement
tags: [python, pydantic, sqlite, cli, aggregation, meas-01, meas-03]

# Dependency graph
requires:
  - phase: 01-rules-core
    provides: "GameState reducer (rules_core/reducer.py) with turn_count/failure_count/clock_advances/total_tokens fields"
  - phase: 03-ai
    provides: "AiInvoked event always submitted (even on narration failure), so total_tokens is never silently short"
provides:
  - "build_report(state) — pure GameState -> 13-field aggregate dict, MEAS-01/MEAS-03 numbers"
  - "write_report(state, base_dir) — UTF-8 JSON file, overwrite-not-append"
  - "require_safe_session_id / UnsafeSessionId — session_id -> filename safety gate"
  - "gptrpg report --db --session [--out-dir] CLI subcommand (D-44 query+save in one call)"
affects: [04-01, 04-03, 05-experiment-run, 06-hypothesis-verdict]

# Actuals (#2632)
actuals:
  tokens: 5100
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Co-equal import-linter layers share logic via the nearest common lower layer (session_actor), not by placing it in either co-equal layer"
    - "Write-time safety checks (require_safe_session_id) run before any filesystem side effect, not just at the HTTP boundary"

key-files:
  created:
    - src/gptrpg/session_actor/report.py
    - tests/test_report.py
  modified:
    - src/gptrpg/cli/main.py

key-decisions:
  - "build_report/write_report placed in session_actor/report.py (not cli/ or web/) so both the CLI report subcommand (this plan) and 04-03's SessionActor auto-save hook can import it once .importlinter makes cli/web co-equal layers"
  - "write_report reuses the same generated_at value it prints, rather than calling utc_now_iso() twice, so the printed timestamp and the saved file always agree"
  - "failure_to_clock_ratio computed once as None/float in build_report — no separate 0-vs-None branch logic duplicated in the CLI printer, which only chooses the placeholder string"

patterns-established:
  - "REPORT_FIELD_NAMES frozenset locks the aggregate dict's key set, following rules_core/entities.py's ENTITY_FIELD_NAMES convention — any future field add/remove breaks a test immediately"

requirements-completed: [MEAS-01, MEAS-03]

coverage:
  - id: D1
    description: "build_report(state) turns a GameState into a 13-field dict: event_count/turn_count/check_count/failure_count/clock_segment/clock_advances/failure_to_clock_ratio/narration_count/ai_calls/total_tokens/last_grade/session_id/generated_at, with failure_to_clock_ratio == None (not 0/inf) when clock_advances == 0"
    requirement: "MEAS-01, MEAS-03"
    verification:
      - kind: unit
        ref: "tests/test_report.py#test_build_report_matches_fake_session_log_counts"
        status: pass
      - kind: unit
        ref: "tests/test_report.py#test_build_report_failure_to_clock_ratio_matches_fake_session_log"
        status: pass
      - kind: unit
        ref: "tests/test_report.py#test_failure_to_clock_ratio_is_none_when_clock_never_advanced"
        status: pass
      - kind: unit
        ref: "tests/test_report.py#test_failure_to_clock_ratio_is_zero_when_no_failures_but_clock_advanced"
        status: pass
      - kind: unit
        ref: "tests/test_report.py#test_build_report_keys_match_report_field_names"
        status: pass
    human_judgment: true
    rationale: "Plan's Flagged Assumptions section explicitly requires a human to confirm MEAS-01/MEAS-03's acceptance against .planning/REQUIREMENTS.md and ROADMAP.md Phase 4 success criterion 5 — the auto-edge-classifier could not classify these two requirements from the Korean source text. Tests fully prove the code's numeric correctness; the open question is whether the aggregation's definition (simple prompt+completion token sum, simple cumulative-failure/cumulative-clock ratio) is the right one for Phase 6's kill-criteria input, which only a human can settle."
  - id: D2
    description: "write_report(state, base_dir) writes build_report's dict as UTF-8 JSON (ensure_ascii=False) to {base_dir}/{session_id}.json, overwriting on repeat calls; require_safe_session_id rejects session_id outside [A-Za-z0-9_-]{1,64} before any mkdir/write"
    requirement: "MEAS-01, MEAS-03"
    verification:
      - kind: unit
        ref: "tests/test_report.py#test_write_report_file_is_utf8_and_korean_not_escaped"
        status: pass
      - kind: unit
        ref: "tests/test_report.py#test_write_report_rejects_unsafe_session_id_before_writing_any_file"
        status: pass
      - kind: unit
        ref: "tests/test_report.py#test_require_safe_session_id_rejects_disallowed_characters"
        status: pass
    human_judgment: false
  - id: D3
    description: "gptrpg report --db --session [--out-dir] prints 13 Korean-labeled lines (reusing _cmd_replay's existing label names) including a ratio line and a null-ratio placeholder text, then writes the same aggregate as JSON via write_report — query and auto-save happen in the same invocation (D-44)"
    requirement: "MEAS-01, MEAS-03"
    verification:
      - kind: integration
        ref: "tests/test_report.py#test_cli_report_prints_totals_and_ratio"
        status: pass
      - kind: integration
        ref: "tests/test_report.py#test_cli_report_writes_json_file_with_matching_total_tokens"
        status: pass
      - kind: integration
        ref: "tests/test_report.py#test_cli_report_prints_placeholder_when_clock_never_advanced"
        status: pass
      - kind: integration
        ref: "tests/test_report.py#test_cli_report_rejects_unsafe_session_id"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-08-03
status: complete
---

# Phase 4 Plan 2: 세션 집계 — MEAS-01/MEAS-03 Summary

**`build_report`/`write_report`가 `GameState`에서 열세 칸짜리 UTF-8 JSON 집계를 만들고, `gptrpg report` CLI 하위 명령이 세션 도중에도 조회와 파일 저장을 한 번에 한다.**

## Performance

- **Duration:** ~20min (start time not captured at session start; based on task scope)
- **Completed:** 2026-08-03T00:46:27Z
- **Tasks:** 2
- **Files modified:** 3 (1 new module, 1 new test file, 1 modified CLI file)

## Accomplishments

- `session_actor/report.py`: `build_report(state)` produces the 13-field aggregate dict MEAS-01(실제 토큰·턴 수)와 MEAS-03(실패 대비 시계 진행 비율)이 필요로 하는 숫자를 리듀서에서 그대로 옮겨 담아 만든다. 어떤 필터링도 하지 않는다 — 실패 턴·오류 턴이 전부 세어진다.
- `failure_to_clock_ratio`가 `clock_advances == 0`일 때 `None`(0도 무한대도 아님)으로 나오는 것을 경계값 테스트로 못 박았다.
- `write_report`가 UTF-8 JSON(`ensure_ascii=False`)으로 저장하고, 세션 식별자가 `[A-Za-z0-9_-]{1,64}`를 벗어나면 파일을 쓰기 전에 `UnsafeSessionId`를 던진다(T-04-05).
- `gptrpg report --db --session [--out-dir]` CLI 하위 명령이 `_cmd_replay`와 같은 열 개 라벨 + 비율 줄 + 생성 시각 줄을 찍고, 같은 호출이 집계 파일도 최신으로 갱신한다(D-44).
- 이 모듈이 `session_actor/`에 있으므로 04-01이 `.importlinter`를 `cli | web` co-equal 층으로 바꾼 뒤에도 두 층 모두가 import할 수 있다.

## Task Commits

Each task was committed atomically:

1. **Task 1: 집계 함수 하나 — 조회와 자동 저장이 같은 곳을 지난다** - `08ddfdd` (feat)
2. **Task 2: `gptrpg report` — 운영자가 세션 도중에도 숫자를 본다** - `7b6360f` (feat)

_Note: this is a worktree-isolated parallel agent run — the plan-metadata commit (SUMMARY.md + REQUIREMENTS.md) is made separately by the execute-plan workflow after this file is written; STATE.md/ROADMAP.md are updated centrally by the orchestrator after all wave agents complete._

## Files Created/Modified

- `src/gptrpg/session_actor/report.py` - `build_report`/`write_report`/`require_safe_session_id`/`UnsafeSessionId`/`REPORT_FIELD_NAMES`/`DEFAULT_REPORTS_DIR`/`SAFE_SESSION_ID`
- `tests/test_report.py` - 14 tests: 10 pure-function tests (behavior items 1-8 plus two direct `require_safe_session_id` tests) + 4 CLI integration tests
- `src/gptrpg/cli/main.py` - `_cmd_report`, `report` subparser registration (`--db`/`--session`/`--out-dir`), import of `session_actor.report`

## Decisions Made

- Placed `build_report`/`write_report` in `session_actor/report.py` rather than `cli/` or `web/` — per the plan's explicit layering note, once 04-01 makes `.importlinter` contract 2's `gptrpg.cli | gptrpg.web` a co-equal pair, neither can import the other, so the shared aggregation logic must live in the nearest common lower layer both can reach (`session_actor`).
- `_cmd_report` calls `write_report(state, generated_at=report["generated_at"])` reusing the exact `generated_at` value already printed, rather than letting `write_report` call `utc_now_iso()` a second time — avoids a millisecond-level mismatch between the printed timestamp and the one saved in the JSON file for the same invocation.
- Test file combines both tasks' tests in one `tests/test_report.py` per the plan's `files_modified` list, but the two task commits stage disjoint sections of that file (Task 1's commit has only the 10 pure-function tests; Task 2's commit adds the 4 CLI tests alongside the `cli/main.py` change) to keep per-task commits atomic and independently revertible.

## Deviations from Plan

None - plan executed exactly as written. The plan's own `<action>` text for Task 1 already anticipated the exact field list, exception, and regex; Task 2's action text already specified the exact label reuse and D-44 single-call behavior. No Rule 1-4 auto-fixes were needed.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. Pure Python, no new dependencies.

## Next Phase Readiness

- `build_report`/`write_report` are ready for 04-03's `SessionActor` auto-save hook to import directly (`from gptrpg.session_actor.report import write_report`) — no further design work needed on that side.
- **Flagged for human review (carried from plan's Flagged Assumptions section, not resolved by this plan):** whether MEAS-01's "실제 토큰 소모량" should be prompt+completion tokens summed as-is, or whether cached-prompt-token accounting is needed given the project's 3.7x caching-cost-impact lock decision; and whether MEAS-03's cumulative failure/clock ratio is sufficient or a time-windowed breakdown is needed. Both are explicitly out of this plan's scope per the plan's own text — Phase 5/6 should read `.planning/REQUIREMENTS.md` (MEAS-01/MEAS-03 entries) and confirm before treating these numbers as final kill-criteria inputs.
- This plan ran in parallel with 04-01 (web layer) in a separate worktree, touching disjoint files (`session_actor/report.py`, `cli/main.py`'s `report` subcommand only) — no merge conflict expected with 04-01's `.importlinter`/`web/` changes, though 04-01's planned `web/report.py` reference in RESEARCH.md's project-structure sketch does not exist; this plan's `session_actor/report.py` is the actual, single implementation both `cli` and any future `web` route should import.

---
*Phase: 04-experiment-tool*
*Completed: 2026-08-03*

## Self-Check: PASSED

- FOUND: src/gptrpg/session_actor/report.py
- FOUND: tests/test_report.py
- FOUND: src/gptrpg/cli/main.py (modified)
- FOUND: .planning/phases/04-experiment-tool/04-02-SUMMARY.md
- FOUND commit: 08ddfdd (Task 1)
- FOUND commit: 7b6360f (Task 2)
