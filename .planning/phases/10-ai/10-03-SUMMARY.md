---
phase: 10-ai
plan: 03
subsystem: ai-safety
tags: [streaming, narration-guard, prompt-assembly, event-sourcing, regeneration]

requires:
  - phase: 10-ai
    provides: "10-01의 narrate() 1문장 지연 버퍼 + NarrationChunk 반환 타입, safety_flagged 사건(판 6), NOTICE_FILTERED/NOTICE_GAVE_UP 상수. 10-02의 원문 겹침 대조(source_texts)와 build_gm_prompt의 영구/세션 고정 블록 분리"
provides:
  - "build_gm_prompt(..., avoid_text=None, written_so_far=()) — 재생성 전용 매개변수 둘. turn(messages)에만 들어가고 system(영구·세션 고정)은 무변경이라 캐시가 안 깨진다"
  - "master_gm.MAX_REGENERATIONS = 1 — 한 턴에 재생성은 최대 한 번"
  - "narrate()의 독립 재생성 경로 — 문장이 걸리면 그 자리에서 스트림 소비를 멈추고 build_gm_prompt를 avoid_text/written_so_far로 다시 불러 단발 재생성 호출(내부 재시도 없음)을 한다. 한 턴의 제공자 스트림 호출 상한이 3회(정상 최대 2 + 재생성 1)로 고정된다"
  - "narrate()의 D-08 종료 경로 — 재생성도 걸리거나 실패·스톨하면 NOTICE_GAVE_UP 조각을 마지막으로 내보내고, 성공한 스트림의 토큰 값을 살린 실패 껍데기(_failure_envelope_preserving_tokens)를 남긴다. 웹/CLI 호출부는 기존 narration_failed 경로를 무변경으로 재사용한다"
affects: []

actuals:
  tokens: 14400
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "narrate() 안에 클로저 제너레이터(_drive)를 두어 정상 경로·재생성 경로가 스트림 소비+지연 버퍼+판정 로직 하나를 공유한다 — yield from으로 forward하며 (avoid_text, reason, matched_len, subject_len) 튜플을 return 값으로 돌려받는다"
    - "emit_block_notice 플래그로 '판정 사실은 항상 기록하되 화면 안내는 억누른다'를 표현 — 재생성 자신의 차단은 별도 NOTICE_FILTERED를 내지 않고 D-08의 NOTICE_GAVE_UP 하나로 합쳐, safety_flagged 사건이 정확히 두 건(첫 차단 + 최종 차단)으로 유지된다"

key-files:
  created: []
  modified:
    - src/gptrpg/agents/prompt_assembly.py
    - src/gptrpg/agents/master_gm.py
    - tests/test_master_gm.py
    - tests/test_narration_guard.py
    - tests/test_safety_flag_pipeline.py
    - tests/test_web_actions.py
    - tests/test_turn_flow_failure.py

key-decisions:
  - "재생성은 걸린 그 자리에서 스트림 소비를 즉시 멈추고 별도의 단발 provider.stream() 호출로 이어 쓴다 — 기존 MAX_ATTEMPTS 재시도 루프를 한 글자도 안 바꾸고 완전히 밖에 둔다(RESEARCH.md Pitfall 2, 03-04의 22분 먹통 사고 재발 방지)"
  - "재생성 호출은 system을 다시 만들지 않고 첫 호출 때 만든 객체를 그대로 재사용한다 — 캐시 유지 + 원문 겹침 대조 소스가 두 호출에서 바이트 단위로 같아짐을 시험(같은 객체 단언)으로 못박았다"
  - "재생성 스트림이 다시 걸렸을 때 그 자리의 NOTICE_FILTERED를 화면에 내지 않는다(emit_block_notice=False) — 판정 사실(reason/matched_len/subject_len)은 그대로 들고 있다가 D-08의 NOTICE_GAVE_UP 하나로 합쳐 낸다. 이걸 안 하면 '걸렀어요'와 '끝까지 못 썼어요'가 연달아 나가고 safety_flagged가 세 건이 되어, 계획이 명시한 '두 건(첫 차단 + 최종 차단)' acceptance criteria를 어긴다"
  - "실패 껍데기는 provider.last_result()가 갖고 있는 값을 살려서 ok=False로 되돌린다(_failure_envelope_preserving_tokens, T-10-10) — last_result()가 예외를 던지면(제공자 규약 위반이거나 원래 스트림이 조각을 하나도 못 얻은 경우) 0으로 채운 껍데기로 대신한다. 재생성이 시도된 적 없는(순수 호출 실패) 턴은 이 로직 없이 기존 0-토큰 실패 껍데기 그대로다 — D-06/D-07/D-08은 '호출은 성공했는데 내용이 나빴다'에만 적용된다"

