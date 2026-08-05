---
phase: 02-two-rulebooks-one-vessel
plan: 01
subsystem: rules-engine
tags: [pydantic, d100, rulebook-declaration, event-schema-versioning, import-linter]

requires:
  - phase: 01-rules-core-and-event-log
    provides: "2d6 판정(resolve_2d6/reroll_2d6), 여섯 종류 사건 스키마, 세션 액터의 검증->규칙코어->순번->append 파이프라인, .importlinter 계약"
provides:
  - "d100 롤언더 판정 방식(resolve_d100) — resolve_2d6과 같은 CheckOutcome 모양, 같은 check_resolved 사건 종류"
  - "룰북이 등급 집합·판정 방식을 스스로 선언하는 구조(rules_core/rulebook.py + gptrpg/rulebooks/)"
  - "OpenQuest SRD(CC BY 4.0) 등급 4종 실제 콘텐츠 + LICENSES.md 표기"
  - "실패 집계가 등급 이름이 아니라 룰북 선언 신호(counts_as_failure)로 계산되는 리듀서"
  - "EVENT_SCHEMA_VERSION 1->2 + 판 1 옛 기록 해석 경로(하위호환)"
affects: [02-02-modifiers, 02-03-entities, 02-04-interface-changes, phase-6-measurement]

actuals:
  tokens: 9337
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "룰북 선언(GradeBand/Rulebook)을 rules_core가 갖되, 선언 내용(openquest.py/dungeonworld_like.py)은 별도 계층에 둔다 — rules_core -> rulebooks import는 .importlinter layers 계약으로 기계적으로 금지"
    - "margin 부호 규약으로 굴림 방향(roll-over vs roll-under)을 룰북 데이터에서 숨긴다: margin = total-target 또는 target-total, 둘 다 margin>=0이 성공"
    - "판정 후 항상 require_band(rulebook.grade_bands, outcome.grade)로 이름->밴드를 재조회한다 — CheckOutcome.grade는 문자열일 뿐이고 counts_as_failure의 권위는 언제나 선언 쪽에 있다"

key-files:
  created:
    - src/gptrpg/rules_core/rulebook.py
    - src/gptrpg/rules_core/resolution_d100.py
    - src/gptrpg/rulebooks/__init__.py
    - src/gptrpg/rulebooks/openquest.py
    - src/gptrpg/rulebooks/dungeonworld_like.py
    - LICENSES.md
    - tests/test_tracer_d100.py
    - tests/test_reducer_failure_count.py
  modified:
    - src/gptrpg/event_log/schema.py
    - src/gptrpg/rules_core/reducer.py
    - src/gptrpg/rules_core/grading.py
    - src/gptrpg/rules_core/resolution.py
    - src/gptrpg/rules_core/dice.py
    - src/gptrpg/session_actor/actor.py
    - src/gptrpg/session_actor/live_roller.py
    - src/gptrpg/cli/main.py
    - .importlinter
    - tests/conftest.py
    - tests/test_event_log.py
    - tests/test_session_actor.py

key-decisions:
  - "Task 1 체크포인트: option-a 선택 — EVENT_SCHEMA_VERSION 1->2, CheckResolved.counts_as_failure 필수 필드, 리듀서에 판 1 해석 경로(_legacy_v1_counts_as_failure). 이미 쓰인 판 1 기록은 손대지 않는다(D-12)."
  - "Grade를 event_log/schema.py와 rules_core/grading.py 양쪽에서 Literal[3종]->str로 넓혔다(promote, RESEARCH Pattern 1). 던전월드 세 이름은 플랫폼 타입에서 rulebooks/dungeonworld_like.py의 한 룰북 내용으로 격하."
  - "rules_core/grading.py의 grade_for_total은 이번 단계에서 고치지 않는다 — 세션 액터가 그 함수가 돌려준 이름을 dungeonworld_like.py 선언과 대조해 counts_as_failure를 읽는 식으로, 이름의 권위만 선언 쪽으로 옮겼다. 완전 제거는 세 번째 룰북(M1의 d20)이 강제할 때로 미룬다."
  - "resolve_d100은 이 태스크에서 어떤 수정치 유형도 지원하지 않는다(자리만 열어둔 것이 아니라 실제로 예외로 거부) — 수정치 네 유형은 02-02-PLAN의 몫."

patterns-established:
  - "룰북 등록소(RULEBOOKS dict + get_rulebook)를 session_actor가 조회 — rules_core는 절대 rulebooks를 모른다"
  - "PercentileRoller Protocol을 Roller와 나란히 추가(확장이지 변경이 아니다) — LiveRoller가 상속 없이 둘 다 만족"

