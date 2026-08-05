---
phase: 03-ai
plan: 03
subsystem: ai
tags: [timeout, retry, error-handling, envelope, sentence-chunking, resilience]

# Dependency graph
requires:
  - phase: 03-ai
    plan: "03-01"
    provides: "gptrpg.agents 패키지 골격, AgentResult 응답 껍데기(D-30 네 칸), Provider 프로토콜(complete/stream/last_result), action_classifier.classify()/master_gm.narrate()/chunk_sentences()의 첫 구현(성공 경로만)"
  - phase: 03-ai
    plan: "03-02"
    provides: "다섯 제공자 어댑터 전부(Anthropic/OpenAI/NIM/OpenRouter/Gemini), 역할별 제공자·모델 선택 영속화 — 이 계획이 감싸는 provider.complete()/provider.stream() 호출은 이 다섯 어댑터 중 무엇이든 될 수 있다"
provides:
  - "agents/invoke.py — call_with_one_retry(fn, *, timeout_s) -> tuple[AgentResult, str | None], CLASSIFIER_TIMEOUT_S(5.0)/GM_TIMEOUT_S(15.0)/MAX_ATTEMPTS(2) 상수"
  - "action_classifier.classify() — 재시도까지 실패하면 예외 없이 candidates=() Proposal을 돌려주는 실패 경로(D-29). UnknownMove는 재시도 층 밖에서 즉시 던져진다"
  - "master_gm.narrate() — GM_TIMEOUT_S 적용, 첫 조각 전 실패는 재시도하고 조각이 나간 뒤 실패는 재시도하지 않는 스트리밍 전용 재시도 규칙, 어느 쪽이든 provider.last_result()가 성공/실패를 반영"
  - "chunk_sentences() — 여덟 개 경계 상황(무종결부호/중단/델타경계분할/공백뿐/한국어종결/여러공백/순서)을 시험으로 못박음. 로직 변경 없이 기존 구현이 이미 전부 만족함을 확인"
affects: ["03-04 (신뢰도 UI가 classify()의 실패-시-빈-후보 경로를 소비한다)", "06 (원가·실패율 계산이 실패한 호출도 AiInvoked로 기록되는 것에 의존)"]

# Actuals (#2632)
actuals:
  tokens: 7018
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "call_with_one_retry(fn, *, timeout_s) -> tuple[AgentResult, str|None] — 전역 상태 없이 마지막 실패 사유를 선택적 반환 경로로 전달"
    - "스트리밍 재시도 규칙 = '첫 조각 전엔 재시도, 조각이 나간 뒤엔 즉시 종료' — 호출 한 번짜리 재시도 규칙과 다른 규칙을 별도로 문서화"
    - "Provider 프로토콜에 없는 어댑터 내부 관례(_last_result)에 narrate()가 직접 기대어 실패를 반영 — 새 프로토콜 메서드 추가로 다섯 어댑터를 전부 고치는 대신 택한 범위 안 해법"

key-files:
  created:
    - src/gptrpg/agents/invoke.py
    - tests/test_agents_retry.py
    - tests/test_master_gm.py
  modified:
    - src/gptrpg/agents/action_classifier.py
    - src/gptrpg/agents/master_gm.py

key-decisions:
  - "call_with_one_retry는 AgentResult 하나가 아니라 tuple[AgentResult, str | None]을 돌려준다 — 마지막 예외 문자열을 전역 변수 없이 부르는 쪽에 전달하기 위해서다(플랜 원문의 구체화된 지시)"
  - "narrate()의 실패 반영은 provider._last_result를 직접 갈아 끼우는 방식을 택했다 — Provider 프로토콜에 새 세터 메서드를 추가하면 다섯 어댑터 파일을 전부 고쳐야 하는데, 그건 이 계획의 files_modified 범위 밖이다. 다섯 어댑터와 conftest.py의 FakeProvider가 이미 03-01/03-02부터 '_last_result'라는 같은 이름을 공유해 온 관례에 기대는 것으로 범위를 지켰다"
  - "chunk_sentences()는 로직을 고치지 않았다 — 여덟 개 경계 상황을 실제로 실행해 전부 이미 통과함을 확인한 뒤, 도크스트링만 그 여덟 가지 보장을 명시하도록 넓혔다. 없는 버그를 고치는 대신 실제로 존재하는 정확성을 시험으로 못박는 쪽을 택했다"
  - "classify()의 UnknownMove 판정은 call_with_one_retry 밖(껍데기를 돌려받은 뒤)에서 한다 — 목록 위반이 제공자 장애로 오인되어 재시도되는 일이 없게 하려는 것으로, 플랜이 명시한 배치다"

