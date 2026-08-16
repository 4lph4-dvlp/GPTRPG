---
phase: 11-rulebook-vocabulary
plan: 03
subsystem: rules-core
tags: [fastapi, pydantic, react, typescript, resource-axis, none-exclusion]

# Dependency graph
requires:
  - phase: 11-01
    provides: "여섯 형태 어휘(ResourceAxisForm)와 여덟 칸 StatEntry, numeric 형태 한 줄기가 룰북 선언부터 화면까지 관통한 상태"
  - phase: 11-02
    provides: "등록 시점 검증(가려짐/구멍, 개체-룰북 축 정합성) — 이 계획이 붙이는 렌더 갈래가 등록에서 걸러지지 않은 데이터만 받는다는 전제"
provides:
  - "_visible_stats(entity, rulebook) — form==\"none\" 축을 시트 응답 조립 단계에서 제외하는 서버 쪽 헬퍼(RULE-12 성공 기준 2)"
  - "StatusPane의 여섯 갈래 렌더 — numeric(기존 유지)/clock(ThreatClock 재사용)/named_slots(SlotGrid 신설)/tag_list(TagList 신설)/usage_die(UsageDie 신설)/none(서버가 이미 제외해 도달 불가)"
  - "축이 하나도 없는 시트를 위한 COPY.noResourceAxes 문구 — 회색 빈 패널 대신 의도된 한 줄"
affects: [11-04, 11-06, 11-07]

# Actuals (#2632)
actuals:
  tokens: 4482
  tasks: 3
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "서버 응답 조립 단계에서 제외하는 관례 — 프론트엔드 조건부 렌더링으로 숨기지 않는다(RULE-12 성공 기준 2). _visible_stats가 두 신호(룰북 축 선언의 form, 개체 StatEntry.form)를 둘 다 독립적으로 확인해 등록 검증 전제에 기대지 않는다"
    - "기존 컴포넌트 재사용 우선 — ThreatClock을 pulsing 없이 그대로 재사용해 세그먼트 원을 새로 만들지 않는다"
    - "같은 파일 안 하위 컴포넌트 — SlotGrid/TagList/UsageDie는 여러 화면이 공유하지 않는 이 판 전용이라 components/로 빼지 않는다(StatusPane.tsx 도크스트링 관례)"

key-files:
  created: []
  modified:
    - src/gptrpg/web/routes_characters.py
    - tests/test_web_characters.py
    - frontend/src/panes/StatusPane.tsx
    - frontend/src/labels.ts
    - frontend/src/styles.css

key-decisions:
  - "_visible_stats는 등록 시점 검증(validate_entity_axes, 11-02)이 이미 두 신호(룰북 축 form / 개체 StatEntry.form)를 일치시켰다는 전제에 기대지 않고, 이 함수 자신이 두 신호를 독립적으로 다시 확인한다 — 방어가 한 겹만 있으면 등록 검증을 우회한 데이터가 그대로 새 나간다"
  - "체크포인트(Task 3) 확인 과정에서 실제 룰북(dungeonworld_like·openquest) 둘 다 지금 numeric 형태만 선언하고 있어 clock/named_slots/tag_list/usage_die/none 다섯 형태를 실제 데이터로 눈으로 볼 방법이 없다는 것이 드러났다 — 서버 메모리에만 임시로 데모 캐릭터 둘(여섯 형태 시연·축 없음 시연)을 얹어 확인 후 폐기했다. 어떤 저장소 파일도 바뀌지 않았고, requirements.md의 RULE-11 주석이 이 사실(11-04가 실제 룰북 데이터로 나머지 다섯 형태를 실증한다)을 명시하도록 갱신했다"
  - "requirements mark-complete 도구가 traceability 표의 기존 상태가 \"In Progress\"인 두 항목(RULE-11/RULE-12)에서 not_found를 반환해 자동 전환이 안 됐다 — 도구가 \"Pending\" 상태에서의 전환만 처리하는 것으로 보인다. REQUIREMENTS.md를 직접 편집해 RULE-12만 Complete로, RULE-11은 계획서 Source Coverage 표(\"나머지 다섯 형태는 11-03·11-04가 붙인다\")를 따라 In Progress로 유지했다. 이 과정에서 확인 명령을 시험하다 실수로 RULE-09/RULE-10(이 계획과 무관)을 두 번 잘못 Complete로 찍었으나 즉시 git checkout으로 되돌렸다 — 최종 REQUIREMENTS.md diff는 RULE-11/RULE-12 두 줄만 건드린다"

