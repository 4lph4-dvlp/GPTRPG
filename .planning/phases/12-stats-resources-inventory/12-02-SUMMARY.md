---
phase: 12-stats-resources-inventory
plan: 02
subsystem: rules-engine
tags: [dice-notation, event-sourcing, resource-management, form-dispatch]

requires:
  - phase: 12-stats-resources-inventory
    provides: "12-01 — 「축 · 동작 · 양」 세 칸 형식, ResourceOperation Literal(delta 하나), apply_resource_op(numeric만), resolve_character_stats, depleted_axes, EVENT_SCHEMA_VERSION 8 + ResourceChanged 사건"
provides:
  - "DieRoller Protocol + LiveRoller.roll_die/ReplayRoller.roll_die — 굴림 도구 둘에 나란히 얹은 세 번째 확장(D-06)"
  - "resource_change.roll_amount — 고정 정수/주사위식(NdM+flat) 양쪽을 (정수, 굴린 눈 튜플)로 통일해서 돌려주는 유일한 무작위 통로, MAX_DICE_COUNT/MAX_DIE_SIDES 상한을 굴림 전에 검사"
  - "ResourceOperation 여덟 값(delta/advance/fill/clear/add_tag/remove_tag/step_down/deplete) — apply_resource_op이 stat.form으로 갈라 형태별 허용 동작만 받는다(RULE-09 「자랄 수 있는 모양」 실증)"
  - "depleted_axes가 형태별 「다 썼다」 기준(numeric current<=0/usage_die current==0/clock current>=max/named_slots 빈칸 0개)을 안다"
  - "rules_core.reducer.OutOfOrderEvent — fold()가 저장소 정렬에 기대지 않고 순번을 스스로 검사한다(QUAL-01)"
  - "event_log.schema.CorruptEventRecord — 형식 표시 빠짐/손상 셋(칸 없음·정수 아님·알 수 없는 종류)을 옛 판 기록과 구분되는 예외 관례로 멈춘다(QUAL-02)"
affects: [12-03, 12-04-outcome-lists, 12-06-discretionary-ruling, 13-regression-tests]

actuals:
  tokens: 15983
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "굴림 도구는 기존 Protocol을 고치지 않고 나란히 세 번째를 추가한다 — Roller/PercentileRoller에 이어 DieRoller(구조적 타이핑이라 메서드를 더하면 기존 즉석 객체가 프로토콜을 벗어난다)"
    - "형태 우선 갈래(stat.form으로 먼저 나눈 뒤 그 형태가 허용하는 동작만 받는다)가 apply_resource_op의 표준 모양 — 여섯 형태 × 여덟 동작 대응표가 모듈 도크스트링에 명시적으로 산다"
    - "정수/문자열 amount 혼용 자료형(ResourceOp.amount: int | str)을 형태별 헬퍼(_require_int_amount/_require_str_amount)로 형변환 없이 검증"

key-files:
  created:
    - tests/test_dice_amount.py
  modified:
    - src/gptrpg/rules_core/dice.py
    - src/gptrpg/event_log/replay_roller.py
    - src/gptrpg/session_actor/live_roller.py
    - src/gptrpg/rules_core/resource_change.py
    - src/gptrpg/rules_core/reducer.py
    - src/gptrpg/event_log/schema.py
    - tests/test_dice_replay.py
    - tests/test_reducer_resource_change.py
    - tests/test_entities.py
    - tests/test_event_log.py

