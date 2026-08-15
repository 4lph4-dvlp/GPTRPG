---
phase: 11-rulebook-vocabulary
plan: 02
subsystem: rules-core
tags: [validation, registration, grade-band, resource-axis, import-time-check]

# Dependency graph
requires:
  - phase: 11-01
    provides: "ResourceAxisDecl/여덟 칸 StatEntry, Rulebook.resource_axes 필수 필드"
provides:
  - "validate_grade_bands() — 가려짐(ShadowedGradeBand)/구멍(UncoveredOutcomeGap) 등록 시점 검증(QUAL-03, D-15)"
  - "validate_entity_axes() — 개체 StatEntry 이름·form이 룰북 선언 축과 어긋나면 EntityAxisMismatch(D-01)"
  - "validate_move_stats() — MoveDecl.default_stat이 룰북 축 목록에 없으면 EntityAxisMismatch(T-11-07)"
  - "validate_registered_rulebooks() — rulebooks 패키지 임포트 시점에 세 검사를 전부 돌리는 등록 게이트"
  - "grade_for_margin()과 validate_grade_bands()가 _band_matches() 하나를 공유 — 두 판정 규칙이 구조적으로 갈라질 수 없다"
affects: [11-03, 11-04, 11-05, 11-06, 11-07]

# Actuals (#2632)
actuals:
  tokens: 7768
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "두 세계(is_doubles) × 원자 구간 스윕으로 「가려짐/구멍」을 잡는 정수 구간 검증 — 외부 구간 자료구조 없이 rules_core 안에서 완결"
    - "판정 규칙 공유 헬퍼(_band_matches) — 런타임 판정과 등록 시점 검증이 같은 함수를 호출해 두 규칙이 구조적으로 갈라지지 않는다"
    - "등록 시점 검증 + 런타임 방어선의 이중 방어 — 정적 등록(import time)과 RULEBOOKS 런타임 패치(_GAPPED_RULEBOOK류) 두 경로를 서로 다른 시험이 각각 지킨다"

key-files:
  created: []
  modified:
    - src/gptrpg/rules_core/rulebook.py
    - src/gptrpg/rulebooks/__init__.py
    - src/gptrpg/rulebooks/openquest.py
    - src/gptrpg/rulebooks/moves.py
    - tests/test_rulebook.py

key-decisions:
  - "ROADMAP 성공 기준 5의 「겹치거나」는 D-15에 따라 「가려져 영영 도달 불가능하거나」로 읽는다 — 단순 겹침은 정상. 이 해석을 test_existing_rulebooks_pass_validation/test_simple_overlap_is_legal로 회귀 시험에 고정했다"
  - "[편차, 확인 필요] OpenQuest 무브 열 개의 default_stat(기술 이름)이 애초에 어떤 자원 축으로도 선언돼 있지 않았다 — validate_move_stats를 실제 등록에 연결하자마자 즉시 드러났다. 이미 moves.py에 있던 기술 이름 열 개를 그대로 OPENQUEST_RESOURCE_AXES에 축으로 추가해 해소했다(새로 지어낸 값 없음, 크리처에 그 축의 StatEntry를 요구하지 않음 — D-04)"
  - "[편차, 사람 확인 필요] 던전월드류의 defy_danger/aid_or_interfere 두 무브는 default_stat이 '상황에 맞는 능력치'(어떤 능력치든 가능하다는 원문 설계)였다 — 등록 시점 축 대조가 생기면서 더 이상 그 문구를 허용할 수 없어, DEX/CHA로 대체했다. default_stat은 분류기 프롬프트 힌트일 뿐 실제 판정 능력치를 강제하지 않지만(ConfirmRequest.stat이 확인 시점에 자유롭게 재선택된다), 원문의 '어느 능력치든 가능하다'는 설계 유연성을 근사치 하나로 좁혔다는 점은 명시적으로 남긴다"

patterns-established:
  - "_band_matches(band, margin, is_doubles) 공유 헬퍼 — 등급 판정 규칙을 두 곳(런타임 grade_for_margin, 등록 검증 validate_grade_bands)에 따로 구현하지 않는다"
  - "등록 시점 검증 함수는 rulebooks/__init__.py 모듈 바닥에서 한 번 호출되고, moves.py 순환 참조는 함수 내부 지연 import로 푼다"

requirements-completed: [QUAL-03]

