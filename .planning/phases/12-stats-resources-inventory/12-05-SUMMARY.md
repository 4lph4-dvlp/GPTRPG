---
phase: 12-stats-resources-inventory
plan: 05
subsystem: agents
tags: [dataclass-refactor, prompt-assembly, event-sourcing, fastapi]

requires:
  - phase: 12-stats-resources-inventory
    provides: "resource_change.py의 resolve_character_stats(RULE-06 접기 함수) — 이 계획이 파티 전원에 그대로 재사용"
provides:
  - "TurnContext.party_state(tuple[Entity, ...]) + actor_character_id(str | None) — character_state 단일 칸을 대체"
  - "NarrationFacts도 같은 두 칸으로 전환"
  - "PARTY_MEMBER_LIMIT=8 + ActorNotInParty 예외(agents/context.py)"
  - "actor_stats(ctx) — party_state에서 행위자 한 명을 뽑는 파생 함수(prompt_assembly.py)"
  - "_format_party_state + _session_block_text_with_party — 상황판단·서술 전용 파티 렌더러/조립 함수"
  - "_session_block_text — 분류기 전용, actor_stats(ctx)만 렌더링(D-17 분기)"
  - "web/routes_actions.py::_current_party_state — 세션 파티 전원을 접은 지금 값으로 조립"
  - "build_turn_context(party_state=, actor_character_id=) — character_stats 단일 인자를 대체"
affects: [12-06-discretionary-ruling, 12-07-web-ui, 13-regression-tests, 14-memory]

actuals:
  tokens: 18177
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "일차 개념 승격(promote) — 「행위자 한 명의 상태」를 별도 칸으로 나란히 두지 않고 「파티 전원 + 파생 조회 함수」로 재구성해, 두 값이 어긋날 자리를 구조적으로 없앤다"
    - "역할별 조립 함수 명시적 분기 — 같은 함수를 공유하던 두 소비처(분류기/상황판단)를 새 함수로 가르고, 도크스트링이 서로를 지목한다(_clock_judge_session_block_text가 이미 세운 관례를 재사용)"
    - "순환 import 회피용 로직 중복 + 상호 참조 주석 — routes_characters.py의 _current_stats를 import 못 하는 자리에서, 같은 결합 규칙을 독립적으로 반복하고 두 도크스트링이 서로를 지목해 갈림을 막는다"

key-files:
  created: []
  modified:
    - src/gptrpg/agents/context.py
    - src/gptrpg/agents/prompt_assembly.py
    - src/gptrpg/turn/context.py
    - src/gptrpg/turn/judgments.py
    - src/gptrpg/web/routes_actions.py
    - src/gptrpg/cli/turn_flow.py
    - tests/test_agent_context_caps.py
    - tests/test_prompt_assembly_scenario.py
    - tests/test_narration_isolation.py
    - tests/test_turn_tracer.py
    - tests/test_action_classifier.py
    - tests/test_web_actions.py
    - tests/test_adversarial_fence.py
    - tests/test_agents_retry.py
    - tests/test_master_gm.py
    - tests/test_measurement.py
    - tests/test_narration_guard.py
    - tests/test_parallel_judgment.py
    - tests/test_scene_entity_judge.py
    - tests/test_situation_judge.py

key-decisions:
  - "actor_stats(ctx)를 agents/prompt_assembly.py에 정의(계획 원문 그대로) — 하지만 ActorNotInParty를 실제로 던지는 행동 시험은 tests/test_agent_context_caps.py(Task 1의 파일)에 넣었다. Task 1 acceptance criteria가 '시험이 있다'를 요구하는데 actor_stats 자체는 Task 2 산출물이라, 두 커밋에 걸쳐 완결된다"
  - "web/routes_actions.py::_current_party_state가 파티 구성원의 entity_id를 짧은 캐릭터 식별자(bram)로 다시 쓴다 — characters_data.py의 긴 형태(player.bram)를 그대로 두면 actor_stats(ctx)의 entity_id==actor_character_id 완전 일치 조회가 identity.character_id(짧은 형태)와 어긋나 항상 ActorNotInParty가 난다"
  - "_current_stats(routes_characters.py)를 import하지 않고 같은 결합 규칙을 routes_actions.py에 독립적으로 반복 — routes_characters.py가 이미 routes_actions.py를 import하므로 반대 방향 import는 순환 import가 된다. 계획이 제시한 두 대안(옮기거나 주석으로 못박거나) 중 후자를 택했다"

