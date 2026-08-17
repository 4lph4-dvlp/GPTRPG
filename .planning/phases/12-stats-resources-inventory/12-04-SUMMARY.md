---
phase: 12-stats-resources-inventory
plan: 04
subsystem: rules-engine
tags: [rulebook-data, outcome-categories, grade-bands, dataclasses]

requires:
  - phase: 12-stats-resources-inventory
    provides: "12-02 — 「축 · 동작 · 양」 세 칸을 주사위식까지 넓힌 ResourceChangeDecl/ResourceOp, ResourceOperation 여덟 값, apply_resource_op의 형태별 갈래"
  - phase: 12-stats-resources-inventory
    provides: "12-01 — GradeBand·Rulebook·resource_axes 최초 형식"
provides:
  - "GradeBand.succeeded/.costs — 「성공했나」·「대가가 붙나」·「실패로 세나」 세 칸이 서로 독립(D-13/D-14)"
  - "OutcomeCategory/OutcomeList — 결과 카테고리 닫힌 목록 그릇, 빈 목록·NO_CHANGE_CATEGORY_ID가 정상값(RULE-13)"
  - "RetroDeclarationDecl — 소급 선언 허용 여부 + 비용 축·동작 잠금(D-16, RULE-16)"
  - "validate_outcome_list/require_outcome_category/ordered_categories — 등록 시점 축·형태·동작 대조 + 선언 순서 고정 적용"
  - "세 룰북의 실제 결과 목록·소급 선언 데이터(DUNGEONWORLD_OUTCOME_LIST/OPENQUEST_OUTCOME_LIST/CAIRN_OUTCOME_LIST/CAIRN_RETRO_DECLARATION)"
affects: [12-06-discretionary-ruling]

actuals:
  tokens: 16126
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "「없다」를 1급 값으로 두는 관례가 세 번째로 반복됨 — check_trigger_mode(11-04) → difficulty_levels(12-01) → outcome_list/retro_declaration(12-04), 전부 기본값이 '이 룰북엔 그 개념이 없다'를 뜻한다"
    - "룰북과의 대조가 필요한 검증은 dataclass __post_init__이 아니라 별도 함수(validate_outcome_list)로 — validate_entity_axes/validate_move_stats가 세운 배치를 그대로 재사용"

key-files:
  created: []
  modified:
    - src/gptrpg/rules_core/rulebook.py
    - src/gptrpg/rulebooks/dungeonworld_like.py
    - src/gptrpg/rulebooks/openquest.py
    - src/gptrpg/rulebooks/cairn.py
    - src/gptrpg/web/routes_actions.py
    - tests/test_rulebook.py
    - tests/test_grading_d100.py
    - tests/test_session_actor.py
    - tests/test_web_characters.py

key-decisions:
  - "GradeBand의 succeeded/costs를 counts_as_failure와 같은 이유로 기본값 없는 필수 칸으로 뒀다 — 세 룰북 열한 개 등급을 즉시 채우게 강제(RULE-14 edge probe 플래그, 계획이 사람 확인 권장으로 표시)"
  - "succeeded/costs는 CheckResolved 사건에 싣지 않는다 — 읽는 자리(session_actor/web)가 이미 rulebook_id를 알아 require_band로 직접 읽을 수 있어, EVENT_SCHEMA_VERSION을 또 올릴 필요가 없다"
  - "OutcomeList.__post_init__은 목록 자체의 정합성(중복 식별자·max_picks 범위)만, 룰북과의 대조(축 존재·form·operation)는 validate_outcome_list 별도 함수로 — 등록 시점 자동 배선(rulebooks/__init__.py)은 이 계획의 files_modified에 없어 하지 않았다. 그 대신 세 룰북 전부에 대해 validate_outcome_list가 예외 없이 통과한다는 전용 시험으로 실제 데이터를 검증했다"
  - "Cairn의 소급 선언 비용 축을 Hit Protection이 아니라 Inventory로 골랐다 — SRD가 실제로 정한 사실은 'Fatigue가 소지품 칸을 차지한다'는 것뿐이라(LICENSES.md/CAIRN_RESOURCE_AXES 주석), 그 기존 SRD 조항을 그대로 재사용했다(operation=fill)"
  - "OpenQuest의 outcome_list는 빈 튜플로 남긴다 — 인용 중인 SRD 범위(스킬 판정 등급 산출)가 실패 결과를 절차로 정하지 않아, 지어내 넣지 않는 이 파일의 기존 규율을 따랐다"
  - "던전월드류 결과 목록 카테고리 식별자는 던전월드 GM 대응 목록 원문이 아니라 플랫폼 어휘로 새로 지었다(라이선스 경계, T-12-19) — '자원을 소모시킨다' 항목에 12-02의 주사위식 통로(-1d4)를 실제 데이터에 처음 물렸다"

