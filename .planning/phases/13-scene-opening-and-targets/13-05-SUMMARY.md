---
phase: 13-scene-opening-and-targets
plan: 05
subsystem: gameplay-scene
tags: [action-classifier, target-selection, event-schema, session-actor, turn-context, fastapi, cli]

# Dependency graph
requires:
  - phase: 13-scene-opening-and-targets (plan 04)
    provides: "Three-layer scene entity resolution (rules_core/scenario.py: normalize_entity_name, resolve_scene_layers), scene_entity_emerged event + RecordEmergedEntity/EntityAlreadyEmerged, turn/emerged_entities.record_emerged_entities shared helper, build_turn_context(..., emerged_entities=...)"
provides:
  - "TargetClaim/_parse_target (agents/action_classifier.py) — classifier picks a target alongside move/stat, same item_use-style closed-list pattern but out-of-list is a normal presence='unknown' return, never an absorbed exception (SCENE-04)"
  - "EVENT_SCHEMA_VERSION 13->14: ActionClassified gains target_name/target_presence/target_kind (no new event kind), GameState.declare_targets fold, actor closed-list validation — all in the same commit"
  - "turn/emerged_entities.apply_declared_target — the single helper confirm()/proceed()(web) and the judged-turn + no-check paths (cli) all call to branch an out-of-layer target on ScenarioDecl.improv_people/improv_things"
  - "agents.context.TARGET_ABSENT_FACT — platform-authored fact string fed through build_narration_facts(..., extra_facts=...) when an out-of-layer target is declared but the scenario forbids it"
  - "web declare() and cli _turn_flow both wire scenario=+emerged_entities= into build_turn_context and build allowed_targets from the resulting ctx.scene_entities — the closed list the classifier's target selection needs"
affects: [13-06-roster-screen, 14-relationship-ledger]

# Actuals (#2632)
actuals:
  tokens: 24042
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Normal-return-not-exception for a closed-list miss when the miss is a legitimate branch, not a contract violation — _parse_target mirrors _parse_item_use's structure but inverts its failure mode on purpose (documented side-by-side in both docstrings so the difference survives future 'let's unify these two parsers' refactors)"
    - "'Modeless' 2-value kind at the record boundary: apply_declared_target computes an open/closed decision even when kind is unknown (both improv axes must be open), but never invents a kind value to satisfy RecordEmergedEntity's structural person/thing-only constraint — an ambiguous target is allowed to exist narratively without ever reaching the roster"
    - "extra_facts prepended ahead of the model's own facts in build_narration_facts, then jointly truncated to SITUATION_FACTS_LIMIT — platform-authored facts are this turn's deterministic result and outrank model-authored ones under the same cap, without adding a second cap or a new NarrationFacts field"

key-files:
  created:
    - tests/test_scene_target.py
  modified:
    - src/gptrpg/agents/action_classifier.py
    - src/gptrpg/agents/prompt_assembly.py
    - src/gptrpg/agents/context.py
    - src/gptrpg/event_log/schema.py
    - src/gptrpg/rules_core/reducer.py
    - src/gptrpg/session_actor/actor.py
    - src/gptrpg/turn/judgments.py
    - src/gptrpg/turn/emerged_entities.py
    - src/gptrpg/web/routes_actions.py
    - src/gptrpg/cli/turn_flow.py
    - tests/test_action_classifier.py
    - tests/test_web_actions.py
    - tests/test_event_schema_migration.py
    - tests/fixtures/session1_expected_state.json

