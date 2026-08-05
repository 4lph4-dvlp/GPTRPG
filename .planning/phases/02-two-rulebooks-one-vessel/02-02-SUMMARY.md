---
phase: 02-two-rulebooks-one-vessel
plan: 02
subsystem: rules-engine
tags: [d100, modifiers, tdd, hypothesis, replay]

requires:
  - phase: 02-two-rulebooks-one-vessel
    provides: "02-01: 무수정치 d100 롤언더 판정(resolve_d100), rules_core/rulebook.py(GradeBand/Rulebook/grade_for_margin), gptrpg/rulebooks/ 계층, OpenQuest 등급 4종"
provides:
  - "resolve_d100이 수정치 네 유형(FLAT/TARGET_SHIFT/BONUS_DICE/PUSH)을 전부 실제 계산에 반영 — 각기 다른 계산 시점(굴리기 전/굴림 자체/굴린 뒤/판정 후)에서"
  - "push_d100 — reroll_2d6과 같은 불변식(앞선 눈 보존, 새 눈만으로 재채점, PUSH 미보유 시 PushNotPermitted)"
  - "OpenQuest 난이도 다섯 단계(difficulty_modifier) — TARGET_SHIFT 수정치로 표현"
  - "등급 밴드가 빈틈·겹침 없이 굴림 범위 전체를 덮는다는 hypothesis 성질 테스트, 수치 구간형 룰북 선언이 같은 GradeBand 구조로 통과한다는 증명"
  - "ReplayRoller.roll_tens/roll_units — roll_d6과 같은 반복자 공유, d100 판정 재생 가능"
affects: [02-03-entities, 02-04-interface-changes, phase-6-measurement]

actuals:
  tokens: 8658
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "수정치는 '언제 적용되는가'로 분류한다 — 한 번의 목록 순회에서 FLAT/TARGET_SHIFT/BONUS_DICE/PUSH로 나누고, 굴리기 전(target 계산) -> 굴림 자체(다이스 개수·채택 규칙) -> 굴린 뒤(FLAT 가산) 순서로 계산한다. _flat_total을 복사해 유형만 늘리는 접근은 보너스 다이스(굴림 절차 자체를 바꾸는 지시)를 표현할 수 없어서 폐기했다"
    - "재굴림(push_d100)은 reroll_2d6의 골격을 그대로 물려받는다 — previous.rolls를 접두사로 보존하고 새 눈만으로 total/grade를 다시 계산하며 modifiers/target은 승계한다. '같은 골격, 다른 주사위 모양'이 판정 방식 두 개 사이에서 실물로 성립한다"
    - "룰북이 허용하지 않은 재굴림은 previous.modifiers에 PUSH 표식이 없다는 사실만으로 거부된다(PushNotPermitted) — resolve_d100이 PUSH를 계산에 반영하지 않는 것은 '조용한 무시'가 아니라 다른 함수가 읽는 명시적 표식이라는 것을 실물로 증명"
    - "등급 밴드 선언은 이름 목록형·수치 구간형 둘 다 같은 GradeBand 구조로 표현된다 — 수치 구간형(이름이 숫자 문자열, margin_at_least/margin_at_most만 사용, requires_doubles 미사용)은 테스트 파일 안에서만 선언해 rulebooks/에 세 번째 룰북을 출하하지 않으면서도 구조가 통과한다는 것을 증명한다"

key-files:
  created:
    - tests/test_resolution_d100.py
    - tests/test_grading_d100.py
  modified:
    - src/gptrpg/rules_core/resolution_d100.py
    - src/gptrpg/rulebooks/openquest.py
    - src/gptrpg/event_log/replay_roller.py