requirements-completed: [SAFE-04]

coverage:
  - id: D1
    description: "첫 문장이 차단되면 안내 조각이 먼저 나가고 그 뒤 재생성 스트림의 문장들이 이어 나온다 — 턴이 멈추지 않는다(D-06)"
    requirement: "SAFE-04"
    verification:
      - kind: unit
        ref: "tests/test_master_gm.py#test_narrate_regenerates_once_after_a_blocked_sentence_and_calls_stream_twice"
        status: pass
      - kind: integration
        ref: "tests/test_narration_guard.py#test_narrate_does_not_block_narration_mentioning_scene_entity_and_character_state"
        status: pass
    human_judgment: false
  - id: D2
    description: "재생성 프롬프트의 messages에 걸린 문장 원문과 '그러지 마라' 지시, 지금까지 쓴 문장이 실린다 — 걸린 원문은 모델에게만 가고 플레이어 화면에는 안 나간다(D-07)"
    requirement: "SAFE-04"
    verification:
      - kind: unit
        ref: "tests/test_master_gm.py#test_narrate_regeneration_prompt_carries_avoid_text_and_written_so_far"
        status: pass
    human_judgment: false
  - id: D3
    description: "재생성 프롬프트의 system 두 조각(영구·세션 고정)은 첫 호출과 바이트 단위로 같다 — 캐시가 안 깨진다"
    requirement: "SAFE-04"
    verification:
      - kind: unit
        ref: "tests/test_master_gm.py#test_narrate_regeneration_reuses_identical_system_object"
        status: pass
    human_judgment: false
  - id: D4
    description: "정상 스트림(차단 없음)에서 provider.stream() 호출이 정확히 1회, 차단 1회 시나리오에서 정확히 2회다 — 재생성이 재시도와 곱해지지 않는다"
    requirement: "SAFE-04"
    verification:
      - kind: unit
        ref: "tests/test_master_gm.py#test_narrate_clean_stream_calls_provider_stream_exactly_once"
        status: pass
      - kind: unit
        ref: "tests/test_master_gm.py#test_narrate_regenerates_once_after_a_blocked_sentence_and_calls_stream_twice"
        status: pass
    human_judgment: false
  - id: D5
    description: "두 번 다 걸리면(첫 스트림 + 재생성) NOTICE_GAVE_UP이 마지막으로 나오고 provider.stream() 호출은 정확히 2회로 끝난다 — 재생성 자체가 재시도되지 않는다(D-08)"
    requirement: "SAFE-04"
    verification:
      - kind: unit
        ref: "tests/test_master_gm.py#test_narrate_gives_up_with_notice_after_regeneration_also_blocks"
        status: pass
    human_judgment: false
  - id: D6
    description: "두 번 다 걸린 턴도 실패 껍데기가 토큰을 0으로 지우지 않고 마지막으로 성공한 스트림의 값을 살린다(T-10-10)"
    requirement: "SAFE-04"
    verification:
      - kind: unit
        ref: "tests/test_master_gm.py#test_narrate_give_up_failure_envelope_preserves_tokens_from_last_successful_stream"
        status: pass
    human_judgment: false
  - id: D7
    description: "웹 경로 — 두 번 다 걸리는 가짜 제공자로 confirm을 부르면 응답 200 + narration_failed=True + rolls/grade/target 유지, safety_flagged 두 건(첫 차단+최종 차단, 모델이 쓴 글자 없음), ai_invoked 토큰 0 아님을 확인한다"
    requirement: "SAFE-04"
    verification:
      - kind: integration
        ref: "tests/test_web_actions.py#test_narration_blocked_twice_gives_up_with_notice_and_keeps_roll_result"
        status: pass
    human_judgment: false
  - id: D8
    description: "명령줄 경로 — 같은 시나리오가 웹과 짝을 이뤄 기존 서사 실패 종료 코드를 재사용하고, 안내 문구가 표준출력에, 운영자 사유가 표준오류에, 판정 결과 사건은 그대로 남는다"
    requirement: "SAFE-04"
    verification:
      - kind: integration
        ref: "tests/test_turn_flow_failure.py#test_narration_blocked_twice_exits_zero_with_gave_up_notice_and_keeps_roll_result"
        status: pass
    human_judgment: false
  - id: D9
    description: "src/gptrpg/web/routes_actions.py와 src/gptrpg/cli/turn_flow.py가 이 계획의 diff에 없다 — 기존 실패 경로(narration_failed, RecordSafetyFlag 소비)를 그대로 재사용했다는 증거"
    requirement: "SAFE-04"
    verification:
      - kind: other
        ref: "git diff --name-only src/gptrpg/web/routes_actions.py src/gptrpg/cli/turn_flow.py (빈 출력)"
        status: pass
    human_judgment: false