patterns-established:
  - "「성공했나」·「대가가 붙나」·「실패로 세나」 세 독립 칸이 GradeBand의 표준 모양 — 다음 등급 축(예: 크리티컬 여부)이 필요해지면 같은 방식으로 나란히 추가한다"
  - "결과 카테고리는 축·동작·양만 담고 서술 문장 필드는 절대 두지 않는다(D-11) — OutcomeCategory의 필드 두 개(category_id/changes)가 이 원칙을 코드로 못박는다"

requirements-completed: [RULE-14]
# RULE-13/RULE-16도 이 계획의 frontmatter `requirements`에 있었지만, 12-06-PLAN.md의
# `requirements`에도 RULE-13/RULE-16이 나란히 있다(그릇+데이터는 12-04, 실제 선택+
# 확인+적용 경로는 12-06) — 여러 계획에 걸친 요구사항을 한쪽 계획만으로 Complete로
# 찍지 않는다. REQUIREMENTS.md에도 두 항목을 "Pending (12-04 container+data done,
# 12-06 pending)"으로 정정해 남겼다. RULE-14는 이 계획 하나로 완전히 닫힌다(다른
# 어떤 계획의 requirements에도 없음).

coverage:
  - id: D1
    description: "등급 밴드가 「성공했나」·「대가가 붙나」·「실패로 세나」 세 독립 칸을 갖고, succeeded=True이면서 counts_as_failure=True인 조합도 등록을 거부하지 않는다(D-13/D-14, RULE-14) — 세 룰북 열한 개 등급이 실제로 이 세 칸을 채웠고 counts_as_failure 값은 이전과 동일하다"
    requirement: "RULE-14"
    verification:
      - kind: unit
        ref: "tests/test_rulebook.py#test_succeeded_and_counts_as_failure_can_both_be_true_registration_not_rejected"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_dungeonworld_weak_hit_band_has_succeeded_true_costs_true_not_a_failure"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_dungeonworld_counts_as_failure_values_unchanged_by_new_fields"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_openquest_counts_as_failure_values_unchanged_by_new_fields"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_cairn_counts_as_failure_values_unchanged_by_new_fields"
        status: pass
    human_judgment: false
  - id: D2
    description: "결과 카테고리 닫힌 목록의 그릇이 있고, 빈 목록·NO_CHANGE_CATEGORY_ID가 정상값이며, 존재하지 않는 축·form=none·form-operation 어긋남·중복 식별자·순서 위반이 전부 등록 시점(validate_outcome_list/OutcomeList.__post_init__)에 거부된다(RULE-13)"
    requirement: "RULE-13"
    verification:
      - kind: unit
        ref: "tests/test_rulebook.py#test_outcome_list_with_empty_categories_is_normal_and_registers"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_validate_outcome_list_rejects_unknown_axis_name"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_validate_outcome_list_rejects_none_form_axis"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_validate_outcome_list_rejects_form_operation_mismatch"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_ordered_categories_ignores_pick_order_uses_declaration_order"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_ordered_categories_rejects_the_same_category_picked_twice"
        status: pass
    human_judgment: false
  - id: D3
    description: "세 룰북이 각자의 스펙트럼 위치에 맞는 결과 목록을 실제로 선언했다(던전월드류는 다섯 항목 중 하나가 no-change, OpenQuest·Cairn은 빈 목록) — Cairn만 소급 선언과 그 비용 축(Inventory/fill)을 선언한다(RULE-16, D-16)"
    requirement: "RULE-16"
    verification:
      - kind: unit
        ref: "tests/test_rulebook.py#test_dungeonworld_outcome_list_has_at_least_four_categories_with_changes"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_dungeonworld_outcome_list_absorbs_the_former_miss_hp_cost_constant"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_openquest_outcome_list_is_empty"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_cairn_allows_retro_declaration_with_a_locked_cost_axis"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_all_three_rulebooks_pass_validate_outcome_list"
        status: pass
      - kind: integration
        ref: ".venv/bin/python -m pytest -q (1090 passed, includes tests/test_web_actions.py exercising the routes_actions.py miss-cost path unchanged)"
        status: pass
    human_judgment: false