patterns-established:
  - "12-05가 처음 실증: 같은 조립 함수를 공유하던 두 소비처를 가를 때, 새 함수 이름에 '_with_party' 같은 접미사를 붙이고 원래 함수는 좁은 쪽(더 제한적인 역할)이 그대로 쓰도록 남긴다 — 호출부 diff가 최소화된다"

requirements-completed: [RULE-08]

coverage:
  - id: D1
    description: "서술하는 진행자와 상황 판단자가 파티 전원의 상태를 본다 — 지금 행동한 사람 하나가 아니다"
    requirement: "RULE-08"
    verification:
      - kind: unit
        ref: "tests/test_prompt_assembly_scenario.py#test_situation_and_gm_prompts_include_all_four_party_member_names"
        status: pass
      - kind: unit
        ref: "tests/test_web_actions.py#test_next_turn_gm_prompt_reflects_folded_resource_change_not_starting_value"
        status: pass
    human_judgment: false
  - id: D2
    description: "분류기 프롬프트에 다른 캐릭터의 상태가 들어 있지 않다 — 두 갈래가 같은 조립 함수를 공유하던 구조를 명시적으로 갈랐다"
    requirement: "RULE-08"
    verification:
      - kind: unit
        ref: "tests/test_prompt_assembly_scenario.py#test_classifier_prompt_excludes_non_actor_party_members_names_and_axes"
        status: pass
    human_judgment: false
  - id: D3
    description: "장면 대상 판단과 시계 판단도 파티 상태를 받지 않는다 — 각자의 문맥 타입에 그 칸이 아예 없다"
    verification:
      - kind: unit
        ref: "tests/test_agent_context_caps.py#test_clock_judge_context_has_no_party_state_or_scene_entities_field"
        status: pass
      - kind: unit
        ref: "tests/test_agent_context_caps.py#test_entity_judge_context_has_no_clock_state_or_party_state_field"
        status: pass
    human_judgment: false
  - id: D4
    description: "파티 구성원 각각의 상태가 여섯 표현 형태 전부에서 지금과 같은 문자열로 나온다 — 11-07 렌더러 재사용, 새로 안 만든다"
    verification:
      - kind: unit
        ref: "git diff (프롬프트 assembly.py) — _format_character_state 함수 본문 변경 줄 없음"
        status: pass
    human_judgment: false
  - id: D5
    description: "웹과 명령줄 두 호출부가 같은 자리에서 같은 모양으로 파티 상태를 넘긴다"
    requirement: "RULE-08"
    verification:
      - kind: integration
        ref: "tests/test_web_actions.py#test_party_state_axis_value_matches_character_sheet_response"
        status: pass
      - kind: integration
        ref: "tests/test_turn_tracer.py (CLI 회귀 전체 통과)"
        status: pass
    human_judgment: false
  - id: D6
    description: "파티 상태에 담기는 값이 「접은 지금 값」이다 — 파이썬 상수 시작값이 아니다"
    requirement: "RULE-08"
    verification:
      - kind: integration
        ref: "tests/test_web_actions.py#test_next_turn_gm_prompt_reflects_folded_resource_change_not_starting_value"
        status: pass
    human_judgment: false
  - id: D7
    description: "파티가 비어 있어도(구성원 0명) 프롬프트 조립이 예외 없이 끝나고 「없음」 자리표시자가 나온다"
    verification:
      - kind: unit
        ref: "tests/test_prompt_assembly_scenario.py#test_all_three_prompts_assemble_without_exception_at_any_party_size[0]"
        status: pass
    human_judgment: false
  - id: D8
    description: "행위자 식별자가 파티 목록에 없는 이름이면 조용히 빈 상태로 넘어가지 않고 예외로 멈춘다"
    verification:
      - kind: unit
        ref: "tests/test_agent_context_caps.py#test_actor_stats_raises_actor_not_in_party_when_id_missing_from_party"
        status: pass
      - kind: unit
        ref: "tests/test_agent_context_caps.py#test_actor_stats_raises_actor_not_in_party_when_id_none_but_party_nonempty"
        status: pass
    human_judgment: false
  - id: D9
    description: "파티 인원에 상한이 있고 그 상한을 넘기면 예외로 멈춘다"
    verification:
      - kind: unit
        ref: "tests/test_agent_context_caps.py#test_turn_context_raises_context_cap_exceeded_over_party_member_limit"
        status: pass
      - kind: unit
        ref: "tests/test_agent_context_caps.py#test_narration_facts_raises_context_cap_exceeded_over_party_member_limit"
        status: pass
    human_judgment: false

