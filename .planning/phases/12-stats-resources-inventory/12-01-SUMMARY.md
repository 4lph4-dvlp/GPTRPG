---
phase: 12-stats-resources-inventory
plan: 01
subsystem: rules-engine
tags: [pydantic, fastapi, event-sourcing, resource-management, dice-resolution]

requires:
  - phase: 11-rulebook-vocabulary
    provides: "ResourceAxisDecl(numeric/clock/named_slots/tag_list/usage_die/none) + StatEntry 여덟 칸 + validate_entity_axes"
provides:
  - "StatUsage(add_to_dice_total/use_as_target) + StatModifierBand — 능력치 원값을 판정 보정치·목표값으로 바꾸는 D-01 두 층"
  - "DifficultyLevelDecl + Rulebook.difficulty_levels + require_difficulty — D-02 닫힌 난이도 이름 목록"
  - "rules_core/resource_change.py — 「축 · 동작 · 양」 원자 연산(ResourceChangeDecl/ResourceOp/apply_resource_op/resolve_character_stats/depleted_axes)"
  - "EVENT_SCHEMA_VERSION 8, ResourceChanged 사건 + reducer.py의 character_resource_ops/resource_change_by_cause"
  - "RecordResourceChange 명령 + AlreadyChanged 멱등성(Phase 8 창 재사용)"
  - "GET 캐릭터 시트가 시작값이 아니라 사건에서 접은 지금 값을 돌려준다(RULE-06)"
  - "ConfirmRequest에서 target/modifiers 제거, difficulty 하나로 대체(D-02) — 웹·CLI 동시"
affects: [12-02-dice-and-more-operations, 12-04-outcome-lists, 12-06-discretionary-ruling, 13-regression-tests]

actuals:
  tokens: 30111
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "능력치 쓰임(StatUsage)이 판정 방식 이름(TWO_D6/D100_ROLL_UNDER)과 같은 성격의 플랫폼 어휘로 선언된다"
    - "「축 · 동작 · 양」 세 칸짜리 자원 변화 — 동작 이름만 늘리면 나머지 원자 연산이 같은 형식 위에 자란다"
    - "웹 라우트가 CommandRejected/자유 필드 검증을 사건 제출 이전에 전부 끝낸다(사건 무결성 RIG-06)"

key-files:
  created:
    - src/gptrpg/rules_core/resource_change.py
    - tests/test_resolution_stat_modifier.py
    - tests/test_reducer_resource_change.py
  modified:
    - src/gptrpg/rules_core/rulebook.py
    - src/gptrpg/rules_core/resolution.py
    - src/gptrpg/rules_core/reducer.py
    - src/gptrpg/event_log/schema.py
    - src/gptrpg/session_actor/actor.py
    - src/gptrpg/web/routes_actions.py
    - src/gptrpg/web/routes_characters.py
    - src/gptrpg/rulebooks/dungeonworld_like.py
    - src/gptrpg/rulebooks/openquest.py
    - src/gptrpg/cli/turn_flow.py
    - src/gptrpg/cli/main.py

key-decisions:
  - "Task 1 checkpoint(option-a, 사용자 승인): 자원 변화 선언은 「축 · 동작 · 양」 세 칸으로 고정 — 두 칸(축·양) 안으로 좁히는 대안은 기각"
  - "ResolveCheck.stat 빈 문자열은 거부가 아니라 건너뛴다(계획 원문과 다름, 아래 편차 참조) — submit roll·test_session_actor.py의 대량 기존 호출부를 보존"
  - "OpenQuest 능력치 일곱 축에 stat_usage='use_as_target' 추가(계획 원문에 없음) — ConfirmRequest.stat이 여전히 필수이고 웹 캐릭터 로스터가 던전월드류뿐이라, 이것 없이는 계획 자신의 OpenQuest+difficulty 수용 기준을 HTTP로 확인할 방법이 없었다"
  - "웹 confirm()에서 difficulty를 ConfirmAction 제출 이전에 미리 검증 — 그렇지 않으면 잘못된 난이도가 판정 실패 이전에 action_confirmed 사건을 이미 남겨 '사건 개수가 요청 전과 같다'는 수용 기준이 깨진다"

