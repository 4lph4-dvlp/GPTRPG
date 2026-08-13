---
phase: 10-ai
plan: 01
subsystem: ai-safety
tags: [event-sourcing, narration-guard, streaming, pydantic, sqlite, regex]

requires:
  - phase: 08-identity-and-idempotency
    provides: "EVENT_SCHEMA_VERSION 판 올리기 + reducer.py 같은 커밋 관례(D-06), 옛 판 해석 경로 패턴(D-13)"
  - phase: 09-agent-architecture
    provides: "master_gm.narrate()가 서술 전용으로 분리된 상태, NarrationFacts가 시나리오 원문을 안 받는 구조"
provides:
  - "narration_guard.py leaf 모듈 — inspect_sentence/strip_think_blocks/GuardVerdict (생각 블록 검사 갈래만 채움, 10-02/10-04가 원문 겹침·캐릭터 이탈 갈래를 이어붙일 자리)"
  - "master_gm.narrate()의 1문장 지연 버퍼 + NarrationChunk 반환 타입 — 10-02~10-05가 이 뼈대 위에 검사 종류를 덧붙인다"
  - "safety_flagged 사건 종류(판 6) — 서사 검사(source=narration)와 분류기 계약 위반(source=classifier)을 함께 담는 그릇"
  - "웹·CLI 두 호출부의 NarrationChunk 소비 패턴(_submit_narration_chunk) — 10-02~10-05가 disposition 갈래를 늘릴 때 이 함수만 손대면 된다"
affects: [10-02, 10-03, 10-04, 10-05]

actuals:
  tokens: 18000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "1문장 지연 버퍼 안쪽에 try/except를 하나 더 둬 '스톨·실패 도중에도 이미 도착한 문장은 판정해 내보낸다'를 지킨다 — 바깥 재시도 판단(except StreamStalled/except Exception)은 문자 하나 안 바뀐다"
    - "닫힌 목록 + 숫자 칸만 있는 사건으로 안전 장치 기록을 남기고, 사람이 읽을 발췌는 표준오류에만 찍는다(T-10-03)"

key-files:
  created:
    - src/gptrpg/agents/narration_guard.py
    - tests/test_safety_flag_pipeline.py
    - tests/test_event_schema_migration.py
  modified:
    - src/gptrpg/agents/json_parsing.py
    - src/gptrpg/agents/master_gm.py
    - src/gptrpg/event_log/schema.py
    - src/gptrpg/rules_core/reducer.py
    - src/gptrpg/session_actor/actor.py
    - src/gptrpg/web/routes_actions.py
    - src/gptrpg/cli/turn_flow.py
    - tests/test_master_gm.py
    - tests/test_agents_retry.py
    - tests/test_turn_flow_failure.py
    - tests/test_clock_condition_cli.py
    - tests/test_clock_condition_web.py
    - tests/test_narration_isolation.py

key-decisions:
  - "Task 1 checkpoint: option-a — 사건 종류 하나(safety_flagged, source 칸이 narration/classifier를 가른다). 판 올리기가 되돌릴 수 없는 조작이므로 한 번에 D-04·D-12를 둘 다 덮는다."
  - "narrate()의 지연 버퍼 안쪽에 'except → 보류 문장 판정·방출 → 다시 던지기'를 추가해, 바깥 재시도 로직(그대로 유지)을 안 건드리면서도 03-04의 '이미 나간 조각은 스톨 뒤에도 살아남는다' 보장을 지연 버퍼 구조 안에서 지켰다."
  - "판 5·895건이라는 CONTEXT/RESEARCH/VALIDATION의 서술이 실제 파일과 어긋난다는 것을 재확인 — .gptrpg/events.db는 전부 판 2, 판 5 기록은 .gptrpg/uat9.db(221건, 세션 넷)에 있다."

requirements-completed: [SAFE-01, SAFE-03, TEST-03]

