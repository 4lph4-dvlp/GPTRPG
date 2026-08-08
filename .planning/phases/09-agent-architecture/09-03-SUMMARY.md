---
phase: 09-agent-architecture
plan: 03
subsystem: ai-agents
tags: [asyncio-gather, ast-regression-test, agent-architecture, prompt-assembly]

# Dependency graph
requires:
  - phase: 09-agent-architecture (plan 01)
    provides: clock_judge agent role, ClockJudgeContext pattern, never-raise D-05 failure contract
  - phase: 09-agent-architecture (plan 02)
    provides: situation_judge agent role, NarrationFacts value object, turn/judgments.gather_turn_judgments (two-coroutine gather), RECORD_AI_CALL wiring pattern in web/routes_actions.py and cli/turn_flow.py
provides:
  - "scene_entity_judge agent role — judge_new_entity(provider, model, ctx: EntityJudgeContext, rulebook_display_name) -> EntityJudgment, following clock_judge.py's never-raise shape"
  - "EntityJudgeContext value object (agents/context.py) — three fields only (scene_entities, recent_turns, check_summary), own ENTITY_JUDGE_RECENT_TURNS_LIMIT=4 cap (ARCH-06's third slice)"
  - "NarrationFacts.new_entities: tuple[str, ...] — D-03 (a)'s result reaches the narration prompt's turn-varying messages block before narrate() is called"
  - "turn/judgments.gather_turn_judgments's single asyncio.gather now lists three coroutines (judge_situation, judge_new_entity, judge_clock_signal) unconditionally — ARCH-04 locked by an ast-based regression test, not just a docstring promise"
  - "tests/test_parallel_judgment.py — three-layer ARCH-04 net (behavior/syntax/timing-overlap)"
  - "tests/test_agent_context_caps.py — ARCH-06 net across all four value objects (TurnContext/ClockJudgeContext/EntityJudgeContext/NarrationFacts), including a session-length-independence proof and a direct re-assertion of the agents/event_log import boundary"
affects: [09-04-decisions-and-pipeline-docs, phase-10-output-validation, phase-11-scene-entity-management, phase-12-character-state]

actuals:
  tokens: 20447
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "ast-based structural regression test: gather_turn_judgments's freedom from conditional branching is locked by parsing its own source with `ast` and asserting no ast.If/IfExp exists in the function body, plus asserting the single asyncio.gather call has exactly three positional args that are each asyncio.to_thread calls — this cannot be defeated by rewording a comment, only by actually changing the code shape"
    - "role-instruction-substring dispatch in single-fake-provider CLI test doubles (established 09-02, extended here): when one FakeProvider instance serves every role (--provider fake --model fake-model), the dispatch key is the fixed permanent-block instruction text baked into each build_*_prompt, not call order or count — safe under asyncio.gather's concurrent complete() calls from different threads"

key-files:
  created:
    - src/gptrpg/agents/scene_entity_judge.py
    - tests/test_scene_entity_judge.py
    - tests/test_parallel_judgment.py
    - tests/test_agent_context_caps.py
  modified:
    - src/gptrpg/agents/context.py
    - src/gptrpg/agents/invoke.py
    - src/gptrpg/agents/prompt_assembly.py
    - src/gptrpg/turn/judgments.py
    - src/gptrpg/web/routes_actions.py
    - src/gptrpg/cli/turn_flow.py
    - tests/conftest.py
    - tests/test_web_actions.py
    - tests/test_turn_flow_failure.py
    - tests/test_clock_condition_cli.py
    - tests/test_narration_isolation.py
    - tests/test_situation_judge.py
    - tests/test_turn_tracer.py
    - tests/test_agents_retry.py
    - tests/test_master_gm.py
    - tests/test_measurement.py

key-decisions:
  - "DP-08 confirmed: each of the three parallel judgments is its own independent LLM call — no single call returning multiple JSON fields. scene_entity_judge follows the same call-shape as situation_judge/clock_judge."
  - "DP-09 confirmed: scene_entity_judge's result is consumed only as a fact fed to narration (NarrationFacts.new_entities, a tuple of display-name strings) — never written to an event or pushed into an Entity list. Relationship-impact judgment stays deferred to Phase 14 (no dead code added for it)."
  - "D-03/D-04 confirmed: the (a) slice (new scene entities) resolves before narrate() is called and its result reaches the narration prompt's messages block; the (b) slice (threat-clock signal, built in 09-01/09-02) still resolves after narration via the background path."