duration: ~50min
completed: 2026-08-14
status: complete
---

# Phase 10 Plan 3: 걸린 문장 재생성과 두 번째 차단 시 안내 종료 Summary

**`narrate()`가 검사에 걸린 문장을 만나면 그 자리에서 스트림을 멈추고 독립된 단발 호출로 딱 한 번 이어서 다시 쓰며(D-06/D-07), 재생성도 걸리면 `NOTICE_GAVE_UP` 안내와 함께 토큰 값을 보존한 실패 껍데기로 거기서 끝낸다(D-08) — 한 턴의 제공자 스트림 호출 상한이 3회로 고정된다.**

## Performance

- **Duration:** ~50분
- **Completed:** 2026-08-14
- **Tasks:** 2/2
- **Files modified:** 7 (소스 2 + 시험 5)

## Accomplishments

- `agents/prompt_assembly.py`의 `build_gm_prompt`에 `avoid_text`(걸린 문장 원문)·`written_so_far`(지금까지 실제로 나간 문장들) 매개변수 둘을 기본값과 함께 추가 — `turn`(messages)에만 들어가고 `system`(영구·세션 고정)은 한 글자도 안 바뀐다. D-07과 SAFE-03이 서로 다른 이야기(걸린 원문은 모델에게만 간다)라는 것을 함수 도크스트링에 못박았다.
- `agents/master_gm.py`에 `MAX_REGENERATIONS = 1` 상수와 `_consume_narration_stream`(스트림 소비 + 1문장 지연 버퍼 + 판정을 한 곳으로 뽑은 공용 제너레이터, 정상·재생성 경로가 공유) 신설.
- `narrate()`를 세 단계로 재구성 — ① 정상 경로(기존 `MAX_ATTEMPTS` 재시도 세 갈래 무변경) ② 걸린 문장이 있으면 `build_gm_prompt`를 `avoid_text`/`written_so_far`로 다시 불러 **독립된 단발 재생성 호출**(내부 재시도 없음, `system`은 첫 호출 것을 그대로 재사용) ③ 재생성도 걸리거나 실패·스톨하면 `NOTICE_GAVE_UP` 조각을 마지막으로 내보내고 `_failure_envelope_preserving_tokens`(신설)로 마지막 성공 스트림의 토큰 값을 살린 실패 껍데기를 남긴다.
- 재생성 자신의 "걸렀어요" 안내는 화면에 안 나간다(`_drive(..., emit_block_notice=False)`) — 판정 사실은 그대로 붙잡아 두었다가 D-08의 `NOTICE_GAVE_UP` 하나로 합쳐서 `safety_flagged` 사건이 정확히 두 건(첫 차단 + 최종 차단)으로 유지된다.
- `web/routes_actions.py`·`cli/turn_flow.py`는 **한 글자도 안 고쳤다** — 두 호출부의 기존 `narration_failed`/`RecordSafetyFlag` 소비 경로가 새 종료 모양을 그대로 흡수한다.
- `tests/test_master_gm.py`에 재생성 회귀 시험 6개(정상 호출 1회, 차단-후-재생성 호출 2회, 재생성 프롬프트 내용물, `system` 객체 동일성, 두 번 다 걸린 종료, 토큰 보존) 신설.
- `tests/test_web_actions.py`·`tests/test_turn_flow_failure.py`에 웹·명령줄 짝 시험(두 번 다 걸리는 대역으로 `confirm`/`turn`을 몬다) 신설.