requirements-completed: [RIG-08, HYP-03]

coverage:
  - id: D1
    description: "d100 판정 한 번이 명령 -> 룰북 선언 조회 -> 순수 판정 함수(resolve_d100) -> 같은 CheckOutcome 모양 -> check_resolved 사건 -> 저장 -> rebuild_state 재구성까지 실제로 돈다"
    requirement: "RIG-08"
    verification:
      - kind: e2e
        ref: "tests/test_tracer_d100.py#test_openquest_success_check_records_and_reconstructs"
        status: pass
      - kind: e2e
        ref: "tests/test_tracer_d100.py#test_openquest_doubles_over_skill_is_fumble_and_counts_as_failure"
        status: pass
    human_judgment: false
  - id: D2
    description: "OpenQuest 네 등급 이름(critical/success/failure/fumble)이 rules_core/event_log/session_actor 어디에도 문자열로 등장하지 않는다"
    requirement: "RIG-08"
    verification:
      - kind: other
        ref: "grep -rEc 'critical|fumble' src/gptrpg/rules_core src/gptrpg/event_log src/gptrpg/session_actor | grep -v ':0$' -> empty"
        status: pass
    human_judgment: false
  - id: D3
    description: "실패 집계(failure_count)가 등급 이름 비교가 아니라 룰북 선언 신호(counts_as_failure)로 계산된다 — 던전월드 실패 등급 이름을 가졌지만 counts_as_failure=false인 사건은 실패로 세어지지 않는다"
    requirement: "RIG-08"
    verification:
      - kind: unit
        ref: "tests/test_reducer_failure_count.py#test_v2_miss_grade_with_counts_as_failure_false_does_not_increment"
        status: pass
      - kind: unit
        ref: "tests/test_reducer_failure_count.py#test_all_registered_rulebooks_failure_band_count_matches_declared_counts_as_failure"
        status: pass
    human_judgment: false
  - id: D4
    description: "EVENT_SCHEMA_VERSION 1로 기록된 옛 사건(counts_as_failure 칸이 아예 없는 기록)을 판 2 코드로 접어도 판 1 때와 같은 실패 수가 나온다"
    requirement: "HYP-03"
    verification:
      - kind: unit
        ref: "tests/test_reducer_failure_count.py#test_v1_payload_without_counts_as_failure_field_uses_legacy_grade_name_rule"
        status: pass
      - kind: unit
        ref: "tests/test_reducer_failure_count.py#test_v1_and_v2_events_mixed_in_one_record_each_rule_applies_independently"
        status: pass
    human_judgment: false
  - id: D5
    description: "룰북 선언에 없는 등급 이름이나 등록되지 않은 rulebook_id는 사건이 기록되기 전에 CommandRejected로 거부되고 순번을 소모하지 않는다"
    requirement: "RIG-08"
    verification:
      - kind: e2e
        ref: "tests/test_tracer_d100.py#test_unknown_rulebook_id_is_rejected_and_appends_nothing"
        status: pass
    human_judgment: false
  - id: D6
    description: "Phase 1의 142개 회귀 테스트가 하나도 깨지지 않고 그대로 통과한다(신규 12개 추가, 총 154개)"
    verification:
      - kind: unit
        ref: "uv run pytest -q -> 154 passed"
        status: pass
    human_judgment: false
  - id: D7
    description: "gptrpg.rules_core의 어떤 모듈도 gptrpg.rulebooks를 import하지 않는다(D32) — .importlinter layers 계약이 기계적으로 강제"
    requirement: "RIG-08"
    verification:
      - kind: integration
        ref: "uv run lint-imports -> 'cli -> session_actor -> rulebooks -> (rules_core | event_log) KEPT'"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-08-01
status: complete
---

# Phase 2 Plan 1: 판정 방식이 다른 두 번째 룰북(OpenQuest d100) 트레이서 Summary

**d100 롤언더 판정이 룰북 선언(OpenQuest SRD, CC BY 4.0) 하나만으로 세션 액터를 통해 기록·재구성되고, 실패 집계는 등급 이름이 아니라 룰북이 선언한 counts_as_failure 신호로 계산된다.**

## Performance

- **Duration:** 40 min (approx.)
- **Completed:** 2026-08-01
- **Tasks:** 3 (checkpoint:decision + tracer + auto)
- **Files modified:** 19 (12 modified, 8 created)

## Accomplishments