coverage:
  - id: D1
    description: "GradeBand 선언의 「가려짐」(앞 밴드에 완전히 가려져 영영 안 나오는 등급)과 「구멍」(어떤 결과값에도 안 맞는 판정 정지)을 등록 시점에 잡는다 — 단순 겹침은 정상으로 통과시킨다(D-15, QUAL-03)"
    requirement: "QUAL-03"
    verification:
      - kind: unit
        ref: "tests/test_rulebook.py#test_existing_rulebooks_pass_validation"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_shadowed_band_rejected"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_hole_rejected"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_empty_grade_bands_rejected_as_hole"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_simple_overlap_is_legal"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_touching_bands_leave_no_gap"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_declaration_order_decides_shadowing"
        status: pass
    human_judgment: false
  - id: D2
    description: "개체의 StatEntry 이름·form이 그 개체 룰북이 선언한 자원 축과 어긋나면 등록 시점에 EntityAxisMismatch — 「이 세계에 존재하는 축」과 「이 개체가 가진 축」의 분리가 검사로 성립한다(D-01)"
    verification:
      - kind: unit
        ref: "tests/test_rulebook.py#test_all_player_characters_match_their_rulebook_axes"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_all_openquest_creatures_match_their_rulebook_axes"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_undeclared_axis_name_on_entity_is_rejected"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_entity_form_must_match_declared_axis_form"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_axis_name_comparison_is_exact_no_normalization"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_declared_axis_not_present_on_entity_is_legal"
        status: pass
    human_judgment: false
  - id: D3
    description: "MoveDecl.default_stat이 룰북의 resource_axes 목록에 없으면 등록 시점에 EntityAxisMismatch(T-11-07) — 실제 등록에 연결하면서 OpenQuest 기술 축 열 개 누락과 던전월드류 두 무브의 비-축 default_stat 값을 발견·수정했다"
    verification:
      - kind: unit
        ref: "tests/test_rulebook.py#test_move_default_stat_must_be_a_declared_axis"
        status: pass
      - kind: unit
        ref: "python -c \"validate_move_stats((m.default_stat for m in DUNGEONWORLD_LIKE_MOVES+OPENQUEST_MOVES), rulebook); print('ok')\" (수동 실행)"
        status: pass
    human_judgment: true
    rationale: "defy_danger/aid_or_interfere의 default_stat을 DEX/CHA로 근사한 것은 룰 원문의 '어느 능력치든 가능하다'는 설계 의도를 좁히는 판단이다 — 게임 메커니즘(ConfirmRequest.stat)은 안 바뀌지만 이 특정 근사치 선택이 맞는지는 사람이 확인해야 한다."
  - id: D4
    description: "gptrpg.rulebooks 패키지가 임포트되는 순간 세 검사(가려짐/구멍, 개체 축, 무브 축)가 자동으로 돈다 — 위반이 있으면 임포트 자체가 죽는다. _GAPPED_RULEBOOK 같은 런타임 RULEBOOKS 패치 시험은 이 게이트를 지나가지 않아 별개로 계속 유효하다"
    requirement: "QUAL-03"
    verification:
      - kind: unit
        ref: "tests/test_rulebook.py#test_importing_rulebooks_package_runs_registration_validation"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_registration_rejects_a_shadowed_rulebook"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_registration_rejects_a_rulebook_with_a_hole"
        status: pass
      - kind: unit
        ref: "tests/test_session_actor.py#test_rulebook_with_incomplete_grade_bands_is_rejected_not_a_raw_traceback"
        status: pass
      - kind: integration
        ref: "uv run pytest -q (868 passed) + uv run lint-imports (4 kept, 0 broken) + python -c \"import gptrpg.rulebooks\""
        status: pass
    human_judgment: false

# Metrics
duration: ~35min
completed: 2026-08-15
status: complete
---

# Phase 11 Plan 02: 등록 시점 「가려짐/구멍」 검증 + 축 정합성 검증 Summary

**등급 밴드가 앞 밴드에 완전히 가려지거나 어떤 결과값도 못 잡는 구멍이면 룰북 등록 자체가 예외로 죽는다(QUAL-03, D-15) — 개체·무브가 가리키는 축이 룰북 선언 밖이면 D-01도 같은 등록 관문에서 함께 걸린다**

## Performance

- **Duration:** ~35분 (체크포인트 없음 — 계획 자체가 `autonomous: true`, `type="checkpoint"` 태스크 없음)
- **Completed:** 2026-08-15
- **Tasks:** 3
- **Files modified:** 5개 (신규 파일 없음)