duration: ~35분 (계획 파일·기존 코드 조사 포함 실행 세션 기준)
completed: 2026-08-17
status: complete
---

# Phase 12 Plan 5: 파티 전원 상태 주입 Summary

**`TurnContext`/`NarrationFacts`의 「행동한 사람 하나」 칸을 「파티 전원 + 행위자 파생 조회」로 재구성하고, 분류기·상황판단·서술 세 소비처가 각자 다른 것을 받도록 프롬프트 조립 함수를 명시적으로 갈랐다 — 세션1에서 AI가 네 명을 한 사람으로 인식한 사고의 코드 쪽 원인을 없앴다.**

## Performance

- **Duration:** 약 35분 (기존 코드·테스트 전수 조사 포함)
- **Tasks:** 3/3
- **Files modified:** 20개 (신규 파일 없음)

## Accomplishments

- **파티가 일차 개념, 행위자는 파생값** — `TurnContext.character_state`(행위자 한 명의 상태값 튜플)를 `party_state: tuple[Entity, ...]` + `actor_character_id: str | None` 두 칸으로 재구성했다. 「행위자 한 명의 상태」는 이제 `agents.prompt_assembly.actor_stats(ctx)`가 매번 파티에서 뽑아내는 파생값이다 — 두 값을 나란히 저장하지 않으므로 어긋날 자리가 구조적으로 사라졌다(12-RESEARCH.md가 권고한 "나란히 추가" 대안을 명시적으로 기각한 근거는 계획 원문의 `assumption_delta_decision` 절 참조).
- **분류기와 상황판단의 갈림** — 예전에는 `build_classifier_prompt`와 `build_situation_prompt`가 같은 `_session_block_text(ctx)`를 공유했다. 이제 `_session_block_text`(분류기 전용)는 `actor_stats(ctx)`로 행위자 한 명만, 새 `_session_block_text_with_party`(상황판단 전용)는 `_format_party_state(ctx.party_state)`로 파티 전원을 렌더링한다. 서술(`build_gm_prompt`)의 `_narration_session_block_text`도 같은 이유로 파티 전원을 받도록 바뀌었다.
- **여섯 형태 렌더러 재사용** — `_format_party_state`가 구성원마다 기존 `_format_character_state`를 그대로 불러 표시 이름과 줄로 잇는다(`_format_scene_entities`와 같은 모양). `_format_character_state` 자체의 함수 본문은 이 계획에서 한 글자도 안 바뀌었다(`git diff`로 확인 가능).
- **누출 방지 시험** — 파티 넷, 각자 고유한 축 이름을 가진 픽스처로 「분류기 프롬프트에 행위자가 아닌 세 명의 표시 이름·고유 축 이름이 하나도 없다」를 문자열 검색으로 잡는 시험을 신설했다(D-17 핵심 그물). 파티 크기 0·1·2·4 매개변수화 시험으로 「한 명 전제가 되살아나면 즉시 빨개진다」는 회귀 방지 그물도 세웠다.
- **웹의 두 호출부** — `web/routes_actions.py`에 `_current_party_state(store, session_id)`를 신설해 세션의 캐릭터 전원을 `resolve_character_stats`(12-01)로 접은 지금 값으로 조립한다. `confirm()`과 `proceed()` 둘 다 `build_turn_context(party_state=..., actor_character_id=identity.character_id, ...)`로 부른다 — 하나만 고치면 "굴린 턴은 파티를 보고 안 굴린 턴은 못 보는" 어긋남이 생긴다는 것이 계획이 지목한 함정이었다.
- **CLI는 회귀 없음** — `cli/turn_flow.py`의 세 `build_turn_context` 호출부는 새 인자를 넘기지 않는다. 기본값(`party_state=None, actor_character_id=None`)이 예시 개체 하나짜리 파티를 채워 기존 동작을 그대로 유지한다.
- **자원 변화가 실제로 반영됨을 결정론적으로 증명** — 자원을 깎는 `resource_changed` 사건을 하나 넣은 세션에서 다음 턴의 진행자 프롬프트에 깎인 값이 나오고 시작값은 안 나온다는 것을, 실제 다이스가 개입하는 HTTP `confirm()` 왕복이 아니라 `_current_party_state` → `build_turn_context` → `build_narration_facts` → `build_gm_prompt`를 직접 호출해 결정론적으로 확인했다. 캐릭터 시트 응답(`routes_characters.py`)과 파티 상태(`routes_actions.py`)가 같은 축에서 같은 값을 보여준다는 것도 별도 시험으로 확인했다.