key-decisions:
  - "ResourceChangeDecl.amount의 str 거절(12-01)을 완전 삭제가 아니라 주사위식 문법(_DICE_EXPR) 형식 검사로 좁혔다 — 12-01은 모든 문자열을 거절했지만, 이제 유효한 NdM 문자열은 통과하고 그 밖은 여전히 InvalidResourceChange다"
  - "ResourceOp.amount를 int에서 int | str로 넓혔다 — named_slots(fill/clear)·tag_list(add_tag/remove_tag)가 문자열 페이로드(슬롯 내용·태그 이름)를 실어야 해서 불가피했다. 형변환 없이 _require_int_amount/_require_str_amount로 형태-동작 짝을 검증한다"
  - "clock의 최대치 자르기는 위아래 둘 다(0과 max) — numeric은 위쪽만(0 아래는 룰북 몫, D-08). 「clock은 max가 항상 필수」라는 StatEntry 규약을 그대로 이용했다"
  - "OutOfOrderEvent 검사를 fold() 한 자리에만 뒀다 — apply_event는 건드리지 않았다(두 자리에 검사를 두면 서로 다른 규칙으로 갈릴 수 있다는 _band_matches 관례를 그대로 따름)"
  - "CorruptEventRecord는 정확히 세 사유(칸 없음/정수 아님/알 수 없는 종류)만 잡고, 그 밖의 pydantic 검증 실패(예: 알려진 종류인데 고유 필수 칸이 빠짐)는 원래 ValidationError를 그대로 다시 던진다 — 계획의 플래그된 가정(QUAL-02 edge probe)이 정한 경계를 넘지 않았다"

patterns-established:
  - "무작위는 DieRoller 하나의 통로로만 들어온다 — roll_amount 안에서만 roller.roll_die를 부르고, 상한 검사가 그 호출보다 먼저 온다(T-12-09)"
  - "형태 × 동작 대응표를 코드 도크스트링에 표로 못박는 관례 — 다음 원자 연산이 늘 때 이 표부터 갱신한다"

requirements-completed: [RULE-09, QUAL-01, QUAL-02, QUAL-06]