key-decisions:
  - "NO_TARGET lives in action_classifier.py (not agents/context.py where NO_ITEM_USED lives) — TargetClaim is a Proposal field with a literal-instance default, so it must be defined before Proposal in the same file (Python evaluates dataclass field defaults at class-body execution time); NO_CHECK_SIGNAL already establishes the 'reserved marker declared in action_classifier.py, imported locally by prompt_assembly.py' convention this follows instead."
  - "The prompt's target instruction block does NOT re-render the closed list — it reuses the 'scene entities' block _session_block_text(ctx) already renders (built from the same ctx.scene_entities allowed_targets is derived from), avoiding a duplicate token-costly list."
  - "kind=None on an out-of-layer target: the open/closed gate requires BOTH improv axes open, but even when open, RecordEmergedEntity is never called — EmergedEntityFold's kind is structurally person/thing-only (_VALID_EMERGED_ENTITY_KINDS), so an unclassifiable target is allowed to exist in narration but never invented into the roster. No absent-fact either (it IS allowed) — silently no side effect. This resolves what read as a self-contradicting plan clause ('허용 -> submit... kind가 None이면 여기 도달하지 않으므로 항상 값이 있다') once EmergedEntityFold's structural constraint is taken as authoritative: the sentence is literally true by construction under this design."
  - "declare()'s build_turn_context call now receives scenario=+emerged_entities= (13-04 deliberately left this untouched, flagged for 13-05 in its own SUMMARY's 'Next Phase Readiness') — needed so ctx.scene_entities carries the full 1st+2nd-layer closed list the classifier's allowed_targets is built from. confirm()/proceed()'s build_turn_context calls were NOT touched (still THREAT_CAST fallback per 13-04's own decision) — they only needed a separate scenario lookup for the improv-flag check, not a change to ctx assembly."
  - "apply_declared_target lives in turn/emerged_entities.py (extending 13-04's module), not a new file the plan's own <files> lists never named for Task 2/3 — required so both web (confirm/proceed) and cli (judged-turn + no-check paths) can share one decision function; turn/ is the one layer that sees both agents and session_actor (.importlinter contract:2), matching 13-04's own record_emerged_entities precedent exactly."

patterns-established:
  - "A closed-list parser that returns a normal 'not in the list' value instead of absorbing it as a contract violation, when the plan's own domain model requires that branch to be legitimate (SCENE-04) rather than an AI mistake (RULE-16's item_use) — the two parsers' docstrings cross-reference each other so a future 'unify these' refactor has to consciously override this distinction rather than discover it by accident."

requirements-completed: [SCENE-04]

