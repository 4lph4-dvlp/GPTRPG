---
phase: 09-agent-architecture
plan: 02
subsystem: ai-agents
tags: [prompt-assembly, asyncio-gather, agent-architecture, tdd-contract-tests]

# Dependency graph
requires:
  - phase: 09-agent-architecture (plan 01)
    provides: clock_judge agent role, ClockJudgeContext pattern, turn/clock_condition.run_clock_condition_check background path, AGENT_ROLES widened to five with ROLE_FALLBACKS
provides:
  - "situation_judge agent role — judge_situation absorbs every judgment/persona instruction build_gm_prompt used to carry, returning SituationJudgment(scene_summary, facts, ai) and never raising (D-05/ARCH-05)"
  - "NarrationFacts value object (agents/context.py) — no clock_state field exists on the type, so narrate() has no path by which scenario text/clock state can reach it (ARCH-02 enforced structurally, not by convention)"
  - "narrate()/build_gm_prompt() narrowed to (facts: NarrationFacts, ...) — TurnContext and check_summary are no longer accepted parameters anywhere in the narration call chain"
  - "turn/judgments.gather_turn_judgments — the single asyncio.gather site (situation_judge + clock_judge signal gate, always listed, no runtime branch) that both web/routes_actions.confirm and cli/turn_flow._turn_flow call (ARCH-04); build_narration_facts and empty_turn_judgments are its companions"
  - "tests/test_narration_isolation.py — regression net asserting build_gm_prompt's system never contains M0_THREAT_CLOCK identity/wants/catastrophe/segments (or any _format_clock_state output line), plus an explicit non-xfail warning test documenting the one residual gap (situation_judge summary carrying scenario text verbatim) that Phase 10's output filter must close"
affects: [09-03-parallel-judgment, phase-10-output-validation]

actuals:
  tokens: 24033
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Judgment/narration split (D-06, ARCH-02): the persona+judgment instructions that used to live in build_gm_prompt's permanent block moved wholesale to build_situation_prompt — narrate() now receives only a narrow, capped value object (NarrationFacts) with no field capable of carrying scenario text"
    - "Content-addressed test-double dispatch: once two roles (situation_judge, clock_judge signal gate) can run concurrently via asyncio.gather against the same shared fake-provider instance, call-order-based dispatch in test doubles becomes racy — doubles now match on the fixed role-instruction substring baked into each build_*_prompt's permanent block (e.g. \"행동 분류기\", \"상황판단 담당\", \"위협 시계 관문 판단자\") instead of a call counter"

key-files:
  created:
    - src/gptrpg/agents/situation_judge.py
    - src/gptrpg/turn/judgments.py
    - tests/test_situation_judge.py
    - tests/test_narration_isolation.py
  modified:
    - src/gptrpg/agents/context.py
    - src/gptrpg/agents/invoke.py
    - src/gptrpg/agents/prompt_assembly.py
    - src/gptrpg/agents/master_gm.py
    - src/gptrpg/web/routes_actions.py
    - src/gptrpg/cli/turn_flow.py
    - tests/conftest.py
    - tests/test_agents_retry.py
    - tests/test_master_gm.py
    - tests/test_measurement.py
    - tests/test_web_actions.py
    - tests/test_turn_flow_failure.py
    - tests/test_turn_tracer.py
    - tests/test_clock_condition_cli.py
    - tests/test_prompt_assembly_scenario.py

key-decisions:
  - "DP-05 confirmed: narration's system carries zero scenario content; the one-two-sentence scene_summary situation_judge produces rides in messages (turn-varying), keeping the two-block cache-stability contract intact"
  - "DP-06 confirmed: narrate()/build_gm_prompt() take facts: NarrationFacts only — no ctx or check_summary parameter exists anywhere in the signature, so TurnContext structurally cannot reach narrate()"
  - "DP-07 confirmed: asyncio.gather introduced now in turn/judgments.py, with 09-01's clock-signal-gate call relocated into it — the web/CLI call sites will not need to touch this wiring again when 09-03 adds a third coroutine"

requirements-completed: [ARCH-02, ARCH-05, ARCH-06]