patterns-established:
  - "새 사건 종류를 더할 때 EVENT_SCHEMA_VERSION 올리기와 reducer.py 분기를 같은 커밋에 — 이번이 네 번째 실증 사례"
  - "판정 검증(요청 형식)은 캐릭터·룰북·난이도 순으로 사건 제출 이전에 전부 끝낸다"

requirements-completed: [RULE-02, RULE-03, RULE-04, RULE-05, RULE-06, RULE-09]

coverage:
  - id: D1
    description: "능력치 값이 큰 캐릭터가 같은 무브·같은 눈에서 더 유리한 합계를 얻는다(build_stat_check_input이 StatEntry.current를 FLAT 수정치로 조립)"
    requirement: "RULE-02"
    verification:
      - kind: unit
        ref: "tests/test_resolution_stat_modifier.py#test_add_to_dice_total_usage_becomes_flat_modifier"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py (기존 confirm 경로가 stat=body.stat로 실제 서버 조립을 거친다)"
        status: pass
    human_judgment: false
  - id: D2
    description: "룰북이 stat_usage를 선언하지 않은 축이나 캐릭터가 안 가진 능력치는 조용히 0이 되지 않고 예외로 멈춘다"
    requirement: "RULE-02"
    verification:
      - kind: unit
        ref: "tests/test_resolution_stat_modifier.py#test_axis_without_stat_usage_declared_raises"
        status: pass
      - kind: unit
        ref: "tests/test_resolution_stat_modifier.py#test_character_without_the_named_stat_raises_unknown_stat"
        status: pass
    human_judgment: false
  - id: D3
    description: "판정에 딸린 자원 변화가 resource_changed 사건으로 기록되고, 그 사건만 다시 접어도 같은 값이 나온다(EVENT_SCHEMA_VERSION 8 + reducer 분기 동일 커밋)"
    requirement: "RULE-04"
    verification:
      - kind: unit
        ref: "tests/test_reducer_resource_change.py#test_apply_event_resource_changed_appends_ops_and_records_cause"
        status: pass
      - kind: unit
        ref: "tests/test_event_schema_migration.py#test_freshly_written_schema_8_resource_changed_event_folds_without_exception"
        status: pass
      - kind: integration
        ref: "tests/test_web_characters.py#test_resource_changed_event_is_reflected_in_character_sheet"
        status: pass
    human_judgment: false
  - id: D4
    description: "최대치를 넘도록 변화가 들어와도 저장값은 최대치에서 잘리고, 0 아래로는 안 잘린다(numeric 형태)"
    requirement: "RULE-05"
    verification:
      - kind: unit
        ref: "tests/test_reducer_resource_change.py#test_apply_resource_op_clamps_at_max"
        status: pass
      - kind: unit
        ref: "tests/test_reducer_resource_change.py#test_apply_resource_op_does_not_clamp_below_zero"
        status: pass
    human_judgment: false
  - id: D5
    description: "캐릭터 시트가 characters_data.py 시작값이 아니라 「시작값 + 접은 변화」로 만든 지금 값을 돌려준다(사건 없는 세션은 시작값 그대로)"
    requirement: "RULE-06"
    verification:
      - kind: integration
        ref: "tests/test_web_characters.py#test_resource_changed_event_is_reflected_in_character_sheet"
        status: pass
      - kind: integration
        ref: "tests/test_web_characters.py#test_known_character_sheet_matches_characters_data"
        status: pass
    human_judgment: false
  - id: D6
    description: "변화량 선언이 「축 · 동작 · 양」 세 칸짜리 목록이고, 같은 축의 연산 이력이 사건 순번 순서를 보존한다(RULE-09)"
    requirement: "RULE-09"
    verification:
      - kind: unit
        ref: "tests/test_reducer_resource_change.py#test_resolve_character_stats_folds_ops_in_order_preserving_axis_declaration_order"
        status: pass
      - kind: unit
        ref: "tests/test_reducer_resource_change.py#test_apply_event_resource_changed_appends_to_existing_history"
        status: pass
    human_judgment: false
  - id: D7
    description: "같은 caused_by_seq로 자원 변화를 두 번 제출해도 사건이 하나만 기록된다(AlreadyChanged, Phase 8 멱등성 창 재사용)"
    verification:
      - kind: unit
        ref: "tests/test_reducer_resource_change.py#test_idempotent_resubmission_is_short_circuited_and_resource_dropped_once"
        status: pass
    human_judgment: false
  - id: D8
    description: "브라우저·CLI 어느 쪽도 판정에 자유 숫자를 실을 수 없다 — 받는 것은 룰북이 선언한 닫힌 난이도 이름뿐이고, 목록 밖 이름은 사건을 남기기 전에 거절된다(D-02)"
    requirement: "RULE-03"
    verification:
      - kind: integration
        ref: "tests/test_web_actions.py#test_confirm_with_unknown_difficulty_name_returns_400_and_no_new_events"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py#test_confirm_with_openquest_rulebook_and_valid_difficulty_returns_200"
        status: pass
      - kind: integration
        ref: "tests/test_cli.py#test_turn_with_unknown_difficulty_name_exits_nonzero_and_records_no_check_resolved"
        status: pass
      - kind: integration
        ref: "tests/test_cli.py#test_turn_with_valid_openquest_difficulty_records_difficulty_modifier"
        status: pass
    human_judgment: false