coverage:
  - id: D1
    description: "변화량을 「1d6」·「2d8+1」·「-1d6」 같은 주사위식으로 적을 수 있고, 굴린 눈이 결과와 함께 돌아오며, 같은 눈을 되먹이면 같은 결과가 다시 나온다(RULE-09, D-06)"
    requirement: "RULE-09"
    verification:
      - kind: unit
        ref: "tests/test_dice_amount.py (26개 — 고정 정수·단일/복수 주사위·부호·문법 오류·상한 초과 열 갈래)"
        status: pass
      - kind: unit
        ref: "tests/test_dice_replay.py#test_replaying_same_recorded_rolls_twice_gives_same_roll_amount_result"
        status: pass
    human_judgment: false
  - id: D2
    description: "새 무작위 경로가 생기지 않았다 — rules_core 안에 random/secrets import가 없고, ruff/lint-imports가 그것을 강제한다"
    requirement: "RULE-09"
    verification:
      - kind: unit
        ref: "grep -rn 'import random|import secrets' src/gptrpg/rules_core/ (빈 결과)"
        status: pass
      - kind: other
        ref: ".venv/bin/python -m ruff check src tests; .venv/bin/lint-imports"
        status: pass
    human_judgment: false
  - id: D3
    description: "여섯 표현 형태 전부(numeric/clock/named_slots/tag_list/usage_die/none) 각각에서 「변한다」의 뜻에 맞는 동작이 성립하고, 형태와 동작이 어긋나면 InvalidResourceChange로 멈춘다(RULE-09)"
    requirement: "RULE-09"
    verification:
      - kind: unit
        ref: "tests/test_reducer_resource_change.py (clock/named_slots/tag_list/usage_die/none 각 형태 3개 이상, 상호 배제 케이스 포함)"
        status: pass
    human_judgment: false
  - id: D4
    description: "최대치가 선언된 축(numeric max/clock)은 넘치는 변화가 잘리고, 상한이 없는 축(numeric max=None)은 안 자르며, 0 아래는 numeric에서 안 잘린다(QUAL-06)"
    requirement: "QUAL-06"
    verification:
      - kind: unit
        ref: "tests/test_reducer_resource_change.py#test_apply_resource_op_numeric_boundary_exactly_at_max_stays_at_max"
        status: pass
      - kind: unit
        ref: "tests/test_reducer_resource_change.py#test_apply_resource_op_clock_advance_negative_steps_back_and_stops_at_zero"
        status: pass
      - kind: unit
        ref: "tests/test_entities.py#test_clamped_resource_change_result_still_passes_stat_entry_validation"
        status: pass
    human_judgment: false
  - id: D5
    description: "사건 접기(fold)가 저장소 정렬에 기대지 않고 순번을 스스로 검사한다 — 겹침·역행은 OutOfOrderEvent, 사이가 빈 순번은 정상(QUAL-01)"
    requirement: "QUAL-01"
    verification:
      - kind: unit
        ref: "tests/test_reducer_resource_change.py#test_fold_duplicate_sequence_number_raises_out_of_order_event"
        status: pass
      - kind: unit
        ref: "tests/test_reducer_resource_change.py#test_fold_gapped_sequence_numbers_is_normal"
        status: pass
      - kind: unit
        ref: "tests/test_reducer_resource_change.py#test_fold_folding_same_event_list_twice_gives_same_result"
        status: pass
    human_judgment: false
  - id: D6
    description: "기록 형식 표시가 아예 빠진 레코드(칸 없음/정수 아님)와 알 수 없는 사건 종류가 CorruptEventRecord로 멈추고, 진짜 옛 판 기록(schema_version 작은 정수)은 예외 없이 정상으로 읽힌다(QUAL-02)"
    requirement: "QUAL-02"
    verification:
      - kind: unit
        ref: "tests/test_event_log.py#test_corrupt_event_record_missing_schema_version_field_raises"
        status: pass
      - kind: unit
        ref: "tests/test_event_log.py#test_legacy_schema_version_2_check_resolved_record_is_read_normally_not_corrupt"
        status: pass
      - kind: unit
        ref: "tests/test_event_log.py#test_corrupt_event_record_string_representation_does_not_leak_raw_json_body"
        status: pass
    human_judgment: false
  - id: D7
    description: "실제 사건 기록(.gptrpg/events.db 판 2 895건, .gptrpg/uat9.db 판 5 221건)이 새 순번 검사로 깨지지 않는다"
    verification:
      - kind: integration
        ref: "tests/test_event_schema_migration.py (skipif 스모크, 두 DB 모두 존재해 3건 실행)"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-08-17
status: complete
---

# Phase 12 Plan 2: 주사위 양·여섯 형태·기록 방어 Summary

**변화량을 주사위식(`"1d6"`·`"2d8+1"`)으로 적을 수 있게 됐고, 자원 변화가 여섯 표현 형태(numeric/clock/named_slots/tag_list/usage_die/none) 전부에서 형태에 맞는 동작으로 성립하며, 사건 접기가 순번 어긋남과 기록 형식 표시 빠짐을 스스로 검사한다.**

## Performance

- **Duration:** 약 20분 (읽기 포함, 세 태스크 커밋 사이는 9분)
- **Tasks:** 3/3
- **Files modified:** 10개 (신규 1개 포함)

## Accomplishments

