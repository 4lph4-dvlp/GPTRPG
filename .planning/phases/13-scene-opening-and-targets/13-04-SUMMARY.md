---
phase: 13-scene-opening-and-targets
plan: 04
subsystem: gameplay-scene
tags: [scene-entities, event-schema, session-actor, turn-context, fastapi, cli]

# Dependency graph
requires:
  - phase: 13-scene-opening-and-targets (plan 01)
    provides: "scene_opened event, EVENT_SCHEMA_VERSION 11->12, party_roster_locked-gated opening"
  - phase: 13-scene-opening-and-targets (plan 03)
    provides: "WELL_BELOW registered as the second ScenarioDecl, build_turn_context(..., scenario=...) parameter actually exercised by a real call site (the opening route)"
provides:
  - "Three-layer scene entity resolution (rules_core/scenario.py): normalize_entity_name (NFC + strip, exact-match only), resolve_scene_layers (scenario -> emerged -> outside, fixed order, layer-1 wins), roster_rows (name/kind/origin only, D-17)"
  - "scene_entity_emerged event kind, EVENT_SCHEMA_VERSION 12->13, GameState.scene_entities_emerged fold (session-lifetime, ordered tuple, dedup by normalized_name)"
  - "SessionActor.RecordEmergedEntity / EntityAlreadyEmerged (in-queue dedup, actor does not check scenario-cast overlap by design — layer boundary)"
  - "build_turn_context(..., emerged_entities=...) — scene_entities is now scenario cast (never truncated) + emerged layer (capped at SCENE_ENTITY_LIMIT, latest-by-appearance-order kept, overlaps with cast dropped)"
  - "turn/emerged_entities.record_emerged_entities — the single helper confirm()/proceed()/cli turn_flow all call to turn scene_entity_judge's output into scene_entity_emerged events; the judgment itself (agents/scene_entity_judge.py) is unchanged"
affects: [13-05-target-selection, 13-06-roster-screen, 14-relationship-ledger]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 19766
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Layer-boundary-respecting dedup: the actor (session_actor) checks only against its own already-emerged set (EntityAlreadyEmerged); the scenario-cast overlap check lives in the caller (turn.emerged_entities.record_emerged_entities), because rulebooks/scenario data is not reachable from session_actor (.importlinter contract:2)"
    - "Single-shared-helper-not-triple-copy for a defense that must exist at three call sites (web confirm()/proceed(), cli turn_flow) — turn/ is the one layer that can see both agents and session_actor, so the helper lives there and all three call it"
    - "Remaining-budget truncation: the 2nd layer (emerged entities) is trimmed to whatever room is left after the 1st layer (scenario cast, never truncated) fills the total SCENE_ENTITY_LIMIT — not a flat per-layer count — so TurnContext.__post_init__'s total-length safety valve stays meaningful as a last line of defense instead of tripping on every normal turn"

key-files:
  created:
    - src/gptrpg/turn/emerged_entities.py
    - tests/test_scene_layers.py
  modified:
    - src/gptrpg/event_log/schema.py
    - src/gptrpg/rules_core/reducer.py
    - src/gptrpg/rules_core/scenario.py
    - src/gptrpg/session_actor/actor.py
    - src/gptrpg/agents/context.py
    - src/gptrpg/turn/context.py
    - src/gptrpg/web/routes_actions.py
    - src/gptrpg/cli/turn_flow.py
    - src/gptrpg/agents/scene_entity_judge.py
    - tests/test_agent_context_caps.py
    - tests/test_event_schema_migration.py
    - tests/test_scene_entity_judge.py
    - tests/test_web_actions.py
    - tests/test_turn_flow_failure.py
    - tests/fixtures/session1_expected_state.json