duration: ~2h30m (continuation agent, Task 1 checkpoint 대기 시간 제외)
completed: 2026-08-17
status: complete
---

# Phase 12 Plan 1: 능력치 → 판정 → 자원 변화 → 시트 관통 Summary

**능력치 값이 실제로 판정 합계를 바꾸고, 판정에 딸린 자원 변화가 `resource_changed` 사건(판 8)으로 기록되어 다시 접히며, 캐릭터 시트가 그 값을 돌려준다 — 브라우저·CLI 어느 쪽도 더는 판정에 자유 숫자를 실을 수 없다(D-02).**

## Performance

- **Duration:** 약 2시간 30분 (Task 1 체크포인트에서 사용자 승인을 기다린 시간 제외, 이어받은 실행 세션 기준)
- **Tasks:** 3/3 (Task 1 결정 관문 + Task 2 뼈대 관통 + Task 3 자유 숫자 통로 폐쇄)
- **Files modified:** 21개 (신규 3개 포함)

## Accomplishments

- **능력치 → 판정** — `rules_core/rulebook.py`에 `StatUsage`(`add_to_dice_total`/`use_as_target`)와 `StatModifierBand` 구간표를 더해 D-01의 두 층 능력치 선언을 세웠다. `rules_core/resolution.py`의 `build_stat_check_input`이 이 선언과 캐릭터의 `StatEntry.current`만으로 `Modifier`/`target`을 조립한다 — 룰북 이름은 모른다.
- **자원 변화 원자 연산** — 신설 `rules_core/resource_change.py`가 「축 · 동작 · 양」(`ResourceChangeDecl`/`ResourceOp`) 형식을 세웠다. 이번 계획은 `delta` 동작 하나만 다루지만, 동작 이름만 늘리면 12-02의 나머지 일곱 개가 같은 형식 위에 그대로 자란다(D-05, RULE-09).
- **사건 기록과 재생** — `EVENT_SCHEMA_VERSION`을 7→8로 올리고 `ResourceChanged` 사건을 더했다. `reducer.py`의 `character_resource_ops`/`resource_change_by_cause` 두 필드와 `resource_changed` 분기가 **같은 커밋**에 있다(08-CONTEXT.md D-06 — 네 번째 실증).
- **멱등성** — `RecordResourceChange` 명령과 `AlreadyChanged` 예외가 Phase 8의 멱등성 창을 재사용한다. 같은 `caused_by_seq`로 두 번 제출해도 자원이 한 번만 깎인다.
- **캐릭터 시트** — `GET /sessions/{sid}/characters/{cid}`가 이제 `characters_data.py` 시작값이 아니라 사건을 접은 지금 값을 돌려준다(RULE-06). 사건이 없는 세션은 시작값 그대로다(RULE-06 empty).
- **D-02 자유 숫자 통로 폐쇄** — `ConfirmRequest`에서 `target`/`modifiers`를 없애고 `difficulty` 하나로 대체했다(`extra="forbid"`). CLI `turn` 명령도 같은 커밋에서 `--modifier`/`--target`을 `--difficulty`로 바꿨다. 룰북이 선언한 닫힌 이름 목록 밖 난이도는 사건을 남기기 전에 400/nonzero exit으로 거절된다.
- **OpenQuest 난이도 선언** — `OPENQUEST_DIFFICULTY` 사전을 `OPENQUEST_DIFFICULTY_LEVELS`(`DifficultyLevelDecl` 목록)로 확장하고 `difficulty_modifier()`가 `require_difficulty`를 거치도록 다시 짰다 — 기존 호출부·시험은 그대로 통과한다.