## Task Commits

1. **Task 1: 걸린 지점부터 한 번 이어서 다시 쓰기 (SAFE-04, D-06/D-07)** - `081396a` (feat)
2. **Task 2: 두 번 다 걸렸을 때의 종료 — 기존 서사 실패 경로 재사용 (SAFE-04, D-08)** - `3009338` (feat)

**Plan metadata:** (이 커밋 — STATE.md/ROADMAP.md/REQUIREMENTS.md 갱신과 함께)

## Files Created/Modified

- `src/gptrpg/agents/prompt_assembly.py` - `build_gm_prompt`에 `avoid_text`/`written_so_far` 매개변수
- `src/gptrpg/agents/master_gm.py` - `MAX_REGENERATIONS`, `_consume_narration_stream`, `_failure_envelope_preserving_tokens`, 재구성된 `narrate()`
- `tests/test_master_gm.py` - 재생성·D-08 종료 회귀 시험 신설
- `tests/test_narration_guard.py` - 기존 원문 겹침 시험을 재생성 뒤 이어지는 흐름 기준으로 갱신(Rule 1)
- `tests/test_safety_flag_pipeline.py` - 생각 블록 시험 넷을 재생성 이후 흐름 기준으로 갱신(Rule 1), 호출 횟수별로 다른 텍스트를 내는 대역 신설
- `tests/test_web_actions.py` - 두 번 다 걸리는 웹 경로 짝 시험 신설
- `tests/test_turn_flow_failure.py` - 두 번 다 걸리는 명령줄 경로 짝 시험 신설

## Decisions Made

- 재생성을 기존 재시도 루프 완전히 밖의 독립된 단발 호출로 설계 — 위 "key-decisions" 참조.
- `system` 재사용(다시 조립하지 않음) — 캐시 유지 + 대조 소스 동일성.
- `emit_block_notice=False`(재생성 전용) — 계획의 명시적 acceptance criteria("safety_flagged 사건 두 건")를 만족시키기 위한 설계 판단. 위 "key-decisions" 참조.
- 재생성이 시도된 적 없는(순수 호출 실패) 턴은 토큰 보존 로직을 안 타고 기존 0-토큰 실패 껍데기 그대로 둔다 — D-06/D-07/D-08은 "호출은 성공했는데 내용이 나빴다"에만 적용되고, "호출 자체가 안 됐다"는 이 계획 밖(10-01 이후 상태 그대로)이다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Task 1의 재생성 도입으로 정직하게 깨진 기존 시험 다섯 개를 갱신**
- **Found during:** Task 1, `uv run pytest tests/test_master_gm.py tests/test_narration_guard.py -x` 첫 실행 및 전체 스위트 실행
- **Issue:** 10-01/10-02가 만든 시험 중, 걸린 문장 뒤에도 같은 스트림이 계속 소비된다고 가정한 것들(`test_narrate_blocks_narration_that_quotes_permanent_block_verbatim` 및 `test_safety_flag_pipeline.py`의 생각 블록 시험 넷)이 "차단 시 그 자리에서 스트림 소비를 멈추고 재생성한다"는 이 계획의 의도된 변경과 직접 충돌해 깨졌다. 이 시험들의 가짜 제공자는 `messages`(재생성 지시)와 무관하게 항상 같은 텍스트를 내므로, 재생성 호출도 곧바로 같은 자리에서 다시 걸리거나(정직한 실패), 반대로 "한 번 걸리고 끝"이라는 옛 가정이 새 동작과 어긋났다.
- **Fix:** `_LeakingProvider`에 `note_result()`를 추가하고 두 번 다 걸리는 기대값으로 갱신. `test_safety_flag_pipeline.py`의 `FakeProvider`/`_StreamTextProvider` 사용처를 호출 횟수에 따라 다른 텍스트를 내는 대역(`_CallVaryingStreamProvider`, `_StreamTextProvider.regen_text`)으로 바꿔 "재생성이 깨끗한 문장을 내 턴이 이어진다"는 D-06의 실제 의도를 보이도록 재설계했다.
- **Files modified:** `tests/test_narration_guard.py`, `tests/test_safety_flag_pipeline.py`
- **Verification:** `uv run pytest` 전체 스위트 787건 초록불(Task 1 커밋 시점).
- **Committed in:** `081396a` (Task 1 커밋)