coverage:
  - id: D1
    description: "생각 블록이 섞인 문장이 웹·CLI 어느 화면에도 안 나가고, 대신 고정 안내 문구(NOTICE_FILTERED)가 나간다"
    requirement: "SAFE-01"
    verification:
      - kind: integration
        ref: "tests/test_safety_flag_pipeline.py#test_web_think_block_within_one_sentence_is_filtered_not_leaked"
        status: pass
      - kind: integration
        ref: "tests/test_safety_flag_pipeline.py#test_cli_think_block_within_one_sentence_is_filtered_not_leaked"
        status: pass
      - kind: unit
        ref: "tests/test_narration_isolation.py#test_think_open_and_close_markers_in_different_sentences_are_caught_by_delay_buffer"
        status: pass
    human_judgment: false
  - id: D2
    description: "걸린 사실이 safety_flagged 사건 하나로 남고, payload에 모델이 쓴 글자가 한 자도 없다"
    requirement: "SAFE-03"
    verification:
      - kind: integration
        ref: "tests/test_safety_flag_pipeline.py#test_web_think_block_within_one_sentence_is_filtered_not_leaked"
        status: pass
      - kind: unit
        ref: "tests/test_event_schema_migration.py#test_freshly_written_schema_6_safety_flagged_event_folds_without_exception"
        status: pass
    human_judgment: false
  - id: D3
    description: "판 2(895건)·판 5(221건) 실기록이 판 6 코드로 예외 없이 재생된다"
    requirement: "TEST-03"
    verification:
      - kind: integration
        ref: "tests/test_event_schema_migration.py#test_events_db_v2_records_fold_without_exception_under_schema_6"
        status: pass
      - kind: integration
        ref: "tests/test_event_schema_migration.py#test_uat9_db_v5_records_fold_without_exception_per_session"
        status: pass
    human_judgment: false
  - id: D4
    description: "narrate()의 재시도 세 갈래(스톨 절대 재시도 금지 등)가 지연 버퍼 도입 뒤에도 그대로 남는다"
    verification:
      - kind: unit
        ref: "tests/test_master_gm.py#test_narrate_keeps_already_emitted_sentence_when_stream_stalls_mid_way"
        status: pass
      - kind: unit
        ref: "tests/test_agents_retry.py#test_narrate_mid_stream_failure_keeps_emitted_chunks_and_marks_failure"
        status: pass
    human_judgment: false

duration: ~40min (continuation agent — Task 1 체크포인트 이후 Task 2·3만)
completed: 2026-08-14
status: complete
---

# Phase 10 Plan 1: 생각 블록 방어 관통로 Summary

**`narrate()`에 1문장 지연 버퍼 + `NarrationChunk` 반환 타입을 넣고, `safety_flagged` 사건(판 6)으로 웹·CLI 두 경로 모두에서 생각 블록 유출을 화면 전에 걸러 기록한다.**

## Performance

- **Duration:** ~40분 (연속 실행 에이전트 — Task 1 체크포인트를 사람이 해결한 뒤 Task 2·3만 수행)
- **Completed:** 2026-08-14
- **Tasks:** 2/2 (Task 1은 이전 실행자가 체크포인트에서 멈췄고, 이번 실행에서 사람 결정을 이어받아 Task 2·3을 완료)
- **Files modified:** 16 (신설 3 + 수정 13)

## Checkpoint 해결 기록

**Task 1 (`checkpoint:decision`, gate=blocking)** — 사람이 **option-a**를 선택했다: 새 사건 종류를 **하나만**(`safety_flagged`) 만들고 `source` 칸(`"narration"` | `"classifier"`)으로 서사 검사 기록과 분류기 계약 위반 기록을 가른다. 이 선택은 계획의 명시적 기본값이었고(`10-01-PLAN.md` Task 1 `<decision>`), Task 2의 행동 지침이 이미 이 선택 기준으로 쓰여 있어 별도 재작성 없이 그대로 실행했다.

## Accomplishments