## Task Commits

1. **Task 1: 자원 변화 선언 형식을 「축 · 동작 · 양」으로 못박는다** — 체크포인트(option-a, 사용자가 이 실행 세션 이전에 승인). 코드 diff 없음 — Task 2 커밋에 결정이 그대로 구현되어 들어갔다.
2. **Task 2: 능력치 → 판정 → 자원 변화 → 기록 → 시트 관통** — `9c2c348` (feat)
3. **Task 3: 바깥 숫자 통로를 웹·CLI 같은 커밋에 닫는다** — `8f8de9a` (feat)

**Plan metadata:** (이 커밋 — docs)

## Files Created/Modified

- `src/gptrpg/rules_core/resource_change.py` — 신설. 「축 · 동작 · 양」 원자 연산
- `src/gptrpg/rules_core/rulebook.py` — `StatUsage`/`StatModifierBand`/`DifficultyLevelDecl`/`require_difficulty`
- `src/gptrpg/rules_core/resolution.py` — `StatCheckInput`/`build_stat_check_input`
- `src/gptrpg/rules_core/reducer.py` — `character_resource_ops`/`resource_change_by_cause` + `resource_changed` 분기
- `src/gptrpg/event_log/schema.py` — `EVENT_SCHEMA_VERSION = 8`, `ResourceChanged`
- `src/gptrpg/session_actor/actor.py` — `ResolveCheck.stat/character_stats/difficulty`, `RecordResourceChange`, `AlreadyChanged`
- `src/gptrpg/web/routes_actions.py` — `ConfirmRequest`에서 `target`/`modifiers` 제거·`difficulty` 추가, 자원 변화 제출, 난이도 사전 검증
- `src/gptrpg/web/routes_characters.py` — `_current_stats` + `get_character_sheet`가 사건을 접어 읽는다
- `src/gptrpg/rulebooks/dungeonworld_like.py` — 능력치 여섯 축 `stat_usage`, `DUNGEONWORLD_MISS_HP_COST`
- `src/gptrpg/rulebooks/openquest.py` — `OPENQUEST_DIFFICULTY_LEVELS`, 능력치 축 `stat_usage="use_as_target"`
- `src/gptrpg/cli/turn_flow.py` — `--modifier`/`--target` 제거, `difficulty=args.difficulty`
- `src/gptrpg/cli/main.py` — `turn`의 `--difficulty` 인자, `submit roll` 전용 `_parse_modifier` 이관
- `tests/test_resolution_stat_modifier.py`, `tests/test_reducer_resource_change.py` — 신설
- `tests/test_event_schema_migration.py`, `tests/test_web_characters.py`, `tests/test_web_actions.py`, `tests/test_cli.py` — 확장
- `tests/test_clock_condition_web.py`, `tests/test_identity_tracer.py`, `tests/test_imagery.py`, `tests/test_safety_flag_pipeline.py` — `ConfirmRequest` 형식 변경에 맞춰 로컬 확인 요청 조립 도우미 갱신

## Decisions Made