requirements-completed: [ARCH-04, ARCH-05, ARCH-06]

coverage:
  - id: D1
    description: "The three post-check judgments (situation, scene-entity, clock-signal) always run inside a single asyncio.gather with no runtime branch deciding what to parallelize — proven at behavior, syntax (ast), and timing-overlap layers"
    requirement: ARCH-04
    verification:
      - kind: unit
        ref: "tests/test_parallel_judgment.py#test_each_judgment_called_exactly_once_for_ordinary_success_check"
        status: pass
      - kind: unit
        ref: "tests/test_parallel_judgment.py#test_gather_turn_judgments_body_has_no_if_or_ternary"
        status: pass
      - kind: unit
        ref: "tests/test_parallel_judgment.py#test_gather_turn_judgments_has_exactly_one_gather_call_with_three_positional_args"
        status: pass
      - kind: unit
        ref: "tests/test_parallel_judgment.py#test_three_judgments_actually_overlap_in_time"
        status: pass
    human_judgment: false
  - id: D2
    description: "scene_entity_judge failing both attempts (D-05/ARCH-05) does not block the turn — narration completes with entities=(), the other two judgments' results still apply, on both web and CLI paths"
    requirement: ARCH-05
    verification:
      - kind: integration
        ref: "tests/test_web_actions.py#test_scene_entity_judge_both_attempts_fail_narration_still_completes"
        status: pass
      - kind: integration
        ref: "tests/test_turn_flow_failure.py#test_scene_entity_judge_both_attempts_fail_narration_still_completes_and_turn_exits_zero"
        status: pass
      - kind: unit
        ref: "tests/test_scene_entity_judge.py#test_judge_new_entity_both_attempts_fail_yields_empty_judgment_without_raising"
        status: pass
    human_judgment: false
  - id: D3
    description: "EntityJudgeContext declares exactly three fields (no clock/character-state slot) with its own ENTITY_JUDGE_RECENT_TURNS_LIMIT cap; all four agent-context value objects each get only their own slice and none grow with session length"
    requirement: ARCH-06
    verification:
      - kind: unit
        ref: "tests/test_agent_context_caps.py#test_entity_judge_context_has_no_clock_state_or_character_state_field"
        status: pass
      - kind: unit
        ref: "tests/test_agent_context_caps.py#test_derived_context_recent_turns_do_not_grow_when_event_count_doubles"
        status: pass
      - kind: unit
        ref: "tests/test_agent_context_caps.py#test_no_module_under_agents_imports_event_log_or_session_actor"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-03 (a): scene_entity_judge's result reaches NarrationFacts.new_entities before narrate() is called, and the narration prompt's turn message includes the new names when present (absent when empty — no placeholder leaks into every turn)"
    verification:
      - kind: unit
        ref: "tests/test_situation_judge.py#test_new_entities_names_appear_in_narration_messages_when_present"
        status: pass
      - kind: unit
        ref: "tests/test_situation_judge.py#test_new_entities_line_absent_when_empty_messages_shorter_than_when_present"
        status: pass
    human_judgment: false
  - id: D5
    description: "One confirm/turn request records exactly one ai_invoked event per parallel-judgment role (situation_judge, scene_entity_judge, clock_judge), on both web and CLI paths"
    verification:
      - kind: integration
        ref: "tests/test_web_actions.py#test_confirm_records_exactly_one_ai_invoked_per_parallel_judgment_role"
        status: pass
      - kind: integration
        ref: "tests/test_turn_flow_failure.py#test_turn_records_exactly_one_ai_invoked_per_parallel_judgment_role"
        status: pass
    human_judgment: false

duration: ~12min active work, single session
completed: 2026-08-09
status: complete
---

# Phase 9 Plan 3: Parallel Judgment — Scene Entity Detection Summary

**Added `scene_entity_judge` as the third coroutine in `turn/judgments.gather_turn_judgments`'s single `asyncio.gather`, and locked ARCH-04's "no runtime branch decides what to parallelize" claim with an `ast`-based structural regression test rather than just a docstring promise.**

## Performance