- `agents/narration_guard.py` 신설 — 생각 블록 검사 갈래만 채운 leaf 모듈(`GuardVerdict`/`inspect_sentence`/`strip_think_blocks`). `agents` 안에서 `json_parsing`만 import한다(`.importlinter` 계약 3 유지).
- `agents/json_parsing.py`의 `_THINK_BLOCK`을 공개 이름 `THINK_BLOCK`으로 승격(정규식 본문 무변경) — 이전 실행자가 이미 해 둔 것을 검증만 하고 그대로 썼다.
- `master_gm.narrate()`가 이제 `NarrationChunk`(text/disposition/reason/matched_len/subject_len)를 낸다. 문장을 만드는 즉시 내보내지 않고 한 문장 지연 버퍼로 판정한 뒤 내보낸다 — 다음 문장이 오거나 스트림이 끝나면(정상 종료·스톨·실패 어느 쪽이든) 보류 문장을 판정해 방출한다.
- `event_log/schema.py`: `EVENT_SCHEMA_VERSION` 5→6, `SafetyFlagged` 사건 신설(닫힌 목록 셋 + 숫자 둘, 자유 문자열 없음).
- `rules_core/reducer.py` + `session_actor/actor.py`: `safety_flagged` 분기 + `RecordSafetyFlag` 명령/검증 — 스키마 판 올리기와 **같은 커밋**.
- `web/routes_actions.py`, `cli/turn_flow.py`: 두 호출부가 `NarrationChunk`를 소비해 `AppendNarration` + (걸렸으면) `RecordSafetyFlag`를 제출한다. `disposition == "blocked"`인 조각은 `narration_texts`(배경 시계 조건 검사 입력)에서 제외한다.
- `tests/test_safety_flag_pipeline.py` 신설 — 웹·CLI 두 경로에서 생각 블록이 문장 하나/두 문장에 걸친 경우 모두 화면에 안 새고 사건 한 건으로 남는 것, 재생이 안 깨지는 것, 깨끗한 스트림은 그대로 흐르는 것을 확인.
- `tests/test_event_schema_migration.py` 신설 — `.gptrpg/events.db`(판 2, 895건)와 `.gptrpg/uat9.db`(판 5, 221건, 세션 넷)가 판 6 코드로 예외 없이 재생되는 것 + 새로 쓴 `safety_flagged` 사건의 양방향 확인.
- `tests/test_narration_isolation.py` 확장 — `narration_guard.inspect_sentence`를 직접 불러 생각 블록 경계 다섯 가지(델타 분할·문장 분할·미종결·대소문자·오탐 방지)를 못박음.

## Task Commits

1. **Task 2: 생각 블록 방어를 스트림부터 사건 기록까지 한 줄기로 관통** - `9dbabf0` (feat)
2. **Task 3: 옛 판 실기록 재생 회귀와 스트림 조각 경계 시험** - `d3cde5e` (test)

**Plan metadata:** (이 커밋 — STATE.md/ROADMAP.md/REQUIREMENTS.md 갱신과 함께)

## Files Created/Modified

- `src/gptrpg/agents/narration_guard.py` - 생각 블록 판정 leaf 모듈(신설)
- `src/gptrpg/agents/json_parsing.py` - `THINK_BLOCK` 공개 승격
- `src/gptrpg/agents/master_gm.py` - `NarrationChunk` + 1문장 지연 버퍼가 든 `narrate()`
- `src/gptrpg/event_log/schema.py` - 판 6, `SafetyFlagged` 사건
- `src/gptrpg/rules_core/reducer.py` - `safety_flagged` 리듀서 분기
- `src/gptrpg/session_actor/actor.py` - `RecordSafetyFlag` 명령 + 검증
- `src/gptrpg/web/routes_actions.py` - `NarrationChunk` 소비 + 안전 장치 사건 제출
- `src/gptrpg/cli/turn_flow.py` - 위와 같은 모양(CLI, print 유지)
- `tests/test_safety_flag_pipeline.py` - 관통로 회귀(신설)
- `tests/test_event_schema_migration.py` - 옛 판 실기록 재생 회귀(신설)
- `tests/test_narration_isolation.py` - 생각 블록 경계 다섯 가지 확장
- `tests/test_master_gm.py`, `tests/test_agents_retry.py`, `tests/test_turn_flow_failure.py` - `narrate()` 반환 타입 변경에 맞춘 기존 시험 갱신
- `tests/test_clock_condition_cli.py`, `tests/test_clock_condition_web.py` - "판 5 그대로" 고정 시험을 판 6 기준으로 갱신

## Decisions Made