coverage:
  - id: D1
    description: "The narration system prompt (build_gm_prompt) never contains the scenario's identity/wants/catastrophe sentences or any segment description, even concatenated across both system blocks"
    requirement: ARCH-02
    verification:
      - kind: unit
        ref: "tests/test_narration_isolation.py#test_narration_system_excludes_identity_wants_catastrophe_and_every_segment"
        status: pass
      - kind: unit
        ref: "tests/test_narration_isolation.py#test_narration_system_excludes_every_line_of_format_clock_state_output"
        status: pass
      - kind: unit
        ref: "tests/test_situation_judge.py#test_narration_system_excludes_scenario_identity_wants_catastrophe_and_segments"
        status: pass
    human_judgment: false
  - id: D2
    description: "NarrationFacts has no clock_state field — the type itself, not a convention, prevents scenario/clock data from reaching narrate()"
    requirement: ARCH-02
    verification:
      - kind: unit
        ref: "tests/test_narration_isolation.py#test_narration_facts_has_no_clock_state_field"
        status: pass
      - kind: unit
        ref: "tests/test_situation_judge.py#test_narration_facts_field_names_have_no_clock_state_slot"
        status: pass
    human_judgment: false
  - id: D3
    description: "narrate() receives a structured facts bundle (scene summary + fact list + check result) instead of a single check_summary string"
    requirement: ARCH-02
    verification:
      - kind: unit
        ref: "tests/test_narration_isolation.py#test_narrate_signature_has_no_ctx_or_check_summary"
        status: pass
    human_judgment: false
  - id: D4
    description: "situation_judge failing both attempts still lets narration complete and the turn/confirm request succeed — narration proceeds with an empty fact bundle"
    requirement: ARCH-05
    verification:
      - kind: integration
        ref: "tests/test_web_actions.py#test_situation_judge_both_attempts_fail_narration_still_completes"
        status: pass
      - kind: integration
        ref: "tests/test_turn_flow_failure.py#test_situation_judge_both_attempts_fail_narration_still_completes_and_turn_exits_zero"
        status: pass
      - kind: unit
        ref: "tests/test_situation_judge.py#test_judge_situation_both_attempts_fail_yields_empty_judgment_without_raising"
        status: pass
    human_judgment: false
  - id: D5
    description: "situation_judge and narrate receive distinct value-object types (TurnContext vs. NarrationFacts), each with its own cap enforced in __post_init__"
    requirement: ARCH-06
    verification:
      - kind: unit
        ref: "tests/test_situation_judge.py#test_narration_facts_raises_when_facts_exceed_limit"
        status: pass
      - kind: unit
        ref: "tests/test_situation_judge.py#test_judge_situation_truncates_facts_over_limit_without_raising"
        status: pass
    human_judgment: false
  - id: D6
    description: "One confirm/turn request records exactly one ai_invoked event with agent_role=situation_judge and exactly one with agent_role=clock_judge, on both success and failure paths"
    requirement: null
    verification:
      - kind: integration
        ref: "tests/test_web_actions.py#test_situation_judge_both_attempts_fail_narration_still_completes"
        status: pass
      - kind: integration
        ref: "tests/test_turn_flow_failure.py#test_situation_judge_both_attempts_fail_narration_still_completes_and_turn_exits_zero"
        status: pass
    human_judgment: false

duration: ~45min single session
completed: 2026-08-09
status: complete
---

# Phase 9 Plan 2: Situation Judge / Narration Split Summary

**Split the narrator into a `situation_judge` (reads full scenario + judgment instructions) and a narrowed `narrate()` that receives a typed `NarrationFacts` bundle with no clock/scenario field to leak — regression-locked by a system-string vs. real-scenario-data comparison test.**

## Performance

- **Duration:** ~45 min, single continuous session
- **Started:** 2026-08-09T01:34:12+09:00 (Task 1 commit)
- **Completed:** 2026-08-09T01:49:48+09:00 (Task 3 commit)
- **Tasks:** 3/3
- **Files modified:** 19 (4 new + 15 modified, across the whole plan)

## Accomplishments