patterns-established:
  - "StatRows의 stat.form 여섯 값 명시적 분기 — 신규 형태 추가 시 이 분기 하나만 늘리면 된다(11-01의 StatEntry._validate_form_payload와 같은 확장 패턴)"

requirements-completed: [RULE-12]

coverage:
  - id: D1
    description: "form==\"none\" 축이 GET 캐릭터 시트 응답 자체에서 제외된다 — 응답 JSON 본문 문자열 어디에도 그 축 이름이 등장하지 않는다(RULE-12 성공 기준 2)"
    requirement: "RULE-12"
    verification:
      - kind: unit
        ref: "tests/test_web_characters.py#test_none_axis_excluded_from_sheet_response"
        status: pass
      - kind: manual_procedural
        ref: "사람 확인 관문(Task 3) — 데모 캐릭터로 브라우저에서 실제로 축 이름이 화면 어디에도 없음을 확인, 오케스트레이터가 API로 별도 재확인(숨겨진 문자열 0건)"
        status: pass
    human_judgment: false
  - id: D2
    description: "resource_axes=()인 룰북을 쓰는 개체의 시트 응답이 stats: []이고 HTTP 200이다"
    requirement: "RULE-11"
    verification:
      - kind: unit
        ref: "tests/test_web_characters.py#test_rulebook_with_zero_axes_returns_empty_stats"
        status: pass
    human_judgment: false
  - id: D3
    description: "시트 응답의 stats 순서가 Entity.stats 선언 순서와 완전히 같다 — 어디서도 다시 정렬하지 않는다"
    requirement: "RULE-11"
    verification:
      - kind: unit
        ref: "tests/test_web_characters.py#test_sheet_stats_preserve_declaration_order"
        status: pass
    human_judgment: false
  - id: D4
    description: "여섯 표현 형태가 StatusPane에서 각자 자기 갈래로 그려진다 — clock은 ThreatClock 재사용, named_slots/tag_list/usage_die는 신설 컴포넌트, none은 서버가 이미 제외해 도달 불가 갈래로 남는다. 축이 없는 시트는 COPY.noResourceAxes 한 줄을 보인다"
    requirement: "RULE-11"
    verification:
      - kind: other
        ref: "cd frontend && npx tsc --noEmit / npm run build — 둘 다 종료 코드 0"
        status: pass
      - kind: manual_procedural
        ref: "Task 3 사람 확인 관문 — 브람(numeric 회귀 없음), [데모] 여섯 형태 시연, [데모] 축 없음 세 캐릭터를 브라우저에서 직접 확인. 승인됨"
        status: pass
    human_judgment: true
    rationale: "이 저장소에 프론트엔드 자동 시험 틀이 없어(vitest/jest 미구성) 여섯 형태가 실제로 사람 눈에 어떻게 그려지는지는 자동 단언으로 증명되지 않는다 — Task 3 사람 확인 관문이 유일한 검증 경로였다. 사장님이 실제로 브라우저에서 확인하고 승인했다."

# Metrics
duration: ~25min (Task 1-2 실행) + 체크포인트 확인 대기(익일 재개)
completed: 2026-08-16
status: complete
---

# Phase 11 Plan 03: 나머지 다섯 표현 형태 화면 연결 + 서버 응답 제외 Summary

**`_visible_stats()`가 「안 쓴다」 축을 시트 응답 조립 단계에서 제외하고, `StatusPane`이 clock/named_slots/tag_list/usage_die 네 형태를 새 갈래로 그리며 세그먼트 원은 `ThreatClock`을 재사용 — 사람 확인 관문에서 실제 브라우저로 승인됨**

## Performance

- **Duration:** Task 1-2 실행 약 25분, Task 3(사람 확인 관문)은 다음 날 재개되어 승인 — 순수 실행 시간과 대기 시간을 분리해서 본다
- **Completed:** 2026-08-16
- **Tasks:** 3 (Task 1 자동, Task 2 자동, Task 3 사람 확인 관문)
- **Files modified:** 5개 (신규 파일 없음)

## Accomplishments