patterns-established:
  - "호출 한 번짜리 재시도(call_with_one_retry)와 스트리밍 재시도(narrate() 안의 자체 루프)를 하나로 합치지 않는다 — 스트리밍은 '이미 나간 조각을 두 번 쓰지 않는다'는 별도 규칙이 필요하기 때문"

requirements-completed: [MEAS-02, RIG-03]

coverage:
  - id: D1
    description: "action_classifier 호출이 실제로 5.0(CLASSIFIER_TIMEOUT_S)을 provider.complete()에 넘긴다"
    requirement: MEAS-02
    verification:
      - kind: unit
        ref: "tests/test_agents_retry.py#test_classify_uses_classifier_timeout"
        status: pass
    human_judgment: false
  - id: D2
    description: "master_gm 호출이 실제로 15.0(GM_TIMEOUT_S, D-27이 건드리지 않은 기존 확정값)을 provider.stream()에 넘긴다"
    requirement: MEAS-02
    verification:
      - kind: unit
        ref: "tests/test_agents_retry.py#test_narrate_uses_gm_timeout"
        status: pass
    human_judgment: false
  - id: D3
    description: "실패해도 성공해도 제공자 호출은 정확히 MAX_ATTEMPTS(2)번을 넘지 않는다 — 특히 두 시도 모두 실패해도 3번째 호출이 절대 없다"
    verification:
      - kind: unit
        ref: "tests/test_agents_retry.py#test_both_attempts_fail_calls_provider_exactly_twice_never_three, test_first_fails_second_succeeds_calls_provider_exactly_twice"
        status: pass
    human_judgment: false
  - id: D4
    description: "예외 종류(TimeoutError vs ValueError)와 무관하게 같은 재시도·실패 결과가 나온다 — 오류 종류별 분기가 없다(D-28)"
    verification:
      - kind: unit
        ref: "tests/test_agents_retry.py#test_exception_kind_does_not_change_behavior_timeout_error, test_exception_kind_does_not_change_behavior_value_error"
        status: pass
    human_judgment: false
  - id: D5
    description: "제공자가 두 번 다 실패해도 action_classifier.classify()는 예외를 던지지 않고 candidates=()인 Proposal을 돌려준다 — 기존 '무브 없음' 경로가 그대로 이어받는다(D-29)"
    requirement: RIG-03
    verification:
      - kind: unit
        ref: "tests/test_agents_retry.py#test_classify_falls_back_to_empty_candidates_when_provider_fails_twice"
        status: pass
    human_judgment: false
  - id: D6
    description: "룰북 목록에 없는 무브 이름에는 UnknownMove가 즉시 뜨고, 재시도 층이 이를 삼켜 다시 시도하지 않는다(제공자 호출 횟수=1)"
    verification:
      - kind: unit
        ref: "tests/test_agents_retry.py#test_classify_raises_unknown_move_without_retrying"
        status: pass
    human_judgment: false
  - id: D7
    description: "재시도까지 실패한 호출도 응답 껍데기를 남긴다 — 성공 칸 거짓, elapsed_ms는 실제로 잰 값(0 이상), 토큰 두 칸은 0"
    requirement: MEAS-02
    verification:
      - kind: unit
        ref: "tests/test_agents_retry.py#test_both_failed_envelope_has_zero_tokens_and_nonnegative_elapsed, test_classify_failed_envelope_has_nonnegative_elapsed_and_zero_tokens"
        status: pass
    human_judgment: false
  - id: D8
    description: "제공자가 조각을 흘려보낸 뒤 스트림 도중 실패하면 이미 나온 조각은 살아남고, 재시도하지 않으며(stream 호출 1회), provider.last_result()가 실패를 반영한다"
    requirement: RIG-03
    verification:
      - kind: unit
        ref: "tests/test_agents_retry.py#test_narrate_mid_stream_failure_keeps_emitted_chunks_and_marks_failure"
        status: pass
    human_judgment: false
  - id: D9
    description: "chunk_sentences()가 여덟 개 경계 상황(문장 셋 -> 조각 셋 / 종결부호 없음 -> 조각 1개 / 스트림 중단 -> 남은 버퍼가 마지막 조각 / 델타경계가 종결부호를 가름 -> 문장 하나로 병합 / 공백뿐 -> 0개 / 한국어 종결 3형태 / 여러 공백·줄바꿈 -> 빈 조각 없음 / 순서 유지)에서 전부 기대대로 동작한다"
    requirement: RIG-03
    verification:
      - kind: unit
        ref: "tests/test_master_gm.py#test_three_sentences_yield_three_chunks, test_no_terminal_punctuation_yields_exactly_one_chunk_not_zero, test_stream_cut_off_mid_sentence_yields_remaining_buffer_as_last_chunk, test_delta_boundary_splitting_sentence_terminator_still_merges_to_one, test_whitespace_only_deltas_yield_zero_chunks, test_korean_sentence_endings_chunk_like_english, test_multiple_spaces_and_newlines_between_sentences_are_trimmed_no_empty_chunk, test_chunk_order_matches_input_order"
        status: pass
    human_judgment: false
  - id: D10
    description: "narrate()를 시험용 스트리밍 이중체로 돌리면 조각 2개 이상이 입력 순서 그대로 나온다"
    requirement: RIG-03
    verification:
      - kind: unit
        ref: "tests/test_master_gm.py#test_narrate_yields_at_least_two_chunks_in_order"
        status: pass
    human_judgment: false
  - id: D11
    description: "실제 다섯 제공자 SDK가 타임아웃을 알리는 예외 형(TimeoutError/httpx.TimeoutException/APITimeoutError 등)이 call_with_one_retry의 종류-불문 catch에 실제로 잡히는지는 이번 계획에서 라이브로 재현되지 않았다 — 플랜의 must_haves가 이 항목을 처음부터 backstop(자동 검증 불가)으로 표시했다"
    verification: []
    human_judgment: true
    rationale: "테스트 이중체(RuntimeError/TimeoutError/ValueError)로는 'except Exception'이 종류를 가리지 않는다는 것만 증명할 수 있고, 실제 SDK가 던지는 구체적 예외 클래스가 파이썬 Exception 계층 안에 있다는 것 자체는 실제 호출로만 최종 확인된다. WINDOWS.md id 3에 unrun-verify로 기록했다"

