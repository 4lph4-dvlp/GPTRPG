---
phase: 10-ai
plan: 07
subsystem: ai-safety
tags: [narration-guard, event-schema, pydantic-model-validator, master-gm, safety-flag]

# Dependency graph
requires:
  - phase: 10-ai (10-03, 10-06)
    provides: narration_guard 네 갈래 판정(think_block/source_overlap/character_break/corrupted_glyph), master_gm 재생성 배선, SafetyFlagged 사건(판 6)
provides:
  - "narration_guard.GuardVerdict.subject_len이 모든 판정 갈래에서 matched_len<=subject_len 불변식을 만족"
  - "master_gm._judge_sentence 표준오류 발췌가 문장 경계 넘는 겹침에서도 실제로 걸린 글자를 보여줌"
  - "event_log.schema.SafetyFlagged에 source×reason 필요충분 model_validator"
  - "session_actor.actor._prepare_safety_flag에 같은 교차검증(액터 층)"
  - "master_gm.py에서 MAX_REGENERATIONS 상수 제거, 3회 호출 상한을 실제 호출-횟수 시험이 보증"
affects: [14-context-compression]

# Actuals (#2632)
actuals:
  tokens: 8302
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "model_validator(mode='after') 쌍(스키마 층 + 액터 층)으로 같은 불변식을 두 번 강제 — CheckResolved._require_identity_from_schema_5 모양을 그대로 재사용"
    - "실제 호출을 세는 시험이 이름뿐인 상수보다 강한 보증이라는 판단 — 상수를 지우고 호출-횟수 단언 시험으로 대체"

key-files:
  created: []
  modified:
    - src/gptrpg/agents/narration_guard.py
    - src/gptrpg/agents/master_gm.py
    - src/gptrpg/event_log/schema.py
    - src/gptrpg/session_actor/actor.py
    - tests/test_narration_guard.py
    - tests/test_master_gm.py
    - tests/test_safety_flag_pipeline.py

key-decisions:
  - "WR-02: matched_len을 자르지 않고 subject_len(분모)을 정직하게 넓히는 쪽을 택함(리뷰의 (b)안 명시적 거부) — Phase 14 심각도 분석이 쓸 유출 크기 정보를 보존"
  - "WR-01: 재생성 블록을 반복문으로 안 바꿈(리뷰의 (a)안 명시적 거부) — 22분 먹통 사고가 난 바로 그 자리를 구조적으로 안 건드림. 대신 실제 호출 횟수를 세는 시험이 3회 상한을 진다"
  - "WR-03: EVENT_SCHEMA_VERSION을 안 올림 — safety_flagged 기록이 세 DB 모두 0건이라 다시 해석할 옛 기록이 없다는 오케스트레이터 사실을 재확인 후 진행"

patterns-established:
  - "matched_len<=subject_len 불변식을 네 갈래 모두에 대해 단언하는 단일 회귀 시험 — 새 판정 갈래가 추가돼도 같은 시험이 자동으로 적용됨"

requirements-completed: [SAFE-01, SAFE-02, SAFE-04]

coverage:
  - id: D1
    description: "matched_len<=subject_len 불변식이 문장 경계를 넘는 원문 겹침에서도 성립하고, 표준오류 발췌가 실제로 걸린 글자를 보여준다(WR-02)"
    requirement: "SAFE-02"
    verification:
      - kind: unit
        ref: "tests/test_narration_guard.py#test_source_overlap_crossing_boundary_keeps_matched_len_within_subject_len"
        status: pass
      - kind: unit
        ref: "tests/test_narration_guard.py#test_matched_len_never_exceeds_subject_len_across_all_four_branches"
        status: pass
      - kind: unit
        ref: "tests/test_narration_guard.py#test_source_overlap_never_truncates_matched_len_to_subject_len"
        status: pass
    human_judgment: false
  - id: D2
    description: "source×reason 말 안 되는 조합이 스키마 층과 액터 층 양쪽에서 독립적으로 거절된다(WR-03)"
    requirement: "SAFE-04"
    verification:
      - kind: unit
        ref: "tests/test_safety_flag_pipeline.py#test_schema_rejects_nonsensical_source_reason_combinations"
        status: pass
      - kind: unit
        ref: "tests/test_safety_flag_pipeline.py#test_actor_rejects_nonsensical_source_reason_combinations_and_appends_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_safety_flag_pipeline.py#test_schema_accepts_the_five_real_source_reason_combinations"
        status: pass
      - kind: unit
        ref: "tests/test_safety_flag_pipeline.py#test_actor_accepts_the_five_real_source_reason_combinations"
        status: pass
    human_judgment: false
  - id: D3
    description: "한 턴에 제공자 stream() 호출이 3회를 못 넘는다는 것을 실제 호출을 세는 시험이 단언한다(WR-01), MAX_REGENERATIONS 상수 제거"
    requirement: "SAFE-01"
    verification:
      - kind: unit
        ref: "tests/test_master_gm.py#test_narrate_never_exceeds_three_provider_stream_calls_in_a_single_turn"
        status: pass
      - kind: unit
        ref: "tests/test_master_gm.py#test_narrate_stream_call_count_stays_within_the_three_call_ceiling_across_all_paths"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-08-14