coverage:
  - id: D1
    description: "분류기가 무브·능력치와 함께 대상을 고르고 새 AI 역할이 안 늘었다 (SCENE-04, D-13①)"
    requirement: "SCENE-04"
    verification:
      - kind: unit
        ref: "tests/test_action_classifier.py::test_parse_target_exact_match_in_allowed_list_yields_known, test_parse_target_not_in_allowed_list_yields_unknown_not_an_exception, test_classify_allowed_targets_provided_known_target"
        status: pass
      - kind: other
        ref: "AGENT_ROLES count identical before/after (7 == 7) — no new AI role added this plan"
        status: pass
    human_judgment: false
  - id: D2
    description: "목록 안 지목은 목록의 이름으로 정해져 같은 인물이 이름으로 갈라지지 않는다 (D-19)"
    requirement: "SCENE-04"
    verification:
      - kind: unit
        ref: "tests/test_action_classifier.py::test_parse_target_normalization_difference_still_matches_known"
        status: pass
    human_judgment: false
  - id: D3
    description: "층 밖 지목이 시나리오의 열림/닫힘 선언대로 갈리고, 사람/사물 두 축이 따로 걸린다 (D-16)"
    requirement: "SCENE-04"
    verification:
      - kind: unit
        ref: "tests/test_scene_target.py::test_improv_allowed_unknown_person_records_event_and_returns_no_facts, test_improv_forbidden_unknown_person_records_no_event_and_returns_absent_fact, test_improv_person_forbidden_thing_allowed_same_session_splits_by_kind, test_improv_kind_none_accumulates_only_when_both_axes_open, test_improv_kind_none_one_axis_closed_yields_absent_fact_not_event"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py::test_confirm_forbidden_improv_person_records_no_event_and_narrates_absent_fact, test_confirm_allowed_improv_thing_records_scene_entity_emerged, test_proceed_forbidden_improv_person_records_no_event_and_narrates_absent_fact, test_proceed_allowed_improv_thing_records_scene_entity_emerged"
        status: pass
      - kind: integration
        ref: "tests/test_scene_target.py::test_cli_forbidden_improv_person_records_no_event_and_narrates_absent_fact, test_cli_allowed_improv_thing_records_scene_entity_emerged"
        status: pass
    human_judgment: false
  - id: D4
    description: "허용이면 되묻지 않고 확정 목록에 쌓이며 등장 순서가 재현된다 (D-14, SCENE-04 ordering)"
    requirement: "SCENE-04"
    verification:
      - kind: unit
        ref: "tests/test_scene_target.py::test_repeated_same_unknown_target_input_yields_same_order"
        status: pass
    human_judgment: false
  - id: D5
    description: "금지면 사건 없이 사실 한 줄만 서술로 흘러 세계가 이야기로 돌려보낸다 — 목록을 꺼내지도, 거절 문구를 쓰지도 않는다 (D-15)"
    requirement: "SCENE-04"
    verification:
      - kind: unit
        ref: "tests/test_scene_target.py::test_target_absent_fact_has_no_system_rejection_phrasing[없습니다-다시 입력-혹시], test_target_absent_fact_flows_into_narration_facts_via_extra_facts"
        status: pass
      - kind: other
        ref: "git diff HEAD -- src/gptrpg/agents/master_gm.py (0 lines) — 진행자 지시문 무변경"
        status: pass
    human_judgment: false
  - id: D6
    description: "「대상 검사를 안 쓴다」 시나리오에서는 프롬프트·판정 훅에서 대상이 완전히 사라진다 (D-22)"
    requirement: "SCENE-04"
    verification:
      - kind: unit
        ref: "tests/test_action_classifier.py::test_classify_allowed_targets_none_skips_target_check_entirely, test_classifier_prompt_omits_target_selection_when_allowed_targets_is_none"
        status: pass
    human_judgment: false
  - id: D7
    description: "웹과 명령줄이 같은 갈래로 돈다 — 분류·기록·진행 세 자리가 양쪽에 있다"
    requirement: "SCENE-04"
    verification:
      - kind: integration
        ref: "tests/test_scene_target.py::test_cli_declare_records_known_target_from_default_scenario_cast, test_cli_action_classified_carries_target_three_fields (paired with the web-level tests in D3 using the identical well_below improv_people=False/improv_things=True scenario)"
        status: pass
    human_judgment: false
  - id: D8
    description: "실제 NIM 분류기 모델이 세 갈래(목록 안/목록 밖-사람/목록 밖-사물/대상 없음)를 모두 실제로 구분해 낸다 — 페이크 제공자로는 증명할 수 없는 질문"
    verification:
      - kind: manual_procedural
        ref: "Live nvidia/nemotron-3-super-120b-a12b call via port-8001 server's configured provider (script run, not a pytest test — see 'AI Quality Note' below for full transcript)"
        status: pass
    human_judgment: true
    rationale: "Model output quality on natural-language target references cannot be asserted as a permanent regression test (model behavior can drift across provider updates) — recorded here as point-in-time evidence, not a repeatable CI check. A human should periodically re-verify this against provider upgrades."
  - id: D9
    description: "기존 시험 전부와 층 계약(.importlinter)이 그대로 통과한다 — 회귀 없음"
    verification:
      - kind: unit
        ref: ".venv/bin/python -m pytest -q --tb=short (1535 passed, 1 pre-existing unrelated failure documented below)"
        status: pass
      - kind: other
        ref: ".venv/bin/lint-imports (4 contracts kept, 0 broken)"
        status: pass
    human_judgment: false

# Metrics
duration: ~2h30m
completed: 2026-08-26
status: complete
---

# Phase 13 Plan 05: Target Selection Summary

**분류기가 무브·능력치와 함께 「누구를·무엇을 상대로」를 고르고, 목록 밖 지목은 시나리오의 즉흥 허용/금지 선언(사람·사물 따로)대로 결정론적으로 갈려 — 허용이면 확정 목록에 쌓이고 금지면 거절 문구 없는 사실 한 줄이 서술로 흘러 세계가 대답한다.**