- **Task 1 checkpoint → option-a.** 위 "Checkpoint 해결 기록" 참조.
- **지연 버퍼 안쪽에 보조 `except`를 하나 더 둔 것(Rule 1급 설계 판단).** 계획의 "반드시 지킬 것 넷"은 바깥 `except StreamStalled`/`except Exception` 두 갈래를 "지금 모양 그대로" 두고 검사 로직을 섞지 말라고 못박았다. 리터럴하게만 구현하면(보류 문장을 스트림 종료 시점에만 판정) 03-04가 이미 지킨 "이미 나간 조각은 스톨 뒤에도 살아남는다"는 보장이 델타 하나만큼의 지연 때문에 깨진다는 것을 기존 회귀 시험 3개(`test_narrate_keeps_already_emitted_sentence_when_stream_stalls_mid_way` 등)를 실행해 실제로 확인했다. 그래서 `next(sentences)`를 감싸는 **안쪽** `try/except`를 추가해, 스트림이 다음 문장을 만드는 도중 죽으면 보류 문장을 그 자리에서 판정·방출하고 **그대로 다시 던진다** — 바깥 두 갈래는 정말로 한 글자도 안 바뀌었고(재시도 여부는 여전히 그 두 갈래가 정한다), 03-04의 보장도 지연 버퍼 안에서 그대로 산다. 세 회귀 시험 모두 원래 기대값 그대로(문자열 → `.text` 비교로만 갱신) 통과한다.
- **`.gptrpg/uat9.db`의 실제 세션 수를 다시 확인.** 계획 문서는 "세션이 둘"(pacing5·uatweb)이라 적었지만 실제 파일에는 네 세션(`1`·`pacing5`·`uat9`·`uatweb`, 합쳐 221건)이 있다. `test_event_schema_migration.py`는 세션 이름을 하드코딩하지 않고 `SELECT DISTINCT session_id`로 파일에 실제 있는 세션을 전부 돈다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `narrate()`의 지연 버퍼가 03-04의 "스톨 뒤 이미 나간 조각 보존" 보장을 깨는 것을 미리 잡아 고침**
- **Found during:** Task 2, `master_gm.py` 구현 직후 전체 시험을 돌리며 발견
- **Issue:** 1문장 지연 버퍼를 계획 문구 그대로("보류 문장은 다음 문장이 오거나 스트림이 끝나면 판정") 구현하면, 스트림이 문장 하나만 내고 중간에 죽는 경우(스톨·예외 불문) 그 문장이 아직 "보류" 상태라 판정·방출되지 않은 채 사라진다 — 03-04가 지킨 기존 보장(이미 모델에서 나온 문장은 살아남는다)이 깨지고, 심지어 재시도 판단(`emitted_any`)까지 틀어져 불필요한 재호출이 생길 수 있었다.
- **Fix:** `chunk_sentences` 반복자를 감싸는 안쪽 `try/except`를 추가해, 다음 문장을 구하다 예외가 나면 보류 중이던 문장을 그 자리에서 판정·방출한 뒤 예외를 다시 던진다. 바깥의 두 재시도 판단 갈래(`except StreamStalled: break` / `except Exception: if emitted_any: break else: continue`)는 문자 그대로 안 바뀌었다.
- **Files modified:** `src/gptrpg/agents/master_gm.py`
- **Verification:** `tests/test_master_gm.py::test_narrate_keeps_already_emitted_sentence_when_stream_stalls_mid_way`, `::test_narrate_keeps_already_emitted_sentence_through_delegate_shaped_provider`, `tests/test_agents_retry.py::test_narrate_mid_stream_failure_keeps_emitted_chunks_and_marks_failure`, `tests/test_turn_flow_failure.py::test_one_chunk_then_stream_raises_exits_nonzero_and_keeps_emitted_chunk` 전부 원래 기대값(문장 수·순서) 그대로 통과.
- **Committed in:** `9dbabf0` (Task 2 커밋)

**2. [Rule 1 - Bug] 기존 시험의 `narrate()` 반환값 문자열 비교를 `NarrationChunk.text` 비교로 갱신**
- **Found during:** Task 2 완료 뒤 전체 스위트 첫 실행(9개 실패)
- **Issue:** `narrate()`의 반환 타입이 `Iterator[str]` → `Iterator[NarrationChunk]`로 바뀐 것은 계획이 의도한 변경이지만, 이 변경에 의존하던 기존 회귀 시험(`test_master_gm.py` 6곳, `test_agents_retry.py` 1곳, `test_turn_flow_failure.py`의 `narrate` 이름 바꿔치기 이중체 1곳)이 문자열과 직접 비교하고 있어 그대로 깨졌다.
- **Fix:** 각 비교를 `.text`(또는 `[c.text for c in ...]`) 추출로 바꾸고, `test_turn_flow_failure.py`의 스텁 제너레이터는 `NarrationChunk`를 내도록 갱신했다. 원래 시험 의도(순서·조각 수·재시도 횟수)는 하나도 안 바꿨다.
- **Files modified:** `tests/test_master_gm.py`, `tests/test_agents_retry.py`, `tests/test_turn_flow_failure.py`
- **Verification:** `uv run pytest` 전체 스위트 645건 초록불.
- **Committed in:** `9dbabf0` (Task 2 커밋)