status: complete
---

# Phase 10 Plan 07: 코드 리뷰 경고 3건 닫기(WR-01/WR-02/WR-03) Summary

**narration_guard의 subject_len 재정의로 matched_len<=subject_len 불변식을 네 판정 갈래 전부에서 성립시키고, SafetyFlagged에 스키마+액터 이중 model_validator로 source×reason 조합을 강제하고, 이름만 지키던 MAX_REGENERATIONS 상수를 지우고 3회 호출 상한을 실제 호출-횟수 시험이 지도록 바꿨다.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 3
- **Files modified:** 7 (4 src + 3 test)

## Accomplishments

- **WR-02 (Task 1):** `narration_guard.inspect_sentence`의 `source_overlap` 갈래에서 `subject_len`을 "이 판정의 `matched_len`을 잰 대상 텍스트의 길이"로 재정의했다. 겹침이 `sentence`를 넘어 `next_sentence`까지 뻗었으면 `subject_len = len(sentence) + len(next_sentence or "")`, 안 넘었으면 지금까지와 같은 `len(sentence)`다. 판정은 `find_source_overlap(sentence, None, source_texts)`(두 번째 호출)로 "next_sentence 없이 얻을 수 있는 최대 겹침 길이"와 비교해 결정한다 — 더 길게 나왔다면 그 초과분은 반드시 `len(sentence)`를 넘어선 자리에서 왔다는 것이 증명이다. `matched_len`은 절대 자르지 않는다(리뷰의 (b)안 명시적 거부). `master_gm._judge_sentence`의 표준오류 발췌도 `verdict.subject_len > len(sentence)`일 때 이어 붙인 텍스트에서 뜨도록 고쳐, 겹침이 다음 문장 쪽에 몰려 있어도 운영자가 실제로 걸린 글자를 본다.
- **WR-03 (Task 2):** `event_log.schema.SafetyFlagged`에 `model_validator(mode="after")` `_require_source_reason_pairing`을 추가했다 — `CheckResolved._require_identity_from_schema_5`가 이미 쓰는 모양을 그대로 따른다. 불변식은 `reason == "unknown_move"`인 것과 `source == "classifier"`인 것이 서로 필요충분이라는 것 하나다. `session_actor.actor._prepare_safety_flag`에 같은 교차검증을 개별 필드 검증(source/reason/disposition 닫힌 목록) 뒤에 이어서 추가했다 — 액터 검증은 명령이 저장소에 닿기 전에 막고, 스키마 검증은 저장소를 우회해 만든 객체까지 막는다는 이중 구조의 이유를 양쪽 주석에 남겼다.
- **WR-01 (Task 3):** `MAX_REGENERATIONS = 1` 상수와 그 도크스트링을 완전히 지웠다 — 실제로는 자기 선언 밖 아무 데서도 안 읽히던 이름뿐인 보증이었다. 이 이름을 언급하던 두 자리(narrate() 도크스트링, 재생성 블록 주석)를 구조적 사실("이 블록은 반복문이 아니라서 정확히 한 번 돈다")을 직접 말하도록 고쳤다. `tests/test_master_gm.py`에 `MAX_ATTEMPTS`(2, 재시도) + 재생성(1)이 같은 턴에서 겹치는 가장 나쁜 경우를 재현하는 새 이중체(`_FailsOnceThenBlocksThenCleanProvider`)와 전용 시험(`test_narrate_never_exceeds_three_provider_stream_calls_in_a_single_turn`, 도크스트링이 03-04의 22분 먹통 사고를 직접 인용)을 추가해 `provider.stream()` 호출이 정확히 3회에서 멈추는지 실제로 센다. 재생성 블록은 반복문으로 안 바꿨다(리뷰의 (a)안 명시적 거부).

## Task Commits

Each task was committed atomically:

1. **Task 1: 겹친 글자수 불변식을 바로잡는다 (WR-02, SAFE-02)** - `0374c20` (fix)
2. **Task 2: source × reason 조합을 스키마가 막는다 (WR-03)** - `49b28d8` (feat)
3. **Task 3: 턴당 호출 횟수를 시험이 지킨다 (WR-01, SAFE-04)** - `7704715` (test)