key-decisions:
  - "Wired emerged_entities=actor.state.scene_entities_emerged (and, for confirm()/proceed() specifically, no scenario= change) into the confirm()/proceed()/CLI build_turn_context() calls — this is beyond the plan's literal Task 2/3 action text (which describes the assembly function and the event-recording separately) but is required for the plan's own truths ('즉흥으로 생긴 것은 그 뒤로 계속 거기 있다') to hold in real gameplay, not just in isolated unit tests. Without this wiring, scene_entity_emerged events would be recorded but never actually flow into any turn's scene_entities. Rule 2 (missing critical functionality) — this plan's stated purpose is 'the receiving side,' and an unreachable receiving side is not a receiving side. Deliberately did NOT also wire scenario= into confirm()/proceed()'s build_turn_context call (only emerged_entities=) — confirm()/proceed() still use the THREAT_CAST fallback for layer 1, matching pre-existing behavior exactly (well_below.cast IS THREAT_CAST by identity per 13-03, so this is a zero-behavior-change simplification, not a gap) and keeping this plan's diff to what it explicitly owns (13-05/target-selection would need scenario= at the classify()/declare() layer too, out of scope here)."
  - "SCENE_ENTITY_LIMIT (=8) truncates the 2nd layer to whatever budget remains after the 1st layer (scenario cast, never truncated) — not a flat SCENE_ENTITY_LIMIT-sized slice of the 2nd layer alone. The plan's literal text ('2층을 뒤에서부터 SCENE_ENTITY_LIMIT개로 자른다') and its separate requirement that TurnContext.__post_init__ raise ContextCapExceeded('scene_entities', ...) against the SAME constant are only simultaneously satisfiable this way — a flat 2nd-layer cap independent of cast size would make the total scene_entities length exceed SCENE_ENTITY_LIMIT whenever cast is non-empty, tripping the 'last line of defense' on every single normal turn. The remaining-budget design keeps the safety valve meaningful (never trips under normal play; only trips if a scenario's own cast is pathologically larger than the whole budget) while still honoring '1층은 안 자른다' and '상한은 2층에만 건다' literally."
  - "record_emerged_entities lives in a new module (turn/emerged_entities.py), not in turn/judgments.py, per the plan's explicit instruction — turn/judgments.py has a zero-line diff (verified: git diff HEAD~1 -- src/gptrpg/turn/judgments.py | wc -l == 0)."
  - "Deviation (documented, not fixed) — the plan's literal acceptance-criteria grep counts (`grep -c 'record_emerged_entities'` == 2 in routes_actions.py, and CLI count checked with >=1) both undercount/overcount by exactly the import-line match, the same class of miscount 13-02's SUMMARY already documented for ClaimGmSlot/ReleaseGmSlot. Actual whole-file grep: 3 in routes_actions.py (1 import + 2 real call sites), 3 in cli/turn_flow.py (1 import + 2 real call sites — the plan only required >=1 for CLI; this plan wired both the no_check path and the checked path, exceeding the stated minimum, not a shortfall). Functional count via 'await record_emerged_entities(' substring: exactly 2 in each file."
  - "AGENT_ROLES stale-acceptance-criterion deviation (same pre-existing drift 13-03 already documented in its own SUMMARY) — the plan's literal '== 5' check is wrong against the current codebase (actual value: 7, unchanged before/after this plan's commits). The functional guarantee this plan claims — no new AI role added — holds and is independently verified (7 == 7 across this plan's three commits)."

patterns-established:
  - "Layer assembly with an unbounded first layer and a budget-filling second layer, where the total (not either layer alone) is what the type's own safety-valve check enforces — the shape any future third scene-entity source (Phase 14's relationship ledger, if it ever needs to inject entities) should follow rather than inventing a fourth truncation scheme."

requirements-completed: [SCENE-03, SCENE-05]