- `situation_judge` agent role added (`agents/situation_judge.py`): `judge_situation` absorbs the persona/judgment-instruction text that used to live inside `build_gm_prompt`, follows `clock_judge.py`'s never-raise shape (`call_with_one_retry` + `try_parse_json_array`), and truncates `facts` to `SITUATION_FACTS_LIMIT` itself (the truncation responsibility sits in the judge function, not the value object)
- `NarrationFacts` (`agents/context.py`) declared with exactly six fields (`check_summary`, `scene_summary`, `facts`, `scene_entities`, `character_state`, `recent_turns`) and **no `clock_state` field** — ARCH-02 is enforced by the type, proven by a `dataclasses.fields()` assertion, not by a comment saying "don't use that slot"
- `build_gm_prompt` rewritten to accept only `facts: NarrationFacts`; its `permanent` block is narration-only rules (four sentences), its `session` block (`_narration_session_block_text`) never calls `_format_clock_state`. `build_situation_prompt` (new) absorbed the old judgment-instruction text plus the full scenario session block and a closed JSON output contract (`scene_summary` + `facts`, capped)
- `narrate()`'s signature is now `(*, provider, model, facts: NarrationFacts, rulebook_display_name, stall_timeout_s)` — `ctx`/`check_summary` do not exist as parameters anywhere, so `TurnContext` has no path into narration (proven via `inspect.signature`)
- `turn/judgments.py` (new): `gather_turn_judgments` lists `judge_situation` and `judge_clock_signal` in a single `asyncio.gather` **unconditionally** (ARCH-04 — no runtime branch decides whether to parallelize); relocated 09-01's inline clock-signal-gate call out of both `web/routes_actions.py` and `cli/turn_flow.py` into this one shared function so the judgment can't accidentally run twice
- Both web (`confirm()`) and CLI (`_turn_flow`) now submit `RecordAiCall` for `situation_judge` and `clock_judge` on both success and failure (MEAS-02) — previously the clock-signal gate call wasn't recorded at all
- `tests/test_narration_isolation.py` (new, 8 tests): imports `M0_THREAT_CLOCK`/`THREAT_CAST` directly and asserts the narration `system` string never contains their content (including every individual line `_format_clock_state` would produce), that `NarrationFacts` has no clock-state field, that `narrate`'s signature has no `ctx`/`check_summary`, and one **explicit non-xfail warning test** proving the one residual gap this plan can't structurally close (a situation_judge summary that carries scenario text verbatim still reaches `narrate()`'s `messages` through the legitimate `build_narration_facts` path) — documented as Phase 10's job (T-09-08)

## Task Commits

Each task was committed atomically:

1. **Task 1: 상황판단을 새 자리로 떼어내고 서술이 받을 수 있는 것을 타입으로 좁힌다** - `28b8e58` (feat) — `situation_judge.py`, `NarrationFacts`, `SITUATION_TIMEOUT_S`, `build_situation_prompt`, narrowed `build_gm_prompt`/`narrate`, `tests/test_situation_judge.py`
2. **Task 2: 웹·CLI 두 경로를 새 흐름으로 갈아 끼우고 두 판단을 한 자리에서 병렬로 부른다** - `0bb301f` (feat) — `turn/judgments.py`, rewired `web/routes_actions.py`/`cli/turn_flow.py`, ARCH-05 coverage tests added to `test_web_actions.py`/`test_turn_flow_failure.py`
3. **Task 3: 유출이 다시 열리면 시험이 먼저 깨지게 만든다** - `8ea072c` (test) — `tests/test_narration_isolation.py`, retargeted `tests/test_prompt_assembly_scenario.py`

## Files Created/Modified

- `src/gptrpg/agents/situation_judge.py` - **new**: `SituationJudgment` dataclass, `judge_situation` function
- `src/gptrpg/agents/context.py` - `NarrationFacts`, `SITUATION_FACTS_LIMIT`, `TurnContext` docstring updated (now only `action_classifier`/`situation_judge` use it)
- `src/gptrpg/agents/invoke.py` - `SITUATION_TIMEOUT_S = 15.0`
- `src/gptrpg/agents/prompt_assembly.py` - `build_situation_prompt` (new), `build_gm_prompt` narrowed, `_narration_session_block_text`/`_format_facts` (new helpers)
- `src/gptrpg/agents/master_gm.py` - `narrate()` signature narrowed to `facts: NarrationFacts`; streaming/chunking/stall-retry logic untouched
- `src/gptrpg/turn/judgments.py` - **new**: `TurnJudgments`, `gather_turn_judgments`, `empty_turn_judgments`, `build_narration_facts`
- `src/gptrpg/web/routes_actions.py` - `confirm()` calls `gather_turn_judgments` once before `narrate()`, submits both new `RecordAiCall`s, removed the 09-01 inline clock-signal-gate call
- `src/gptrpg/cli/turn_flow.py` - `_turn_flow` mirrors the web wiring; removed unused `asyncio` import (gather now lives inside `turn/judgments.py`)
- `tests/conftest.py` - `web_client_with_fake_provider` gained a `situation_judge` kwarg
- `tests/test_situation_judge.py` - **new**, 15 tests (NarrationFacts contract, narration/situation system exclusion/inclusion, judge_situation D-05/parsing/truncation)
- `tests/test_narration_isolation.py` - **new**, 8 tests (ARCH-02 regression net + explicit bypass-warning test)
- `tests/test_prompt_assembly_scenario.py` - retargeted from `_session_block_text` to `build_situation_prompt`, cross-references `test_narration_isolation.py`
- `tests/test_web_actions.py`, `tests/test_turn_flow_failure.py` - added an ARCH-05 case each (situation_judge fails both attempts, narration/turn still succeeds)
- `tests/test_master_gm.py`, `tests/test_agents_retry.py`, `tests/test_measurement.py` - `narrate()` call sites updated to `facts=NarrationFacts(...)`; streaming/chunk/stall assertions themselves untouched
- `tests/test_turn_tracer.py`, `tests/test_clock_condition_cli.py` - test-double dispatch switched from call-order to prompt-content matching (see Deviations)

## Decisions Made

See `key-decisions` in frontmatter — DP-05/DP-06/DP-07 all confirmed exactly as `09-02-PLAN.md`'s `<planning_decisions>` specified; none were reversed during execution.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `narrate()` signature change broke call sites outside this plan's `files_modified`**
- **Found during:** Task 1's own `<verify>` command (`uv run pytest tests/test_agents_retry.py`)
- **Issue:** `tests/test_agents_retry.py` and `tests/test_measurement.py` call `narrate(ctx=..., check_summary=...)` and aren't listed in the plan's `files_modified`, but the plan's own Task 1 `<verify>` runs `test_agents_retry.py`
- **Fix:** Updated both files' `narrate()` calls to `facts=NarrationFacts(...)`
- **Files modified:** `tests/test_agents_retry.py`, `tests/test_measurement.py`
- **Committed in:** `28b8e58` (Task 1 commit)

**2. [Rule 3 - Blocking] `_MultiRoleProvider`/`fake_provider.calls`-index test doubles became racy under `asyncio.gather`**
- **Found during:** Task 2's own `<verify>` command (`test_clock_condition_cli.py`) and the full-suite run
- **Issue:** `situation_judge` and `clock_judge`'s signal gate now run concurrently via `asyncio.gather` against the *same* shared fake-provider instance (CLI's `--provider fake --model fake-model` applies one provider object to every role). Test doubles in `tests/test_clock_condition_cli.py` and `tests/test_turn_tracer.py` dispatched/indexed by call order/count, which is a race once two roles call `complete()` from different threads
- **Fix:** Rewrote dispatch to match on the fixed role-instruction substring each `build_*_prompt` bakes into its `permanent` system block (`"행동 분류기"`, `"상황판단 담당"`, `"위협 시계 관문 판단자"`, `"위협 시계 조건 판단자"`, `"서술 담당"`) instead of call position; verified stable across repeated runs
- **Files modified:** `tests/test_clock_condition_cli.py`, `tests/test_turn_tracer.py`
- **Committed in:** `0bb301f` (Task 2 commit)

