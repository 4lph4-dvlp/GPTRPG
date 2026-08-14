---
phase: 10-ai
plan: 06
subsystem: ai
tags: [narration-guard, safety-flagged, event-schema, unicode, u+fffd]

# Dependency graph
requires:
  - phase: 10-ai (10-01)
    provides: SafetyFlagged event kind (판 6), reducer의 safety_flagged 분기
  - phase: 10-ai (10-02)
    provides: inspect_sentence의 원문 겹침·캐릭터 이탈 갈래, GuardVerdict 모양
provides:
  - "inspect_sentence의 네 번째 갈래 — 깨진 글자(U+FFFD) 탐지, reason=corrupted_glyph"
  - "REPLACEMENT_CHAR 상수 · count_corrupted_glyphs() 함수"
  - "SafetyFlagged.reason Literal에 corrupted_glyph 추가 (판 안 올림)"
affects: [10-ai future plans, 12-observability if it audits safety_flagged reasons]

actuals:
  tokens: 5140
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "내용 무관 탐지 갈래: 문구 목록·모델 이름 분기 없이 REPLACEMENT_CHAR 존재 여부만 본다"
    - "품질 결함 vs 안전 유출을 disposition으로 구분 — flagged(통과+기록)와 blocked(자동 차단)를 판정 순서로 우선순위화"

key-files:
  created: []
  modified:
    - src/gptrpg/agents/narration_guard.py
    - src/gptrpg/event_log/schema.py
    - src/gptrpg/session_actor/actor.py
    - tests/test_narration_guard.py
    - tests/test_safety_flag_pipeline.py
    - tests/test_event_schema_migration.py

key-decisions:
  - "깨진 글자는 flagged이지 blocked가 아니다 — 심하게 깨뜨리는 모델에서는 거의 모든 문장이 걸려 blocked면 10-03의 재생성·포기 경로를 타고 게임이 멈춘다"
  - "EVENT_SCHEMA_VERSION을 6에서 안 올린다 — reason은 쓰기 검증에서만 쓰이고 reducer의 safety_flagged 분기는 reason을 안 본다, 두 실기록 DB(895건/221건)로 못박음"
  - "판정 순서에서 마지막 — 캐릭터 이탈이 먼저 걸리면 그 사유가 이긴다(두 사유를 합치는 칸을 새로 만들지 않는다)"

patterns-established:
  - "네 번째 검사 갈래도 inspect_sentence 하나의 판정 순서 체인에 추가 — 새 함수·새 반환 모양을 만들지 않고 기존 GuardVerdict를 그대로 재사용"

requirements-completed: [SAFE-01]

coverage:
  - id: D1
    description: "narration_guard.inspect_sentence가 U+FFFD가 섞인 문장을 flagged/corrupted_glyph로 판정하고 원문을 그대로 통과시킨다"
    requirement: "SAFE-01"
    verification:
      - kind: unit
        ref: "tests/test_narration_guard.py#test_corrupted_glyph_is_flagged_not_blocked_and_keeps_original_text"
        status: pass
      - kind: unit
        ref: "tests/test_narration_guard.py#test_corrupted_glyph_branch_never_produces_blocked"
        status: pass
    human_judgment: false
  - id: D2
    description: "깨진 글자 판정이 웹 턴 파이프라인 끝까지 흘러 safety_flagged 사건으로 기록되면서 같은 문장이 narration_appended로도 나간다"
    requirement: "SAFE-01"
    verification:
      - kind: integration
        ref: "tests/test_safety_flag_pipeline.py#test_web_corrupted_glyph_is_recorded_and_still_reaches_the_screen"
        status: pass
    human_judgment: false
  - id: D3
    description: "EVENT_SCHEMA_VERSION이 6에서 안 올랐고, 옛 판 2/판 5 실기록(895건/221건)에 corrupted_glyph가 없으며 모두 예외 없이 접힌다"
    requirement: "SAFE-01"
    verification:
      - kind: unit
        ref: "tests/test_event_schema_migration.py#test_event_schema_version_is_still_six"
        status: pass
      - kind: integration
        ref: "tests/test_event_schema_migration.py#test_events_db_has_no_corrupted_glyph_reason_yet"
        status: pass
      - kind: integration
        ref: "tests/test_event_schema_migration.py#test_uat9_db_has_no_corrupted_glyph_reason_yet"
        status: pass
    human_judgment: false

duration: ~25min
completed: 2026-08-14
status: complete
---

# Phase 10 Plan 06: 깨진 글자(U+FFFD) 탐지 갈래 Summary