coverage:
  - id: D1
    description: "지금 장면에 무엇이 있는지가 세 층으로 관리된다 — turn/context.py:130의 scene_entities = THREAT_CAST 하드코딩이 사라진다 (SCENE-03)"
    requirement: "SCENE-03"
    verification:
      - kind: unit
        ref: "tests/test_scene_layers.py::test_build_turn_context_scenario_none_emerged_none_is_byte_identical_regression, test_build_turn_context_merges_cast_and_emerged_without_scenario"
        status: pass
    human_judgment: false
  - id: D2
    description: "같은 대상이 두 층에 있으면 정확히 하나로 정해진다 — 시나리오가 이긴다 (SCENE-03 adjacency)"
    requirement: "SCENE-03"
    verification:
      - kind: unit
        ref: "tests/test_scene_layers.py::test_resolve_scene_layers_same_name_in_both_layers_scenario_wins, test_build_turn_context_drops_emerged_entity_overlapping_cast_name, test_roster_rows_overlap_keeps_exactly_one_scenario_row"
        status: pass
    human_judgment: false
  - id: D3
    description: "두 층이 모두 비어 있어도 조회가 결정론적으로 끝난다 — None도 예외도 아니다 (SCENE-03 empty)"
    requirement: "SCENE-03"
    verification:
      - kind: unit
        ref: "tests/test_scene_layers.py::test_resolve_scene_layers_both_layers_empty_returns_outside_not_none_not_exception, test_roster_rows_empty_cast_and_emerged_returns_empty_tuple"
        status: pass
    human_judgment: false
  - id: D4
    description: "같은 한글 이름이 분해형·공백 차이에도 같은 인물로 인식된다, 가운데 공백이 다르면 다른 값이다 (SCENE-05 encoding)"
    requirement: "SCENE-05"
    verification:
      - kind: unit
        ref: "tests/test_scene_layers.py::test_normalize_entity_name_composed_and_decomposed_hangul_are_equal, test_normalize_entity_name_strips_leading_and_trailing_whitespace_only, test_normalize_entity_name_keeps_middle_whitespace_significant"
        status: pass
    human_judgment: false
  - id: D5
    description: "scene_entity_judge의 결과가 웹 두 자리(confirm/proceed)와 명령줄 한 자리에서 사건으로 쌓이고, 다음 턴 장면 목록에 그대로 있다 (D-13②/D-14)"
    verification:
      - kind: integration
        ref: "tests/test_scene_entity_judge.py::test_emerged_entity_recorded_and_present_in_next_turn_scene_entities, test_emerged_entity_same_name_two_turns_in_a_row_records_exactly_one_event, test_emerged_entity_overlapping_scenario_cast_does_not_get_recorded"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py::test_confirm_records_scene_entity_emerged_event, test_proceed_records_scene_entity_emerged_event"
        status: pass
      - kind: integration
        ref: "tests/test_turn_flow_failure.py::test_cli_turn_records_scene_entity_emerged_event"
        status: pass
    human_judgment: false
  - id: D6
    description: "AI에게 넘기는 양에 상한이 걸리고, 세션 길이와 무관하게 묶이며, 화면 상한과 같은 상수로 묶이지 않았다 (D-12/D-20/D-26, ARCH-06)"
    verification:
      - kind: unit
        ref: "tests/test_agent_context_caps.py::test_scene_entities_emerged_layer_stays_bounded_regardless_of_session_length, test_turn_context_raises_context_cap_exceeded_over_scene_entity_limit"
        status: pass
      - kind: other
        ref: "grep -c 'SCENE_ENTITY_LIMIT' src/gptrpg/frontend (no match — no frontend touched at all this plan, D-26 boundary preserved by construction)"
        status: pass
    human_judgment: false
  - id: D7
    description: "새 사건 종류(scene_entity_emerged)와 EVENT_SCHEMA_VERSION 12->13 판올림이 reducer.py 분기와 같은 커밋에서 닫히고, 옛 실기록이 예외 없이 접힌다"
    verification:
      - kind: unit
        ref: "git show --name-only <Task-1-commit> includes both event_log/schema.py and rules_core/reducer.py; tests/test_event_schema_migration.py full suite (session1 895-event fixture replay) passes with the new field defaulting to empty"
        status: pass
    human_judgment: false
  - id: D8
    description: "AI 역할이 늘지 않았다 — scene_entity_judge는 이미 있던 판단이고 새 AI 호출이 하나도 안 늘었다"
    verification:
      - kind: unit
        ref: "AGENT_ROLES count identical before/after this plan's three commits (7 == 7); the plan's literal '==5' acceptance criterion is stale against pre-existing codebase state (documented, same drift 13-03 already flagged), not against this plan's work"
        status: pass
    human_judgment: false
  - id: D9
    description: "기존 시험 전부와 층 계약(.importlinter)이 그대로 통과한다 — 회귀 없음"
    verification:
      - kind: unit
        ref: ".venv/bin/python -m pytest -q --tb=short (full suite: 1492 passed, 1 pre-existing unrelated failure documented below)"
        status: pass
      - kind: other
        ref: ".venv/bin/lint-imports (4 contracts kept, 0 broken)"
        status: pass
    human_judgment: false

