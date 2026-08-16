---
phase: 11-rulebook-vocabulary
plan: 07
subsystem: ai
tags: [prompt-assembly, rulebook-vocabulary, resource-axis, none-declaration, korean-narration]

# Dependency graph
requires:
  - phase: 11-03
    provides: "_visible_stats() — form==\"none\" 축을 시트 응답 조립 단계에서 제외하는 서버 쪽 헬퍼(RULE-12). 이 계획은 그 제외 경로가 실제로 작동하는 첫 실제 데이터를 만든다"
  - phase: 11-04
    provides: "Cairn 등록 + check_trigger_mode + MoveDecl.default_stat 옵셔널화 — prompt_assembly._format_moves가 이미 None default_stat을 처리하는 선례를 남겼다"
provides:
  - "던전월드류 룰북의 실제 form=\"none\"/none_kind=\"discretionary\" 축 선언(소지품) — RULE-12를 시험 픽스처가 아니라 저장소 데이터로 실증"
  - "_format_resource_treatment(axes) + RESOURCE_TREATMENT_LINES_LIMIT — 「안 쓴다」 축의 두 갈래(discretionary/absent)를 서로 다른 처리 지침 문장으로 세 프롬프트 조립 함수의 영구 고정 블록에 싣는다(D-08)"
  - "classify()/judge_situation()/narrate()/gather_turn_judgments()의 resource_axes 매개변수(기본값 (), 웹·CLI 실제 호출부는 rulebook.resource_axes를 넘김)"
  - "_format_character_state가 StatEntry.form 여섯 값 전부를 명시적으로 다루는 렌더 갈래"
affects: [phase-12]

# Actuals (#2632)
actuals:
  tokens: 11118
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "프롬프트 조립 함수에 룰북 파생 데이터(resource_axes)를 추가할 때 기본값 ()를 준다 — 기존 호출부·시험을 깨지 않으면서 실제 호출부(web/cli)만 명시적으로 채운다. 값을 실제로 넘겨야 하는 자리가 명확한 소수(routes_actions.py 5곳, turn_flow.py 5곳)로 좁혀진다"
    - "stat.form 여섯 값 명시적 분기 관례(11-01의 StatEntry._validate_form_payload, 11-03의 StatRows)를 진행자 프롬프트 렌더 함수에도 적용 — 신규 형태 추가 시 분기 하나만 늘리면 된다"

key-files:
  created: []
  modified:
    - src/gptrpg/rulebooks/dungeonworld_like.py
    - src/gptrpg/agents/prompt_assembly.py
    - src/gptrpg/agents/action_classifier.py
    - src/gptrpg/agents/situation_judge.py
    - src/gptrpg/agents/master_gm.py
    - src/gptrpg/turn/judgments.py
    - src/gptrpg/web/routes_actions.py
    - src/gptrpg/cli/turn_flow.py
    - tests/test_web_characters.py
    - tests/test_rulebook.py
    - tests/test_prompt_assembly_scenario.py
    - tests/test_agent_context_caps.py
    - tests/test_parallel_judgment.py
    - tests/test_turn_flow_failure.py
    - .planning/REQUIREMENTS.md