## Accomplishments

- `validate_grade_bands()`가 「가려짐」(`ShadowedGradeBand`)과 「구멍」(`UncoveredOutcomeGap`)을 등록 시점에 잡는다 — `is_doubles` 두 세계 × 원자 구간 스윕으로, `grade_for_margin`이 이미 쓰던 「선언 순서 첫 매치」 규칙을 `_band_matches()` 헬퍼로 공유해 두 판정이 구조적으로 갈라질 수 없다
- **단순 겹침은 정상이다(D-15 회귀 확인)** — 던전월드류의 `strong_hit`/`weak_hit`와 OpenQuest의 `critical`/`success`가 실제로 겹치게 선언돼 있는데, 두 룰북 모두 새 검증을 그대로 통과한다
- `validate_entity_axes()`가 개체의 `StatEntry` 이름·`form`이 그 룰북이 선언한 자원 축과 완전 일치하는지 검사한다(D-01) — 이름 비교는 유니코드 정규화 없이 파이썬 `==`이고, 룰북이 선언했지만 개체가 안 가진 축은 위반이 아니다(D-04)
- `validate_move_stats()`가 `MoveDecl.default_stat`을 같은 방식으로 대조한다(T-11-07) — `rules_core`는 `MoveDecl` 타입을 모르는 채로 문자열 이터러블만 받아 층 경계를 지킨다
- `validate_registered_rulebooks()`가 `gptrpg.rulebooks` 패키지 임포트 시점에 세 검사를 전부 돌린다 — 위반이 있으면 임포트 자체가 예외로 죽는다. `tests/test_session_actor.py`의 `_GAPPED_RULEBOOK`(런타임에 `RULEBOOKS`에 직접 꽂는 시험)은 이 게이트를 지나가지 않아 계속 독립적으로 유효하다
- 플레이어 캐릭터 넷·OpenQuest 크리처 둘·`EXAMPLE_SINGLE_STAT_FOE` 전부 실제 데이터로 축 정합성 시험을 통과했다

## Task Commits

각 태스크를 개별 커밋했다:

1. **Task 1: 가려짐·구멍 스윕 검증 함수를 규칙 코어에 신설** — `39fff6c` (test)
2. **Task 2: 룰북 선언과 개체가 가진 축이 어긋나면 잡는다** — `ac51d48` (feat)
3. **Task 3: 등록소가 임포트 시점에 세 검사를 돌린다 (+ 편차 수정 포함)** — `8e88562` (feat)

**Plan metadata:** 이 커밋 (SUMMARY.md 등)

## Files Created/Modified

- `src/gptrpg/rules_core/rulebook.py` - `ShadowedGradeBand`/`UncoveredOutcomeGap`/`EntityAxisMismatch` 예외, `_band_matches` 공유 헬퍼, `validate_grade_bands`/`validate_entity_axes`/`validate_move_stats` 순수 함수 신설. `grade_for_margin`이 `_band_matches`를 쓰도록 재작성(동작 변경 없음)
- `src/gptrpg/rulebooks/__init__.py` - `validate_registered_rulebooks()` 신설 + 모듈 바닥에서 1회 호출. `_REGISTERED_ENTITIES_FOR_AXIS_CHECK` 매핑으로 `EXAMPLE_SINGLE_STAT_FOE`·`OPENQUEST_CREATURES`를 등록 검증 대상에 포함(플레이어 캐릭터는 층 방향 때문에 제외, 대신 시험이 담당)
- `src/gptrpg/rulebooks/openquest.py` - `OPENQUEST_RESOURCE_AXES`에 OpenQuest 기술 축 열 개 추가(편차, 아래 참조) — 열 축 → 스무 축
- `src/gptrpg/rulebooks/moves.py` - `defy_danger`/`aid_or_interfere`의 `default_stat`을 `"상황에 맞는 능력치"`에서 `"DEX"`/`"CHA"`로 교체(편차, 아래 참조)
- `tests/test_rulebook.py` - Task 1~3 시험 20건 추가(가려짐/구멍 7건, 개체·무브 축 정합성 7건, 등록 게이트 3건), 기존 `OPENQUEST_RESOURCE_AXES` 개수 단언을 10→20으로 갱신

## Decisions Made

