---
phase: 11-rulebook-vocabulary
plan: 01
subsystem: rules-core
tags: [dataclass, pydantic, resource-axis, stat-entry, typescript]

# Dependency graph
requires:
  - phase: 02-two-rulebooks-one-grader
    provides: "Rulebook/GradeBand 선언 패턴, Entity/StatEntry 네 칸 그릇"
provides:
  - "ResourceAxisForm/NoneKind 리터럴 — 여섯 표현 형태 어휘(D-13)"
  - "여덟 칸 StatEntry — form 필수, 형태별 페이로드 정합성 검증"
  - "ResourceAxisDecl/InvalidResourceAxis — 룰북이 자원 축 목록을 선언하는 자리(D-01/D-02)"
  - "Rulebook.resource_axes 필수 필드 — 빠뜨리면 TypeError, 중복 이름은 InvalidResourceAxis"
  - "numeric 형태 하나가 룰북 선언 → Entity → 시트 응답 → StatusPane 화면까지 관통"
affects: [11-02, 11-03, 11-04, 11-05, 11-06, 11-07, phase-12]

# Actuals (#2632)
actuals:
  tokens: 11681
  tasks: 3
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "판별 필드 + 폼별 선택 페이로드 (GradeBand와 같은 모양) — ResourceAxisDecl/StatEntry"
    - "조용히 넘기지 않는 예외 관례 (Invalid*/Unknown*/NoMatching*) 신규 InvalidResourceAxis로 계승"

key-files:
  created:
    - tests/test_rulebook.py
  modified:
    - src/gptrpg/rules_core/entities.py
    - src/gptrpg/rules_core/rulebook.py
    - src/gptrpg/rulebooks/dungeonworld_like.py
    - src/gptrpg/rulebooks/openquest.py
    - src/gptrpg/rulebooks/openquest_creatures.py
    - src/gptrpg/rulebooks/threat_clocks.py
    - src/gptrpg/web/characters_data.py
    - src/gptrpg/web/routes_characters.py
    - frontend/src/api/types.ts
    - frontend/src/panes/StatusPane.tsx
    - tests/test_entities.py
    - tests/test_session_actor.py
    - tests/test_narration_guard.py
    - tests/test_web_characters.py

key-decisions:
  - "Task 0 체크포인트(widen-now, 사용자 승인): StatEntry를 네 칸에서 여덟 칸으로 넓힌다. D-20을 뒤집는 게 아니라 그 그릇이 담는 범위를 자원 축 전체로 다시 그리는 것(D-64/D-65/D-66과 같은 패턴)"
  - "여섯 형태 중 numeric 하나만 이번 계획이 룰북 선언부터 화면까지 관통시킨다 — 나머지 다섯은 어휘로만 정의(11-03이 데이터·화면을 붙인다)"
  - "routes_characters.py의 form==\"none\" 응답 제외 로직은 이번 계획에 넣지 않는다 — Source Coverage Audit이 그 Pitfall 2 대응을 11-03으로 명시 배정했다"

patterns-established:
  - "StatEntry.__post_init__의 _validate_form_payload — 여섯 형태 각각의 필수/금지 필드를 명시적으로 나열하는 검증 패턴. 신규 형태 추가 시 이 분기 하나만 늘리면 된다"
  - "ResourceAxisDecl은 GradeBand와 동일한 '판별 필드 + 폼별 선택 필드' 모양을 따른다 — 이 저장소의 룰북 선언 관례가 일관됨"

requirements-completed: [RULE-11, RULE-12]