## Performance

- **Duration:** ~2h30m
- **Started:** 2026-08-26 (session continuation from 13-04)
- **Completed:** 2026-08-26
- **Tasks:** 3 (Task 1 auto+tdd, Task 2 auto, Task 3 auto)
- **Files modified:** 14 (1 created, 13 modified)

## Accomplishments

- **Task 1 (`dd8b394`):** `agents/action_classifier.py`가 `TargetClaim`(닫힌 세 값 `presence`)과 `_parse_target`을 얻었다 — 침묵·빈 문자열·공백은 `presence="none"`, 닫힌 목록(1층+2층) 안이면 정규화 뒤 완전 일치로 **목록의 원본 이름**을 돌려주고(D-19), 목록 밖이면 `_parse_item_use`와 달리 **예외를 던지지 않고** `presence="unknown"`을 정상 반환한다 — SCENE-04가 명시적으로 다루라고 요구하는 정당한 갈래이지 계약 위반이 아니기 때문이다. `Proposal.target`이 새 칸으로 늘었고 `tier` 계산은 한 글자도 안 바뀌었다. `classify()`가 새 `allowed_targets: dict[str,str] | None` 인자를 얻었다 — `None`이면(대상 검사를 안 쓰는 시나리오) 프롬프트에 대상 칸이 아예 안 붙고 결과는 항상 `presence="none"`이다(D-22). `EVENT_SCHEMA_VERSION` 13→14가 `event_log/schema.py`(`ActionClassified.target_name/target_presence/target_kind` + `_require_target_from_schema_14` 검증기)·`rules_core/reducer.py`(`TargetFold`, `GameState.declare_targets`, `action_classified` 분기 갱신)·`session_actor/actor.py`(`RecordActionClassification` 세 칸 + `_prepare_record_action_classification`의 닫힌 목록 검증)에서 **같은 커밋**으로 닫혔다. `tests/test_action_classifier.py`에 19개 시험(빨강→초록, 아래 RED/GREEN 증거 참조)이 이 갈래들을 고정한다.
- **Task 2 (`09d422e`):** `agents/context.py`가 `TARGET_ABSENT_FACT(name)` — 이름 하나를 끼워 넣는 플랫폼 고정 사실 문장 함수를 얻었다(`NO_CHECK_SUMMARY`/`OPENING_CHECK_SUMMARY`와 같은 성격, 거절 문구가 아니라 사실 문장, D-15). `turn/judgments.py`의 `build_narration_facts`가 `extra_facts: tuple[str,...] = ()` 인자를 얻어 플랫폼 사실을 모델의 `facts`보다 앞세워 `SITUATION_FACTS_LIMIT`으로 함께 자른다(기존 호출부 무변경, 회귀 시험으로 고정). `turn/emerged_entities.py`가 `apply_declared_target` — `GameState.declare_targets`를 다시 읽어(ASVS V5) `presence="unknown"`일 때 시나리오의 `improv_people`/`improv_things`를 사람·사물 따로 판단하고(D-16), 허용이면 `RecordEmergedEntity`를 제출(D-14, `EntityAlreadyEmerged`는 성공으로 읽음)하고 금지면 `TARGET_ABSENT_FACT`를 돌려주는 공유 헬퍼를 얻었다. `web/routes_actions.py`의 `declare()`가 `scenario=`+`emerged_entities=`를 처음으로 `build_turn_context`에 넘기고 그 결과(`ctx.scene_entities`)에서 `allowed_targets`를 만들며, `confirm()`/`proceed()` 둘 다 같은 헬퍼로 열림/닫힘을 판단한다. `tests/test_scene_target.py`(신규, 18개)와 `tests/test_web_actions.py`(+7개)가 이 갈래들을 고정한다.
- **Task 3 (`7d4154c`):** `cli/turn_flow.py`가 웹과 같은 방식으로 대상 닫힌 목록을 만들어 `classify()`에 넘기고, `RecordActionClassification`에 같은 세 칸을 남기며, `_proceed_without_check`와 판정 뒤 구간 둘 다 `apply_declared_target`을 부른다. `session_scenario_id`가 `None`인 명령줄 세션은 `DEFAULT_SCENARIO_ID`(well_below)로 명시적으로 떨어진다 — 오프닝이 왜 웹/CLI 예외이고 대상 지목은 왜 아닌지가 코드 주석으로 남았다. `tests/test_scene_target.py`에 CLI 시험 4개가 추가됐다.