## Task Commits

1. **Task 1: 파티 전원을 일차 표현으로 올리고, 행위자 한 명을 그것에서 뽑아내는 값으로 내린다** — `387e791` (feat)
2. **Task 2: 분류기와 상황 판단이 공유하던 조립 함수를 명시적으로 가른다 — 분류기는 파티를 못 본다 (D-17)** — `9148c06` (feat)
3. **Task 3: 웹과 명령줄 두 호출부가 같은 모양으로 파티의 「지금 값」을 넘긴다** — `6a8884b` (feat)

**Plan metadata:** (이 커밋 — docs)

## Files Created/Modified

- `src/gptrpg/agents/context.py` — `TurnContext.party_state`/`actor_character_id`, `NarrationFacts`도 같은 두 칸, `PARTY_MEMBER_LIMIT=8`, `ActorNotInParty`, `TURN_CONTEXT_FIELD_NAMES` 다섯 칸으로 재고정
- `src/gptrpg/agents/prompt_assembly.py` — `actor_stats`, `_format_party_state`, `_session_block_text_with_party` 신설. `_session_block_text`(분류기 전용)·`_narration_session_block_text`(서술)가 새 파생/렌더 함수를 쓰도록 재작성. `build_situation_prompt`가 `_session_block_text_with_party`를 부르도록 변경
- `src/gptrpg/turn/context.py` — `build_turn_context(party_state=, actor_character_id=)`. 인자 없이 부르면 예시 개체 하나짜리 파티가 기본값
- `src/gptrpg/turn/judgments.py` — `build_narration_facts`가 `party_state`/`actor_character_id`를 그대로 옮김
- `src/gptrpg/web/routes_actions.py` — `_current_party_state` 신설(세션 파티 전원을 접은 지금 값으로 조립). `declare()`/`confirm()`/`proceed()` 세 호출부 모두 새 인자로 전환
- `src/gptrpg/cli/turn_flow.py` — 호출부 세 곳에 "왜 파티를 안 넘기는가" 주석만 추가, 동작 무변경
- `tests/test_agent_context_caps.py` — 파티 상한(8/9) 시험, `TurnContext` 다섯 칸 고정 재확인, `actor_stats`/`ActorNotInParty` 행동 시험 신설
- `tests/test_prompt_assembly_scenario.py` — 분류기 누출 방지 시험(파티 넷, 고유 축 이름), 상황판단·서술 파티 전원 포함 시험, 파티 크기 0/1/2/4 매개변수화 시험
- `tests/test_narration_isolation.py`, `tests/test_action_classifier.py` — 필드명 전환
- `tests/test_turn_tracer.py` — `TurnContext` 직접 생성 자리 필드명 전환(전체 CLI 회귀 계속 통과)
- `tests/test_web_actions.py` — 자원 변화 반영·시트-파티 값 일치 결정론적 시험 2건 신설
- `tests/test_adversarial_fence.py`, `test_agents_retry.py`, `test_master_gm.py`, `test_measurement.py`, `test_narration_guard.py`, `test_parallel_judgment.py`, `test_scene_entity_judge.py`, `test_situation_judge.py` — 필드명 전환(기계적, 시험 의도 무변경). `test_narration_guard.py`는 비어 있지 않은 캐릭터 상태 픽스처를 단일 구성원 파티로 재구성. `test_situation_judge.py`의 `NarrationFacts` 필드 집합 하드코딩 단언도 새 다섯 이름으로 갱신