key-decisions:
  - "resource_axes를 세 조립 함수(build_classifier_prompt/build_gm_prompt/build_situation_prompt)와 그 호출부(classify/judge_situation/narrate/gather_turn_judgments)에 기본값 ()로 넓혔다 — 필수 인자로 만들면 이 저장소 전역의 프롬프트 조립 호출부(test_narration_isolation.py·test_situation_judge.py·test_adversarial_fence.py·test_narration_guard.py·test_action_classifier.py 등, 이 계획 <files> 목록 밖)가 전부 깨진다. 기본값이 있으면 실제 룰북 데이터를 아는 자리(web/routes_actions.py 5곳, cli/turn_flow.py 5곳)만 명시적으로 rulebook.resource_axes를 넘기면 되고, 그 외 호출부는 한 글자도 안 고쳐도 된다(기존 933→919 통과 시험 전부 무변경 통과)"
  - "_format_scene_entities()는 이번 계획 범위 밖으로 남겼다 — 같은 stat.form 가정 버그(numeric 전제)를 갖고 있지만 Task 3의 <files> 범위는 _format_character_state 하나였다. WINDOWS.md에 todo로 기록해 후속 계획이 놓치지 않게 했다(Deviations 참조)"
  - "named_slots 빈 칸 렌더는 \"이름 없음 (빈 칸 N개)\"으로, 채워진 칸이 있으면 \"이름 장검, 랜턴 (빈 칸 N개)\"으로 통일했다 — 채워진 칸 목록과 빈 칸 개수를 항상 함께 보여줘 진행자가 소지품 칸 여유를 알 수 있게 했다"

patterns-established:
  - "프롬프트 조립 함수의 신규 매개변수는 기본값 ()로 넓혀 호출부 폭발을 막는 관례 — 이번에 5+5개 실제 호출부만 고치고 나머지 수십 개 시험 호출부는 무변경으로 통과했다"

requirements-completed: [RULE-12]