- **D-15 해석 확정 기록:** ROADMAP 성공 기준 5의 「겹치거나」는 「가려져 영영 도달 불가능하거나」로 읽는다. 이 해석 없이 문자 그대로 구현했다면 이 저장소 자신의 두 룰북이 등록 거부됐을 것이다 — `test_existing_rulebooks_pass_validation`이 회귀로 고정한다
- **알고리즘 선택:** 구간 트리 등 외부 자료구조 없이, `is_doubles` 두 세계 × 유한 원자 구간(경계점 = `margin_at_least`, `margin_at_most+1`)을 정수 집합 연산만으로 스윕한다 — `.importlinter` contract 1(`rules_core`는 시간·무작위·파일·네트워크 금지)을 자연스럽게 지킨다
- **등록 검증 함수 위치:** `RULEBOOKS` 딕셔너리 바로 다음 줄이 아니라 `UnknownRulebook`/`get_rulebook` 정의 다음, 파일 바닥에서 호출한다 — `moves.py`가 `gptrpg.rulebooks.UnknownRulebook`을 최상단에서 import하므로, `validate_registered_rulebooks()` 내부의 `moves.py` 지연 import가 실행되는 시점에 `UnknownRulebook`이 이미 모듈 네임스페이스에 있어야 순환 import가 안 깨진다

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] OpenQuest 무브 열 개의 `default_stat`이 애초에 어떤 자원 축으로도 선언돼 있지 않았다**
- **Found during:** Task 3, `validate_move_stats`를 실제 `OPENQUEST_MOVES`/`OPENQUEST_RESOURCE_AXES`에 연결해 확인하는 단계
- **Issue:** `OPENQUEST_MOVES`의 `default_stat`(근접 무기 기술·회피 기술 등 기술 이름 열 개)은 `OPENQUEST_RESOURCE_AXES`(능력치 일곱 + HP/MP/AP)에 하나도 없었다. Task 2·3의 `<verify>`/`<acceptance_criteria>`가 요구하는 `uv run pytest -q` 전체 초록과 `import gptrpg.rulebooks` 성공이, 이 상태로는 `validate_registered_rulebooks()`가 등록 시점에 예외를 던져 성립할 수 없었다. 11-CONTEXT.md 자신도 이 대조를 "사장님 결정 밖, 계획이 판단할 것"이라고 명시해 뒀다
- **Fix:** `moves.py`에 이미 있던 기술 이름 열 개(근접 무기 기술/회피 기술/은신 기술/지각 기술/일반 지식 기술/설득 기술/장치 기술/운동 기술/의지 기술/원거리 무기 기술)를 그대로 `OPENQUEST_RESOURCE_AXES`에 `ResourceAxisDecl(form="numeric")`로 추가했다 — 새로 지어낸 값이 없다. 고블린·스켈레톤 크리처는 이 축들의 `StatEntry`를 갖지 않아도 위반이 아니다(D-04, 룰북이 선언한 축을 개체가 전부 가질 필요는 없다)
- **Files modified:** `src/gptrpg/rulebooks/openquest.py`, `tests/test_rulebook.py`(개수 단언 10→20)
- **Verification:** `uv run pytest -q` 868 passed, `python -c "import gptrpg.rulebooks"` 성공
- **Committed in:** `8e88562` (Task 3 커밋)
- **사용자 확인 필요:** 낮은 위험(새 값을 지어내지 않고 이미 있던 문자열을 축으로 승격했을 뿐) — 그래도 OpenQuest SRD 원문 대비 이 열 개 명칭이 정확한 표기인지는 확인이 필요하다.