- **Duration:** ~12 min active work, single continuous session
- **Started:** 2026-08-09T01:58:27+09:00 (Task 1 commit)
- **Completed:** 2026-08-09T02:09:53+09:00 (final coverage commit)
- **Tasks:** 3/3
- **Files modified:** 20 (4 new + 16 modified, across the whole plan)

## Accomplishments

- `scene_entity_judge` agent role added (`agents/scene_entity_judge.py`): `judge_new_entity` returns `EntityJudgment(entities: tuple[NewEntity, ...], ai: AgentResult)`, follows `clock_judge.py`'s shape (`call_with_one_retry` + `try_parse_json_array`, never raises), drops names already present in `ctx.scene_entities`, truncates to `NEW_ENTITY_LIMIT=3`, and skips malformed elements (missing `name`, `kind` outside the two-value closed list) instead of raising — no `UnknownMove` analog exists because `name` is model-authored free text with no rulebook list to check against
- `EntityJudgeContext` (`agents/context.py`) declared with exactly three fields (`scene_entities`, `recent_turns`, `check_summary`) — no clock-state or character-state slot, own `ENTITY_JUDGE_RECENT_TURNS_LIMIT=4` cap (narrower than `RECENT_TURNS_LIMIT=10`, same reasoning as `ClockJudgeContext`)
- `NarrationFacts` gained `new_entities: tuple[str, ...]` (no default — every call site must decide explicitly), capped by new `NEW_ENTITY_LIMIT=3`; `build_gm_prompt`'s turn message appends a one-line "new entities in this scene" instruction only when the tuple is non-empty (no placeholder line leaks into every turn)
- `turn/judgments.gather_turn_judgments`'s single `asyncio.gather` now lists `judge_situation`, `judge_new_entity`, `judge_clock_signal` — the call site in `web/routes_actions.py`/`cli/turn_flow.py` did not need restructuring (09-02 built the extension point on purpose); both routes resolve a `scene_entity_judge` provider and submit `RecordAiCall(agent_role="scene_entity_judge", ...)` on both success and failure, symmetrically with the two existing roles
- `tests/test_parallel_judgment.py` (new, 8 tests): behavior layer (three counting stubs called exactly once across four distinct inputs), syntax layer (`ast.parse`s `turn/judgments.py`'s own source, asserts zero `ast.If`/`ast.IfExp` in `gather_turn_judgments`'s body and exactly one `asyncio.gather` call with exactly three positional args that are each `asyncio.to_thread` calls), and a timing layer (the three stubbed calls' `[start, end]` windows actually overlap via `time.monotonic`, catching a regression to sequential execution)
- `tests/test_agent_context_caps.py` (new, 16 tests): cap-exceeded contract for all four value objects reading limits from module constants (not re-hardcoded numbers), field-name-set assertions proving each object gets only its own slice, a session-length-independence proof (doubling stored event count does not change derived `recent_turns` counts — a fixed window, not a growing one), and a direct `ast`-based re-assertion (independent of `.importlinter`) that no module under `gptrpg.agents` imports `gptrpg.event_log`/`gptrpg.session_actor`

## Task Commits

Each task was committed atomically:

1. **Task 1: 장면 신규 대상 판단 (a)를 만든다** - `8a47950` (feat) — `EntityJudgeContext`, `NarrationFacts.new_entities`, `SCENE_ENTITY_TIMEOUT_S`, `build_scene_entity_prompt`, `scene_entity_judge.py`, `tests/test_scene_entity_judge.py` (14 tests)
2. **Task 2: 세 판단을 하나의 gather에 나열하고 (a)의 결과를 서술까지 흘린다** - `f892ef6` (feat) — `TurnJudgments.entity`, third `asyncio.gather` coroutine, web/CLI provider resolution + `RecordAiCall` wiring, ARCH-04/ARCH-05 test coverage in `test_web_actions.py`/`test_turn_flow_failure.py`
3. **Task 3: ARCH-04와 ARCH-06을 회귀 방지 그물로 못박는다** - `e21b385` (test) — `tests/test_parallel_judgment.py`, `tests/test_agent_context_caps.py`

Plus one follow-up coverage commit closing a manually-verified-only gap:

4. **Coverage addendum** - `e2d7b18` (test) — direct pytest coverage for D-03 (a)'s "new_entities reaches the narration prompt" acceptance criterion (previously only verified with an ad-hoc `python -c` check during Task 2)

## Files Created/Modified

- `src/gptrpg/agents/scene_entity_judge.py` - **new**: `NewEntity`/`EntityJudgment` dataclasses, `judge_new_entity` function
- `src/gptrpg/agents/context.py` - `EntityJudgeContext`, `ENTITY_JUDGE_RECENT_TURNS_LIMIT`, `NEW_ENTITY_LIMIT`, `NarrationFacts.new_entities`
- `src/gptrpg/agents/invoke.py` - `SCENE_ENTITY_TIMEOUT_S = 5.0`
- `src/gptrpg/agents/prompt_assembly.py` - `build_scene_entity_prompt` (new), `build_gm_prompt` appends the conditional new-entities line
- `src/gptrpg/turn/judgments.py` - `TurnJudgments.entity`, `_build_entity_judge_context`, third `asyncio.gather` coroutine, `build_narration_facts` fills `new_entities`
- `src/gptrpg/web/routes_actions.py`, `src/gptrpg/cli/turn_flow.py` - resolve `scene_entity_judge` provider, pass `entity_provider`/`entity_model` through, submit the third `RecordAiCall`
- `tests/test_scene_entity_judge.py` - **new**, 14 tests (cap/field-shape contract, D-05 failure contract, truncation, dedup, malformed-element skip)
- `tests/test_parallel_judgment.py` - **new**, 8 tests (ARCH-04 three-layer net)
- `tests/test_agent_context_caps.py` - **new**, 16 tests (ARCH-06 net across all four value objects)
- `tests/conftest.py` - `web_client_with_fake_provider` gained a `scene_entity_judge` kwarg
- `tests/test_web_actions.py`, `tests/test_turn_flow_failure.py` - new ARCH-04 (one-ai_invoked-per-role) and ARCH-05 (entity judge fails, narration still completes) coverage
- `tests/test_situation_judge.py` - `NarrationFacts` field-set assertion updated for `new_entities`; two new tests locking D-03 (a)'s prompt-reach behavior
- `tests/test_narration_isolation.py`, `tests/test_master_gm.py`, `tests/test_agents_retry.py`, `tests/test_measurement.py` - `NarrationFacts(...)`/`TurnJudgments(...)` call sites updated for the new required fields
- `tests/test_turn_tracer.py`, `tests/test_turn_flow_failure.py` - hardcoded `ai_invoked` counts bumped from 4 to 5
- `tests/test_clock_condition_cli.py` - `_MultiRoleProvider` dispatch gained a `"장면 신규 대상 판단자"` branch, `complete_calls` assertion bumped from 3 to 4

## Decisions Made

See `key-decisions` in frontmatter — DP-08/DP-09 confirmed exactly as `09-03-PLAN.md`'s `<planning_decisions>` specified; D-03/D-04 confirmed as implemented. None were reversed during execution.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pre-existing tests broke on `NarrationFacts.new_entities`/`TurnJudgments.entity` field additions**
- **Found during:** Task 2's own full-suite verification run
- **Issue:** `tests/test_situation_judge.py`, `tests/test_narration_isolation.py`, `tests/test_master_gm.py`, `tests/test_agents_retry.py`, `tests/test_measurement.py` construct `NarrationFacts(...)` directly without the new field (missing positional argument, since it has no default by design); `tests/test_narration_isolation.py` also constructs `TurnJudgments(...)` directly without `entity=`
- **Fix:** Added `new_entities=()`/`entity=EntityJudgment(entities=(), ai=empty_ai)` to each call site
- **Files modified:** the five files above
- **Committed in:** `f892ef6` (Task 2 commit)

**2. [Rule 3 - Blocking] Hardcoded `ai_invoked` event counts (4) needed bumping to 5**
- **Found during:** Task 2's own full-suite verification run
- **Issue:** `tests/test_turn_tracer.py` and `tests/test_turn_flow_failure.py` (two assertions) hardcoded `len(ai_events) == 4` (classifier + situation + clock + master_gm); the new scene_entity_judge call makes the true count 5
- **Fix:** Updated the counts and their explanatory comments
- **Files modified:** `tests/test_turn_tracer.py`, `tests/test_turn_flow_failure.py`
- **Committed in:** `f892ef6` (Task 2 commit)

**3. [Rule 3 - Blocking] `_MultiRoleProvider` (CLI test double) needed a scene-entity-judge dispatch branch**
- **Found during:** Task 2's own full-suite verification run
- **Issue:** `tests/test_clock_condition_cli.py`'s `_MultiRoleProvider` (a single fake provider serving all roles, dispatching on the role-instruction substring baked into each `build_*_prompt`'s permanent block — 09-02's established pattern) had no branch for `"장면 신규 대상 판단자"`, so `judge_new_entity`'s call raised `AssertionError("알 수 없는 역할의 프롬프트")` inside both retry attempts, then fell through the D-05 quiet-failure path (test still passed, but the `complete_calls` count assertion was off by one)
- **Fix:** Added the dispatch branch (returns `entity_value: str = "[]"` by default) and bumped `test_signal_skip_never_calls_deep_judgment_provider`'s `complete_calls` assertion from 3 to 4
- **Files modified:** `tests/test_clock_condition_cli.py`
- **Committed in:** `f892ef6` (Task 2 commit)

**4. [Rule 2 - Missing critical] `conftest.py`'s `web_client_with_fake_provider` needed a `scene_entity_judge` kwarg**
- **Found during:** Task 2, writing the ARCH-05 coverage the plan's own action item ⑤ requires
- **Issue:** The shared fixture (not in this plan's `files_modified`) had a `clock_judge`/`situation_judge` kwarg but no `scene_entity_judge` one, mirroring the same gap 09-02 hit for `situation_judge`
- **Fix:** Added a `scene_entity_judge: FakeProvider | None = None` kwarg mirroring the existing two
- **Files modified:** `tests/conftest.py`
- **Committed in:** `f892ef6` (Task 2 commit)

---

**Total deviations:** 4 auto-fixed (all Rule 3 blocking, plus one Rule 2 missing-critical-coverage). All were necessary to get the plan's own `<verify>` commands green after the required field additions; none expand scope beyond what Task 1/2's own action items already committed to.

## Issues Encountered

**Acceptance-criteria grep proxy vs. actual codebase documentation density (same class of finding as 09-02).** Task 2's acceptance criteria specify `grep -rn "judge_new_entity" src | grep -v "def judge_new_entity" | wc -l` should equal `2`. The actual count is 9, because this codebase's established convention is dense cross-referencing docstrings (`turn/judgments.py`'s module docstring and inline comments mention `judge_new_entity` by name multiple times, and `context.py`/`prompt_assembly.py` reference it in docstrings too). The actual structural property the grep is a proxy for — `judge_new_entity` is *invoked* from exactly one file — was verified directly: `grep -rn "judge_new_entity(\|^\s*judge_new_entity,\|import.*judge_new_entity" src` shows exactly one import line and one reference-as-callable, both in `turn/judgments.py`. No documentation was stripped to force a naive count match.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 09-04 (decisions/pipeline docs + human confirmation) can now document a fully closed ARCH-04/ARCH-05/ARCH-06 story for Phase 9 — all three requirements are `[x]` in REQUIREMENTS.md as of this plan
- Phase 10 (output validation) inherits `NarrationFacts.new_entities` as another turn-varying field that reaches `narrate()`'s `messages` (not `system`) — same trust-boundary class as the pre-existing `scene_summary`/`facts` fields from 09-02, already covered by this plan's `T-09-12`/`T-09-13` threat entries (`kind` closed-list validation for the model-authored `name`, and an explicit `accept` disposition for the model-authored-not-scenario-text distinction)
- Phase 11/12 (scene entity and character-state management) inherit `scene_entity_judge`'s output as facts-only — DP-09 explicitly kept the write path (event, `Entity` list) out of scope, verified structurally (`grep -c "NewEntity.*session_actor\|event_log"` == 0)
- No blockers. `EVENT_SCHEMA_VERSION` and `rules_core/reducer.py` untouched — no schema-migration risk carried forward

---
*Phase: 09-agent-architecture*
*Completed: 2026-08-09*

## Self-Check: PASSED

All claimed files verified present on disk (src/gptrpg/agents/scene_entity_judge.py, tests/test_scene_entity_judge.py, tests/test_parallel_judgment.py, tests/test_agent_context_caps.py, this SUMMARY.md) and all four commit hashes (8a47950, f892ef6, e21b385, e2d7b18) verified present in git log.