coverage:
  - id: D1
    description: "ResourceAxisForm(6값)/NoneKind(2값) 리터럴 신설, StatEntry 4칸→8칸 확장(form 필수, 형태별 페이로드 정합성 검증)"
    requirement: "RULE-11"
    verification:
      - kind: unit
        ref: "tests/test_entities.py#test_stat_entry_field_names_are_exactly_eight"
        status: pass
      - kind: unit
        ref: "tests/test_entities.py#test_axis_form_payload_mismatch_is_rejected"
        status: pass
    human_judgment: false
  - id: D2
    description: "ResourceAxisDecl/InvalidResourceAxis 신설, Rulebook.resource_axes 필수 필드화(빠뜨리면 TypeError), 중복 이름 거부"
    requirement: "RULE-11"
    verification:
      - kind: unit
        ref: "tests/test_rulebook.py#test_rulebook_without_resource_axes_raises_type_error"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_rulebook_with_duplicate_axis_names_raises"
        status: pass
    human_judgment: false
  - id: D3
    description: "numeric 형태 하나가 던전월드류 룰북 선언 → Entity(브람 등) → GET 시트 응답(form:\"numeric\" 포함) → StatusPane 화면(stat.form === \"numeric\" 명시 판별)까지 끊기지 않고 관통"
    requirement: "RULE-11"
    verification:
      - kind: integration
        ref: "tests/test_web_characters.py#test_known_character_sheet_matches_characters_data"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_dungeonworld_resource_axes_are_all_numeric_form"
        status: pass
      - kind: e2e
        ref: "실행 중 TestClient로 GET /api/sessions/s1/characters/bram 직접 호출, 모든 stats 항목에 form:\"numeric\" 확인(수동 실행, 세션 로그 기록)"
        status: pass
    human_judgment: false
  - id: D4
    description: "RULE-12의 값 0 / 개념 없음 / 규칙으로 안 셈 세 상태가 서로 다른 객체로 구분된다"
    requirement: "RULE-12"
    verification:
      - kind: unit
        ref: "tests/test_entities.py#test_zero_value_and_absent_concept_are_different_entries"
        status: pass
      - kind: unit
        ref: "tests/test_entities.py#test_discretionary_and_absent_are_different_none_kinds"
        status: pass
    human_judgment: false
  - id: D5
    description: "브람·나리 수치가 이전과 한 자리도 다르지 않고(D-49), StatusPane의 max===0 게이지가 NaN%가 아니라 0%로 계산된다"
    verification:
      - kind: unit
        ref: "tests/test_web_characters.py#test_bram_and_nari_stats_are_pinned_by_d49"
        status: pass
      - kind: manual_procedural
        ref: "frontend/src/panes/StatusPane.tsx 코드 검사 — stat.max === 0 ? \"0%\" : ... 분기. 프런트엔드 테스트 러너가 저장소에 아직 없어 자동 시험으로 고정하지 못함"
        status: pass
    human_judgment: true
    rationale: "StatusPane의 max===0 게이지 폭 계산은 코드 검사로 확인했지만 frontend에 vitest/jest 같은 테스트 러너가 구성되어 있지 않아(package.json scripts에 test 없음) 자동 회귀 시험으로 고정할 수 없었다. 브라우저 육안 확인이 필요하면 사람이 판단해야 한다."

# Metrics
duration: ~45min
completed: 2026-08-15
status: complete
---

# Phase 11 Plan 01: 자원 축 그릇 신설 + numeric 형태 관통 Summary

**`ResourceAxisDecl`/여덟 칸 `StatEntry` 신설 — 여섯 형태 중 `numeric` 하나가 룰북 선언부터 캐릭터 판 화면까지 실제로 뚫렸고, 브람·나리 수치는 한 자리도 안 바뀜(D-49)**

## Performance

- **Duration:** ~45분 (체크포인트 2회 — Task 0 결정 관문, Task 1 tracer 통합 확인 관문 — 사람 검토 대기 시간 제외)
- **Completed:** 2026-08-15
- **Tasks:** 2 (+ Task 0 결정 관문, 코드 변경 없음)
- **Files modified:** 14개 수정 + 1개 신규(`tests/test_rulebook.py`)

## Accomplishments