**3. [Rule 3 - Blocking] `ai_invoked` event-count assertions needed updating**
- **Found during:** full-suite run after Task 2
- **Issue:** `tests/test_turn_flow_failure.py` and `tests/test_turn_tracer.py` had hardcoded `len(ai_events) == 2` (classifier + master_gm) assertions; adding two always-recorded agent calls (situation_judge, clock_judge) made the true count 4
- **Fix:** Updated the counts and their explanatory comments
- **Files modified:** `tests/test_turn_flow_failure.py`, `tests/test_turn_tracer.py`
- **Committed in:** `0bb301f` (Task 2 commit)

**4. [Rule 2 - Missing critical] `conftest.py` needed a `situation_judge` kwarg to write the ARCH-05 coverage the plan's own acceptance criteria require**
- **Found during:** Task 2, writing "situation_judge fails both attempts, narration still completes" tests
- **Issue:** The plan's acceptance criteria explicitly require this case in both `test_web_actions.py` and `test_turn_flow_failure.py`, but the shared `web_client_with_fake_provider` fixture in `conftest.py` (not in this plan's `files_modified`) had no way to inject a role-specific failing double for `situation_judge`
- **Fix:** Added a `situation_judge: FakeProvider | None = None` kwarg mirroring the existing `clock_judge` one
- **Files modified:** `tests/conftest.py`
- **Committed in:** `0bb301f` (Task 2 commit)