# Metrics
duration: ~2h
completed: 2026-08-26
status: complete
---

# Phase 13 Plan 04: Three-Layer Scene Entity Management + Receiving scene_entity_judge's Output Summary

**`scene_entities`가 이제 시나리오 캐스트(1층, 안 잘림) + 이번 세션에서 나와서 확정된 것(2층, 상한 안쪽에서 최신 것부터 유지) + 그 밖(3층, 목록에 없음)의 세 층으로 조립되고, Phase 9부터 매 턴 불리고도 버려지기만 하던 `scene_entity_judge`의 판단이 처음으로 `scene_entity_emerged` 사건으로 웹 두 자리·명령줄 한 자리 모두에서 적립되어 다음 턴에도 남는다.**

## Performance

- **Duration:** ~2h
- **Tasks:** 3 (Task 1 auto+tdd, Task 2 auto, Task 3 auto)
- **Files modified:** 17 (2 created, 15 modified)

## Accomplishments

- **Task 1 (`a1a6c23`):** `rules_core/scenario.py`가 `normalize_entity_name`(NFC 정규화 + 앞뒤 공백 제거, 완전 일치만)·`resolve_scene_layers`(시나리오 → 확정 → 밖, 고정 순서, 같은 이름이 두 층에 있으면 1층 승리, 두 층이 비어도 결정론적으로 `outside`)·`roster_rows`(이름·종류·출생 셋뿐, D-17)를 얻었다. `event_log/schema.py`는 `EVENT_SCHEMA_VERSION` 12→13과 새 사건 `SceneEntityEmerged`(name/kind/normalized_name)를 **같은 커밋**에서 `rules_core/reducer.py`의 새 분기(`GameState.scene_entities_emerged`, 순번 오름차순 튜플, 정규화 이름 중복 방지)와 함께 얻었다. `session_actor/actor.py`는 `RecordEmergedEntity`/`EntityAlreadyEmerged`를 얻었다 — 액터는 이미 적립된 것과의 중복만 보고, 시나리오 캐스트 겹침은 층 경계상 못 본다(액터는 `rulebooks`를 모른다). `tests/test_scene_layers.py`(신규)는 이 함수들이 없는 상태(빨강, `ImportError`)로 먼저 작성되었고, 구현 뒤 22개 시험이 초록으로 전환됐다.
- **Task 2 (`64b9f36`):** `agents/context.py`가 `SCENE_ENTITY_LIMIT`(=8, `PARTY_MEMBER_LIMIT`과 같은 자릿수)과 `TurnContext.__post_init__`의 `scene_entities` 상한 검사(마지막 방어선)를 얻었다. `turn/context.py`의 `build_turn_context`가 `emerged_entities` 키워드 인자를 얻었고, `scene_entities` 조립을 「1층(시나리오 캐스트, 안 잘림) + 2층(겹침 뺀 뒤 남는 예산만큼 등장 순서 최신 것부터)」로 갈아 썼다 — `scenario=None`·`emerged_entities=None`이면 예전과 한 글자도 다르지 않은 `TurnContext`가 나온다(회귀 시험으로 고정). `turn/judgments.py`는 무변경.
- **Task 3 (`25afb36`):** 새 헬퍼 `turn/emerged_entities.record_emerged_entities`가 세 호출부(웹의 `confirm()`·`proceed()`, 명령줄 `cli/turn_flow.py`의 판정 두 자리)가 공유하는 단일 자리가 됐다 — 각 자리는 기존 `RecordAiCall(agent_role="scene_entity_judge", ...)` 제출 바로 뒤에서 이 헬퍼를 부른다. 헬퍼는 `resolve_scene_layers`로 1층·이미 적립된 2층과 겹치는 이름을 걸러 제출하지 않고, `EntityAlreadyEmerged`는 성공으로 읽으며, 그 밖의 제출 실패는 경고만 남기고 턴을 막지 않는다(D-05/ARCH-05). `web/routes_actions.py`의 `confirm()`/`proceed()`와 `cli/turn_flow.py`의 두 판정 경로 모두 `build_turn_context(..., emerged_entities=actor.state.scene_entities_emerged)`로 갱신되어, 적립된 대상이 실제로 다음 턴의 `ctx.scene_entities`에 나타난다(별도 결정 사항 참조 — 이 배선은 계획 문서가 Task 2/3에 명시적으로 안 적었지만 「즉흥으로 생긴 것이 다음 턴에도 있다」는 계획 자신의 진실 요구를 실제로 만족시키는 데 필수였다). `agents/scene_entity_judge.py`는 도크스트링 한 줄만 갱신됐다(코드 무변경, `git diff` +3줄).