**서사 문장에 U+FFFD가 섞이면 `inspect_sentence`가 네 번째 갈래(`corrupted_glyph`)로 잡아 운영자 기록을 남기되, 문장 자체는 그대로 화면에 내보낸다 — `EVENT_SCHEMA_VERSION`은 6에서 그대로다.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2/2
- **Files modified:** 6

## Accomplishments
- `narration_guard.py`에 `REPLACEMENT_CHAR` 상수와 `count_corrupted_glyphs()` 함수, `inspect_sentence`의 네 번째(마지막) 판정 갈래를 더했다 — 내용 무관, `flagged`만, 캐릭터 이탈이 먼저 걸리면 그쪽이 이긴다
- `event_log/schema.py`의 `SafetyFlagged.reason` Literal과 `session_actor/actor.py`의 `_VALID_SAFETY_FLAG_REASONS`에 `corrupted_glyph`를 같은 커밋으로 더했다(한쪽만 고치면 안전 기록 제출이 예외로 죽는 구조)
- 웹 파이프라인 시험 하나로 "기록됨"과 "화면에 나감"을 동시에 단언해 두 방향 회귀를 함께 잡는 시험을 추가했다
- 옛 실기록 DB 두 개(판 2 895건, 판 5 221건)에 `corrupted_glyph`가 없다는 것과 `EVENT_SCHEMA_VERSION == 6`을 명시적으로 못박는 시험을 추가했다
- `master_gm.py`의 `_judge_sentence`가 이미 `reason`을 사유별 분기 없이 그대로 실어 나른다는 것을 확인했다 — 사유가 늘어도 코드 변경이 필요 없어(계획 판단 ④의 "확인만 하고 끝난다" 경로), 이 파일은 무변경으로 남았다

## Task Commits

Each task was committed atomically:

1. **Task 1: 깨진 글자 탐지 갈래 (SAFE-01)** - `3624741` (feat)
2. **Task 2: 통로 끝까지 흐르는지 + 옛 기록 무사한지 (SAFE-01)** - `f6ec56f` (test)

**Plan metadata:** (see below, committed after this file)

## Files Created/Modified
- `src/gptrpg/agents/narration_guard.py` - `REPLACEMENT_CHAR`·`count_corrupted_glyphs()`, `inspect_sentence`의 4번째 갈래, 모듈/함수 도크스트링 확장
- `src/gptrpg/event_log/schema.py` - `SafetyFlagged.reason` Literal에 `corrupted_glyph` 추가, 판 안 올리는 이유 주석
- `src/gptrpg/session_actor/actor.py` - `_VALID_SAFETY_FLAG_REASONS`에 `corrupted_glyph` 추가
- `tests/test_narration_guard.py` - 깨진 글자 갈래 단위 시험 8개(정상 판정, 우선순위 두 방향, 예외 없음, blocked 불가능 회귀 그물)
- `tests/test_safety_flag_pipeline.py` - 웹 턴에서 corrupted_glyph 기록+화면 도달 동시 단언
- `tests/test_event_schema_migration.py` - 옛 기록 0건 명시 단언 2개, 새 fold 시험 1개, `EVENT_SCHEMA_VERSION == 6` 핀 1개

## Decisions Made
- 판정 순서 마지막에 둔다: 생각 블록 → 원문 겹침 → 캐릭터 이탈 → 깨진 글자. 앞의 셋은 안전, 이건 품질이라 순서상 뒤에 둬도 안전성 손실이 없다(계획 설계 판단 4 그대로 구현)
- `master_gm.py`는 사유별 분기가 없어 무변경 — 계획이 명시적으로 허용한 "확인만 하고 끝나는" 경로를 그대로 밟았다

## Deviations from Plan

None - plan executed exactly as written. 계획의 「계획이 확정한 설계 판단」 1~3에 실린 세 코드 사실(actor.py:214/751의 쓰기-전용 검증, reducer.py:246의 reason 무시)을 재확인했고 모두 정확했다.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `corrupted_glyph` 사유가 검사기→사건 기록까지 끊김 없이 흐르고, 다음에 어떤 모델이 같은 방식으로 글자를 깨뜨려도 사람이 눈으로 찾을 필요 없이 운영자 기록에 자동으로 남는다
- 옛 기록 1116건(events.db 895 + uat9.db 221)이 이 변경 뒤에도 예외 없이 접힌다는 것을 시험으로 확인했다
- Phase 10의 나머지 계획(있다면)이나 향후 관측 단계에서 `safety_flagged` 사건의 `reason` 분포를 집계할 때 `corrupted_glyph`가 다섯 번째 값으로 나타날 수 있다는 것을 유의할 것

---
*Phase: 10-ai*
*Completed: 2026-08-14*

## Self-Check: PASSED

All created/modified files found on disk; both task commit hashes (`3624741`, `f6ec56f`) verified present in `git log`.