## Decisions Made

- **`actor_stats`의 위치와 시험의 분리(Task 1 acceptance criteria 재현 문제 해소).** 계획 원문의 artifacts 표는 `actor_stats`를 `prompt_assembly.py`(Task 2)에 명시했고, Task 2의 자체 acceptance criteria도 `def actor_stats`가 그 파일에 문자 그대로 있어야 한다고 못박는다(grep 검사). 그런데 Task 1의 acceptance criteria는 "actor_character_id가 파티에 없으면 ActorNotInParty가 난다는 시험이 있다"를 요구한다 — 이 둘을 동시에 만족하려면 함수는 Task 2에, 그 함수를 실제로 호출하는 행동 시험은 Task 1이 이미 다루는 `tests/test_agent_context_caps.py`에 두는 것이 유일한 정합적 해법이었다. `actor_stats` 자체의 구현은 Task 2 커밋(`9148c06`)에 들어갔다.
- **파티 구성원의 `entity_id`를 짧은 캐릭터 식별자로 다시 쓴다.** `characters_data.PLAYER_CHARACTERS`가 쓰는 `entity_id`는 `"player.bram"`(긴 형태)이지만, 브라우저 신원(`identity.character_id`)과 세션 상태 계층 전체(`GameState.character_resource_ops`의 키)는 `"bram"`(짧은 형태)을 쓴다. `actor_stats(ctx)`는 `entity_id == actor_character_id` **완전 일치**로 행위자를 찾으므로(D-17, 유니코드 정규화·대소문자 접기 없음), 두 식별자 공간이 갈리면 항상 `ActorNotInParty`가 난다. `_current_party_state`가 `dataclasses.replace(entity, entity_id=character_id, ...)`로 짧은 형태를 다시 씌워 이 어긋남을 없앴다.
- **`routes_characters.py::_current_stats`를 import하지 않는다.** `routes_characters.py`가 이미 `routes_actions.py`의 `MAX_ID_LEN`을 import하므로, 반대 방향 import는 순환 import가 된다. 계획이 제시한 두 대안("공용 자리로 옮기거나, 옮기지 않으면 서로를 지목하는 주석으로 못박는다") 중 후자를 택해 `_current_party_state`가 같은 결합 규칙(시작값 + `resolve_character_stats`)을 독립적으로 반복하고, 두 함수의 도크스트링이 서로를 지목한다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - 차단 이슈] Task 1의 `<verify>`가 요구한 `tests/test_turn_tracer.py`를 Task 1 커밋 안에서 함께 고쳤다**
- **Found during:** Task 1 실행 직후 `uv run pytest tests/test_turn_tracer.py -x -q` 실행
- **Issue:** 이 파일은 계획 원문에서 Task 3의 `<files>`로 선언돼 있다. 하지만 `TurnContext(character_state=...)`를 직접 생성하는 자리가 있어, Task 1이 필드 이름을 바꾸는 순간 `TypeError`로 즉시 깨진다 — Task 1 자신의 `<verify>` 명령이 이 파일을 돌린다.
- **Fix:** 그 자리의 키워드 인자만 `party_state=`/`actor_character_id=`로 바꿨다. 이 시험 파일의 나머지(Task 3의 행동 회귀 검증)는 원래 계획대로 손대지 않았다.
- **Files modified:** `tests/test_turn_tracer.py`
- **Verification:** `uv run pytest tests/test_turn_tracer.py -x -q` 통과
- **Committed in:** `387e791`