duration: ~40min
completed: 2026-08-17
status: complete
---

# Phase 12 Plan 4: 등급의 세 독립 칸 + 결과 카테고리 닫힌 목록 Summary

**등급 밴드가 「성공했나」·「대가가 붙나」·「실패로 세나」 세 독립 칸을 갖게 됐고, 판정 결과에 붙는 닫힌 목록(결과 카테고리)을 룰북이 선언하는 그릇이 생겼다 — 던전월드류가 다섯 항목(그중 하나는 「이번엔 안 변한다」)을 실제로 선언하고, Cairn만 소지품 소급 선언과 그 비용 축을 선언한다.**

## Performance

- **Duration:** 약 40분
- **Tasks:** 3/3
- **Files modified:** 9개 (계획 원문 8개 + 편차로 1개 추가)

## Accomplishments

- **등급 세 칸 독립(D-13/D-14, RULE-14)** — `GradeBand`에 `succeeded`·`costs`를 `counts_as_failure` 옆에 나란히 더했다. 셋 다 기본값 없는 필수 칸이고, `succeeded=True`이면서 `counts_as_failure=True`인 조합도 등록을 거부하지 않는다 — 「성공했는데도 상황은 나빠진다」를 쓰는 룰북을 표현할 수 있다는 것이 이 계획이 지키는 성질 자체다. 세 룰북 열한 개 등급을 실제로 채웠고(`weak_hit`은 D-13이 직접 든 예 그대로 `succeeded=True, costs=True, counts_as_failure=False`), `counts_as_failure` 값은 이전과 한 글자도 안 바뀌었다.
- **결과 카테고리 닫힌 목록 그릇(RULE-13)** — `OutcomeCategory`(category_id + changes, 서술 문장 필드 없음)·`OutcomeList`(빈 목록·`NO_CHANGE_CATEGORY_ID`가 정상값, `max_picks`가 D-12)·`RetroDeclarationDecl`(D-16)을 신설했다. `Rulebook.outcome_list`/`.retro_declaration`은 기본값이 「이 룰북엔 그 개념이 없다」다 — `check_trigger_mode`가 세운 같은 판단을 세 번째로 반복한다. `validate_outcome_list`가 축 존재·`form != "none"`·form-operation 대응(`_FORM_ALLOWED_OPERATIONS`가 `resource_change.py` 도크스트링의 표를 등록 시점 검증용으로 거울처럼 옮김)을 대조하고, `ordered_categories`가 고른 순서를 무시하고 룰북 선언 순서로 적용 순서를 고정한다(재생 일치).
- **세 룰북의 실제 데이터(RULE-13/RULE-16)** — 던전월드류는 다섯 항목(대상을 다치게 한다·가진 것을 빼앗는다·자원을 소모시킨다·대가를 요구하되 이득을 준다·이번엔 안 변한다)을 선언했다. 카테고리 식별자는 던전월드 GM 대응 목록 원문이 아니라 이 저장소 어휘로 새로 지었다(라이선스 경계). 12-01이 남긴 임시 상수 `DUNGEONWORLD_MISS_HP_COST`(체력 -6)를 그대로 흡수했고, 「자원을 소모시킨다」 항목은 12-02가 연 주사위식 통로(`"-1d4"`)를 실제 룰북 데이터에 처음 물렸다. OpenQuest·Cairn은 빈 목록이다(SRD가 실패 결과를 절차로 정하지 않는다, 지어내지 않는다). Cairn만 소급 선언을 허용하고 비용 축을 `Inventory`(`operation="fill"`)로 잠갔다 — SRD가 실제로 정한 「Fatigue가 소지품 칸을 차지한다」는 사실을 그대로 재사용했고, 소지품을 세는 유일한 룰북이라 「없는 것을 쓴다」가 데이터로 성립하는 유일한 자리다.