key-decisions:
  - "고친 곳: resolve_d100의 계산 순서를 세 시점(굴리기 전/굴림 자체/굴린 뒤)으로 재구성 — 02-01의 '수정치 전면 거부' 임시 게이트를 걷어내고 실제 계산으로 교체했다"
  - "고친 곳: T-02-06(위협 모델) 대응으로 MAX_BONUS_DICE_MAGNITUDE=20 상한을 추가 — BONUS_DICE 합의 절대값이 상한을 넘으면 UnsupportedModifier로 거부한다. 계획에 명시된 acceptance_criteria는 아니었지만 위협 모델의 mitigate 처분 항목이라 Rule 2로 자동 추가했다"
  - "참은 곳: Modifier 자료구조(resolution.py)를 한 글자도 고치지 않았다 — TARGET_SHIFT/BONUS_DICE/PUSH 세 유형 모두 기존 Modifier(type, value, source) dataclass 그대로 표현된다. 새 수정치 유형을 추가하는 데 플랫폼 자료구조 변경이 전혀 필요 없었다는 것이 이 단계의 핵심 증거다"
  - "참은 곳: grade_for_margin/GradeBand(rulebook.py)도 고치지 않았다 — 이름 목록형(OpenQuest 4종)과 수치 구간형(테스트 전용 NUMERIC_BAND_RULEBOOK_BANDS)이 같은 GradeBand 구조로 통과한다"
  - "수치 구간형 룰북 선언은 rulebooks/에 세 번째 모듈로 출하하지 않고 tests/test_grading_d100.py 안에서만 선언했다 — 세 번째 판정 방식(M1의 d20)이 강제할 때까지 미룬다는 02-01의 결정을 그대로 따랐다"

patterns-established:
  - "ScriptedPercentileRoller가 호출 횟수(tens_call_count/units_call_count)를 셀 수 있게 만들어, '보너스 다이스가 합산 흉내가 아니라 실제로 굴림 도구를 더 부른다'는 것을 테스트가 직접 단언한다"
  - "ReplayRoller.roll_tens/roll_units가 roll_d6과 같은 내부 반복자(_next_roll)를 공유 — 판정 방식과 무관하게 rolls_from_events가 만든 평평한 목록이 기록된 순서 그대로 되먹여진다"

requirements-completed: [RIG-08]