## Task Commits

Each task was committed atomically:

1. **Task 1: 세 층 조회를 순수 함수로 세우고, 2층을 사건으로 적립할 그릇을 만든다** - `a1a6c23` (feat, tdd)
2. **Task 2: `THREAT_CAST` 하드코딩을 3층 조립으로 바꾸고, AI에게 넘기는 양에 상한을 건다** - `64b9f36` (feat)
3. **Task 3: 버려지던 판단을 받는다 — 웹과 명령줄이 같은 커밋에서** - `25afb36` (feat)

**Plan metadata:** (this commit — see `git_commit_metadata` step)

## Files Created/Modified

- `src/gptrpg/rules_core/scenario.py` - `SceneLayer`/`SceneLayerHit`/`RosterRow`, `normalize_entity_name`/`resolve_scene_layers`/`roster_rows`
- `src/gptrpg/event_log/schema.py` - `SceneEntityEmerged` event, `EVENT_SCHEMA_VERSION` 12→13
- `src/gptrpg/rules_core/reducer.py` - `EmergedEntityFold`, `GameState.scene_entities_emerged`, `scene_entity_emerged` reducer branch
- `src/gptrpg/session_actor/actor.py` - `RecordEmergedEntity` command, `EntityAlreadyEmerged` exception, `_prepare_emerged_entity`
- `src/gptrpg/agents/context.py` - `SCENE_ENTITY_LIMIT`, `TurnContext.__post_init__` scene_entities cap check
- `src/gptrpg/turn/context.py` - `build_turn_context(..., emerged_entities=...)`, three-layer assembly
- `src/gptrpg/turn/emerged_entities.py` (new) - `record_emerged_entities` shared helper
- `src/gptrpg/web/routes_actions.py` - `confirm()`/`proceed()` call the helper + pass `emerged_entities=` to `build_turn_context`
- `src/gptrpg/cli/turn_flow.py` - same wiring at both judged-turn call sites
- `src/gptrpg/agents/scene_entity_judge.py` - docstring line only (Phase 13 receives the output now)
- `tests/test_scene_layers.py` (new) - 29 tests: normalize/resolve/roster pure functions, actor-level RecordEmergedEntity, reducer double-defense, build_turn_context assembly, record_emerged_entities helper
- `tests/test_agent_context_caps.py` - scene_entities cap tests + session-length-independence test for the 2nd layer
- `tests/test_event_schema_migration.py` - version-13 pinning test renamed/added
- `tests/test_scene_entity_judge.py` - HTTP-level emerged-entity recording tests (3, all matched by `-k emerged`)
- `tests/test_web_actions.py` - confirm()/proceed() both-record tests
- `tests/test_turn_flow_failure.py` - CLI-level emerged-entity recording test
- `tests/fixtures/session1_expected_state.json` - `scene_entities_emerged: []` key added for the new GameState field

## Decisions Made