- `src/gptrpg/web/routes_characters.py`에 `_visible_stats(entity, rulebook)`이 신설되어, 룰북이 `form="none"`으로 선언한 축과 개체 자신의 `StatEntry.form=="none"`인 항목을 **둘 다 독립적으로** 확인해 시트 응답 조립 단계에서 제외한다 — 프론트엔드가 숨기는 것이 아니라 서버가 애초에 안 보낸다는 것이 응답 본문 **문자열** 단언(`test_none_axis_excluded_from_sheet_response`)으로 고정됐다
- `frontend/src/panes/StatusPane.tsx`의 `StatRows`가 `stat.form` 여섯 값에 대한 명시적 분기로 재작성됐다 — `numeric`(기존 두 모양 유지), `clock`(`ThreatClock` 재사용, `pulsing` 없이), `named_slots`(신설 `SlotGrid`), `tag_list`(신설 `TagList`), `usage_die`(신설 `UsageDie`), `none`(서버가 이미 제외해 도달 불가 — 명시적 주석과 함께 `null`)
- 자원 축이 하나도 없는 시트가 회색 빈 패널이 아니라 `COPY.noResourceAxes`(「이 룰북은 세는 수치를 쓰지 않아요」) 한 줄을 보인다
- 회귀 시험 두 건 추가 — `resource_axes=()`인 룰북의 시트가 `stats: []`, 브람의 시트 응답이 `Entity.stats` 선언 순서를 그대로 보존
- **사람 확인 관문(Task 3)이 실제 브라우저로 통과했다** — 브람 수치 무변화(D-49), 축 없는 캐릭터의 의도된 문구, 「안 쓴다」 축 이름이 화면 어디에도 없음, 다섯 새 형태가 각자 읽을 만하게 보임을 전부 확인 후 승인

## Task Commits

각 태스크를 개별 커밋했다:

1. **Task 1: 「안 쓴다」 축을 시트 응답 조립 단계에서 제외한다** — `6a90841` (feat)
2. **Task 2: 캐릭터 판이 여섯 표현 형태를 각자 자기 모양으로 그린다** — `8d592ef` (feat)

Task 3(사람 확인 관문)은 코드 변경이 없는 순수 확인이라 별도 커밋이 없다 — 승인 시점이 이 SUMMARY 작성 직전이다.

**Plan metadata:** 이 커밋 (SUMMARY.md 등)

## Files Created/Modified

- `src/gptrpg/web/routes_characters.py` - `_visible_stats(entity, rulebook)` 신설, `get_character_sheet`가 이 함수를 거쳐 조립하도록 재작성, `StatEntryView`/`CharacterSheetView` 도크스트링에 「이 제외는 서버 쪽 책임」 명시
- `tests/test_web_characters.py` - `test_none_axis_excluded_from_sheet_response`(응답 본문 문자열 단언 포함), `test_rulebook_with_zero_axes_returns_empty_stats`, `test_sheet_stats_preserve_declaration_order` 3건 추가
- `frontend/src/panes/StatusPane.tsx` - `StatRows`를 `stat.form` 여섯 값 명시적 분기로 재작성, `SlotGrid`/`TagList`/`UsageDie` 신설, 빈 `sheet.stats`에 `COPY.noResourceAxes` 표시
- `frontend/src/labels.ts` - `noResourceAxes`/`emptySlot`/`usageDieSpent` 세 문구 추가
- `frontend/src/styles.css` - `.stat-clock`/`.stat-slots`/`.stat-slots__grid`/`.slot`/`.stat-tags`/`.stat-tags__chips`/`.chip`/`.stat-usage-die` 스타일 추가(기존 다크 잉크 + 놋쇠 색 어휘 그대로, 새 npm 패키지 없음)

## Decisions Made