- 룰북이 「이 세계에 어떤 자원 축이 있는가」를 선언하는 자리(`Rulebook.resource_axes`)가 생겼고, 빠뜨리면 `TypeError`로 즉시 죽는다(D-02)
- `StatEntry`가 네 칸에서 여덟 칸으로 넓어졌다 — `form`이 여섯 표현 형태(`numeric`/`clock`/`named_slots`/`tag_list`/`usage_die`/`none`) 중 하나를 필수로 선언하고, 생성자가 형태별 페이로드 정합성을 즉시 검사한다(Pitfall 1, T-11-01)
- `numeric` 한 형태가 던전월드류 룰북의 자원 축 선언 → 브람·나리의 `Entity` → `GET /sessions/{sid}/characters/{id}` 응답(`form: "numeric"` 포함) → `StatusPane`의 명시적 `stat.form === "numeric"` 판별 화면까지 실제로 관통했다
- RULE-12의 핵심 — 「값 0」 vs 「개념 자체가 없음」(`none_kind="absent"`) vs 「규칙으로 안 셈」(`none_kind="discretionary"`)이 서로 다른 객체로 구분됨을 시험으로 고정했다
- 고정 시험이 삭제되지 않고 여덟 칸 집합으로 재고정됐다(D-03)

## Task Commits

각 태스크를 개별 커밋했다:

1. **Task 1 [tracer]: 자원 축 하나가 룰북 선언 → 등록 → 시트 응답 → 화면까지 한 줄기로 도달** — `f850442` (feat)
2. **Task 2: 고정 시험 재고정 + 형태별 정합성·구분 시험** — `692f18e` (test)

Task 0(D-03 결정 관문)은 코드 변경이 없는 순수 결정 확인이라 별도 커밋이 없다 — 사용자가 `widen-now`를 승인한 시점이 Task 1 착수 직전이다.

**Plan metadata:** 이 커밋 (SUMMARY.md 등)

## Files Created/Modified

- `src/gptrpg/rules_core/entities.py` - `ResourceAxisForm`/`NoneKind` 리터럴, 여덟 칸 `StatEntry` + `_validate_form_payload` 형태별 검증
- `src/gptrpg/rules_core/rulebook.py` - `ResourceAxisDecl`/`InvalidResourceAxis` 신설, `Rulebook.resource_axes` 필수 필드 + 중복 이름 거부
- `src/gptrpg/rulebooks/dungeonworld_like.py` - `DUNGEONWORLD_RESOURCE_AXES`(여덟 축, 전부 numeric) 신설·연결
- `src/gptrpg/rulebooks/openquest.py` - `OPENQUEST_RESOURCE_AXES`(열 축, 전부 numeric) 신설·연결
- `src/gptrpg/rulebooks/openquest_creatures.py` - `StatEntry(...)` 20곳에 `form="numeric"` 추가, 수치 불변
- `src/gptrpg/rulebooks/threat_clocks.py` - `StatEntry(...)` 2곳에 `form="numeric"` 추가
- `src/gptrpg/web/characters_data.py` - `StatEntry(...)` 29곳에 `form="numeric"` 추가, D-49 규율 문장 보강
- `src/gptrpg/web/routes_characters.py` - `StatEntryView` 여덟 칸으로 확장(asdict 조립 방식은 그대로 — form=="none" 제외는 11-03 몫)
- `frontend/src/api/types.ts` - `StatEntry` 인터페이스 여덟 칸 + `form` 여섯 리터럴 유니온
- `frontend/src/panes/StatusPane.tsx` - `StatRows`가 `stat.max === null` 암묵 판별 대신 `stat.form === "numeric"` 명시 판별로 렌더, `max===0` 0으로 나누기 제거
- `tests/test_entities.py` - 고정 시험 8칸 재고정 + 형태별 정합성/RULE-12 구분 시험 6종 추가, 기존 호출부 form= 보강(Task 1 앞당김)
- `tests/test_session_actor.py` - `_GAPPED_RULEBOOK`에 `resource_axes=()` 명시
- `tests/test_narration_guard.py` - `StatEntry(...)` 1곳에 `form="numeric"` 추가
- `tests/test_web_characters.py` - 시트 응답 키 집합 8칸 갱신, `form` 필드 비교 추가(Task 1 앞당김)
- `tests/test_rulebook.py` (신규) - `ResourceAxisDecl`/`Rulebook.resource_axes` 회귀 시험 12건