# Metrics
duration: ~25min
completed: 2026-08-02
status: complete
---

# Phase 3 Plan 3: 실패 쪽 — 타임아웃·재시도·무브없음 낙하 Summary

**호출 한 번을 감싸는 타임아웃·재시도 층(`call_with_one_retry`)을 만들고 두 에이전트를 그 뒤로 옮겼다 — 재시도까지 실패해도 분류기는 예외 대신 기존 「무브 없음」 경로로 조용히 떨어지고, 실패한 호출도 실제로 잰 시간과 함께 기록에 남는다. 서사 문장 조각내기는 여덟 개 경계 상황 전부에서 이미 정확했음을 시험으로 확인했다.**

## Performance

- **Duration:** ~25분 (체크포인트 없음, 세 작업 전부 자동)
- **Tasks:** 3/3 (auto, tdd)
- **Files modified:** 5 (3 new, 2 modified)

## Accomplishments

- `agents/invoke.py` 신설 — `call_with_one_retry(fn, *, timeout_s) -> tuple[AgentResult, str | None]`, `CLASSIFIER_TIMEOUT_S=5.0`(D-27)·`GM_TIMEOUT_S=15.0`(기존 D-33 확정값, 안 건드림)·`MAX_ATTEMPTS=2`(D-28) 세 상수
- `action_classifier.classify()`가 제공자를 직접 부르지 않고 재시도 층을 거친다. 재시도까지 실패하면 예외 없이 `candidates=()`인 `Proposal`을 돌려줘 §4.7의 「무브 없음」 경로가 그대로 이어받는다(D-29). `UnknownMove`(목록 위반)는 재시도 층 밖에서 즉시 던져져 재시도 대상이 아니다
- `master_gm.narrate()`가 `GM_TIMEOUT_S`를 적용하고, 스트리밍 전용 재시도 규칙(첫 조각 전 실패는 재시도, 조각이 나간 뒤 실패는 즉시 종료)을 갖췄다. 두 경로 모두 `provider.last_result()`가 성공/실패를 반영한다
- `chunk_sentences()`의 여덟 경계 상황(문장 셋/종결부호 없음/중단/델타경계 분할/공백뿐/한국어 종결/여러 공백/순서)을 실제로 실행해 기존 구현이 이미 전부 만족함을 확인 — 로직은 그대로 두고 도크스트링만 여덟 보장을 명시하도록 확장
- `tests/test_agents_retry.py`(14개 -> 22개, Task 1에서 8개 신설 + Task 2에서 6개 추가)와 `tests/test_master_gm.py`(9개, 신설)로 위 항목을 전부 자동 시험으로 못박음

## Task Commits

Each task was committed atomically:

1. **Task 1: 호출 한 번을 감싸는 타임아웃·재시도 층** - `ca4b4b0` (feat)
2. **Task 2: 두 에이전트를 타임아웃·재시도 층 뒤로 옮기고, 실패를 「무브 없음」으로 떨어뜨린다** - `aea78db` (feat)
3. **Task 3: 서사 문장 조각내기를 경계값까지 단단하게** - `11b630b` (test)