## Task Commits

1. **Task 1: 등급 세 칸 독립(D-13/D-14, RULE-14)** — `4cdf77b` (feat)
2. **Task 2: 결과 카테고리 닫힌 목록 그릇 + 등록 시점 검증(RULE-13)** — `9da57b9` (feat)
3. **Task 3: 세 룰북의 실제 결과 목록·소급 선언(RULE-13, RULE-16)** — `6bdc331` (feat)

**Plan metadata:** (이 커밋 — docs)

## Files Created/Modified

- `src/gptrpg/rules_core/rulebook.py` — `GradeBand.succeeded`/`.costs`, `OutcomeCategory`/`OutcomeList`/`RetroDeclarationDecl`, `Rulebook.outcome_list`/`.retro_declaration`, `InvalidOutcomeList`/`UnknownOutcomeCategory`, `validate_outcome_list`/`require_outcome_category`/`ordered_categories`, `NO_CHANGE_CATEGORY_ID`
- `src/gptrpg/rulebooks/dungeonworld_like.py` — `DUNGEONWORLD_OUTCOME_LIST`(다섯 항목), `DUNGEONWORLD_MISS_HP_COST` 제거(목록 항목 안으로 흡수)
- `src/gptrpg/rulebooks/openquest.py` — `OPENQUEST_OUTCOME_LIST`(빈 목록, 근거 주석)
- `src/gptrpg/rulebooks/cairn.py` — `CAIRN_OUTCOME_LIST`(빈 목록)·`CAIRN_RETRO_DECLARATION`(Inventory/fill)
- `src/gptrpg/web/routes_actions.py` — (편차) `DUNGEONWORLD_MISS_HP_COST` 참조를 `require_outcome_category(DUNGEONWORLD_LIKE.outcome_list, "대상을 다치게 한다")` 조회로 교체, 값(축·동작·양) 무변경
- `tests/test_rulebook.py` — Task 1/2/3 신규 시험 약 40건, 기존 `GradeBand(...)` 호출부 전체를 새 필수 칸까지 채우도록 갱신
- `tests/test_grading_d100.py`, `tests/test_session_actor.py`, `tests/test_web_characters.py` — 기존 `GradeBand(...)` 생성 자리를 새 필수 칸까지 채우도록 갱신

## Decisions Made

- `succeeded`/`costs`를 `CheckResolved` 사건에 싣지 않는다 — 읽는 자리(session_actor/web)가 이미 `rulebook_id`를 알아 `require_band`로 선언에서 직접 읽을 수 있어, `EVENT_SCHEMA_VERSION`을 또 올릴 필요가 없다(도크스트링에 근거를 남겼다).
- `validate_outcome_list`를 `rulebooks/__init__.py`의 `validate_registered_rulebooks()`에 자동 배선하지 않았다 — 이 계획의 `files_modified`에 그 파일이 없고, Task 3 acceptance criteria가 "세 룰북 전부에 대해 명시적으로 단언하는 시험"을 요구해 그 형태로 구현했다. 자동 배선은 12-06(실제 목록에서 고르고 적용하는 경로)이 다룰 몫으로 남겼다.
- Cairn의 소급 선언 비용 축을 Hit Protection이 아니라 Inventory로 골랐다 — SRD가 실제로 정한 사실은 "Fatigue가 소지품 칸을 차지한다"는 것뿐이라, 지어내지 않고 그 기존 SRD 조항을 그대로 재사용했다.
- 던전월드류 결과 목록 카테고리 식별자는 던전월드 원문("자원을 소모시킨다" 등 GM 대응 목록의 정확한 문구)이 아니라 이 저장소 어휘로 새로 지었다 — 라이선스 경계(T-12-19)를 지키기 위해서다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `web/routes_actions.py`의 `DUNGEONWORLD_MISS_HP_COST` import가 Task 3에서 깨짐**
- **Found during:** Task 3 (`dungeonworld_like.py`에서 `DUNGEONWORLD_MISS_HP_COST` 제거 중)
- **Issue:** Task 3의 acceptance criteria는 "12-01이 두었던 파일 수준 변화 상수 이름이 이 파일에 더 이상 모듈 상수로 남아 있지 않다"를 요구하지만, 그 상수는 `web/routes_actions.py`(이 계획의 `files_modified` 목록 밖)가 6곳에서 직접 참조하고 있었다 — 문자 그대로 지우면 import가 깨져 전체 시험(`uv run pytest -q`, Task 3 자신의 `<verify>`)이 즉시 실패한다.
- **Fix:** `web/routes_actions.py`의 참조를 `require_outcome_category(DUNGEONWORLD_LIKE.outcome_list, "대상을 다치게 한다")` 조회로 교체했다 — `require_difficulty`와 같은 모양의 이름 조회다. 실제로 제출되는 자원 변화 값(축="체력", 동작="delta", 양=-6)은 한 글자도 안 바뀌었다.
- **Files modified:** `src/gptrpg/web/routes_actions.py`
- **Verification:** `.venv/bin/python -m pytest -q` 1090건 전부 통과(`tests/test_web_actions.py`의 기존 미스-비용 경로 시험 포함), `.venv/bin/lint-imports` 4계약 유지
- **Committed in:** `6bdc331` (Task 3 커밋)