## Decisions Made

- **Task 0 (D-03, one-way, 사용자 승인):** `widen-now` — `StatEntry`를 네 칸에서 여덟 칸으로 넓힌다. `side-container`(옆에 새 그릇을 하나 더 두는 대안)는 채택하지 않았다. D-20/D-65가 잠근 「네 칸」은 적/NPC 숫자 그릇 하나의 **모양**이었고, 이번 확장은 그 그릇이 담는 **범위**를 자원 축 전체로 다시 그리는 것 — 원 결정을 뒤집는 게 아니라 D-64·D-65·D-66과 같은 「적용 범위 재설정」 패턴이다. `entities.py:41`의 `StatEntry` 도크스트링이 D-20을 부정하지 않고 이 범위 재설정을 설명하도록 다시 썼다.
- **Task 1 tracer 통합 확인 관문 (사용자 승인):** 자동화된 `<verify>` 세 명령(전체 pytest, lint-imports, tsc)과 `<behavior>` 아홉 줄 전부를 실제로 실행해 확인한 뒤 진행했다. 오케스트레이터가 독립적으로 재검증(커밋 존재, diff 내용, D-49 수치 불변)한 결과도 일치했다.
- **routes_characters.py의 form=="none" 제외 로직을 이번 계획에 넣지 않는다** — 계획서 Source Coverage Audit이 「Pitfall 2 서버 응답에서 제외」를 11-03으로 명시 배정했고, 이번 계획은 어떤 룰북도 `none` 형태를 아직 선언하지 않아 실증할 데이터가 없다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `test_entities.py`/`test_web_characters.py`를 Task 1의 `<files>` 목록 밖인데도 Task 1에서 손댔다**
- **Found during:** Task 1 (tracer) 실행 중, 검증 단계
- **Issue:** Task 1의 `<files>` 목록에는 `tests/test_entities.py`/`tests/test_web_characters.py`가 없었지만, Task 1의 `<verify>`는 `uv run pytest tests/test_entities.py tests/test_web_characters.py ...`를 명시적으로 요구했다. `StatEntry.form`이 기본값 없는 필수 필드가 되면서 두 파일의 기존 `StatEntry(...)` 호출부(13곳)와 고정 시험(`test_stat_entry_field_names_are_exactly_four`)이 즉시 깨졌다 — 고치지 않으면 Task 1 자체가 초록이 될 수 없었다.
- **Fix:** `test_entities.py`의 기존 호출부 13곳에 `form="numeric"` 추가, 고정 시험을 `test_stat_entry_field_names_are_exactly_eight`로 이름 바꾸고 8칸 집합으로 재고정(Task 2가 계획서상 하기로 한 이름 바꾸기를 이 시점에 앞당김). `test_web_characters.py`의 시트 응답 키 집합 단언을 8칸으로 갱신, `form` 필드 비교 한 줄 추가.
- **Files modified:** `tests/test_entities.py`, `tests/test_web_characters.py`
- **Verification:** `uv run pytest tests/test_entities.py tests/test_web_characters.py tests/test_session_actor.py tests/test_narration_guard.py -q` — 130 passed
- **Committed in:** `f850442` (Task 1 커밋)
- **사용자 승인:** Task 1 통합 확인 관문에서 명시적으로 승인됨 — "두 파일 모두 계획서 frontmatter의 `files_modified` 안에 있고, Task 1의 `<verify>`가 두 파일의 pytest 통과를 요구하는 이상 구조적으로 불가피했다. 계획 범위 이탈이 아니라 계획서가 태스크 사이에 파일을 나눈 방식의 문제였다."
- **파급:** Task 2의 실제 범위가 「고정 시험 재고정 + 새 시험 추가」에서 「새 시험 추가」로 줄었다 — 재고정은 이미 Task 1에서 끝났다.