**2. [Rule 3 - Blocking, 사람 확인 강력 권고] 던전월드류 두 무브의 `default_stat`이 "상황에 맞는 능력치"라는 서술형 문구였다**
- **Found during:** Task 3, 위와 같은 단계
- **Issue:** `defy_danger`("위험을 무릅쓰다")와 `aid_or_interfere`("돕거나 훼방 놓다") 두 무브는 `default_stat="상황에 맞는 능력치"`였다 — 이것은 Dungeon World 원문 설계("Defy Danger"는 접근 방식에 따라 어느 능력치든 쓸 수 있고 고정된 기본값이 없다)를 그대로 반영한 서술이지, 실수로 빠뜨린 축 이름이 아니었다. 등록 시점 축 대조가 생기면서 이 문구는 더 이상 유효한 값일 수 없다
- **Fix:** `defy_danger`는 `"DEX"`(회피·피하기에 가장 근접), `aid_or_interfere`는 `"CHA"`(사회적 개입에 가장 근접)로 교체했다. `default_stat`은 `agents/prompt_assembly.py`가 분류기 프롬프트에 그대로 넣는 힌트 텍스트일 뿐 실제 판정 능력치를 강제하지 않는다 — `ConfirmRequest.stat`이 확인 시점에 플레이어/AI가 자유롭게 다시 정하는 구조이므로 게임 메커니즘 자체는 안 바뀐다. 다만 원문의 "어느 능력치든 가능하다"는 유연성이 코드 상에서는 근사치 하나로 좁혀진다는 트레이드오프는 명시적으로 남긴다(moves.py 주석)
- **Files modified:** `src/gptrpg/rulebooks/moves.py`
- **Verification:** `uv run pytest -q` 868 passed (기존 시험은 전부 `moves[i].default_stat`을 동적으로 참조해 하드코딩된 문자열 의존이 없었다)
- **Committed in:** `8e88562` (Task 3 커밋)
- **사용자 확인 필요(높음):** 이것은 코드 정확성 문제가 아니라 **룰북 콘텐츠 설계 판단**이다 — "위험을 무릅쓰다"/"돕거나 훼방 놓다" 두 무브에 DEX/CHA를 기본값으로 못박는 것이 이 프로젝트가 원하는 절충인지, 아니면 `default_stat`을 아예 선택형(옵셔널)으로 바꿔 "어느 능력치든 가능"을 코드로도 표현하는 것이 맞는지는 사람의 판단이 필요하다. CLAUDE.md 메모리 규칙("원 설계 의도와 대조 후 보고")에 따라 이 편차를 승인 요청의 최우선 항목으로 짚어 둔다.

---

**Total deviations:** 2 auto-fixed (둘 다 Rule 3 - 등록 시점 검증을 실제로 연결하면서 드러난 블로킹 이슈)
**Impact on plan:** Task 3의 `<verify>`(`uv run pytest -q` 전체 초록, `import gptrpg.rulebooks` 성공)가 요구하는 최소 조건을 충족하기 위해 구조적으로 불가피했다. 첫 번째는 위험이 낮다(이미 있던 값을 축으로 승격). 두 번째는 게임 메커니즘을 바꾸지 않지만 룰북 콘텐츠의 설계 뉘앙스를 좁히는 판단이라 별도 확인이 필요하다.

## Issues Encountered

None — 세 태스크 모두 계획서의 `<verify>`/`<acceptance_criteria>`를 그대로 실행해 확인했고, 위 두 편차 외에 추가 버그는 없었다.

## User Setup Required

None - 외부 서비스 설정 불필요.

## Next Phase Readiness

- QUAL-03(등급 구간 가려짐/구멍 등록 검증)은 이 계획으로 완전히 끝났다 — REQUIREMENTS.md를 `[x]`/`Complete`로 갱신한다
- RULE-11/RULE-12는 이 계획으로 안 끝난다 — REQUIREMENTS.md의 두 체크박스는 `[ ]`/`In Progress`로 그대로 둔다(11-03/11-04가 나머지 다섯 표현 형태·서버 응답 제외 로직을 맡는다는 기존 주석이 정확하다)
- **11-03이 착수 전에 반드시 확인할 것:** 위 편차 2번(`defy_danger`/`aid_or_interfere`의 `default_stat=DEX/CHA` 근사)이 사람 승인을 받았는지. 승인이 안 되면 `default_stat`을 옵셔널로 바꾸는 작은 구조 변경이 필요할 수 있다
- `validate_registered_rulebooks()`가 이제 세 번째 룰북(계획서에 언급된 Cairn 등)이 들어올 때도 자동으로 같은 세 검사를 돌린다 — 새 룰북 추가 시 이 게이트를 통과해야만 등록된다는 것이 실질적 계약이 됐다

## Self-Check: PASSED

- 파일 존재: `src/gptrpg/rules_core/rulebook.py`, `src/gptrpg/rulebooks/__init__.py`, `src/gptrpg/rulebooks/openquest.py`, `src/gptrpg/rulebooks/moves.py`, `tests/test_rulebook.py` 전부 확인됨
- 커밋 존재: `39fff6c`, `ac51d48`, `8e88562` 전부 `git log --oneline --all`에서 확인됨

---
*Phase: 11-rulebook-vocabulary*
*Completed: 2026-08-15*