**Plan metadata:** (다음 커밋에서 이 SUMMARY.md·STATE.md·ROADMAP.md·REQUIREMENTS.md를 묶음)

## Files Created/Modified

- `src/gptrpg/agents/invoke.py` - `call_with_one_retry()`, `CLASSIFIER_TIMEOUT_S`/`GM_TIMEOUT_S`/`MAX_ATTEMPTS`
- `src/gptrpg/agents/action_classifier.py` - `classify()`가 재시도 층을 거치고 실패 시 빈 후보로 떨어짐
- `src/gptrpg/agents/master_gm.py` - `narrate()`에 `GM_TIMEOUT_S`·스트리밍 재시도 규칙 적용, `chunk_sentences()` 도크스트링 확장(로직 불변)
- `tests/test_agents_retry.py` - Task 1(8개)·Task 2(6개) 시험, 이중체 3종(`_CountingFailer`/`_FailingCompleteProvider`/`_StreamThenFailProvider`)
- `tests/test_master_gm.py` - 여덟 경계 시험 + `narrate()` 순서 시험, 이중체 1종(`_TwoSentenceStreamProvider`)

## Decisions Made

- `call_with_one_retry`는 `AgentResult` 하나가 아니라 `tuple[AgentResult, str | None]`을 돌려준다 — 마지막 예외 문자열을 전역 변수 없이 부르는 쪽에 전달
- `narrate()`의 실패 반영은 `provider._last_result`를 직접 갈아 끼우는 방식(다섯 어댑터가 공유하는 내부 관례에 기댐) — 새 프로토콜 메서드 추가는 이 계획의 파일 범위 밖
- `chunk_sentences()`는 고치지 않았다 — 여덟 경계 상황을 실행해 이미 정확함을 확인한 뒤 시험으로 못박기만 함
- `UnknownMove` 판정은 재시도 층 밖(껍데기를 돌려받은 뒤)에서 함 — 목록 위반이 제공자 장애로 오인되어 재시도되지 않게

## Deviations from Plan

None - plan executed exactly as written. Task 3에서 `chunk_sentences()`에 버그가 있으리라 예상하고 시작했지만, 여덟 경계 상황을 직접 실행해 본 결과 기존 03-01 구현이 이미 전부 정확했다 — 이것은 계획 이탈이 아니라 계획이 요구한 "여덟 항목이 전부 참이 되도록 다듬는다"는 목표를 시험으로 증명하는 것으로 달성한 경우다(코드 변경이 필요 없었을 뿐).

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. 이 계획은 테스트 이중체만으로 검증되었고 실제 제공자 API를 호출하지 않았다(그럴 필요가 없는 순수 로직 계획).

## Next Phase Readiness

- `call_with_one_retry`·타임아웃 상수·실패-시-빈-후보 낙하·스트리밍 실패 반영이 모두 자리 잡아, 03-04(신뢰도별 확인 화면, D-34/D-35/D-36)가 `classify()`의 `Proposal`(성공이든 실패-시-빈-후보든)을 그대로 소비할 수 있다
- `STATE.md` Blockers #2("v1에만 있고 유지·폐기 진술이 없던 구현 약속")의 첫 절반(에이전트 응답 껍데기 + 타임아웃·재시도)이 이 계획으로 해소됐다 — 나머지 절반(연결 유지 신호·재연결 이어붙이기)은 여전히 Phase 4(RIG-07) 몫이다
- `.planning/WINDOWS.md`에 id 3(`unrun-verify`)을 새로 기록 — 실제 다섯 제공자 SDK의 타임아웃 예외 형이 라이브로 확인되지 않았다는 플랜의 backstop 항목. id 1(D-26/D-33 UX 임계값 미구현)은 이 계획의 범위가 아니므로 여전히 open으로 남는다 — 03-04 또는 이후 계획이 다뤄야 한다
- No blockers for continuing phase 3's remaining plans.

---
*Phase: 03-ai*
*Completed: 2026-08-02*

## Self-Check: PASSED

All 5 claimed files (`src/gptrpg/agents/invoke.py`, `tests/test_agents_retry.py`, `tests/test_master_gm.py`, `src/gptrpg/agents/action_classifier.py`, `src/gptrpg/agents/master_gm.py`) exist on disk; all 3 task commit hashes (`ca4b4b0`, `aea78db`, `11b630b`) verified present in `git log --oneline --all`. `.planning/WINDOWS.md` ledger entry recorded (id 3, `unrun-verify`, open) for the must_haves backstop item (real provider timeout exception shapes not live-verified).