coverage:
  - id: D1
    description: "숫자 가감·목표값 변경·주사위 추가/제거·재굴림 네 유형이 서로 다른 계산 시점에서 실제로 total/target/굴림 절차를 바꾼다"
    requirement: "RIG-08"
    verification:
      - kind: unit
        ref: "tests/test_resolution_d100.py#test_target_shift_changes_target_not_roll"
        status: pass
      - kind: unit
        ref: "tests/test_resolution_d100.py#test_flat_changes_total_not_target"
        status: pass
      - kind: unit
        ref: "tests/test_resolution_d100.py#test_bonus_dice_rolls_tens_twice_and_keeps_smaller"
        status: pass
      - kind: unit
        ref: "tests/test_resolution_d100.py#test_push_d100_recomputes_total_and_grade_from_new_roll_only"
        status: pass
    human_judgment: false
  - id: D2
    description: "보너스/페널티 다이스가 굴림 도구 호출 횟수를 실제로 늘린다(합산 흉내가 아니다) — 채택 규칙은 채택된 십의 자리 기준이고 버려진 십의 자리는 등급 산출에 무관하다"
    requirement: "RIG-08"
    verification:
      - kind: unit
        ref: "tests/test_resolution_d100.py#test_bonus_and_penalty_dice_sum_net_effect"
        status: pass
      - kind: unit
        ref: "tests/test_resolution_d100.py#test_discarded_tens_matching_units_does_not_trigger_doubles"
        status: pass
    human_judgment: false
  - id: D3
    description: "push_d100이 앞선 눈을 지우지 않고 새 눈만으로 재채점하며, PUSH 미허가 판정에는 PushNotPermitted가 난다"
    requirement: "RIG-08"
    verification:
      - kind: unit
        ref: "tests/test_resolution_d100.py#test_push_d100_appends_new_rolls_without_erasing_previous"
        status: pass
      - kind: unit
        ref: "tests/test_resolution_d100.py#test_push_d100_without_push_modifier_raises_push_not_permitted"
        status: pass
      - kind: unit
        ref: "tests/test_resolution_d100.py#test_push_d100_twice_in_a_row_keeps_appending_rolls"
        status: pass
    human_judgment: false
  - id: D4
    description: "등급 밴드가 굴림 범위 전체(1..100 x 대표 기술값)를 빈틈·겹침 없이 덮는다"
    requirement: "RIG-08"
    verification:
      - kind: unit
        ref: "tests/test_grading_d100.py#test_property_every_roll_and_skill_maps_to_exactly_one_openquest_band"
        status: pass
    human_judgment: false
  - id: D5
    description: "이름 목록형과 수치 구간형 등급 선언이 코드 수정 없이 같은 GradeBand 구조로 resolve_d100을 통과한다"
    requirement: "RIG-08"
    verification:
      - kind: unit
        ref: "tests/test_grading_d100.py#test_numeric_band_rulebook_passes_through_resolve_d100_without_code_change"
        status: pass
    human_judgment: false
  - id: D6
    description: "기록된 눈만으로 d100 판정을 재생할 수 있다(보너스 다이스로 눈이 셋인 경우 포함)"
    requirement: "RIG-08"
    verification:
      - kind: unit
        ref: "tests/test_resolution_d100.py#test_resolve_d100_replays_from_recorded_rolls_with_bonus_dice"
        status: pass
      - kind: unit
        ref: "tests/test_resolution_d100.py#test_resolve_d100_replay_exhausted_after_recorded_rolls_consumed"
        status: pass
    human_judgment: false
  - id: D7
    description: "OpenQuest 난이도 다섯 단계(Easy/Simple/Normal/Difficult/Hard)가 선언된 값(+50/+20/0/-20/-50)으로 target을 움직인다"
    requirement: "RIG-08"
    verification:
      - kind: unit
        ref: "tests/test_resolution_d100.py#test_openquest_difficulty_five_levels_shift_target_by_declared_value"
        status: pass
    human_judgment: false
  - id: D8
    description: "전체 테스트(183개)가 회귀 없이 통과하고 import-linter 계약이 모두 kept 상태다"
    verification:
      - kind: unit
        ref: "uv run pytest -q -> 183 passed (1.26s)"
        status: pass
      - kind: integration
        ref: "uv run lint-imports -> 2 kept, 0 broken"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-08-01
status: complete
---

# Phase 2 Plan 2: d100 수정치 네 유형 실제 동작 Summary

**resolve_d100이 이제 숫자 가감·목표값 변경·주사위 추가/제거·재굴림 네 유형을 전부 실제 계산에 반영한다 — 보너스 다이스는 굴림 도구 호출 횟수 자체를 바꾸고(합산 흉내가 아니다), push_d100은 reroll_2d6과 같은 불변식으로 앞선 눈을 보존한 채 새 눈만으로 재채점한다.**

## Performance

- **Duration:** 45 min (approx.)
- **Completed:** 2026-08-01
- **Tasks:** 3 (모두 auto, Task 1·2는 tdd="true")
- **Files modified:** 5 (2 modified 소스, 1 modified 재생 도구, 2 신규 테스트 파일)

## Accomplishments