## AI Quality Note (per phase context instructions — honest split)

**시험 스위트가 증명한 것(페이크 제공자, `FakeProvider`):** 배선·형태·검증 로직 — `_parse_target`이 침묵/빈값/공백/목록 안(정규화 포함)/목록 밖/`kind` 없음/`kind` 목록 밖을 정확히 갈래대로 처리한다는 것, `classify()`가 `allowed_targets=None`일 때 대상 칸을 완전히 지운다는 것, `apply_declared_target`이 `declare_targets`를 클라이언트 값 대신 다시 읽는다는 것, 웹/CLI 세 자리가 같은 헬퍼로 같은 결과를 낸다는 것, `TARGET_ABSENT_FACT`에 거절 문구가 없다는 것. **페이크 제공자는 이것들을 증명할 수 있을 뿐, 실제 모델이 「사람이 자연어로 지목한 것」을 제대로 사람/사물로 분류하고 목록 안/밖을 실제로 구분하는지는 증명하지 못한다.**

**실제 NIM 제공자로 직접 확인한 것:** `.gptrpg/agents.json`에 설정된 실제 분류기 모델(`nvidia/nemotron-3-super-120b-a12b`, provider `nim`)을 포트 8001 서버가 쓰는 것과 같은 설정으로 직접 호출했다(스크립트 실행, pytest 시험이 아니다 — `NVIDIA_API_KEY`는 `.env.local`에서 로드). `well_below` 시나리오의 실제 캐스트(THREAT_CAST 4명)를 닫힌 목록으로 주고 네 문장을 넣었다:

| 입력 | 실제 모델 결과 |
|---|---|
| "우물지기 이슬에게 요즘 잠을 못 잔 이유를 캐묻는다" | `TargetClaim(name='우물지기 이슬', presence='known', kind=None)` — 목록 안, 정확히 일치 |
| "문 앞에 나타난 낯선 떠돌이 상인에게 말을 건다" | `TargetClaim(name='낯선 떠돌이 상인', presence='unknown', kind='person')` — 목록 밖, 사람으로 정확히 구분 |
| "우물 옆에 놓인 부서진 등불을 살펴본다" | `TargetClaim(name='부서진 등불', presence='unknown', kind='thing')` — 목록 밖, 사물로 정확히 구분 |
| "그냥 하늘을 올려다본다" | `TargetClaim(name=None, presence='none', kind=None)` — 대상 없음, 정확히 침묵 |

네 갈래 모두 기대대로 나왔다 — 실제 모델이 목록 안/밖과 사람/사물을 정확히 구분했다. 이 결과는 **한 번의 관측**이지 회귀 시험이 아니다(모델 제공자 업데이트로 품질이 흔들릴 수 있다) — `coverage.D8`에 `human_judgment: true`로 기록해 두었다. 사용된 모델은 이 프로젝트의 「분류기는 큰 모델이어야 한다」는 기존 관찰(`.gptrpg/agents.json`에 이미 반영됨)과 일치한다.

## Task Commits

1. **Task 1: 분류기에 대상 칸을 더하고, 그 선택을 사건에 남긴다** - `dd8b394` (feat, tdd)
2. **Task 2: 층 밖 지목이 시나리오 선언대로 갈린다 — 허용이면 쌓이고, 금지면 세계가 이야기로 돌려보낸다** - `09d422e` (feat)
3. **Task 3: 명령줄도 같은 커밋에서 닫는다** - `7d4154c` (feat)

**Plan metadata:** (this commit — see `git_commit_metadata` step)

## Files Created/Modified