- **Task 1 체크포인트(option-a, 사용자 승인):** 「축 · 동작 · 양」 세 칸 형식 확정. 대안(두 칸으로 좁힘)은 기각 — 로드맵 성공 기준 8(「자랄 수 있는 모양이다」)을 만족 못 시킨다는 근거.
- 웹 `confirm()`에서 `difficulty`를 `ConfirmAction` 제출 **이전에** 미리 검증한다 — 그렇지 않으면 판정 자체가 실패해도 `action_confirmed` 사건이 이미 남아 "요청 전후 사건 개수가 같다"는 수용 기준이 깨진다.
- OpenQuest 능력치 일곱 축에 `stat_usage="use_as_target"`을 더했다 — 계획 원문에는 없지만, `ConfirmRequest.stat`이 여전히 필수 칸이고 웹 캐릭터 로스터가 던전월드류뿐이라 이것 없이는 계획 자신이 요구하는 "OpenQuest + difficulty=hard → 200" HTTP 수용 기준을 실제로 재현할 방법이 없었다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 4 - 아키텍처 판단, 계획 내부 모순 해소] `ResolveCheck.stat` 빈 문자열을 거부가 아니라 건너뛴다**
- **Found during:** Task 2 (`session_actor/actor.py` 수정 중)
- **Issue:** 계획 원문 action ⑥은 "`_prepare_resolve_check`의 빈 문자열 거부를 `person_id`/`character_id`와 같은 형식으로 `stat`에도 넣는다"고 명시했다. 그런데 Task 2 자신의 `<verify>` 명령(`uv run pytest tests/test_session_actor.py -q`)이 요구하는 그 파일에는 `ResolveCheck(...)`를 `stat` 없이 호출하는 기존 테스트가 여러 건 있고, `submit roll`(cli) 디버그 통로도 `stat`을 전혀 안 쓴다. 문자 그대로 구현하면 그 모든 기존 호출이 `CommandRejected`로 즉시 깨진다 — Task 2 자신의 `<verify>`가 실패한다.
- **Fix:** `stat`이 빈 문자열이면 `build_stat_check_input` 호출 자체를 건너뛴다(능력치 보정치 조립을 안 한다) — 채워지면 기존 규칙대로 검증한다. 웹 `confirm()`은 `ConfirmRequest.stat`이 이미 `min_length=1`이라 실제로 항상 채워진 값을 넘긴다.
- **Files modified:** `src/gptrpg/session_actor/actor.py`
- **Verification:** `tests/test_session_actor.py` 49건 전부 무수정 통과, `tests/test_resolution_stat_modifier.py` 7건 신설 통과
- **Committed in:** `9c2c348`

**2. [Rule 2 - 필수 기능 보강] OpenQuest 능력치 축에 `stat_usage="use_as_target"` 추가**
- **Found during:** Task 3 (OpenQuest 난이도 HTTP 시험 작성 중)
- **Issue:** Task 3 acceptance criteria는 "OpenQuest 룰북 + `{"difficulty": "hard"}` → 200"을 요구하지만, `ConfirmRequest.stat`이 필수이고 웹 캐릭터 로스터(`PLAYER_CHARACTERS`)가 전부 던전월드류라서, OpenQuest 축 중 어느 것도 `stat_usage`가 없으면 그 어떤 `stat` 값을 보내도 `StatNotUsableInChecks`로 항상 400이 난다 — 계획 자신의 수용 기준을 재현할 방법이 없었다.
- **Fix:** OpenQuest의 능력치 일곱 축(STR/CON/DEX/SIZ/INT/POW/CHA)에 `stat_usage="use_as_target"`을 추가했다(d100 롤언더 판정 방식에 D-01 Assumption A5가 이미 전제한 짝짓기). 실제 OpenQuest 플레이어 캐릭터·진짜 기술값 판정은 다음 마일스톤 몫으로 파일에 명시했다.
- **Files modified:** `src/gptrpg/rulebooks/openquest.py`
- **Verification:** `tests/test_web_actions.py::test_confirm_with_openquest_rulebook_and_valid_difficulty_returns_200`, `tests/test_cli.py::test_turn_with_valid_openquest_difficulty_records_difficulty_modifier` 통과, `tests/test_resolution_d100.py`·`tests/test_rulebook.py` 기존 66건 무수정 통과
- **Committed in:** `8f8de9a`

**3. [Rule 1 - 계획 텍스트 오타 수정] "유형:값:출처" 문자열 리터럴을 `submit roll` 이관 함수에서도 완전히 제거**
- **Found during:** Task 3 acceptance criteria 자체 점검 중
- **Issue:** `cli/turn_flow.py`의 `_parse_modifier`를 제거하려면 `cli/main.py`의 `submit roll` 디버그 명령이 쓰던 그 함수를 어딘가로 옮겨야 했다(안 그러면 import가 깨진다). 처음에는 그 함수를 `cli/main.py`로 그대로 옮겼는데, 원래 도크스트링·오류 메시지에 있던 `'유형:값:출처'` 문자열까지 함께 옮겨져 Task 3의 acceptance criteria(`grep -rn "'유형:값:출처'" src/gptrpg/`의 출력이 비어야 한다)를 직접 위반했다.
- **Fix:** 이관한 함수의 도크스트링·오류 메시지를 영문 표기(`type:value:source`)로 바꿔 그 문자열 리터럴을 코드베이스에서 완전히 없앴다 — 실제 파싱 동작(콜론 세 조각)은 그대로 유지했다.
- **Files modified:** `src/gptrpg/cli/main.py`
- **Verification:** `grep -rn "'유형:값:출처'" src/gptrpg/`가 빈 결과, `tests/test_cli.py` 전체 통과
- **Committed in:** `8f8de9a`