coverage:
  - id: D1
    description: "던전월드류 룰북이 form=\"none\"/none_kind=\"discretionary\" 축(소지품)을 실제로 선언하고, 그 축을 담은 룰북이 등록 검증(11-02)을 통과한다 — RULE-12가 시험 픽스처가 아니라 저장소에 출하되는 실제 데이터로 성립한다"
    requirement: "RULE-12"
    verification:
      - kind: unit
        ref: "tests/test_rulebook.py#test_dungeonworld_resource_axes_are_eight_numeric_and_one_discretionary_none"
        status: pass
      - kind: integration
        ref: "uv run pytest -q (919 passed) — 등록 시점 import가 실패 없이 통과, validate_registered_rulebooks()가 룰북 임포트 시점에 이미 검증"
        status: pass
    human_judgment: false
  - id: D2
    description: "그 선언이 있는 룰북(던전월드류)의 캐릭터 시트 응답에 그 축 이름이 문자열로도 없고, stats 길이가 이전과 같다 — 11-03이 만든 제외 경로가 실제 데이터로 확인된다"
    requirement: "RULE-12"
    verification:
      - kind: unit
        ref: "tests/test_web_characters.py#test_dungeonworld_discretionary_axis_is_absent_from_sheet_response"
        status: pass
      - kind: unit
        ref: "tests/test_web_characters.py#test_dungeonworld_sheet_stat_count_unchanged_by_none_axis"
        status: pass
    human_judgment: false
  - id: D3
    description: "「안 쓴다」의 두 갈래(discretionary/absent)가 AI 진행자에게 서로 다른 처리 지침 문장으로 전달된다 — \"없다\"로 뭉뚱그리지 않는다(D-08). discretionary는 \"서사에는 자유롭게 등장하되 숫자로 세지 않는다\", absent는 \"이 세계에 없다\"로 갈린다"
    verification:
      - kind: unit
        ref: "tests/test_prompt_assembly_scenario.py#test_resource_treatment_discretionary_axis_appears_in_story_but_is_not_counted"
        status: pass
      - kind: unit
        ref: "tests/test_prompt_assembly_scenario.py#test_resource_treatment_absent_axis_tells_gm_the_concept_does_not_exist"
        status: pass
      - kind: unit
        ref: "tests/test_prompt_assembly_scenario.py#test_resource_treatment_two_none_kinds_produce_different_sentences"
        status: pass
      - kind: unit
        ref: "tests/test_prompt_assembly_scenario.py#test_non_none_axes_are_not_in_the_treatment_block"
        status: pass
      - kind: unit
        ref: "tests/test_prompt_assembly_scenario.py#test_resource_treatment_block_omitted_when_rulebook_has_no_none_axes"
        status: pass
    human_judgment: false
  - id: D4
    description: "처리 지침 문장이 룰북 단위로 고정인 영구 고정 블록(system[0])에 들어간다 — 세션 고정 블록(system[1])에는 안 들어간다. 캐싱 순서 규약을 지킨다"
    verification:
      - kind: unit
        ref: "tests/test_prompt_assembly_scenario.py#test_treatment_block_is_in_the_permanent_cached_block"
        status: pass
      - kind: unit
        ref: "tests/test_prompt_assembly_scenario.py#test_build_gm_prompt_system_byte_identical_across_calls_with_same_resource_axes"
        status: pass
    human_judgment: false
  - id: D5
    description: "처리 지침 문장 개수에 명시적 상한(RESOURCE_TREATMENT_LINES_LIMIT=8)이 있고, 상한을 넘으면 조용히 자르지 않고 ContextCapExceeded로 그 자리에서 멈춘다(D-66/ARCH-06)"
    verification:
      - kind: unit
        ref: "tests/test_agent_context_caps.py#test_resource_treatment_lines_over_limit_raises"
        status: pass
      - kind: unit
        ref: "tests/test_agent_context_caps.py#test_resource_treatment_lines_at_limit_does_not_raise"
        status: pass
    human_judgment: false
  - id: D6
    description: "진행자 프롬프트의 캐릭터 상태 문자열이 여섯 표현 형태(numeric/clock/named_slots/tag_list/usage_die/none)를 전부 다루고, None인 칸을 그대로 찍거나 예외를 내지 않는다. form==\"none\"인 값은 문자열에 아예 안 들어간다"
    requirement: "RULE-11"
    verification:
      - kind: unit
        ref: "tests/test_prompt_assembly_scenario.py#test_character_state_renders_all_six_forms"
        status: pass
      - kind: unit
        ref: "tests/test_prompt_assembly_scenario.py#test_character_state_never_prints_the_word_none"
        status: pass
      - kind: unit
        ref: "tests/test_prompt_assembly_scenario.py#test_none_form_stat_is_skipped_in_character_state"
        status: pass
      - kind: unit
        ref: "tests/test_prompt_assembly_scenario.py#test_character_state_numeric_form_matches_pre_11_07_string"
        status: pass
    human_judgment: false
  - id: D7
    description: "「어떻게 다루는가」 문장이 실제 모델 응답의 서사를 의도대로 바꾸는지는 이 계획의 자동 시험이 증명하지 않는다 — 프롬프트에 들어갔다는 것까지가 자동 단언 범위다"
    verification: []
    human_judgment: true
    rationale: "이 저장소의 자동 시험은 전부 가짜 제공자를 쓴다 — 프롬프트가 문자열로 어떻게 조립되는지는 검증하지만 실제 모델이 그 지시를 따르는지는 원리적으로 검증하지 못한다. 이 계획은 조립된 프롬프트 문자열을 직접 읽고 뉘앙스를 판단했지만(아래 본문 참조), 실제 모델로 검증하지 않았다는 사실을 명시한다. 오케스트레이터가 단계 검증에서 실제 모델로 확인할 것."

# Metrics
duration: ~90min
completed: 2026-08-17
status: complete
---

# Phase 11 Plan 07: 「안 쓴다」를 실제 데이터로 선언하고, AI에게 「어떻게 다루는가」를 알려준다 Summary

**던전월드류가 「소지품」을 `form="none"`/`none_kind="discretionary"`로 실제 선언해 RULE-12를 저장소 데이터로 실증했고, `_format_resource_treatment()`가 그 축의 처리 지침을 세 프롬프트 조립 함수의 영구 고정 블록에 싣고, `_format_character_state`가 캐릭터 상태 여섯 표현 형태를 전부 다룬다**

## Performance

- **Duration:** ~90분
- **Completed:** 2026-08-17
- **Tasks:** 3 (전부 자동)
- **Files modified:** 15개 (신규 파일 없음)

## Accomplishments