**2. [Rule 3 - 차단 이슈] 계획에 없는 여덟 개 시험 파일의 기계적 필드명 전환**
- **Found during:** Task 2 실행 중 `uv run pytest -q`(전체 스위트) 실행
- **Issue:** `tests/test_adversarial_fence.py`·`test_agents_retry.py`·`test_master_gm.py`·`test_measurement.py`·`test_narration_guard.py`·`test_parallel_judgment.py`·`test_scene_entity_judge.py`·`test_situation_judge.py` 여덟 파일이 어느 Task의 `<files>`에도 없지만, 전부 `TurnContext(character_state=...)` 또는 `NarrationFacts(character_state=...)`를 직접 생성한다 — 필드 이름이 바뀌는 순간 전부 `TypeError`.
- **Fix:** `character_state=()` → `party_state=(), actor_character_id=None` 기계적 치환(빈 파티 + 행위자 없음, Task 1의 `<behavior>`가 정의한 정상 상태). `test_narration_guard.py`의 비어 있지 않은 한 자리(`character_state=(StatEntry(...),)`)는 단일 구성원 파티(`Entity`)로 재구성했다. `test_situation_judge.py`의 `NarrationFacts` 필드 집합 하드코딩 단언도 새 다섯 이름으로 갱신했다. 시험 의도는 어디도 안 바뀌었다.
- **Files modified:** 위 여덟 파일
- **Verification:** `uv run pytest -q` 전체 1056건 통과(반복 3회 재확인, 흔들림 없음)
- **Committed in:** `9148c06`

**3. [Rule 1 - 버그 수정] `declare()`도 `party_state=`/`actor_character_id=`로 전환 — 계획의 acceptance criteria가 명시한 grep 카운트(2)와 어긋난다**
- **Found during:** Task 3 acceptance criteria 자체 점검 중(`grep -c 'party_state=' routes_actions.py`가 3, 계획 원문은 2를 요구)
- **Issue:** Task 3의 액션 항목은 `confirm()`/`proceed()` 두 호출부만 고치라고 명시하고 `declare()`는 언급하지 않는다. 그런데 Task 1이 `build_turn_context`의 `character_stats` 키워드 인자를 완전히 제거했으므로(제3의 선택지로 남겨두지 않았다), `declare()`의 기존 `character_stats=character.stats` 호출은 무조건 `TypeError`가 난다. 인자를 아예 안 넘기면(기본값에 의존) 분류기가 실제 캐릭터 대신 예시 개체(`EXAMPLE_SINGLE_STAT_FOE`)를 보게 되어, 이미 존재하던 `tests/test_web_actions.py::test_prompt_carries_the_acting_character_real_stat_names`(declare()의 분류기 프롬프트가 실제 캐릭터의 실제 축 이름을 담는다는 기존 통과 시험)가 깨진다.
- **Fix:** `declare()`도 `confirm()`/`proceed()`와 같은 모양으로 `party_state=_current_party_state(store, session_id), actor_character_id=identity.character_id`를 넘기게 했다. `grep -c 'party_state='`가 2가 아니라 3이 되는 결과를 그대로 받아들였다 — 계획의 acceptance criteria 문구보다 계획 자신의 `<verify>`(`uv run pytest tests/test_web_actions.py -x -q`)와 기존 통과 시험의 보존을 우선했다.
- **Files modified:** `src/gptrpg/web/routes_actions.py`
- **Verification:** `tests/test_web_actions.py::test_prompt_carries_the_acting_character_real_stat_names` 무수정 통과, `uv run pytest -q` 전체 통과
- **Committed in:** `6a8884b`