- `src/gptrpg/agents/action_classifier.py` - `TargetClaim`, `_parse_target`, `NO_TARGET`, `Proposal.target`, `classify(..., allowed_targets=...)`
- `src/gptrpg/agents/prompt_assembly.py` - `build_classifier_prompt(..., allowed_targets=...)` target instruction block
- `src/gptrpg/agents/context.py` - `TARGET_ABSENT_FACT(name)` platform fact function
- `src/gptrpg/event_log/schema.py` - `EVENT_SCHEMA_VERSION` 13→14, `ActionClassified` target three fields + validator
- `src/gptrpg/rules_core/reducer.py` - `TargetFold`, `NO_TARGET_FOLD`, `GameState.declare_targets`, `action_classified` branch update
- `src/gptrpg/session_actor/actor.py` - `RecordActionClassification` target fields, `_prepare_record_action_classification` closed-list validation, `_VALID_TARGET_PRESENCE`
- `src/gptrpg/turn/judgments.py` - `build_narration_facts(..., extra_facts=...)`
- `src/gptrpg/turn/emerged_entities.py` - `apply_declared_target` shared helper
- `src/gptrpg/web/routes_actions.py` - `_current_scenario`, `declare()`/`confirm()`/`proceed()` wiring
- `src/gptrpg/cli/turn_flow.py` - `_current_scenario`, `_turn_flow`/`_proceed_without_check` wiring
- `tests/test_action_classifier.py` (+19 tests) - `_parse_target`/`classify()` target integration
- `tests/test_scene_target.py` (new, 22 tests) - improv gating, adjacency/empty, ordering, D-15 phrasing, CLI parity
- `tests/test_web_actions.py` (+7 tests) - declare/confirm/proceed target-selection integration
- `tests/test_event_schema_migration.py` - schema-version pinning test updated 13→14
- `tests/fixtures/session1_expected_state.json` - `declare_targets: {}` key added for the new `GameState` field

## Decisions Made

See frontmatter `key-decisions` for full reasoning — summary:
- `NO_TARGET` placed in `action_classifier.py` (Python dataclass-default ordering forces `TargetClaim` to be declared before `Proposal`, in the same file).
- Target instruction block reuses the existing "scene entities" prompt block instead of re-rendering the closed list.
- `kind=None` out-of-layer targets: open/closed decision needs both improv axes open, but `RecordEmergedEntity` is never called even when open (structural `person`/`thing`-only constraint) — no arbitrary kind guess, no absent-fact either.
- `declare()`'s `build_turn_context` now gets `scenario=`+`emerged_entities=` (13-04 explicitly deferred this); `confirm()`/`proceed()`'s `build_turn_context` calls stay untouched.
- `apply_declared_target` lives in `turn/emerged_entities.py`, extending 13-04's module rather than a new file — matches the layer-sharing precedent `record_emerged_entities` already set.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Wired `scenario=`/`emerged_entities=`/`allowed_targets` into `declare()`'s `build_turn_context`/`classify()` calls**
- **Found during:** Task 2
- **Issue:** The plan's Task 2 action text scopes itself to `confirm()`/`proceed()` (post-classification judgment). Nothing in Task 1 or Task 2's literal text updates `declare()`'s existing `build_turn_context(...)` call (which had neither `scenario=` nor `emerged_entities=`, per 13-04's deliberate exclusion) or wires `allowed_targets` into its `classify()` call. Without this, the classifier's `allowed_targets` parameter added in Task 1 would never receive a real value in production — the plan's own stated goal ("분류기가 대상을 고른다") would only be testable in isolation, never actually reachable end-to-end. Task 3's own text assumes this wiring already exists ("웹의 `declare()`와 같은 방식으로 `allowed_targets`를 만들어 넘긴다").
- **Fix:** Added `scenario=`/`emerged_entities=` to `declare()`'s `build_turn_context` call, built `allowed_targets` from the resulting `ctx.scene_entities`, and passed it to `classify()`.
- **Files modified:** `src/gptrpg/web/routes_actions.py`
- **Verification:** `tests/test_web_actions.py::test_declare_records_known_target_from_scenario_cast`, `test_declare_silent_target_yields_none_presence`
- **Committed in:** `09d422e`