- `resolve_d100`이 수정치 목록을 한 번 훑어 FLAT/TARGET_SHIFT/BONUS_DICE/PUSH 네 유형으로 분류하고, 굴리기 전(target 계산)·굴림 자체(다이스 개수·채택)·굴린 뒤(FLAT 가산) 세 시점으로 계산 순서를 재구성했다. `_flat_total`을 복사해 유형만 늘리는 접근을 폐기하고, 보너스 다이스가 실제로 `roll_tens()` 호출 횟수를 늘리는 것을 `ScriptedPercentileRoller`의 호출 카운터로 직접 단언한다.
- `push_d100`이 신규 — `reroll_2d6`과 정확히 같은 불변식(앞선 눈 보존, 새 눈만으로 재계산, modifiers/target 승계)을 따른다. `previous.modifiers`에 PUSH 표식이 없으면 `PushNotPermitted`가 나서, 룰북이 허용하지 않은 재굴림이 조용히 일어나지 않는다.
- `rulebooks/openquest.py`에 `OPENQUEST_DIFFICULTY`(다섯 단계)와 `difficulty_modifier()`가 신규 — SRD 난이도 표 그대로(+50/+20/0/-20/-50)를 TARGET_SHIFT 수정치로 표현한다.
- `tests/test_grading_d100.py` 신규(8개 테스트) — hypothesis 성질 테스트로 OpenQuest 네 밴드가 굴림 범위 전체를 빈틈·겹침 없이 덮는다는 것, 선언 순서가 크리티컬/성공을 가른다는 것, 이름 목록형·수치 구간형(테스트 전용 `NUMERIC_BAND_RULEBOOK_BANDS`)이 같은 `GradeBand` 구조로 둘 다 통과한다는 것을 증명한다.
- `ReplayRoller`에 `roll_tens`/`roll_units`가 신규 — `roll_d6`과 같은 내부 반복자를 공유해, 보너스 다이스로 눈이 셋인 d100 판정도 기록된 순서 그대로 재생된다.
- 전체 테스트 154(02-01 종료 시점) → 183개(신규 29개), `uv run pytest -q` 1.26초에 전체 통과, `lint-imports` 2 kept, `ruff check .` 0 위반.

## Task Commits

Each task followed RED→GREEN (tdd="true"):

1. **Task 1: 세 시점의 수정치를 실제로 계산한다**
   - `4d42ff0` (test) — 실패하는 테스트 13개 추가 (RED)
   - `85630e2` (feat) — resolve_d100 재구성 + OpenQuest 난이도 선언 (GREEN)
2. **Task 2: 푸시 롤 — 앞선 눈을 지우지 않고 이어 붙인다**
   - `174bbd1` (test) — 실패하는 테스트 7개 추가 (RED)
   - `af45864` (feat) — push_d100/PushNotPermitted 구현 (GREEN)
3. **Task 3: 등급 구간 성질 테스트 + 재생 확인** — `81e3b95` (test) — ReplayRoller 확장 + test_grading_d100.py 신규(8개) + 재생 테스트 2개 추가

## Files Created/Modified

- `src/gptrpg/rules_core/resolution_d100.py` - `TARGET_SHIFT`/`BONUS_DICE`/`PUSH` 상수, `MAX_BONUS_DICE_MAGNITUDE`, 세 시점 계산 순서로 재작성된 `resolve_d100`, `push_d100`, `PushNotPermitted`
- `src/gptrpg/rulebooks/openquest.py` - `OPENQUEST_DIFFICULTY`(dict), `difficulty_modifier()`
- `src/gptrpg/event_log/replay_roller.py` - `ReplayRoller.roll_tens`/`roll_units`(내부 반복자 공유), `_next_roll` 공통 헬퍼로 리팩터
- `tests/test_resolution_d100.py` - 신규, 수정치 네 유형(13) + 푸시(7) + 재생(2) = 22개
- `tests/test_grading_d100.py` - 신규, 등급 산출 행동·성질 테스트 8개

## Decisions Made

