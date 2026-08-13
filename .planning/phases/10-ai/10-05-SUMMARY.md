---
phase: 10-ai
plan: 05
subsystem: ai-safety
tags: [action-classifier, operator-record, event-sourcing, provider-adapters, regression-tests]

requires:
  - phase: 10-ai
    provides: "10-01이 연 safety_flagged 사건 종류(판 6)와 source=\"classifier\" 값, RecordSafetyFlag 명령·검증(reason=\"unknown_move\"까지 이미 열려 있었다)"
provides:
  - "classify() 함수 경계에서 UnknownMove를 흡수해 tier==\"none\" Proposal(unknown_move 칸 포함)로 돌려주는 동작 — _parse_candidates는 여전히 예외를 던진다"
  - "웹 declare()·명령줄 turn_flow가 같은 자리에서 RecordSafetyFlag(source=\"classifier\", reason=\"unknown_move\")를 제출하는 짝 구현"
  - "다섯 제공자 어댑터의 추론 노출 형태를 세 범주(구조적 배제/위임으로 물려받음/정규식 의존)로 고정한 회귀 시험군"
affects: []

actuals:
  tokens: 9800
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "계약 위반 흡수는 호출부가 아니라 함수 경계(classify()) 안에서 한 번만 한다 — 두 호출부(웹·CLI)가 구조적으로 갈라질 수 없다"
    - "닫힌 목록 사건 payload는 자유 문자열 대신 길이 숫자만 담는다(subject_len) — 10-01이 세운 T-10-03 규율을 SAFE-07 기록에도 그대로 적용"

key-files:
  created: []
  modified:
    - src/gptrpg/agents/action_classifier.py
    - src/gptrpg/web/routes_actions.py
    - src/gptrpg/cli/turn_flow.py
    - src/gptrpg/cli/main.py
    - tests/test_action_classifier.py
    - tests/test_web_actions.py
    - tests/test_cli.py
    - tests/test_providers.py
    - tests/test_agents_retry.py
    - tests/test_turn_tracer.py

key-decisions:
  - "classify()가 _parse_candidates(...) 호출을 call_with_one_retry 밖에서 try/except로 감싼다 — 재시도 층을 침범하지 않는다는 도크스트링의 기존 설명(116~127줄)을 그대로 지킨다"
  - "Proposal.unknown_move: str | None = None 신설 — 기본값이 있어 기존 생성 자리를 안 고쳐도 된다. None이면 '못 골랐다', 값이 있으면 '목록 밖 이름을 냈다'"
  - "웹·CLI 두 호출부 모두 RecordAiCall 제출과 같은 자리·같은 조건으로 RecordSafetyFlag를 제출한다 — 한 자리에서 흡수하므로 두 경로가 구조적으로 갈라질 수 없다는 계획의 설계 판단을 그대로 구현"

requirements-completed: [SAFE-07, QUAL-08]