- **주사위 양(D-06)** — `Roller`·`PercentileRoller`를 한 글자도 안 고치고 세 번째 `DieRoller` Protocol을 나란히 추가했다. `LiveRoller.roll_die`/`ReplayRoller.roll_die`가 그 확장을 구현하고, `ReplayRoller`는 기존 `roll_d6`/`roll_tens`와 **같은 반복자**를 공유한다(재생 일치). `resource_change.roll_amount`가 고정 정수와 `NdM(+/-K)` 주사위식을 `(정수, 굴린 눈 튜플)`로 통일해서 돌려주는 유일한 무작위 통로이고, `MAX_DICE_COUNT=20`·`MAX_DIE_SIDES=1000` 상한을 굴림 도구를 부르기 **전**에 검사한다(굴림 호출 폭주 방지, T-12-09).
- **여섯 형태 전부 관통(RULE-09)** — `ResourceOperation`이 `"delta"` 하나에서 여덟 값(`delta`/`advance`/`fill`/`clear`/`add_tag`/`remove_tag`/`step_down`/`deplete`)으로 자랐다. `apply_resource_op`이 `stat.form`으로 먼저 갈라 형태별 허용 동작만 받고, 어긋나면(예: `tag_list`에 `delta`) `InvalidResourceChange`로 멈춘다. `clock`/`tag_list`/`usage_die`는 저장소의 어느 룰북도 아직 선언하지 않았지만(11-VERIFICATION의 RULE-11 3/6 미완), 시험 픽스처로 세 형태의 모든 동작·경계가 덮인다.
- **최대치 자르기 확장(QUAL-06)** — `numeric`은 위쪽만(상한 없으면 안 자름), `clock`은 `max`가 항상 필수이므로 위아래 둘 다 자른다(0에서도 멈춘다). 자른 결과가 `dataclasses.replace`를 거쳐 `StatEntry.__post_init__`을 다시 통과한다는 것을 별도 시험으로 확인했다.
- **`depleted_axes` 형태별 확장** — `numeric`(`current<=0`)·`usage_die`(`current==0`)·`clock`(`current>=max`)·`named_slots`(빈 슬롯 0개) 각각의 「다 썼다」 기준을 구현했다. `tag_list`/`none`은 소진 개념이 없어 항상 `False`다.
- **순번 방어(QUAL-01)** — `fold()`가 저장소의 `ORDER BY seq` 정렬에 **우연히** 기대던 것을 스스로 검사하는 것으로 바꿨다. 겹침(같은 순번 두 번)과 역행(순번이 되돌아감)은 `OutOfOrderEvent`, 사이가 빈 순번(가시성 필터 등으로 건너뛴 사건)은 정상이다. 검사는 `fold` 한 자리에만 뒀다.
- **기록 형식 방어(QUAL-02)** — `parse_event`가 `schema_version` 칸이 아예 없거나 정수가 아니거나 `event_type`이 알려진 열한 종류 밖이면 `CorruptEventRecord`(고정 분류 문자열만, 원본 JSON·pydantic 오류 원문 안 실음)로 멈춘다. `schema_version`이 작은 정수인 **진짜 옛 판** 기록은 이 방어를 그대로 통과해 예전처럼 읽힌다 — 두 상황이 같은 시험 파일에 나란히 있다.

## Task Commits

1. **Task 1: 임의 면수 굴림 확장 + 주사위식 양(D-06)** — `59b2af7` (feat)
2. **Task 2: 여섯 표현 형태 각각의 「변한다」 + 최대치 자르기(RULE-09, QUAL-06)** — `314d7a4` (feat)
3. **Task 3: 순번 방어 + 기록 형식 방어(QUAL-01, QUAL-02)** — `131988a` (fix)

**Plan metadata:** (이 커밋 — docs)

## Files Created/Modified

- `src/gptrpg/rules_core/dice.py` — `DieRoller` Protocol 신설
- `src/gptrpg/event_log/replay_roller.py` — `ReplayRoller.roll_die`(같은 반복자 공유)
- `src/gptrpg/session_actor/live_roller.py` — `LiveRoller.roll_die`(`secrets.randbelow` 기반)
- `src/gptrpg/rules_core/resource_change.py` — `roll_amount`·`MAX_DICE_COUNT`·`MAX_DIE_SIDES`·`_DICE_EXPR`, `ResourceOperation` 여덟 값, `apply_resource_op` 형태별 갈래, `depleted_axes` 형태별 기준
- `src/gptrpg/rules_core/reducer.py` — `OutOfOrderEvent`, `fold()`의 순번 검사
- `src/gptrpg/event_log/schema.py` — `CorruptEventRecord`, `parse_event`의 손상 판별 3갈래
- `tests/test_dice_amount.py` — 신설(26건)
- `tests/test_dice_replay.py`, `tests/test_reducer_resource_change.py`, `tests/test_entities.py`, `tests/test_event_log.py` — 확장