- **고친 곳:** `resolve_d100`의 계산 순서를 세 시점(굴리기 전/굴림 자체/굴린 뒤)으로 재구성했다 — 02-01의 "수정치 전면 거부" 임시 게이트를 걷어내고 실제 계산으로 교체했다.
- **고친 곳(Rule 2, 위협 모델 대응):** T-02-06(보너스 다이스 개수로 인한 DoS, 위협 모델 disposition=mitigate)에 대응해 `MAX_BONUS_DICE_MAGNITUDE=20` 상한을 추가했다. 계획의 `<action>`/`<acceptance_criteria>`에는 명시되지 않았지만, 위협 등록부의 mitigate 처분은 정확성 요구사항으로 다뤄야 한다는 실행 규칙(Rule 2)에 따라 자동으로 추가했다. `BONUS_DICE` 합의 절대값이 상한을 넘으면 `UnsupportedModifier`로 거부한다.
- **참은 곳(핵심 증거):** `resolution.py`의 `Modifier` dataclass(`type`, `value`, `source`)를 한 글자도 고치지 않았다 — 새 수정치 유형 세 개(TARGET_SHIFT/BONUS_DICE/PUSH)가 전부 기존 자료구조 그대로 표현된다. 새 계산 능력을 추가하는 데 플랫폼 자료구조 변경이 전혀 필요 없었다.
- **참은 곳:** `rulebook.py`의 `GradeBand`/`grade_for_margin`도 고치지 않았다 — 이름 목록형(OpenQuest 4종)과 수치 구간형(테스트 전용 선언)이 같은 구조로 둘 다 통과한다.
- **수치 구간형 룰북 배치:** `NUMERIC_BAND_RULEBOOK_BANDS`는 `tests/test_grading_d100.py` 안에서만 선언했다 — `rulebooks/`에 세 번째 룰북을 출하하지 않는다(02-01 결정, 세 번째 판정 방식은 M1로 미뤄짐).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] BONUS_DICE 합에 상한(MAX_BONUS_DICE_MAGNITUDE=20) 추가**
- **Found during:** Task 1 구현 중, 위협 모델 재확인 시
- **Issue:** 계획의 `<action>`/`<acceptance_criteria>`에는 없었지만, 위협 모델의 T-02-06(DoS, disposition=mitigate)이 이 태스크의 파일(`resolution_d100.py`)을 정확히 지목한다 — BONUS_DICE 값이 통제되지 않으면 굴림 도구 호출 횟수가 무한정 커질 수 있다
- **Fix:** `dice_delta`의 절대값이 20을 넘으면 `UnsupportedModifier(BONUS_DICE, ...)`를 던지도록 추가. 상한값과 사유를 모듈 상수 docstring에 명시
- **Files modified:** `src/gptrpg/rules_core/resolution_d100.py`
- **Verification:** 기존 13개 테스트 전부 통과(상한 이하 범위만 사용하므로 회귀 없음), 전체 183개 테스트 통과
- **Committed in:** `85630e2` (Task 1 feat 커밋)

---

**Total deviations:** 1 auto-fixed (Rule 2 - 위협 모델 mitigate 처분 반영)
**Impact on plan:** 계획에 없던 방어 코드 한 줄 추가. 기존 테스트 범위를 벗어나지 않아 회귀 없음. 스코프 확장 없음.

## Issues Encountered

None - 계획의 의사코드(02-RESEARCH.md Pattern 2)와 02-01이 남긴 인터페이스(`resolve_d100(roller, move, modifiers, skill, bands)`)가 정확히 일치해서 별도 문제 해결 없이 진행했다.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `resolve_d100`/`push_d100`이 이제 네 유형을 전부 계산하므로, 02-03(적/NPC 엔티티)이 수정치 출처(장비/부상/상태)를 실제로 붙일 수 있는 계산 기반이 갖춰졌다.
- `NUMERIC_BAND_RULEBOOK_BANDS`가 테스트 파일 안에만 있다는 사실은 02-04의 `02-INTERFACE-CHANGES.md`가 "세 번째 룰북(M1의 d20)이 등장할 때 재확인해야 할 항목"으로 참조해야 한다.
- `MAX_BONUS_DICE_MAGNITUDE` 상한(Rule 2로 추가된 방어 코드)은 02-04에서 위협 모델 갱신 시 T-02-06의 "mitigated" 상태로 반영돼야 한다.
- 02-01-SUMMARY가 이미 "참은 곳"으로 기록한 `rules_core/grading.py`의 `grade_for_total`(2d6용, 미제거) 항목은 이번 단계에서 손대지 않았다 — 여전히 02-04에서 재확인이 필요하다.

---
*Phase: 02-two-rulebooks-one-vessel*
*Completed: 2026-08-01*

## Self-Check: PASSED

All created/modified files exist on disk (5/5 checked). All five task commit hashes (`4d42ff0`, `85630e2`, `174bbd1`, `af45864`, `81e3b95`) found in git log.