_Note: 세 Task 모두 `tdd="true"`였으나 기존 코드(narration_guard/schema/actor/master_gm)가 이미 존재하는 상태에서 불변식·검증·회귀 시험을 더하는 게이트 닫기 작업이라, 각 커밋이 프로덕션 변경과 그 시험을 함께 담았다(개별 RED/GREEN 커밋으로 안 나눔) — 이 계획은 신규 기능이 아니라 리뷰 경고 폐쇄이므로 계획 문서의 `<action>` 지시가 이미 "시험 + 코드"를 한 갈래로 묶어 서술했다._

## Files Created/Modified

- `src/gptrpg/agents/narration_guard.py` - `GuardVerdict.subject_len` 도크스트링 재정의, `inspect_sentence`의 `source_overlap` 갈래가 경계 넘는 겹침에서 이어 붙인 길이를 분모로 씀
- `src/gptrpg/agents/master_gm.py` - `_judge_sentence` 표준오류 발췌가 경계 넘는 겹침에서 이어 붙인 텍스트를 씀, `MAX_REGENERATIONS` 상수 제거 및 관련 도크스트링/주석 정정
- `src/gptrpg/event_log/schema.py` - `SafetyFlagged._require_source_reason_pairing` model_validator 추가
- `src/gptrpg/session_actor/actor.py` - `_prepare_safety_flag`에 source×reason 교차검증 추가
- `tests/test_narration_guard.py` - 4개 신규 시험(경계 넘는 겹침 불변식, 안 넘는 겹침, 네 갈래 통합 불변식, matched_len 비절단 확인)
- `tests/test_master_gm.py` - 5개 신규 시험(3회 상한 최악 경로 전용 시험 1개 + 네 경로 파라미터화 시험 4개), 새 이중체 `_FailsOnceThenBlocksThenCleanProvider`
- `tests/test_safety_flag_pipeline.py` - 14개 신규 시험(스키마 5조합 통과 5개 + 스키마 2조합 거절 2개 + 액터 5조합 통과 5개 + 액터 2조합 거절 2개), `_NoRollNeededRoller`/`_make_safety_actor` 헬퍼

## Decisions Made

- WR-02는 `matched_len`을 자르는 (b)안이 아니라 `subject_len`을 이어 붙인 길이로 넓히는 쪽을 택했다 — 유출 크기 정보가 Phase 14 심각도 분석의 입력이라 깎으면 안 된다는 것이 이유다.
- WR-01은 재생성 블록을 반복문으로 바꾸는 (a)안을 안 골랐다 — 스트리밍 상태 기계를 구조적으로 건드리는 변경이고, 정확히 그 자리가 03-04에서 22분 먹통이 난 자리였다. 강제는 상수가 아니라 시험이 지도록 했다.
- WR-03의 `SafetyFlagged` 교차검증은 `EVENT_SCHEMA_VERSION`을 안 올렸다 — `reason`이 쓰기 검증에만 쓰이고 `reducer.py`가 `reason`을 안 본다는 기존 판단(10-06)이 이번 model_validator 추가에도 그대로 적용된다(구조가 바뀌는 게 아니라 쓰기 시점 검증이 하나 늘 뿐).

## Deviations from Plan

None - plan executed exactly as written. 세 오케스트레이터 확인 사실(safety_flagged 0건, matched_len>subject_len 재현, MAX_REGENERATIONS가 42/399/520줄에서만 언급) 전부 재검증 후 참으로 확인하고 진행했다.

## Issues Encountered

- `tests/test_master_gm.py`의 네 경로 파라미터화 시험에서 `_BlocksOnceThenCleanProvider`가 `stream_call_count` 대신 `stream_calls`(리스트) 속성을 쓴다는 것을 첫 실행 실패로 발견 — 두 이중체 스타일을 모두 지원하는 `getattr` 폴백으로 해결(코드 자체가 아니라 새로 쓴 시험 안의 소소한 어긋남).

## Next Phase Readiness

- 세 경고 모두 닫혔다 — `matched_len<=subject_len`이 코드로 강제되고, source×reason 조합이 이중으로 막히고, 3회 호출 상한이 시험으로 못박혔다.
- `EVENT_SCHEMA_VERSION`은 6에서 그대로다 — 세 DB(events.db/uat9.db/uat10.db) 모두 예외 없이 다시 읽힌다(기존 회귀 시험 그대로 통과).
- 전체 스위트 827건 통과(804 기존 + 23 신규), `ruff check src` 클린, `lint-imports` 4/4 계약 유지.

---
*Phase: 10-ai*
*Completed: 2026-08-14*

## Self-Check: PASSED

All 7 modified files confirmed present on disk; all 3 task commits (`0374c20`, `49b28d8`, `7704715`) confirmed in `git log --oneline --all`.