coverage:
  - id: D1
    description: "분류기가 닫힌 목록 밖 무브 이름을 내도 classify()가 예외 없이 tier==\"none\" Proposal을 돌려주고 unknown_move에 그 이름이 남는다"
    requirement: "SAFE-07"
    verification:
      - kind: unit
        ref: "tests/test_action_classifier.py#test_classify_absorbs_unknown_move_into_none_tier_proposal"
        status: pass
      - kind: unit
        ref: "tests/test_action_classifier.py#test_parse_candidates_still_raises_unknown_move_directly"
        status: pass
    human_judgment: false
  - id: D2
    description: "웹은 200 + tier==\"none\", 명령줄은 종료 코드 0으로 턴이 살아 있고, 플레이어가 친 문장(action_declared)은 기록에 남는다"
    requirement: "SAFE-07"
    verification:
      - kind: integration
        ref: "tests/test_web_actions.py#test_action_declared_event_persists_when_classifier_names_unknown_move"
        status: pass
      - kind: integration
        ref: "tests/test_cli.py#test_turn_classifier_unknown_move_proceeds_without_check_and_records_safety_flag"
        status: pass
    human_judgment: false
  - id: D3
    description: "계약 위반이 safety_flagged 사건 한 건(source=classifier, reason=unknown_move)으로 남고 payload에 이름 문자열이 없다 — 빈 배열 응답에서는 0건이라 '못 골랐다'와 구분된다"
    requirement: "SAFE-07"
    verification:
      - kind: integration
        ref: "tests/test_web_actions.py#test_classifier_unknown_move_records_one_safety_flagged_event_without_the_name"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py#test_classifier_empty_candidates_records_no_safety_flagged_event"
        status: pass
    human_judgment: false
  - id: D4
    description: "목록 밖 이름이 여럿이면 처음 것만 기록되고 후보는 하나도 안 살아남으며, 대소문자·공백·유니코드 정규화 형태 차이는 전부 목록 밖으로 판정된다"
    requirement: "SAFE-07"
    verification:
      - kind: unit
        ref: "tests/test_action_classifier.py#test_classify_multiple_unknown_moves_keeps_only_the_first_and_no_candidates_survive"
        status: pass
      - kind: unit
        ref: "tests/test_action_classifier.py#test_classify_case_variant_move_name_is_treated_as_unknown_move"
        status: pass
      - kind: unit
        ref: "tests/test_action_classifier.py#test_classify_whitespace_padded_move_name_is_treated_as_unknown_move"
        status: pass
      - kind: unit
        ref: "tests/test_action_classifier.py#test_classify_unicode_normalization_variant_move_name_is_treated_as_unknown_move"
        status: pass
    human_judgment: false
  - id: D5
    description: "제공자 호출 횟수가 흡수로 인해 늘지 않는다 — 정상 경로와 똑같이 한 번"
    requirement: "SAFE-07"
    verification:
      - kind: unit
        ref: "tests/test_action_classifier.py#test_classify_unknown_move_does_not_increase_provider_call_count"
        status: pass
    human_judgment: false
  - id: D6
    description: "다섯 제공자 어댑터의 추론 노출 형태가 세 범주(구조적 배제/위임으로 물려받음/정규식 의존)로 시험에 고정되고, Gemini의 한계가 도크스트링에 명시된다"
    requirement: "QUAL-08"
    verification:
      - kind: unit
        ref: "tests/test_providers.py#test_anthropic_extract_text_structurally_excludes_blocks_without_text_attribute"
        status: pass
      - kind: unit
        ref: "tests/test_providers.py#test_openai_stream_yields_nothing_when_delta_content_is_empty_and_reasoning_lives_elsewhere"
        status: pass
      - kind: unit
        ref: "tests/test_providers.py#test_nim_and_openrouter_stream_actually_reaches_openai_provider_stream"
        status: pass
      - kind: unit
        ref: "tests/test_providers.py#test_gemini_stream_skips_chunks_with_empty_text"
        status: pass
      - kind: unit
        ref: "tests/test_providers.py#test_all_five_adapters_are_classified_by_think_exposure_category"
        status: pass
    human_judgment: false

duration: ~35min
completed: 2026-08-14
status: complete
---

# Phase 10 Plan 5: 목록 밖 무브 흡수와 어댑터별 추론 노출 형태 고정 Summary

**분류기가 닫힌 목록 밖 무브 이름을 내도 `classify()` 함수 경계에서 「무브 없음」으로 흡수해 웹 200 · 명령줄 exit 0을 지키고, 계약 위반은 `RecordSafetyFlag(source="classifier")`로 운영자 기록에만 남긴다. 함께 다섯 제공자 어댑터의 추론 노출 형태(구조적 배제/위임/정규식 의존)를 회귀 시험으로 고정했다.**

## Performance

- **Duration:** ~35분
- **Completed:** 2026-08-14
- **Tasks:** 3/3
- **Files modified:** 10 (소스 4 + 시험 6)

## Accomplishments