**4. [Rule 3 - 차단 이슈] "자원 변화 반영" 시험을 HTTP `confirm()` 왕복이 아니라 결정론적 직접 호출로 작성**
- **Found during:** Task 3의 acceptance criteria가 요구한 "다음 턴 진행자 프롬프트에 깎인 값이 나온다" 시험을 처음 HTTP 왕복으로 작성했을 때, 독립 실행에서 산발적으로 실패
- **Issue:** `web_client_with_fake_provider`의 실제 다이스 굴림기(`LiveRoller`)는 주입 지점이 없다 — `confirm()`을 실제로 왕복하면 판정 결과가 무작위이고, "대가가 붙는 등급"이 실제로 나오면 `confirm()` 자신이 **또 다른** `RecordResourceChange`를 제출해 내가 미리 넣어둔 자원 변화 위에 덧씌워, 기대값과 실제값이 굴림 결과에 따라 흔들렸다(flaky).
- **Fix:** `_current_party_state` → `build_turn_context` → `build_narration_facts` → `build_gm_prompt`를 직접 호출하는 결정론적 버전으로 다시 작성했다 — 다이스가 전혀 개입하지 않는다. 3회 반복 실행으로 흔들림 없음을 확인했다.
- **Files modified:** `tests/test_web_actions.py`
- **Verification:** 해당 시험 단독 3회 반복 실행 + 전체 스위트 3회 반복 실행 모두 통과
- **Committed in:** `6a8884b`

---

**Total deviations:** 4 (2건 차단 이슈 — 파일 목록 확장, 1건 버그 수정 — 실 캐릭터 정보 유지, 1건 차단 이슈 — 시험 결정성 확보)
**Impact on plan:** 넷 다 계획 자신의 `<verify>`를 실제로 통과시키거나 기존 통과 시험을 보존하는 데 필요했다. 스콥 확장이 아니라, 계획 텍스트(특정 파일 목록·특정 grep 카운트)와 계획의 실제 검증 기준(전체 스위트 통과, 회귀 없음) 사이의 모순을 해소한 것이다.

## Issues Encountered

- **커밋 경계와 실행 순서의 실제 결합.** Task 1(`agents/context.py`)만 커밋해서는 `tests/test_turn_tracer.py`의 전체 턴 흐름이 돌지 않는다 — 실제 턴은 `build_classifier_prompt` → `_session_block_text(ctx)`를 거치는데, 그 함수 본문이 `ctx.character_state`를 읽던 것을 Task 2가 고친다. 세 태스크를 순서대로 구현·검증한 뒤(작업 트리는 항상 최신 상태), 계획이 선언한 파일 경계를 따라 `git add`를 나눠 커밋했다 — 실행 시점의 검증은 항상 "이미 세 태스크가 다 반영된 작업 트리"를 대상으로 돌았다는 뜻이다. 각 커밋을 개별적으로 checkout하면 Task 1 커밋 단독으로는 전체 턴 흐름 시험이 통과하지 않는다(다만 Task 1 자신의 `<files>`로 좁힌 두 파일 — `test_agent_context_caps.py`/`test_turn_tracer.py` — 은 통과한다).

## Known Stubs

없음 — 이 계획이 만드는 값 객체·함수 어디에도 하드코딩된 빈 값이나 미배선 자리가 없다.

## User Setup Required

None - 외부 서비스 설정 불필요.

## Next Phase Readiness

- 12-06(재량 판정 확인 관문)이 이 계획이 만든 파티 조립 지점(`_current_party_state`) 위에 자연스럽게 올라탈 수 있다 — 재량 판정이 바꾸는 자원도 같은 `resolve_character_stats` 경로를 탄다.
- 12-07(웹 UI)이 파티 상태 화면을 그리게 되면, `_format_party_state`가 이미 세운 "구성원마다 여섯 형태 렌더러 재사용" 관례를 프론트엔드 쪽에서도 참고할 수 있다.
- **알려진 특성(차단 아님):** `EXAMPLE_SINGLE_STAT_FOE`를 CLI 기본 파티로 계속 쓴다 — CLI 경로에 캐릭터 선택 개념이 생기기 전까지는 이 자리표시자가 유효하다.

---
*Phase: 12-stats-resources-inventory*
*Completed: 2026-08-17*

## Self-Check: PASSED

All 12 key files verified present on disk. All three task commit hashes
(`387e791`, `9148c06`, `6a8884b`) verified in `git log --all`.