**2. [Rule 2 - Missing Critical] `tests/test_rulebook.py` 신설 (계획서 `files_modified`에 없음)**
- **Found during:** Task 2 실행 중
- **Issue:** 계획서 `must_haves.truths`가 요구하는 경계 조건 중 「같은 이름의 자원 축 두 번 선언 시 거부」·「공백뿐인 축 이름 거부」·「이름 비교는 유니코드 정규화 없이 완전 일치, 앞뒤 공백만 다른 두 이름은 서로 다른 축」은 `ResourceAxisDecl`/`Rulebook` 수준의 검증인데, 이 계획의 `files_modified`에는 그 회귀 시험을 넣을 파일(`tests/test_rulebook.py`)이 아예 없었다. Task 1에서 ad-hoc 스크립트로 동작만 확인했을 뿐 회귀 시험으로 고정되지 않은 상태였다.
- **Fix:** `tests/test_rulebook.py`를 신설해 12개 시험으로 고정 — `resource_axes` 누락 시 `TypeError`, 중복 이름 거부, 공백뿐인 이름 거부, 앞뒤 공백만 다른 이름은 별개 축으로 허용, `none_kind`/`slot_count` 상호 배타 규칙 4종, 두 룰북(던전월드류/OpenQuest)의 축 목록이 내부적으로 중복 없고 현재 전부 numeric임을 확인.
- **Files modified:** `tests/test_rulebook.py` (신규)
- **Verification:** `uv run pytest tests/test_rulebook.py -q` — 12 passed
- **Committed in:** `692f18e` (Task 2 커밋)
- **사용자 승인:** 오케스트레이터가 Task 1 승인 시 명시적으로 요청함 — "계획서의 must_haves truths에 적힌 경계 조건들(...같은 이름 중복, 공백뿐인 이름...)을 빠짐없이 덮을 것."

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing critical)
**Impact on plan:** 둘 다 계획서 자신의 `<verify>`/`must_haves.truths`가 요구했지만 태스크 간 파일 배분이 그 요구를 충족하지 못했던 구조적 간극을 메운 것이다. 범위 이탈이 아니라 계획서가 명시한 완료 기준을 실제로 달성하기 위한 필수 보강이었고, 두 건 모두 사용자/오케스트레이터가 사전 승인했다.

## Issues Encountered

None — 두 체크포인트(Task 0 결정, Task 1 tracer 확인) 모두 대화형으로 정상 통과했고, 코드 레벨에서 예상 밖 버그는 없었다.

## User Setup Required

None - 외부 서비스 설정 불필요.

## Next Phase Readiness

- `numeric` 형태가 관통하는 그릇 모양이 실증됐다 — 11-03이 나머지 다섯 형태(`clock`/`named_slots`/`tag_list`/`usage_die`/`none`)의 실제 데이터·화면을 이 위에 붙이면 된다.
- `routes_characters.py`의 `form=="none"` 서버 응답 제외 로직(Pitfall 2)은 아직 구현되지 않았다 — 11-03이 반드시 처리해야 한다(계획서가 이미 명시 배정).
- `tests/test_rulebook.py`가 신설됐다 — 11-02(가려짐/구멍 검증, QUAL-03)가 이 파일에 `shadowed_band_rejected`/`hole_rejected`류 시험을 이어 붙이면 된다(PATTERNS.md가 이미 이 파일 이름과 시험 목록을 예상해 뒀다).
- 프런트엔드에 자동 시험 러너(vitest/jest)가 없다는 것이 이번에 드러났다 — `max===0` 게이지 계산처럼 코드 검사로만 확인 가능한 UI 로직이 앞으로도 계속 생길 것이므로, 이 계획 밖의 관찰 사항으로 남긴다(즉시 조치 요구 아님).
- 블로커 없음 — Phase 11의 다음 계획(11-02)으로 바로 이어갈 수 있다.

---
*Phase: 11-rulebook-vocabulary*
*Completed: 2026-08-15*