- `src/gptrpg/rulebooks/dungeonworld_like.py`의 `DUNGEONWORLD_RESOURCE_AXES`에 「소지품」(`form="none"`, `none_kind="discretionary"`) 축이 추가됐다 — RULE-12가 시험 픽스처가 아니라 저장소에 출하되는 실제 룰북 데이터에서 성립한다. 브람의 시트 응답은 완전히 무변화(`stats` 길이·본문 문자열 모두)다.
- `agents/prompt_assembly.py`에 `RESOURCE_TREATMENT_LINES_LIMIT=8`과 `_format_resource_treatment(axes)`가 신설됐다 — `form == "none"`인 축만 골라 `discretionary`(「서사에는 자유롭게 등장하되 숫자로 세거나 갖고 있는지를 따지지 않는다」)와 `absent`(「이 세계에 없다, 서사에도 등장시키지 않는다」) 두 갈래를 서로 다른 문장으로 낸다. 상한을 넘으면 조용히 자르지 않고 `ContextCapExceeded`를 던진다. 세 프롬프트 조립 함수(`build_classifier_prompt`/`build_gm_prompt`/`build_situation_prompt`) 전부 이 블록을 영구 고정 블록(`system[0]`)에 붙인다 — 세션 고정 블록에는 안 들어간다.
- `resource_axes` 매개변수(기본값 `()`)가 `classify()`/`judge_situation()`/`narrate()`/`gather_turn_judgments()`로 넓어졌고, `web/routes_actions.py`(5곳)·`cli/turn_flow.py`(5곳)의 실제 호출부가 `rulebook.resource_axes`를 명시적으로 넘긴다. 기본값 덕분에 이 계획 밖의 수십 개 기존 호출부·시험은 한 글자도 안 고쳐도 됐다.
- `agents/prompt_assembly.py`의 `_format_character_state`가 `stat.form` 여섯 값(`numeric`/`clock`/`named_slots`/`tag_list`/`usage_die`/`none`)에 대한 명시적 분기로 넓어졌다 — `numeric`은 기존 문자열 그대로(회귀 없음), `clock`은 「현재/최대칸」, `named_slots`는 채워진 칸 이름 + 빈 칸 개수, `tag_list`는 태그 나열(없으면 「없음」), `usage_die`는 「dN」 또는 소진 시 「소진」, `none`은 아예 건너뛴다 — 「안 쓴다」로 선언된 것이 값처럼 진행자 문맥에 새지 않는다.

## Task Commits

각 태스크를 개별 커밋했다:

1. **Task 1: 던전월드류 룰북이 「소지품을 규칙으로 안 센다」를 실제로 선언한다** — `70abda6` (feat)
2. **Task 2: AI 진행자에게 「어떻게 다루는가」를 영구 고정 블록으로 알려준다 (D-08)** — `6ab3d11` (feat)
3. **Task 3: 진행자에게 가는 캐릭터 상태 문자열이 여섯 형태를 전부 다룬다** — `f00deb4` (feat)

**Plan metadata:** 이 커밋(SUMMARY.md 등)

## Files Created/Modified