**2. [Rule 3 - Blocking] `NO_TARGET` moved from the plan's literal placement instruction**
- **Issue:** Plan text says to declare `NO_TARGET` "NO_ITEM_USED와 같은 자리에" (`agents/context.py`, where `NO_ITEM_USED` lives) — but Task 1's `<files>` list excludes `context.py` (reserved for Task 2's `TARGET_ABSENT_FACT`), and more fundamentally, `TargetClaim` is used as a `Proposal` field default, which requires `TargetClaim` to be defined *before* `Proposal` in `action_classifier.py` — a forward reference to a class in a different module wouldn't help here since the marker constant itself doesn't need cross-module sharing the way `NO_ITEM_USED` does (item use is parsed AND rendered from two different modules that both need the constant at import time in a way that doesn't require ordering).
- **Fix:** Declared `NO_TARGET` in `action_classifier.py` instead, following the `NO_CHECK_SIGNAL` precedent already established in the same file (also a classifier-owned reserved marker imported locally by `prompt_assembly.py`).
- **Files modified:** `src/gptrpg/agents/action_classifier.py`
- **Verification:** `tests/test_action_classifier.py` — all target parsing/prompt tests pass with this placement.
- **Committed in:** `dd8b394`

**3. [Rule 3 - Blocking, documented not fixed] `AGENT_ROLES == 5` acceptance criterion is stale**
- Same pre-existing drift 13-03/13-04's own SUMMARYs already documented (`outcome_picker`/`creation_gm` predate this phase). The functional guarantee — no new AI role added by this plan — holds and is independently verified: count is 7 both before and after this plan's three commits.

**4. [Rule 4 - Architectural interpretation, resolved without escalation] `kind=None` out-of-layer target's "허용" branch**
- **Found during:** Task 2 design
- **Issue:** The plan's action text for this branch reads, in sequence: "kind가 None이면 두 값이 모두 참일 때만 허용한다" (gate rule) then, in the very next bullet about the RecordEmergedEntity submission, "kind가 None이면 여기 도달하지 않으므로 항상 값이 있다" — read naively these two sentences appear to contradict each other (the gate explicitly allows kind=None through when both axes are open, yet the submission bullet claims kind=None never reaches submission).
- **Resolution:** `EmergedEntityFold`/`RecordEmergedEntity`'s structural constraint (`_VALID_EMERGED_ENTITY_KINDS = {"person", "thing"}`) makes the two sentences consistent by construction: the "허용" decision (should this target be treated as forbidden or not) is computed independently of whether we can *record* it. When `kind` is `None` and both axes are open, the target is not forbidden (no absent-fact), but it is also never submitted to `RecordEmergedEntity` (that call site literally cannot be reached with `kind=None` without inventing a value the plan explicitly prohibits guessing — "「대충 person으로 본다」 같은 임의 선택을 하지 않는다"). This was resolved through structural analysis rather than escalating to the user, since the codebase's own existing invariant (not a new judgment call) forced the answer.
- **Files modified:** `src/gptrpg/turn/emerged_entities.py`
- **Verification:** `tests/test_scene_target.py::test_improv_kind_none_accumulates_only_when_both_axes_open` (asserts no event, no fact — the "silently allowed, not recorded" outcome).
- **Committed in:** `09d422e`

---

**Total deviations:** 2 auto-fixed (1 missing-critical wiring, 1 file-placement correction), 1 documented pre-existing drift (not this plan's defect), 1 architectural ambiguity resolved via structural analysis. **Impact on plan:** The missing-critical fix is what makes the plan's stated goal ("분류기가 대상을 고른다") actually reachable end-to-end rather than only testable in isolation — no scope creep, it is the plan's own goal. No AI role was added; no acceptance criterion's functional intent failed.

## RED/GREEN pytest evidence (Task 1 acceptance criterion)

**RED — before `TargetClaim`/`_parse_target`/`NO_TARGET` existed** (captured by temporarily restoring `action_classifier.py`/`prompt_assembly.py` to their pre-Task-1 committed content via `git show HEAD:<path>`, per this session's `destructive_git_prohibition` guidance against `git stash`/`git checkout --` for this purpose; restored immediately after capturing):

```
==================================== ERRORS ====================================
_______________ ERROR collecting tests/test_action_classifier.py _______________
ImportError while importing test module '/home/alpha-pi/dev/GPTRPG/tests/test_action_classifier.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
../../.local/share/uv/python/cpython-3.14-linux-aarch64-gnu/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_action_classifier.py:14: in <module>
    from gptrpg.agents.action_classifier import (
E   ImportError: cannot import name 'NO_TARGET' from 'gptrpg.agents.action_classifier' (/home/alpha-pi/dev/GPTRPG/src/gptrpg/agents/action_classifier.py)
=============================== warnings summary ===============================
2 warnings, 1 error in 0.49s
```

**GREEN — with the fix applied (Task 1's committed state, target-only selection):**

```
...................                                                      [100%]
19 passed, 43 deselected, 2 warnings in 0.18s
```

**Full `tests/test_action_classifier.py` after Task 1:** `62 passed`.

## Issues Encountered

- **Known pre-existing full-suite failure, unrelated to this plan:** `tests/test_event_schema_migration.py::test_events_db_v2_records_fold_without_exception_under_schema_6` fails because the untracked local `.gptrpg/events.db` disagrees with its committed fixture. The orchestrator independently confirmed this fails identically at commit `3f7458b`, before any Phase 13 work, and 13-04's own SUMMARY documented the same. Not introduced or affected by this plan.

## Scope Fence Honored

- `.planning/todos/pending/2026-08-26-mobile-status-pane-drawer.md` and `.planning/todos/pending/2026-08-26-creation-host-transfers-on-timeout.md` remain untouched.
- 13-06 (roster screen / `StatusPane` frontend work) was not implemented — `git diff --name-only` confirms zero `frontend/` changes across all three task commits.
- No entity list is ever shown to the player, no re-prompt screen was built, no rejection wording was added — all confirmed by test assertions (`test_target_absent_fact_has_no_system_rejection_phrasing`) and the `master_gm.py` zero-diff check.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `apply_declared_target` and `TARGET_ABSENT_FACT` are the exact primitives 13-06 (roster screen) can build on if it ever needs to explain why a targeted name didn't appear — though 13-06's actual scope (per its own PLAN.md) is the `StatusPane` roster display, which is a pure read of `roster_rows(cast, emerged)` (already built by 13-04) and does not need anything new from this plan.
- `GameState.declare_targets` and the `ActionClassified` schema-14 fields are available for any future phase (e.g. Phase 14's relationship ledger) that wants to know what a player actually pointed at during a turn, independent of the emerged-entities roster.
- The live-provider evidence (`coverage.D8`) is a point-in-time observation, not a repeatable check — if `.gptrpg/agents.json`'s classifier model changes, someone should re-run the equivalent of the four-case script documented in "AI Quality Note" before trusting target-selection quality on the new model.

## Self-Check: PASSED

- `tests/test_scene_target.py` verified present on disk.
- Commits `dd8b394`, `09d422e`, `7d4154c` verified present in `git log --oneline`.
- Full test suite: 1535 passed, 1 pre-existing unrelated failure (documented above), 0 newly introduced failures.
- `lint-imports`: 4 contracts kept, 0 broken.
- `AGENT_ROLES` count: 7, identical before and after this plan's commits (no new AI role).
- `EVENT_SCHEMA_VERSION`: 14, bumped exactly once, reducer/actor changes landed in the same commit (`dd8b394`).
- `git diff -- src/gptrpg/agents/master_gm.py`: 0 lines across all three commits.
- `git diff --name-only -- frontend/` across all three commits: empty.

---
*Phase: 13-scene-opening-and-targets*
*Completed: 2026-08-26*