- **`_visible_stats`가 이중 확인을 한다:** 등록 시점 검증(11-02의 `validate_entity_axes`)이 이미 룰북 축 선언의 `form`과 개체 `StatEntry.form`을 일치시켰다는 전제에 기대지 않고, 이 함수 자신이 두 신호(룰북 축의 form, 개체 항목의 form)를 독립적으로 각각 확인해서 제외한다. 방어가 한 겹만 있으면 등록 검증을 우회한 데이터(예: 런타임에 `RULEBOOKS`를 직접 패치하는 시험류)가 그대로 새 나갈 수 있다.
- **체크포인트 확인 과정에서 데모 데이터를 임시로 서버 메모리에만 얹었다.** Task 2까지 끝낸 시점에 확인해 보니, 이 저장소의 실제 두 룰북(dungeonworld_like·openquest)이 지금 전부 `numeric` 형태만 선언하고 있어 계획서 Task 3의 검증 단계(축 없는 캐릭터·「안 쓴다」 축·가방/표식/자원주사위)를 실제 앱 데이터로는 눈으로 확인할 방법이 없었다. 저장소 파일을 건드리지 않고 `gptrpg.rulebooks.RULEBOOKS`/`gptrpg.web.characters_data.PLAYER_CHARACTERS` 딕셔너리에 런타임 패치만 거는 스크립트로 데모 캐릭터 둘(여섯 형태 시연·축 없음 시연)을 서버 프로세스 메모리에만 얹어 확인했다 — 서버 종료와 함께 사라졌고, `git status`로 저장소가 깨끗함을 확인했다.
- **REQUIREMENTS.md를 도구가 아니라 직접 편집으로 갱신했다.** `requirements mark-complete`가 traceability 표의 기존 상태가 "In Progress"인 RULE-11/RULE-12에서 `not_found`를 반환해 자동 전환이 안 됐다(도구가 "Pending → Complete" 전환만 처리하는 것으로 보인다 — "Pending" 상태인 다른 요구사항 RULE-09/RULE-10으로 시험했을 때는 정상 동작했다). 계획서의 Source Coverage 서술("나머지 다섯 형태는 11-03·11-04가 붙인다")을 따라 RULE-12는 `Complete`로, RULE-11은 `In Progress`로 직접 편집했다(아래 편차 참조).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `requirements mark-complete` 도구가 RULE-11/RULE-12에서 `not_found`를 반환해 REQUIREMENTS.md를 직접 편집으로 갱신**
- **Found during:** state_updates 단계, requirements 표 갱신 시도 중
- **Issue:** `gsd-tools requirements mark-complete RULE-11 RULE-12`가 두 요구사항 모두 checkbox·traceability 두 표면에서 `not_found`를 반환했다. 원인을 좁히려 "Pending" 상태인 RULE-09/RULE-10으로 시험했더니 정상 동작했다 — 도구가 기존 상태가 "In Progress"인 항목의 전환을 처리하지 못하는 것으로 보인다. 이 시험 과정에서 RULE-09/RULE-10(이 계획과 완전히 무관)이 실수로 두 번 `Complete`로 찍혔다.
- **Fix:** RULE-09/RULE-10 오염을 `git checkout -- .planning/REQUIREMENTS.md`로 즉시 되돌렸다(두 번, 각 실수 직후). 이후 REQUIREMENTS.md를 Edit 도구로 직접 편집해 RULE-12만 `[x]`/`Complete`로, RULE-11은 계획서 Source Coverage 서술을 반영한 주석과 함께 `[ ]`/`In Progress`로 유지했다.
- **Files modified:** `.planning/REQUIREMENTS.md`
- **Verification:** `git diff .planning/REQUIREMENTS.md` — 최종 diff가 RULE-11/RULE-12 두 줄(+ traceability 표 RULE-12 한 줄)만 건드리는 것을 확인, RULE-09/RULE-10은 원상태로 복귀됨을 재확인
- **Committed in:** 이 커밋(SUMMARY.md 등과 함께)
- **파급:** 후속 계획(11-04~11-07) 실행자는 `requirements mark-complete`가 "In Progress" 상태의 요구사항을 자동 전환하지 못할 수 있다는 것을 알아야 한다 — 표를 직접 대조해 편집하는 것이 이 저장소에서 이미 두 번(11-01, 이번) 필요했다.

**2. [Rule 2 - Missing Critical] 체크포인트 검증 환경에 실제 데이터가 없어 임시 데모 캐릭터를 서버 메모리에 얹음**
- **Found during:** Task 3 체크포인트 자동화 준비 중
- **Issue:** 계획서 Task 3의 검증 단계 3·4·5번이 요구하는 화면(축 없는 캐릭터·「안 쓴다」 축·가방/표식/자원주사위)이 이 저장소의 실제 룰북 데이터로는 존재하지 않았다 — 브람·나리·선·호두 넷 모두 numeric 형태만 쓴다. 체크포인트 프로토콜의 "Claude가 검증 환경을 준비한다" 원칙을 지키려면 사람이 확인할 화면 자체가 있어야 했다.
- **Fix:** 저장소 파일을 전혀 건드리지 않고, 서버 시작 전 `gptrpg.rulebooks.RULEBOOKS`/`gptrpg.web.characters_data.PLAYER_CHARACTERS` 딕셔너리에 데모 룰북·캐릭터 둘을 런타임으로만 얹는 launcher 스크립트를 스크래치패드에 작성해 그 상태로 서버를 띄웠다. 확인 종료 후 서버 프로세스를 종료하고 launcher 스크립트·DB 파일을 삭제해 흔적을 남기지 않았다.
- **Files modified:** 없음(저장소 파일 무변경 — 스크래치패드 임시 파일만 생성 후 삭제)
- **Verification:** 승인 후 `git status --short`로 저장소가 깨끗함을 확인, 오케스트레이터가 별도로 API를 직접 호출해 서버 응답도 재확인(축 7개 선언 → 응답 6개, "숨겨진" 문자열 0건, `demo-zero-axes`는 `stats: []`)
- **Committed in:** 코드 변경이 없어 커밋 없음
- **파급:** 11-04(Cairn 룰북 투입)가 실제 `named_slots` 데이터를 붙이면, 그 시점부터는 이런 임시 데모 없이도 실제 데이터로 화면 확인이 가능해진다.

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing critical)
**Impact on plan:** 첫 번째는 요구사항 문서 갱신 절차의 도구 한계를 우회한 것이고, 두 번째는 계획서 자신의 체크포인트가 요구하는 검증을 실제로 가능하게 만든 것이다. 둘 다 저장소 코드나 커밋된 게임 데이터를 바꾸지 않았다.