---

**Total deviations:** 4 auto-fixed (3 blocking, 1 missing-critical-coverage). All were necessary to get the plan's own `<verify>` commands and acceptance criteria green; none expand scope beyond what Task 1/2's own action items already committed to.

## Issues Encountered

**Acceptance-criteria grep proxy vs. actual codebase documentation density.** Task 2's acceptance criteria specify `grep -rn "judge_clock_signal" src | grep -v "def judge_clock_signal" | wc -l` should equal `2` (one import + one call site, both in `turn/judgments.py`). The actual count is 11, because this codebase's established convention (already true before this plan, e.g. `clock_judge.py`'s own module docstring mentions `judge_clock_signal` by name) is dense cross-referencing docstrings — verified the *same* naive grep against the pre-Task-2 commit (`87fee39`) already totaled 10 across the touched files, so the literal "2" was unattainable independent of this plan's changes. The actual structural property the grep is a proxy for — `judge_clock_signal` is *invoked* (not merely mentioned) from exactly one file — was verified directly: `grep -rn "judge_clock_signal(\|^\s*judge_clock_signal,\|import.*judge_clock_signal" src` shows exactly one import line and one reference-as-callable, both in `turn/judgments.py`. No source or documentation was stripped to force a naive count match.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 09-03 (parallel judgment — scene-entity detection) adds a third coroutine to `turn/judgments.py`'s `asyncio.gather` and a fourth field (`new_entities`) to `NarrationFacts` — both extension points were built anticipating this (see docstrings in `turn/judgments.py`'s `TurnJudgments` and `context.py`'s `NarrationFacts`), so 09-03 should not need to touch `web/routes_actions.py`/`cli/turn_flow.py`'s call sites again
- Phase 10 (output validation/jailbreak defense) inherits a known, explicitly-tested residual gap: a `situation_judge` summary that copies scenario text verbatim still reaches `narrate()`'s `messages` (not `system`) through the legitimate `build_narration_facts` path — `tests/test_narration_isolation.py::test_situation_summary_can_carry_scenario_text_verbatim_into_narration_messages` documents this as the open item Phase 10's output filter must close (T-09-08 in this plan's threat register, disposition `accept`)
- No blockers. `EVENT_SCHEMA_VERSION` and `rules_core/reducer.py` untouched — no schema-migration risk carried forward

---
*Phase: 09-agent-architecture*
*Completed: 2026-08-09*

## Self-Check: PASSED

All claimed files verified present on disk (src/gptrpg/agents/situation_judge.py, src/gptrpg/turn/judgments.py, tests/test_situation_judge.py, tests/test_narration_isolation.py, this SUMMARY.md) and all three task commit hashes (28b8e58, 0bb301f, 8ea072c) verified present in git log.