- `agents/action_classifier.py`: `Proposal.unknown_move: str | None = None` 신설. `classify()`가 `_parse_candidates(...)` 호출을 `call_with_one_retry` **밖**에서 `try/except UnknownMove`로 감싸, 표준오류에 운영자 한 줄을 남기고 후보가 빈 `Proposal`을 돌려준다. `_parse_candidates` 자체는 한 글자도 안 바뀌었다 — 계속 예외를 던진다(계약 위반을 조용히 통과시키지 않는다는 존재 이유는 그대로).
- `web/routes_actions.py` `declare()`: 400 예외 튜플에서 `UnknownMove`를 뺐다. `proposal.unknown_move`가 있으면 `RecordAiCall` 제출과 같은 자리에서 `RecordSafetyFlag(source="classifier", reason="unknown_move", disposition="blocked", subject_len=이름 길이)`를 제출한다. 응답은 평소대로 200 + `tier=="none"`이다 — 새 응답 칸도 새 상태 코드도 없다.
- `cli/turn_flow.py`: 웹과 똑같은 자리·조건으로 `RecordSafetyFlag`를 제출한다. 그 뒤는 기존 `tier == "none"` 갈래(「무브 없음 — 판정 없이 진행합니다」, 종료 코드 0)가 그대로 처리한다 — 새 문구 없음.
- `cli/main.py`: `_cmd_turn`의 except 튜플에서 `UnknownMove`를 뺐다(흡수 이후 이 예외를 던지는 곳에서 여기 도달할 경로가 없다). catch-all에 남기지 않는 것이 의도다 — 흡수가 나중에 깨지면 조용히 exit 1로 되돌아가는 대신 시험이 시끄럽게 실패한다.
- `tests/test_action_classifier.py`: 기존 「`classify()`가 `UnknownMove`를 던진다」 단일 시험을 두 층으로 나눴다 — `_parse_candidates`는 여전히 던진다(계약 유지), `classify()`는 흡수한다(새 동작). 빈 배열/여러 위반/대소문자·공백·유니코드 정규화 변형/제공자 호출 횟수 불변까지 계획의 `<behavior>` 여덟 줄을 각각 시험으로 만들었다.
- `tests/test_web_actions.py`·`tests/test_cli.py`: 웹·명령줄 짝 시험 — 200/exit 0, `action_declared` 사건 보존, `safety_flagged` 사건 정확히 한 건(이름 문자열 없음), 빈 배열 응답에서는 0건.
- `tests/test_providers.py`: QUAL-08의 실제 남은 대상(추론 노출 형태의 어댑터별 차이)을 시험으로 고정. Anthropic `.text` 없는 블록 배제, OpenAI `delta.content` 외 칸 안 읽음, NIM·OpenRouter가 `OpenAIProvider.stream()`으로 실제로 내려감(모놀치 아님을 monkeypatch로 증명), Gemini의 구조적 한계를 도크스트링에 명시, 다섯 어댑터 전수 분류 그물.
- `tests/test_agents_retry.py`·`tests/test_turn_tracer.py`: `classify()`가 `UnknownMove`를 던진다고 단언하던 기존 시험 두 개를 흡수된 `Proposal` 모양을 확인하는 시험으로 갱신(deviation, 아래 참조).

## Task Commits

1. **Task 1: 목록 밖 무브를 「무브 없음」으로 흡수** - `e6482e9` (feat)
2. **Task 2: 두 호출부에서 턴을 죽이던 자리를 없애고 운영자 기록을 남긴다** - `6fd1300` (feat)
3. **Task 3: 어댑터별 추론 노출 형태를 시험으로 고정** - `9dd7464` (test)

**Plan metadata:** (이 커밋 — STATE.md/ROADMAP.md/REQUIREMENTS.md 갱신과 함께)

## Files Created/Modified

- `src/gptrpg/agents/action_classifier.py` - `Proposal.unknown_move` 신설, `classify()`가 함수 경계에서 `UnknownMove`를 흡수
- `src/gptrpg/web/routes_actions.py` - `UnknownMove` 400 제거, `declare()`가 `RecordSafetyFlag(source="classifier")` 제출
- `src/gptrpg/cli/turn_flow.py` - 웹과 같은 자리의 `RecordSafetyFlag` 제출
- `src/gptrpg/cli/main.py` - `UnknownMove`를 except 튜플에서 제거(catch-all에 일부러 안 남김)
- `tests/test_action_classifier.py` - `_parse_candidates`/`classify()` 두 층 분리 시험 + SAFE-07 여덟 behavior 시험
- `tests/test_web_actions.py` - 웹 짝 시험(200/tier none/safety_flagged 한 건/빈 배열 0건)
- `tests/test_cli.py` - 명령줄 짝 시험(exit 0/stderr 이름/safety_flagged 한 건)
- `tests/test_providers.py` - QUAL-08 어댑터별 추론 노출 형태 회귀 시험군
- `tests/test_agents_retry.py`, `tests/test_turn_tracer.py` - 흡수 이후 모양에 맞춘 기존 시험 갱신

## Decisions Made