- Task 1 체크포인트(EVENT_SCHEMA_VERSION 처리 방식)가 사용자 승인으로 option-a로 확정 — 판 올림 + 판 1 해석 경로.
- `rules_core/rulebook.py`(GradeBand/Rulebook/grade_for_margin/require_band)와 `rules_core/resolution_d100.py`(resolve_d100/percentile_value)가 신규 — `resolution.py`의 Modifier/CheckOutcome/UnsupportedModifier를 다시 정의하지 않고 그대로 재사용해, 두 판정 방식이 "같은 모양" 위에서 돈다는 것을 실물로 증명.
- `gptrpg/rulebooks/` 계층이 신규 — OpenQuest(등급 4종, 실제 SRD 콘텐츠)와 dungeonworld_like(Phase 1의 암묵적 세 이름을 명시 선언으로 이전)를 등록. `.importlinter` layers 계약이 `rules_core -> rulebooks` import를 기계적으로 막는다.
- `session_actor/actor.py`가 `ResolveCheck.rulebook_id`(기본값 dungeonworld_like로 Phase 1 호출부 무손상)와 `_RESOLVERS` 배선으로 두 판정 방식을 나눈다. 판정 직후 항상 `require_band`로 이름->밴드를 재조회해 `counts_as_failure`를 페이로드에 싣는다 — 오타난 등급 이름이나 등록되지 않은 rulebook_id는 순번 소모 전에 `CommandRejected`.
- `reducer.py`가 `miss_count`를 `failure_count`로 개명하고, `check_resolved` 분기가 등급 이름 비교 대신 `counts_as_failure` 신호(판 2)나 판 1 해석 함수(`_legacy_v1_counts_as_failure`, 판 1)로 계산한다.
- `LICENSES.md` 신규 — OpenQuest SRD 첨부 문구를 02-RESEARCH.md 인용과 문자 단위로 동일하게 옮김.
- 새 테스트 12개(`test_tracer_d100.py` 5개, `test_reducer_failure_count.py` 6개, `test_event_log.py` 파라미터라이즈 1개 증가) + 기존 픽스처 갱신. `uv run pytest -q` 154 passed(회귀 0), `lint-imports` 2 kept, `ruff check .` 0 위반.

## Task Commits

Each task was committed atomically:

1. **Task 1: 사건 기록 형식 결정** — checkpoint:decision, 사용자가 option-a 선택(커밋 없음, 결정만 기록)
2. **Task 2: d100 판정 한 번이 명령에서 재구성까지 끝까지 돈다** — `b7229e4` (feat)
3. **Task 3: 실패 집계가 이름이 아니라 선언 신호로 계산됨을 못 박는다** — `56e1446` (test)

_Task 1은 코드 변경이 없는 순수 결정 체크포인트다 — 그 결정(option-a)은 Task 2의 구현 자체에 반영되었다._

## Files Created/Modified

- `src/gptrpg/rules_core/rulebook.py` - GradeBand/Rulebook 선언 모양, grade_for_margin/require_band
- `src/gptrpg/rules_core/resolution_d100.py` - resolve_d100/percentile_value, resolution.py의 CheckOutcome 재사용
- `src/gptrpg/rulebooks/__init__.py` - RULEBOOKS 등록소, get_rulebook, UnknownRulebook
- `src/gptrpg/rulebooks/openquest.py` - OpenQuest SRD 등급 4종(critical/success/fumble/failure)
- `src/gptrpg/rulebooks/dungeonworld_like.py` - grade_for_total 경계 규칙을 그대로 선언으로 이전
- `LICENSES.md` - OpenQuest SRD CC BY 4.0 첨부 문구
- `src/gptrpg/event_log/schema.py` - EVENT_SCHEMA_VERSION 2, Grade->str, CheckResolved.counts_as_failure
- `src/gptrpg/rules_core/reducer.py` - failure_count 개명, 판 1/판 2 해석 분기
- `src/gptrpg/rules_core/grading.py` - Grade 별칭 str로 확장(grade_for_total 로직은 무손상)
- `src/gptrpg/rules_core/resolution.py` - UnsupportedModifier에 resolver 키워드(기본값 유지, 메시지 무손상)
- `src/gptrpg/rules_core/dice.py` - PercentileRoller Protocol 추가(Roller 무손상)
- `src/gptrpg/session_actor/actor.py` - ResolveCheck.rulebook_id, _RESOLVERS, require_band 배선
- `src/gptrpg/session_actor/live_roller.py` - roll_tens/roll_units 추가
- `src/gptrpg/cli/main.py` - miss_count -> failure_count 읽기 자리 갱신(라벨 문구는 무손상)
- `.importlinter` - layers 계약에 gptrpg.rulebooks 추가
- `tests/test_tracer_d100.py` - 신규, d100 끝-대-끝 5개
- `tests/test_reducer_failure_count.py` - 신규, 실패 집계 성질 테스트 6개
- `tests/conftest.py` - CheckResolved 생성 3곳에 counts_as_failure 추가(옛 기록을 고친 것이 아니라 새로 만드는 판 2 기록)
- `tests/test_event_log.py` - UNIQUE_FIELDS에 counts_as_failure 추가, miss_count->failure_count 단언
- `tests/test_session_actor.py` - miss_count->failure_count 단언