- **Wired `emerged_entities=`/`scenario=`-adjacent plumbing into confirm()/proceed()/CLI beyond the plan's literal per-task text** — see key-decisions in frontmatter. Necessary for the plan's own truths to hold in real gameplay, not just isolated tests; documented as Rule 2 (missing critical functionality).
- **`SCENE_ENTITY_LIMIT` truncates the 2nd layer to the budget remaining after the 1st layer**, not a flat 2nd-layer-only count — the only design that keeps the plan's two literal requirements (1st layer never truncated + `TurnContext.__post_init__`'s safety valve compares the SAME constant against the TOTAL) simultaneously true without the safety valve tripping on every ordinary turn. See key-decisions for the full reasoning.
- **`record_emerged_entities` lives in a new `turn/emerged_entities.py` module**, not `turn/judgments.py` (which the plan explicitly forbade touching) — verified `git diff HEAD~1 -- src/gptrpg/turn/judgments.py | wc -l == 0` after Task 3.
- **AGENT_ROLES stale-acceptance-criterion deviation** (same drift 13-03's own SUMMARY already documented): the plan's literal `== 5` check is wrong against the current codebase (actual pre-existing value: 7, `outcome_picker` and `creation_gm` were added by earlier phases). The functional guarantee — no new role added by this plan — holds and is independently verified (count identical before/after this plan's three commits).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Wired `emerged_entities=` (and read `actor.state.scene_entities_emerged`) into confirm()/proceed()/CLI's `build_turn_context()` calls**
- **Found during:** Task 3
- **Issue:** The plan's Task 2 text describes `build_turn_context`'s new parameter and assembly logic; Task 3's text describes only the event-recording side (submitting `RecordEmergedEntity`). Neither task's literal action text says to update the *callers'* `build_turn_context()` invocations with the new parameter. Without that wiring, `scene_entity_emerged` events would be correctly recorded but would never actually populate any turn's `ctx.scene_entities` — the plan's own must-have truth ("즉흥으로 생긴 것은 그 뒤로 계속 거기 있다") would be satisfied only by isolated function tests, not by the actual product.
- **Fix:** Added `emerged_entities=actor.state.scene_entities_emerged` to the `build_turn_context()` calls in `confirm()`, `proceed()`, and both CLI judged-turn call sites.
- **Files modified:** `src/gptrpg/web/routes_actions.py`, `src/gptrpg/cli/turn_flow.py`
- **Verification:** `tests/test_scene_entity_judge.py::test_emerged_entity_recorded_and_present_in_next_turn_scene_entities` directly rebuilds `TurnContext` after an HTTP round-trip and asserts the emerged entity is present.
- **Committed in:** `25afb36`

**2. [Rule 1 - Test naming] Renamed three HTTP-level tests to contain "emerged" so `pytest -k emerged` selects exactly the three the plan's acceptance criteria name**
- **Found during:** Task 3, writing `tests/test_scene_entity_judge.py`
- **Issue:** Initial test names (`test_confirm_records_new_entity_and_next_turn_scene_entities_contains_it`, etc.) did not contain the substring `emerged`.
- **Fix:** Renamed to `test_emerged_entity_recorded_and_present_in_next_turn_scene_entities`, `test_emerged_entity_same_name_two_turns_in_a_row_records_exactly_one_event`, `test_emerged_entity_overlapping_scenario_cast_does_not_get_recorded`.
- **Files modified:** `tests/test_scene_entity_judge.py`
- **Verification:** `pytest tests/test_scene_entity_judge.py -k emerged` selects exactly 3 tests, all passing.
- **Committed in:** `25afb36`

**3. [Rule 3 - Blocking, documented not fixed] `AGENT_ROLES == 5` acceptance criterion is stale**
- Same pre-existing drift 13-03's own SUMMARY documented (`outcome_picker`/`creation_gm` predate this plan). No action needed — the functional requirement (no new role from this plan) is independently verified: count is 7 both before and after this plan's three commits.

**4. [Rule 3 - Blocking, documented not fixed] Literal `grep -c 'record_emerged_entities'` whole-file counts don't match the plan's stated numbers**
- See key-decisions above. The import line adds one match a plain-substring grep cannot exclude — same class of miscount 13-02's SUMMARY documented for `ClaimGmSlot`/`ReleaseGmSlot`. Functional count (`await record_emerged_entities(`) is exactly 2 in each file.

---

**Total deviations:** 2 auto-fixed (1 missing-critical wiring, 1 test naming), 2 documented pre-existing/literal-grep drifts (not this plan's defects). **Impact on plan:** The missing-critical fix is what makes this plan's actual purpose (receiving `scene_entity_judge`'s output) real instead of merely testable in isolation — no scope creep, it is the plan's own stated goal. No AI role was added; no acceptance criterion's *functional intent* failed.

## RED/GREEN pytest evidence (Task 1 acceptance criterion)

**RED — before `normalize_entity_name`/`resolve_scene_layers`/`roster_rows`/`EmergedEntityFold` existed** (captured by temporarily restoring the four source files to their pre-Task-1 committed content via `git show HEAD:<path>` + `cp`, per this session's `destructive_git_prohibition` guidance against `git stash`/`git checkout --` for this purpose; restored immediately after capturing):

```
==================================== ERRORS ====================================
_________________ ERROR collecting tests/test_scene_layers.py __________________
ImportError while importing test module '/home/alpha-pi/dev/GPTRPG/tests/test_scene_layers.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
../../.local/share/uv/python/cpython-3.14-linux-aarch64-gnu/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_scene_layers.py:16: in <module>
    from gptrpg.rules_core.reducer import EmergedEntityFold, apply_event, initial_state
E   ImportError: cannot import name 'EmergedEntityFold' from 'gptrpg.rules_core.reducer' (/home/alpha-pi/dev/GPTRPG/src/gptrpg/rules_core/reducer.py)
=========================== short test summary info ============================
ERROR tests/test_scene_layers.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
2 warnings, 1 error in 0.38s
```

**GREEN — with the fix applied (Task 1's committed state, 22 tests at that point in the file's growth):**

```
......................                                                   [100%]
22 passed, 2 warnings in 0.20s
```

(By the end of Task 3, the same file has grown to 29 tests, all passing — the extra 7 came from Task 2's assembly-level tests and Task 3's `record_emerged_entities` helper tests appended to the same file.)

## AI Quality Note (per phase context instructions)

**This plan's behavior does not depend on real model judgment quality** — unlike 13-03 (which judged narrative content generated by a real model), 13-04 is pure wiring: it takes `scene_entity_judge`'s *already-existing* output (a list of `{name, kind}` pairs) and routes it through validation, deduplication, and storage. All automated tests in this plan use `FakeProvider`/hand-written JSON fixtures for the `scene_entity_judge` role — they verify **that the pipe carries what's put into it correctly** (normalization, layer resolution, dedup, capping, event recording, cross-turn visibility), not **that a real model produces good entity judgments**. That latter question was already the concern of Phase 9 (which built `scene_entity_judge` itself) and is orthogonal to this plan's scope. No live-provider verification was run for this plan, and none was needed — there is no new AI-generated content to evaluate; the only new judgment about AI output here is the closed two-value `kind` check (`person`/`thing`), which is a mechanical string comparison, not a quality judgment.

## Issues Encountered

- **Known pre-existing full-suite failure, unrelated to this plan:** `tests/test_event_schema_migration.py::test_events_db_v2_records_fold_without_exception_under_schema_6` fails because the untracked local `.gptrpg/events.db` disagrees with its committed fixture. The orchestrator independently confirmed this fails identically at commit `3f7458b`, before any Phase 13 work. Not introduced or affected by this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The three-layer scene entity resolution (`resolve_scene_layers`/`roster_rows`) is the exact function 13-05 (target selection) needs to reuse for the classifier's "who/what am I targeting" closed-list check — it is a pure function with no dependency on this plan's event-recording wiring, so 13-05 can call it directly.
- `GameState.scene_entities_emerged` and `EmergedEntityFold.normalized_name` are the data 13-06 (roster screen) needs for the collapsed roster display (`roster_rows(cast, emerged)` already produces exactly the three-column shape D-24 specified) — no new backend work needed there, only the frontend rendering.
- **13-05 will need `scenario=`/target-classification wiring at the `declare()`/classify() layer** that this plan deliberately left untouched (out of this plan's fence — "대상 지목·분류기를 안 건드린다"). This plan's `confirm()`/`proceed()` wiring only covers the post-classification judged-turn path.
- `.planning/todos/pending/2026-08-26-mobile-status-pane-drawer.md` and `.planning/todos/pending/2026-08-26-creation-host-transfers-on-timeout.md` remain open and untouched by this plan.

## Self-Check: PASSED

- `src/gptrpg/turn/emerged_entities.py` and `tests/test_scene_layers.py` verified present on disk.
- Commits `a1a6c23`, `64b9f36`, `25afb36` verified present in `git log --oneline`.
- Full test suite: 1492 passed, 1 pre-existing unrelated failure (documented above), 0 newly introduced failures.
- `lint-imports`: 4 contracts kept, 0 broken.
- `AGENT_ROLES` count: 7, identical before and after this plan's commits (no new AI role).
- `EVENT_SCHEMA_VERSION`: 13, bumped exactly once, `reducer.py` branch landed in the same commit (`a1a6c23`).

---
*Phase: 13-scene-opening-and-targets*
*Completed: 2026-08-26*