- 계획이 확정한 설계 판단(흡수는 `classify()` 함수 경계에서 한 번만, `_parse_candidates`는 계속 예외를 던짐, 목록 대조는 `call_with_one_retry` 밖) 그대로 구현했다 — 추가 판단 필요 없음.
- QUAL-08 범위를 계획이 이미 좁혀 둔 대로(추론 노출 형태의 어댑터별 차이 하나) 지켰다 — `note_result`/`last_result` 계약(03-06, G-03-3)은 다시 만들지 않았다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 기존에 `classify()`가 `UnknownMove`를 직접 던진다고 단언하던 시험 두 개가 Task 1 변경으로 정직하게 깨짐**
- **Found during:** Task 1 완료 뒤 전체 스위트 실행(`uv run pytest -q`, 2 failed)
- **Issue:** `tests/test_agents_retry.py::test_classify_raises_unknown_move_without_retrying`와 `tests/test_turn_tracer.py::test_classify_raises_unknown_move_for_name_outside_closed_list`는 계획이 의도적으로 바꾸는 그 동작(`classify()`가 예외를 던진다)을 정확히 단언하고 있었다 — 계획이 예상한 정상적인 깨짐이다.
- **Fix:** 두 시험을 흡수 후 모양(`proposal.tier == "none"`, `proposal.unknown_move == "fireball"`, 재시도 없음 확인용 `provider.call_count == 1` 그대로 유지)을 단언하도록 갱신했다. 각 파일에서 이제 안 쓰는 `UnknownMove`(그리고 `test_turn_tracer.py`의 `pytest`) import도 함께 지웠다.
- **Files modified:** `tests/test_agents_retry.py`, `tests/test_turn_tracer.py`
- **Verification:** `uv run pytest` 전체 스위트 687건 초록불.
- **Committed in:** `6fd1300` (Task 2 커밋 — Task 1 커밋 이후 첫 전체 스위트 실행에서 발견해 Task 2 작업과 함께 정리했다)

**2. [Rule 3 - Blocking] `cli/main.py` 도크스트링이 리터럴 `grep -c "UnknownMove"` 계획 검증 기준(0이어야 함)을 어길 뻔함**
- **Found during:** Task 2, `_cmd_turn` 도크스트링 초안 작성 직후 계획의 acceptance criteria 재확인
- **Issue:** except 튜플에서 `UnknownMove`를 뺀 이유를 설명하는 도크스트링 초안이 그 이름을 그대로 인용해, 계획이 요구하는 `grep -c "UnknownMove" src/gptrpg/cli/main.py`가 0이어야 한다는 기준을 어겼다.
- **Fix:** 도크스트링을 "닫힌 목록 밖 무브 이름 예외(`action_classifier` 모듈, SAFE-07/D-12, 10-05)"로 바꿔 써 코드 식별자 문자열을 완전히 피했다 — 설명 내용은 그대로다.
- **Files modified:** `src/gptrpg/cli/main.py`
- **Verification:** `grep -c "UnknownMove" src/gptrpg/cli/main.py` → 0.
- **Committed in:** `6fd1300` (Task 2 커밋)

---

**Total deviations:** 2 auto-fixed (Rule 1 하나 — 계획이 의도한 변경의 직접 결과로 깨진 기존 시험 갱신, Rule 3 하나 — 계획 검증 기준을 문서화 중 어기지 않도록 문구 조정)
**Impact on plan:** 둘 다 계획의 설계 의도를 뒤집지 않았다. 스코프 확장 없음.

## Known Stubs

없음 — 이 계획이 만든 모든 경로가 실제 호출부에서 소비된다.

## Issues Encountered

없음 — 위 "Deviations from Plan"이 실제로 부딪힌 문제와 해결을 전부 담는다.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- SAFE-07·QUAL-08 둘 다 코드·시험으로 닫혔다 — `uv run pytest`(687건) · `uv run lint-imports`(4계약 유지) · `uv run ruff check src` 전부 초록불.
- 10-03(재생성 시도, D-06/D-07)·10-04(캐릭터 이탈 검사)가 이 계획과 독립적으로(파일이 겹치지 않는다) Wave 2에서 함께 돌 수 있다 — `action_classifier.py`/`routes_actions.py`/`turn_flow.py`/`cli/main.py`를 건드리는 다른 계획이 없다면 병합 충돌 위험은 낮다.
- QUAL-08은 "전수 감사에서 찾은 주석 전제 하나(추론 노출 형태의 어댑터별 차이)를 닫았다"로 보고해야 한다 — "모든 주석 전제를 다 코드로 바꿨다"로 과장하면 안 된다(계획이 명시적으로 경고한 지점).
- 블로커 없음.

---
*Phase: 10-ai*
*Completed: 2026-08-14*

## Self-Check: PASSED

- FOUND: `src/gptrpg/agents/action_classifier.py`
- FOUND: `src/gptrpg/web/routes_actions.py`
- FOUND: `src/gptrpg/cli/turn_flow.py`
- FOUND: `src/gptrpg/cli/main.py`
- FOUND: `tests/test_providers.py`
- FOUND commit: `e6482e9` (Task 1)
- FOUND commit: `6fd1300` (Task 2)
- FOUND commit: `9dd7464` (Task 3)