## Decisions Made

- **Task 1 체크포인트(option-a):** `EVENT_SCHEMA_VERSION`을 1에서 2로 올리고 `CheckResolved.counts_as_failure`를 필수 필드로 추가했다. 리듀서에 판 1 해석 경로(`_legacy_v1_counts_as_failure`, `grade == "miss"`)를 별도 함수로 격리해, 이미 쓰인 판 1 기록은 전혀 건드리지 않았다.
- **Grade promote:** `Grade`를 `event_log/schema.py`와 `rules_core/grading.py` 양쪽에서 `Literal[3종]`에서 `str`로 넓혔다. 던전월드 세 이름은 플랫폼 타입이 아니라 `rulebooks/dungeonworld_like.py`가 선언하는 한 룰북의 내용으로 격하했다.
- **참은 곳:** `rules_core/grading.py`의 `grade_for_total`은 이번 단계에서 지우지 않았다 — 세션 액터가 그 함수가 돌려준 이름을 룰북 선언 집합과 대조해 `counts_as_failure`를 읽게 만들어, 계산은 그대로 두고 이름의 권위만 선언 쪽으로 옮겼다. 완전 제거는 세 번째 룰북(M1의 d20)이 같은 2d6 등급 이름을 다르게 쓰려 할 때로 미룬다 — 이 항목은 02-04-PLAN의 `02-INTERFACE-CHANGES.md`에 "고치고 싶었지만 참았다"로 다시 기록되어야 한다.
- **수정치 범위 제한:** `resolve_d100`은 이번 태스크에서 어떤 수정치 유형도 지원하지 않는다(빈 목록이 아니면 즉시 `UnsupportedModifier`). 자리만 열어두는 것이 아니라 아직 지원하지 않는다는 사실 자체가 예외로 드러난다 — 네 유형은 02-02-PLAN의 몫이다.

## Deviations from Plan

None - plan(및 체크포인트에서 확정된 option-a)을 그대로 실행했다. 계획에 없던 버그 수정이나 누락 보완은 없었다.

## Issues Encountered

- 최초 구현에서 `event_log/schema.py`의 주석 하나가 "OpenQuest의 critical/success/failure/fumble" 문자열을 그대로 담고 있어, 태스크 2 검증 기준(`grep -rEc "critical|fumble" src/gptrpg/rules_core src/gptrpg/event_log src/gptrpg/session_actor`가 0이어야 함)에 걸렸다. 주석에서 구체적 등급 이름을 빼고 "gptrpg.rulebooks 아래 각 룰북 선언에만 있다"는 일반 서술로 바꿔 해결했다(Task 2 커밋에 포함, 별도 deviation 커밋 없음).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `rules_core/rulebook.py`와 `gptrpg/rulebooks/` 계층이 02-02(수정치 네 유형)·02-03(적/NPC 엔티티)이 바로 이어 쓸 수 있는 형태로 자리 잡았다.
- `resolve_d100`이 아직 수정치를 하나도 지원하지 않으므로, 02-02-PLAN이 바로 이어 붙일 첫 확장 지점이 명확하다.
- `02-04-PLAN`의 `02-INTERFACE-CHANGES.md`가 참고해야 할 "고친 곳"/"참은 곳" 기록이 이 SUMMARY의 Decisions Made 절에 이미 정리되어 있다.
- Phase 6 MEAS-03(실패는 많은데 시계가 안 돈다) 채점이 의존하는 `failure_count`가 이제 룰북 신호 기반이라, 세 번째 룰북이 들어와도 채점 로직이 조용히 틀릴 위험이 없다.

---
*Phase: 02-two-rulebooks-one-vessel*
*Completed: 2026-08-01*

## Self-Check: PASSED

All created files exist on disk (9/9 checked). Both task commit hashes (`b7229e4`, `56e1446`) found in git log.