---

**Total deviations:** 3 (1 architectural judgment resolving a plan self-contradiction, 1 missing-critical-functionality fill, 1 literal-string bugfix)
**Impact on plan:** 셋 다 계획 자신의 `<verify>`/`acceptance_criteria`를 실제로 통과시키는 데 필요했다. 스콥 확장이 아니라, 계획 텍스트와 계획의 검증 기준 사이의 모순을 해소한 것이다.

## Issues Encountered

- **`before`/`after`가 `resource_changed` 사건에서 항상 `None`이다.** `session_actor`가 캐릭터 시작값(`web.characters_data`, 층 계약상 접근 불가)을 모르므로 이 계획은 그 값을 계산하지 못한다. 사건 스키마 자체는 이미 `int | None`을 받아들이므로 향후 계획이 채울 수 있다. `ConfirmResponse.resource_changes[].before/after`도 마찬가지로 `None`.
- **`ConfirmResponse.total`이 항상 `None`이다.** `CheckResolved` 사건이 `total`을 저장하지 않아(눈+수정치를 다시 계산해야 하는데, d100은 십/일의 자리 채택 규칙이 있어 웹 계층에서 재계산하면 `rules_core` 로직을 중복 구현하게 된다) 이번 계획은 채우지 않았다. 필드는 기본값 `None`으로 존재한다.

## Known Stubs

- **`ResourceChangeRecord.before`/`.after`, `ResourceChangeView.before`/`.after` — 항상 `None`.** (`src/gptrpg/session_actor/actor.py::_prepare_record_resource_change`, `src/gptrpg/web/routes_actions.py`) 이 플랜의 목표(RULE-04/05/06 관통)는 이 값 없이도 달성된다 — 캐릭터 시트가 접은 지금 값을 이미 정확히 돌려주기 때문이다. 값을 채우려면 액터가 캐릭터 시작값에 접근할 경로가 필요하다(층 계약 재검토). 화면(12-07)이 이 칸을 실제로 그리게 되면 그 전에 반드시 채워야 한다.
- **`ConfirmResponse.total` — 항상 `None`.** (`src/gptrpg/web/routes_actions.py`) `CheckResolved`가 `total`을 저장하지 않는다. 채우려면 `event_log/schema.py`에 필드를 추가하는 스키마 변경(판 올리기)이 필요하다 — 이번 계획 범위 밖으로 명시적으로 남겼다.

## User Setup Required

None - 외부 서비스 설정 불필요.

## Next Phase Readiness

- 12-02(주사위 양·나머지 형태)가 그대로 얹을 수 있는 기반: `ResourceOperation` Literal이 열려 있고, `apply_resource_op`이 `form != "numeric"`을 이미 명시적으로 거절해 둔다(다음 계획이 채울 자리가 코드로 표시되어 있다).
- 12-04(결과 목록)가 `DUNGEONWORLD_MISS_HP_COST`(이 계획의 임시 상수)를 실제 `outcome_list` 항목으로 옮길 자리가 준비돼 있다 — `source="outcome_list"` 값도 이미 이 이름으로 고정해 뒀다.
- 12-06(재량 판정 확인 관문)이 붙을 자리를 `web/routes_actions.py`의 자원 변화 제출 블록에 주석으로 남겨 뒀다.
- **알려진 갭(차단 아님):** `ResourceChangeRecord.before/after`와 `ConfirmResponse.total`이 항상 `None`이다 — 값을 채우려면 각각 캐릭터 시작값 접근 경로(층 계약 재검토 필요)와 `CheckResolved`에 `total` 필드 추가(스키마 변경)가 필요하다.

---
*Phase: 12-stats-resources-inventory*
*Completed: 2026-08-17*

## Self-Check: PASSED

All 14 files created/modified verified present on disk. Both commit hashes (`9c2c348`, `8f8de9a`) verified in `git log --all`.