## Decisions Made

- `ResourceChangeDecl.amount`의 문자열 거절(12-01)을 완전 삭제가 아니라 `_DICE_EXPR` 형식 검사로 좁혔다 — 유효한 주사위식은 이제 통과한다.
- `ResourceOp.amount`를 `int`에서 `int | str`로 넓혔다 — `named_slots`/`tag_list` 동작이 문자열 페이로드를 실어야 해서 불가피했다. 형변환 없이 `_require_int_amount`/`_require_str_amount`로 검증한다.
- `clock`의 최대치 자르기는 위아래 둘 다(0과 `max`) — `numeric`은 위쪽만(0 아래는 룰북 몫, D-08).
- `OutOfOrderEvent` 검사는 `fold()` 한 자리에만 두고 `apply_event`는 건드리지 않았다 — 두 자리에 두면 서로 다른 규칙으로 갈릴 수 있다는 `_band_matches` 관례를 그대로 따랐다.
- `CorruptEventRecord`는 정확히 세 사유(칸 없음/정수 아님/알 수 없는 종류)만 잡는다 — 그 밖의 다른 pydantic 검증 실패(알려진 종류인데 고유 필수 칸이 빠짐 등)는 원래 `ValidationError`를 그대로 다시 던진다. 계획의 플래그된 가정(QUAL-02 edge probe)이 정한 경계를 넘지 않았다.

## Deviations from Plan

None — plan executed exactly as written. 세 태스크의 `<action>`·`<verify>`·`acceptance_criteria`를 문자 그대로 따랐고, 별도의 버그 수정·필수 기능 보강·아키텍처 판단이 필요하지 않았다.

## Issues Encountered

None.

## User Setup Required

None - 외부 서비스 설정 불필요.

## Next Phase Readiness

- **RULE-09가 이제 완전히 닫힌다** — 12-01이 「축 · 동작 · 양」 형식과 `delta` 하나를 세웠고, 이 계획이 나머지 일곱 동작 이름을 같은 형식 위에 붙여 「자랄 수 있는 모양」을 실증했다. STATE.md가 남긴 "12-02 완료 시 RULE-09를 닫을 것" 지시를 따라 `requirements mark-complete`로 표시한다.
- **QUAL-01/QUAL-02/QUAL-06도 이 계획으로 닫힌다** — REQUIREMENTS.md Traceability 표에서 넷 다 Phase 12 하나에만 매핑되어 있고, 이 계획의 세 태스크가 그 넷의 원문 요구사항을 문자 그대로 만족시켰다(그 이상은 벌이지 않았다).
- **여전히 남은 12-01의 알려진 갭(이 계획 범위 밖, 변화 없음):** `ResourceChangeRecord.before`/`.after`와 `ConfirmResponse.total`이 여전히 `None`이다 — 이 계획이 다룬 것은 순수 함수 계층(`resource_change.py`)과 방어(`reducer.py`/`schema.py`)뿐이고, 액터가 캐릭터 시작값에 접근하는 층 계약 재검토는 아직 이뤄지지 않았다.
- **12-03 이후가 이어받을 것:** `clock`/`named_slots`/`tag_list`/`usage_die` 네 형태는 여전히 저장소의 어느 룰북도 실제로 선언하지 않았다 — 이 계획의 검증은 전부 시험 픽스처다(11-VERIFICATION RULE-11 3/6은 아직 미해소). `ResourceChangeDecl` → `ResourceOp` 변환 호출부(룰북 결과 목록 → 사건 제출 경로)는 12-04가 잇는다.

---
*Phase: 12-stats-resources-inventory*
*Completed: 2026-08-17*

## Self-Check: PASSED

All 11 modified/created source and test files verified present on disk. All three
task commit hashes (`59b2af7`, `314d7a4`, `131988a`) verified in `git log --all`.