- `src/gptrpg/rulebooks/dungeonworld_like.py` - 「소지품」 `form="none"`/`none_kind="discretionary"` 축 신설, D-09를 지키는 주석
- `src/gptrpg/agents/prompt_assembly.py` - `RESOURCE_TREATMENT_LINES_LIMIT`·`_format_resource_treatment()` 신설, 세 조립 함수에 `resource_axes` 매개변수(기본값 `()`) 추가, `_format_character_state` 여섯 형태 분기로 재작성
- `src/gptrpg/agents/action_classifier.py` - `classify()`에 `resource_axes` 매개변수 추가, `build_classifier_prompt`로 전달
- `src/gptrpg/agents/situation_judge.py` - `judge_situation()`에 `resource_axes` 매개변수 추가, `build_situation_prompt`로 전달
- `src/gptrpg/agents/master_gm.py` - `narrate()`에 `resource_axes` 매개변수 추가, 첫 호출·재생성 호출 둘 다에 전달
- `src/gptrpg/turn/judgments.py` - `gather_turn_judgments()`에 `resource_axes` 매개변수 추가, `judge_situation` 호출에만 전달
- `src/gptrpg/web/routes_actions.py` - `declare()`/`confirm()`/`proceed()` 다섯 호출부에 `resource_axes=rulebook.resource_axes` 추가
- `src/gptrpg/cli/turn_flow.py` - `_turn_flow()`/`_proceed_without_check()` 다섯 호출부에 `resource_axes=rulebook.resource_axes` 추가
- `tests/test_web_characters.py` - `test_dungeonworld_discretionary_axis_is_absent_from_sheet_response`·`test_dungeonworld_sheet_stat_count_unchanged_by_none_axis` 신설
- `tests/test_rulebook.py` - `test_dungeonworld_resource_axes_are_all_numeric_form`을 아홉 축(numeric 8 + none 1) 실증에 맞게 재고정
- `tests/test_prompt_assembly_scenario.py` - 처리 지침 시험 8건 + 캐릭터 상태 여섯 형태 시험 6건 신설
- `tests/test_agent_context_caps.py` - `test_resource_treatment_lines_over_limit_raises`·`test_resource_treatment_lines_at_limit_does_not_raise` 신설
- `tests/test_parallel_judgment.py` - `_stub_judge_situation` 이중체 두 곳에 `resource_axes=()` 기본값 추가(구조적 불가피, Rule 3)
- `tests/test_turn_flow_failure.py` - `_stub_narrate_emits_one_then_raises` 이중체에 `resource_axes=()` 기본값 추가(구조적 불가피, Rule 3)
- `.planning/REQUIREMENTS.md` - RULE-11 진행 노트를 3/6(numeric·named_slots·none)으로 갱신, RULE-12 완료 근거에 11-07의 실제 데이터 실증과 D-08 처리 지침을 추가(체크박스는 둘 다 무변경 — RULE-11은 `[ ]`, RULE-12는 이미 `[x]`)

## Decisions Made

- **`resource_axes`를 기본값 `()`인 선택 매개변수로 넓혔다.** 필수 인자로 만들면 이 저장소 전역의 프롬프트 조립 호출부(이 계획 `<files>` 목록 밖의 `test_narration_isolation.py`·`test_situation_judge.py`·`test_adversarial_fence.py`·`test_narration_guard.py`·`test_action_classifier.py` 등)가 전부 깨진다. 기본값이 있으면 실제 룰북 데이터를 아는 자리(웹 5곳·CLI 5곳)만 명시적으로 채우면 되고, 나머지는 한 글자도 안 고쳐도 된다 — 두 이중체(`test_parallel_judgment.py`·`test_turn_flow_failure.py`)만 새 키워드 인자를 흡수하도록 구조적으로 불가피하게 고쳤다(Rule 3, 아래 참조).
- **`_format_scene_entities()`는 손대지 않았다.** 이 함수도 `f"{stat.name} {stat.current}"`로 numeric 형태를 전제해 같은 버그를 잠재적으로 갖고 있지만, Task 3의 `<files>` 범위는 `_format_character_state` 하나였다. 저장소 데이터에 아직 non-numeric 형태를 쓰는 장면 등장 개체(`scene_entities`)가 없어 지금 당장 실제로 깨지지는 않지만, WINDOWS.md에 todo로 기록해 후속 계획이 놓치지 않게 했다(아래 Deviations).
- **named_slots 빈 칸 렌더를 "이름 채워진칸들 (빈 칸 N개)"로 통일했다.** 채워진 칸이 하나도 없어도 "이름 없음 (빈 칸 N개)"로 렌더해 채워진 칸 목록과 빈 칸 개수를 항상 함께 보여준다 — 진행자가 소지품 칸 여유를 알 수 있게 했다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `test_dungeonworld_resource_axes_are_all_numeric_form`이 Task 1이 만든 아홉 번째 축과 어긋나 실패**
- **Found during:** Task 1 검증(`uv run pytest tests/test_web_characters.py tests/test_rulebook.py -q`)
- **Issue:** 이 시험은 11-01 시점 상태("여덟 축 전부 numeric")를 그대로 단언하고 있었다 — Task 1이 아홉 번째 축(소지품, `form="none"`)을 의도적으로 추가하면서 이 시험이 실패했다.
- **Fix:** 함수명·본문을 `test_dungeonworld_resource_axes_are_eight_numeric_and_one_discretionary_none`으로 재작성해 새 사실(8 numeric + 1 discretionary-none)을 단언하도록 재고정했다.
- **Files modified:** `tests/test_rulebook.py`
- **Verification:** `uv run pytest tests/test_web_characters.py tests/test_rulebook.py -q` → 74 passed
- **Committed in:** `70abda6` (Task 1 커밋)