---

**Total deviations:** 1 (blocking-issue fix — plan's own file scope excluded a file that the plan's own text change broke)
**Impact on plan:** 값·동작을 하나도 바꾸지 않고 데이터 소스만 교체한 최소 diff. 12-06(실제 목록에서 고르고 확인받고 적용하는 경로)의 영역을 침범하지 않았다 — 이 라우트는 여전히 서버가 단일 고정 항목을 곧바로 결정해서 제출하는 12-01의 탐색적 한 줄기 그대로다.

## Issues Encountered

- **RULE-14 edge probe(자동 분류가 「실패로 세나」를 세 번째 독립 칸으로 포함시킨 것)를 계획 원문대로 따랐다** — 요구사항 원문은 두 축(성공/대가)만 적었지만, D-14가 「실패로 세나」를 세 번째로 더했다는 계획의 판단을 그대로 실행했다. 각 등급의 실제 세 칸 값(특히 OpenQuest·Cairn의 아홉 개)은 이 계획이 SRD 문서에서 도출한 것이라 룰북을 아는 사람의 최종 확인을 권장한다(계획 원문의 「플래그된 가정」 그대로).

## User Setup Required

None - 외부 서비스 설정 불필요.

## Next Phase Readiness

- **RULE-14는 이 계획으로 완전히 닫힌다** — 다른 어떤 계획의 `requirements`에도 없다. **RULE-13/RULE-16은 절반만 닫혔다** — 12-06-PLAN.md의 `requirements`에도 이 둘이 나란히 있다(그릇+데이터는 12-04, 실제 선택+확인+적용 경로는 12-06). REQUIREMENTS.md에 "Pending (12-04 container+data done, 12-06 pending)"으로 정정해 남겼다 — 12-06 완료 시 그때 닫을 것.
- **12-06(재량 판정 확인 관문)이 이어받을 자리:** `Rulebook.outcome_list`에서 실제로 골라 사람 확인을 받고 적용하는 경로는 이 계획이 만들지 않았다 — `web/routes_actions.py`의 미스-비용 제출 자리가 여전히 서버가 단일 항목을 곧바로 결정하는 12-01의 탐색적 한 줄기 그대로이고, 이 자리를 12-06이 실제 결과 목록·확인 UI로 확장한다.
- **`validate_outcome_list`가 아직 등록 시점(rulebooks 패키지 import 시점)에 자동으로 돌지 않는다** — 지금은 세 룰북 전부에 대해 명시적 시험(`test_all_three_rulebooks_pass_validate_outcome_list`)으로만 검증된다. 12-06이 결과 목록을 실제로 쓰기 시작하면 `validate_registered_rulebooks()`에 배선하는 것을 고려할 것.
- **알려진 갭(차단 아님):** OpenQuest는 결과 목록이 없어(빈 목록) 재량 판정 경로로만 간다 — SRD가 그 절차를 안 정하므로 지어내지 않았다. Cairn도 결과 목록은 없지만 소급 선언만 있다.

---
*Phase: 12-stats-resources-inventory*
*Completed: 2026-08-17*

## Self-Check: PASSED

All 9 modified files verified present on disk. All three task commit hashes
(`4cdf77b`, `9da57b9`, `6bdc331`) verified in `git log --all`.