## Issues Encountered

**확인 과정에서 Phase 11과 무관한 기존 결함 2건이 드러났다 — 이 계획 범위 밖, todo로 이관.**

Task 3 체크포인트를 확인하던 중, 캐릭터 변경 관련 기존 결함 2건이 발견됐다. 사장님이 "Phase 11 끝난 뒤에 잡는다"고 결정했고, 이미 `.planning/todos/pending/2026-08-16-character-change-dead-end.md`에 기록되어 커밋(`162175a`)됐다:

1. 한 브라우저가 캐릭터를 하나만 점유할 수 있고 놓는 경로가 없는데, 화면은 「캐릭터 변경하기」를 제공한다 → 두 번째 선택이 409로 거절된다
2. `CharacterSelect.tsx:88-97`이 **선택 실패**를 `characterListError`(「목록을 불러오지 못했어요」)로 표시한다 — 실제로 실패한 것과 다른 메시지를 가리킨다

**이 계획이 만든 결함이 아니다** — `CharacterSelect.tsx`는 저장소 초기 커밋 이후 이 계획에서 수정한 적이 없다. `_visible_stats`/`StatusPane` 변경과 무관하게 이미 존재하던 캐릭터 선택 흐름의 문제다.

## User Setup Required

None - 외부 서비스 설정 불필요.

## Next Phase Readiness

- RULE-12는 이 계획으로 완전히 끝났다 — REQUIREMENTS.md를 `[x]`/`Complete`로 갱신했다
- RULE-11은 플랫폼 능력(여섯 형태 렌더 갈래 + 서버 제외 로직)까지는 이 계획으로 끝났지만, 실제 룰북이 나머지 다섯 형태를 골라 쓰는 실증은 아직이다 — REQUIREMENTS.md에 "11-04(Cairn 등)가 그 실증을 완성한다"는 주석과 함께 `In Progress`로 남겼다
- 11-04(세 번째 룰북 Cairn 투입)가 `named_slots` 형태를 실제 데이터로 선언하면, 이번 계획이 만든 `SlotGrid`가 처음으로 실제 룰북 데이터를 그리게 된다
- 11-07(출하 룰북이 「안 쓴다」를 실제로 선언)이 `form="none"` 축을 실제로 선언하면, 이번 계획의 `_visible_stats` 제외 로직이 처음으로 실제 데이터에서 작동한다
- 캐릭터 변경/선택 흐름의 기존 결함 2건이 todo로 남아 있다 — 이번 계획이 만든 것이 아니고, 사장님 결정에 따라 Phase 11 종료 후 처리한다
- 블로커 없음 — Phase 11의 다음 계획(11-04)으로 바로 이어갈 수 있다

## Self-Check: PASSED

- 파일 존재: `src/gptrpg/web/routes_characters.py`, `tests/test_web_characters.py`, `frontend/src/panes/StatusPane.tsx`, `frontend/src/labels.ts`, `frontend/src/styles.css` 전부 확인됨
- 커밋 존재: `6a90841`, `8d592ef` 전부 `git log --oneline --all`에서 확인됨
- 마감 전 재검증: `uv run pytest -q` 871 passed, `uv run lint-imports` 4 kept/0 broken, `cd frontend && npx tsc --noEmit` 종료 코드 0

---
*Phase: 11-rulebook-vocabulary*
*Completed: 2026-08-16*