**2. [Rule 3 - Blocking] `resource_axes` 매개변수 추가로 두 이중체(테스트 더블)의 엄격한 키워드 시그니처가 깨짐**
- **Found during:** Task 2 이후 `uv run pytest -q` 전체 실행
- **Issue:** `tests/test_parallel_judgment.py`의 `_stub_judge_situation`(2곳)과 `tests/test_turn_flow_failure.py`의 `_stub_narrate_emits_one_then_raises`가 `monkeypatch.setattr`로 실제 함수 이름을 대체하는데, `gather_turn_judgments`/`narrate`가 이제 항상 `resource_axes=resource_axes`(기본값이라도)를 keyword로 넘기면서 `TypeError: got an unexpected keyword argument 'resource_axes'`가 났다. 이 두 파일은 계획 `<files>` 목록 밖이지만, `resource_axes` 매개변수 추가라는 구조적 변화가 이 저장소 어디에나 있는 이중체 관례에 그대로 영향을 미쳤다.
- **Fix:** 세 이중체 함수 시그니처에 `resource_axes=()` 기본값을 추가했다.
- **Files modified:** `tests/test_parallel_judgment.py`, `tests/test_turn_flow_failure.py`
- **Verification:** `uv run pytest -q` → 919 passed(전체 초록)
- **Committed in:** `6ab3d11` (Task 2 커밋)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** 둘 다 계획 자신의 `<verify>`(`uv run pytest -q` 전체 초록)가 요구하는 최소 조건을 충족하기 위해 구조적으로 불가피했다. 범위 이탈이 아니다.

## Issues Encountered

**`_format_scene_entities()`가 `_format_character_state`와 같은 numeric 전제 버그를 잠재적으로 갖고 있다 — 이 계획 범위 밖, WINDOWS.md에 todo로 기록.**

`agents/prompt_assembly.py`의 `_format_scene_entities`(장면에 등장한 다른 개체들을 렌더)는 여전히 `f"{stat.name} {stat.current}"`로 `numeric` 형태만 전제한다. Task 3의 `<files>` 목록은 `_format_character_state`만 지정했고, 지금 저장소 데이터(`THREAT_CAST` 등)에는 non-numeric 형태를 쓰는 장면 등장 개체가 아직 없어 실제로는 안 깨진다. 다만 후속 계획이 clock/tag_list/usage_die 형태를 실제 등록 데이터에 넣으면(RULE-11의 남은 3/6) 이 함수도 같은 이유로 손봐야 한다 — `.planning/WINDOWS.md`에 kind=todo로 기록했다(entry id 6).

## 프롬프트 문자열을 직접 읽고 판단한 내용

`_format_resource_treatment`가 실제로 만드는 두 문장을 조립된 프롬프트 문자열에서 직접 확인했다(`build_gm_prompt`/`build_classifier_prompt`/`build_situation_prompt` 세 곳 모두 동일한 두 줄이 삽입됨):