**2. [Rule 1 - Bug] Task 2의 NOTICE_GAVE_UP 추가로 같은 시험들이 다시 깨져 재조정**
- **Found during:** Task 2, `uv run pytest` 전체 스위트 실행
- **Issue:** Task 2가 D-08 종료 조각(`NOTICE_GAVE_UP`)을 추가하자, Task 1에서 이미 한 번 고친 `test_narrate_blocks_narration_that_quotes_permanent_block_verbatim`(및 신설한 `test_narrate_gives_up_with_notice_after_regeneration_also_blocks`)의 조각 개수 기대값이 다시 어긋났다 — 처음엔 `emit_block_notice`를 안 넣고 구현해 재생성의 차단이 별도 안내로 한 번 더 나가면서 `safety_flagged`가 세 건이 되어 계획의 acceptance criteria("두 건")를 어겼다.
- **Fix:** `_drive`에 `emit_block_notice` 매개변수를 추가해 재생성 자신의 차단 안내를 억누르고 D-08 안내 하나로 합쳤다(위 key-decisions 참조). 이후 관련 시험(2개 파일)의 조각 개수·순서 기대값을 최종 동작에 맞춰 갱신했다.
- **Files modified:** `src/gptrpg/agents/master_gm.py`, `tests/test_master_gm.py`, `tests/test_narration_guard.py`
- **Verification:** `uv run pytest` 전체 스위트 791건 초록불, `uv run ruff check src` 통과, `uv run lint-imports` 4계약 유지.
- **Committed in:** `3009338` (Task 2 커밋)

---

**Total deviations:** 2 auto-fixed (둘 다 Rule 1 — 계획이 의도한 변경의 직접 결과로 깨진 기존 시험을 갱신하거나, 계획 자신의 acceptance criteria를 만족시키기 위해 구현을 다듬었다)
**Impact on plan:** 계획의 설계 의도(독립 재생성 호출, 재시도와 안 곱해짐, 두 번 다 걸리면 안내하고 끝남, 토큰 보존)를 하나도 뒤집지 않았다. 스코프 확장 없음 — `web/routes_actions.py`·`cli/turn_flow.py`는 계획이 요구한 대로 diff에 없다.

## Known Stubs

없음 — 이 계획의 산출물(재생성 경로, D-08 종료 경로)은 전부 실제 동작으로 배선됐고 웹·명령줄 양쪽에서 회귀 시험으로 고정됐다.

## Issues Encountered

없음 — 위 "Deviations from Plan"이 실제로 부딪힌 문제와 해결을 전부 담는다.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- SAFE-04가 코드·시험으로 닫혔다 — `uv run pytest`(791건) · `uv run lint-imports`(4계약 유지) · `uv run ruff check src` 전부 초록불.
- 10-03이 Phase 10(AI 출력 검증과 탈옥 방어)의 마지막 계획이다 — SAFE-01~07 전부 이번 phase 안에서 닫혔다(10-01 SAFE-01/03, 10-02 SAFE-02, 10-04 SAFE-05/06, 10-05 SAFE-07, 10-03 SAFE-04).
- 정직하게 남는 한계(계획이 명시하지 않았지만 실행 중 확인한 것): 재생성 프롬프트가 "그러지 마라"를 얼마나 잘 지키는지는 결정론적으로 보장되지 않는다 — 모델이 재생성 시도에서도 같은 방향으로 다시 걸릴 수 있고, 이 계획은 그 경우를 D-08(안내 후 종료)로 정직하게 처리하는 것까지만 보장한다("막았다"가 아니라 "멈추지 않는다"가 이 계획의 약속이다).
- 블로커 없음.

---
*Phase: 10-ai*
*Completed: 2026-08-14*