**3. [Rule 1 - Bug] "판 5 그대로" 고정 시험을 판 6 기준으로 갱신**
- **Found during:** Task 2 완료 뒤 전체 스위트 실행
- **Issue:** `test_clock_condition_cli.py`/`test_clock_condition_web.py`의 `test_event_schema_version_still_five`는 Phase 9(DP-04 — 위협 시계 조건 검사 자체는 판을 안 올린다)가 남긴 고정 시험이다. 이 계획이 다른 이유(SAFE-01/03)로 판을 6으로 올리면서 이 시험이 정직하게 깨졌다.
- **Fix:** 시험 이름·단언을 `test_event_schema_version_at_least_six`로 바꾸고, 판이 오른 것이 이 계획(Phase 10) 때문이지 위협 시계 조건 검사가 다시 올린 것이 아니라는 것을 문서화했다.
- **Files modified:** `tests/test_clock_condition_cli.py`, `tests/test_clock_condition_web.py`
- **Verification:** `uv run pytest tests/test_clock_condition_cli.py tests/test_clock_condition_web.py` 통과.
- **Committed in:** `9dbabf0` (Task 2 커밋)

---

**Total deviations:** 3 auto-fixed (전부 Rule 1 — 계획이 의도한 변경의 직접 결과로 깨진 기존 시험/보장을 고침)
**Impact on plan:** 셋 다 계획의 설계 의도(1문장 지연 버퍼, 반환 타입 변경, 판 올리기)를 뒤집지 않았고, 기존에 검증된 회귀 방지 보장(03-04 스톨 복원력, Phase 9 판 고정)을 조용히 잃지 않기 위한 보정이었다. 스코프 확장 없음.

## Known Stubs

- `agents/narration_guard.NOTICE_GAVE_UP` — 상수만 정의되어 있고 아직 어디서도 소비하지 않는다. 계획이 명시적으로 "이번 계획에서는 상수만 정의한다 — 재생성 시도(D-06/D-07)를 실제로 잇는 것은 10-03이다"라고 범위를 그었다(`narration_guard.py` 도크스트링에도 같은 문장이 있다). 목표 달성을 막는 스텁이 아니라 다음 계획(10-03)이 채울 자리다.

## Issues Encountered

- 없음 — 위 "Deviations from Plan"이 실제로 부딪힌 문제와 해결을 전부 담는다.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **10-02(원문 겹침 검사)와 10-04(캐릭터 이탈 검사)가 바로 이어붙일 수 있는 뼈대가 갖춰졌다** — `GuardVerdict`/`inspect_sentence`가 이미 세 갈래(생각 블록/원문 겹침/캐릭터 이탈)를 함께 담을 반환 모양을 갖고 있고, `source_texts` 매개변수도 받아만 두고 아직 안 쓴 상태로 열려 있다.
- **10-03(재생성 시도, D-06/D-07)이 쓸 `NOTICE_GAVE_UP` 상수가 이미 준비되어 있다.**
- **웹·CLI 두 호출부의 소비 지점이 `_submit_narration_chunk` 한 함수로 좁혀져 있다** — 10-02/10-04가 `disposition` 갈래를 늘려도 이 두 함수(파일당 하나)만 살펴보면 된다.
- 블로커 없음. `uv run pytest`(645건) · `uv run lint-imports`(4계약 유지) · `uv run ruff check src` 전부 초록불.

---
*Phase: 10-ai*
*Completed: 2026-08-14*

## Self-Check: PASSED

- FOUND: `src/gptrpg/agents/narration_guard.py`
- FOUND: `tests/test_safety_flag_pipeline.py`
- FOUND: `tests/test_event_schema_migration.py`
- FOUND: `.planning/phases/10-ai/10-01-SUMMARY.md`
- FOUND commit: `9dbabf0` (Task 2)
- FOUND commit: `d3cde5e` (Task 3)