- `discretionary`: "소지품: 이 개념은 규칙으로 세지 않는다. 서사에는 자유롭게 등장시켜도 되지만, 숫자로 세거나 갖고 있는지를 따지지 않는다."
- `absent`: "영혼: 이 개념은 이 세계에 없다. 서사에도 등장시키지 않는다."

**판단:** 두 문장이 서로 다른 지시를 명확히 전달한다고 본다 — `discretionary` 쪽은 "서사에 등장해도 된다"와 "숫자로 세지 않는다/갖고 있는지 따지지 않는다"를 한 문장 안에 함께 넣어, 모델이 "소지품 개념이 없다"로 오독할 여지를 줄였다. 특히 "갖고 있는지를 따지지 않는다"가 D-09가 막으려는 실패(진행자가 "그건 갖고 있지 않습니다"로 장면을 끊는 것)를 직접 겨냥한다. `absent` 쪽은 "이 세계에 없다"+"서사에도 등장시키지 않는다"로 등장 자체를 막는다는 것이 분명하다.

**이 지시를 실제 모델로 검증하지 않았다.** 이 저장소의 자동 시험은 전부 가짜 제공자를 쓴다 — 조립된 문자열이 예상한 두 문장을 담고 있는지, 영구 고정 블록에 있는지, 캐싱이 안 깨지는지까지가 자동 단언 범위다. 실제 모델이 이 문장을 읽고 "소지품에 없는 것을 쓰겠다"는 판단 경로를 만들지 않는지, "갖고 있는지 따지지 않는다"를 진짜로 지키는지는 검증하지 않았다. 오케스트레이터가 단계 검증에서 실제 모델로 확인해야 한다.

## User Setup Required

None - 외부 서비스 설정 불필요.

## Next Phase Readiness

- RULE-12는 이 계획으로 시험 픽스처가 아니라 실제 데이터 실증까지 완전히 끝났다 — 체크박스는 이미 `[x]`였고, 근거 문단만 갱신했다.
- RULE-11은 3/6(numeric·named_slots·none)까지 실제 등록 데이터로 실증됐다 — 남은 셋(clock/tag_list/usage_die)은 화면 렌더 갈래(11-03)와 진행자 프롬프트 렌더 갈래(이번 계획) 둘 다 이미 준비돼 있지만, 실제로 그 형태를 선언·영구 등록하는 룰북이 아직 없다. 후속 계획이 그 형태들을 실제 데이터로 등록하면 `_format_scene_entities`의 같은 버그(WINDOWS.md entry 6)도 함께 손봐야 한다.
- Phase 11(룰북 표현 어휘 확장)의 계획 7개가 전부 끝났다 — `.planning/STATE.md`를 Phase 11 완료로 갱신한다.
- 블로커 없음.

## Self-Check: PASSED

- 파일 존재: `src/gptrpg/rulebooks/dungeonworld_like.py`, `src/gptrpg/agents/prompt_assembly.py`, `src/gptrpg/agents/action_classifier.py`, `src/gptrpg/agents/situation_judge.py`, `src/gptrpg/agents/master_gm.py`, `src/gptrpg/turn/judgments.py`, `src/gptrpg/web/routes_actions.py`, `src/gptrpg/cli/turn_flow.py`, `tests/test_web_characters.py`, `tests/test_rulebook.py`, `tests/test_prompt_assembly_scenario.py`, `tests/test_agent_context_caps.py`, `tests/test_parallel_judgment.py`, `tests/test_turn_flow_failure.py` 전부 확인됨
- 커밋 존재: `70abda6`, `6ab3d11`, `f00deb4` 전부 `git log --oneline --all`에서 확인됨
- 마감 전 재검증: `uv run pytest -q` 919 passed, `uv run lint-imports` 4 kept/0 broken, `cd frontend && npx vitest run` 4 passed
- 브람 시트 응답 본문에 「소지품」 없음 확인: `test_dungeonworld_discretionary_axis_is_absent_from_sheet_response` pass

---
*Phase: 11-rulebook-vocabulary*
*Completed: 2026-08-17*
