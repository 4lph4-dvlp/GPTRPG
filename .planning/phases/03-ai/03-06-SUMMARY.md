---
phase: 03-ai
plan: 06
subsystem: ai
tags: [provider-protocol, delegation, exception-handling, cli, regression-test, gap-closure]

# Dependency graph
requires:
  - phase: 03-ai (plan 03)
    provides: master_gm.narrate() 스트리밍 재시도 규칙, provider._last_result 직접 대입(범위 안 해법)
  - phase: 03-ai (plan 04)
    provides: cli/turn_flow.py 세 갈래 확인 화면, 90초 스트림 정지 워치독(_drain_with_stall_timeout)
provides:
  - "Provider 프로토콜의 note_result() 정식 메서드 — 실패 껍데기가 위임 어댑터(nim/openrouter)를 통과해 살아남는다"
  - "master_gm.narrate()가 사적 속성 대신 note_result()로 실패를 남김 — 위임 모양 이중체로 증명"
  - "turn_flow._turn_flow()의 서사 구간 예외 포착 + last_result() 무조건 호출을 안전한 도우미로 교체"
  - "실패해도 RecordAiCall이 항상 제출됨(MEAS-02가 실패 턴을 잃지 않음), 이미 나온 문장은 되감지 않음"
  - "tests/test_turn_flow_failure.py — 4가지 실패 모양(중간 예외/규약 위반/첫 조각 전 실패/generator 자체 교체) 회귀"
affects: [03-ai (G-03-3 gap 닫힘, phase 03 재검증 대상)]

actuals:
  tokens: 9682
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "위임 어댑터(자기 상태 없이 안쪽 객체에 넘기는 구조)를 시험하려면 직접 어댑터 모양 이중체로는 부족하다 — 위임 모양 이중체를 별도로 만들어야 위임 구멍이 잡힌다"
    - "상태를 바깥에서 남기는 유일한 공개 경로는 프로토콜 메서드여야 한다 — 사적 속성 직접 대입은 위임 구조에서 조용히 사라진다"
    - "무조건 호출을 도우미 함수로 감싸 항상 값(성공/합성 실패 껍데기)을 돌려주면, 호출부는 예외 분기 없이 한 모양을 유지한다"

key-files:
  created:
    - tests/test_turn_flow_failure.py
  modified:
    - src/gptrpg/agents/providers/base.py
    - src/gptrpg/agents/providers/openai_provider.py
    - src/gptrpg/agents/providers/anthropic_provider.py
    - src/gptrpg/agents/providers/gemini_provider.py
    - src/gptrpg/agents/providers/nim_provider.py
    - src/gptrpg/agents/providers/openrouter_provider.py
    - src/gptrpg/agents/master_gm.py
    - src/gptrpg/cli/turn_flow.py
    - tests/test_providers.py
    - tests/test_master_gm.py
    - tests/conftest.py
    - tests/test_agents_retry.py
    - .planning/phases/03-ai/03-UAT.md

key-decisions:
  - "Provider 프로토콜에 note_result(result) 메서드를 정식 추가 — 03-03에서 '범위 밖'으로 미뤘던 판단을 뒤집었다. 이유: 계획 단계 실측으로 위임 어댑터(nim/openrouter) 둘에서 기존 사적 속성 대입이 값을 잃어버리는 것을 직접 확인했다 — UAT 진단(turn_flow의 무조건 last_result() 호출)은 사고 원인의 절반이었다"
  - "main.py의 _cmd_turn 예외 허용 목록을 넓히지 않는다 — 서사 경계(_turn_flow 내부)에서만 예외를 잡는다. 거기 Exception을 더하면 이번 크래시는 가려지지만 턴 흐름 전체의 진짜 프로그래밍 오류까지 조용히 삼켜진다"
  - "실패 시에도 RecordAiCall을 항상 제출 — 토큰 0/ok=False 관례로 성공과 구분. 실패 턴이 기록에서 통째로 사라지면 MEAS-02가 실제보다 빠른 응답 속도로 집계된다"
  - "되감지 않는다 — 문장은 나오는 족족 그 자리에서 AppendNarration으로 제출하는 기존 구조를 그대로 둔다. 실패했다고 지우거나 마지막에 모아 제출하는 모양으로 바꾸면 RIG-03(문장 단위 스트리밍)을 깬다"

patterns-established:
  - "위임 모양 시험 이중체(안쪽 객체에 상태를 전부 위임하고 바깥은 상태를 갖지 않는 구조, NimProvider/OpenRouterProvider와 동형) — 직접 어댑터 모양 이중체만으로는 위임 구멍이 안 잡힌다는 사실이 이번 gap의 핵심 교훈"
  - "무조건 호출(제공자가 규약을 어길 수 있는 지점)을 감싸는 도우미는 예외를 삼키지 않고 합성 실패 껍데기를 만들어 반환한다 — 호출부의 분기를 줄이고 항상 기록 가능한 값을 보장"

requirements-completed: [RIG-03, MEAS-02]

coverage:
  - id: D1
    description: "Provider 프로토콜에 note_result() 메서드 추가, 다섯 어댑터 전부 구현 — 실패 껍데기가 위임 어댑터를 통과해 last_result()로 되돌아온다"
    requirement: RIG-03
    verification:
      - kind: unit
        ref: "tests/test_providers.py (다섯 어댑터 순회 note_result 왕복/위임 전파/미호출 RuntimeError 회귀)"
        status: pass
      - kind: unit
        ref: "tests/test_providers.py#test_all_five_adapters_satisfy_provider_protocol"
        status: pass
    human_judgment: false
  - id: D2
    description: "master_gm.narrate()가 사적 속성 대신 note_result()로 실패를 남기고, 위임 모양 이중체로 위임 구멍이 막혔음을 증명"
    requirement: RIG-03
    verification:
      - kind: unit
        ref: "tests/test_master_gm.py (위임 모양 이중체 — 실패 시 last_result().ok is False, RuntimeError 아님)"
        status: pass
    human_judgment: false
  - id: D3
    description: "turn_flow._turn_flow()가 서사 실패를 raw traceback 없이 한 줄 stderr + 0 아닌 종료 코드로 마감, 이미 나온 문장은 보존, RecordAiCall은 성공/실패 모두 제출"
    requirement: MEAS-02
    verification:
      - kind: unit
        ref: "tests/test_turn_flow_failure.py (중간 예외/규약 위반 이중체/첫 조각 전 실패/narrate 자체 교체 — 4가지 실패 모양)"
        status: pass
      - kind: integration
        ref: "uv run pytest -q (전체 321 통과, 정상 경로 동작 변화 없음)"
        status: pass
    human_judgment: false
  - id: D4
    description: "90초 정지 워치독의 TimeoutError가 실제 낙하 경로에 도착 — 안전판이 크래시로 흡수되지 않는다"
    requirement: MEAS-02
    verification: []
    human_judgment: true
    rationale: "네트워크를 실제로 차단해 90초 대기를 실측하는 확인은 이 gap-closure 계획의 범위 밖(03-04가 워치독 자체를 만들었고 실제 사고 재현 시나리오는 스톨/예외 이중체로 대체 증명함) — 실제 네트워크 조건에서의 재확인은 phase 재검증 단계로 넘긴다"

duration: ~45min
completed: 2026-08-03
status: complete
---

# Phase 03 Plan 06: 서사 실패 낙하 경로 + Provider 프로토콜 note_result() Summary

**narrate() 실패 시 raw traceback으로 죽던 크래시를 두 층에서 고쳤다 — Provider 프로토콜에 note_result() 메서드를 추가해 위임 어댑터(nim/openrouter)에서도 실패 껍데기가 살아남게 만들고, turn_flow의 서사 구간을 예외 포착으로 감싸 어떤 실패 모양이든 한 줄 메시지 + 0 아닌 종료 코드로 마감한다. G-03-3을 닫는다.**

## Performance

- **Duration:** ~45 min (커밋 타임스탬프 22:41 ~ 22:48 기준 작업 구간, 계획 단계 실측 포함)
- **Started:** 2026-08-02T22:41:47+09:00 (Task 1 커밋)
- **Completed:** 2026-08-02T22:48:04+09:00 (Task 3 커밋)
- **Tasks:** 3 (전부 auto/tdd)
- **Files modified:** 13 (프로덕션 8, 테스트 5)

## Accomplishments

- `Provider` 프로토콜에 `note_result(result: AgentResult) -> None` 정식 메서드 추가 — 직접 어댑터 셋(openai/anthropic/gemini)은 자기 `_last_result`에 대입, 위임 어댑터 둘(nim/openrouter)은 `self._delegate.note_result(result)`로 전파
- 계획 단계 실측으로 UAT 진단에 없던 실제 크래시 원인을 확인: `master_gm.narrate()`의 기존 실패 경로(`provider._last_result = ...` 사적 속성 직접 대입)가 위임 어댑터에서 아무도 읽지 않는 새 속성만 만들고 값이 사라졌다 — 사용자가 실제로 쓰던 NIM에서 `RuntimeError`가 난 이유
- `master_gm.narrate()`를 `provider.note_result(...)` 호출로 전환, `noqa: SLF001` 제거. 위임 모양 시험 이중체(안쪽에 상태, 바깥은 위임만)를 새로 만들어 이 사슬이 실제로 위임을 통과함을 증명
- `turn_flow._turn_flow()`의 서사 구간(narrate 호출부터 문장 반복까지) 전체를 `Exception`-only 포착으로 감싸고, `gm_provider.last_result()` 무조건 호출을 "항상 값을 돌려주는" 도우미로 교체 — 예외가 나면 서사 시작 시각부터 잰 경과 시간을 담은 합성 실패 껍데기를 만들어 반환
- `RecordAiCall`을 성공/실패 어느 경로에서도 항상 제출 — MEAS-02의 두 번째 지점(확인→서사 첫 글자) 집계가 실패 턴을 잃지 않음. 이미 스트리밍된 문장은 되감지 않고 기존처럼 그 자리에서 제출된 채로 남음
- 실패 시 stderr 한 줄 + 0 아닌 종료 코드로 턴을 마감 — `main.py`의 `_cmd_turn` 예외 목록은 넓히지 않음(서사 경계 하나만 실패를 안다는 판단 유지)
- `tests/test_turn_flow_failure.py` 신설 — 조각 하나 낸 뒤 stream() 예외 / note_result() 규약 위반(값을 버리는) 이중체 / 첫 조각 전 매번 실패 / `narrate` 이름 자체를 실패 생성기로 교체, 네 가지 실패 모양 전부에서 raw traceback 없이 0 아닌 종료 코드 확인
- `03-UAT.md`의 G-03-3 gap을 `resolved`로 마감 (resolved_by: 03-06-PLAN.md, resolved_at: 2026-08-02), root_cause에 위임 어댑터 실측 근거와 resolution_note 추가

## Task Commits

Each task was committed atomically:

1. **Task 1: 실패 껍데기 전달을 Provider 프로토콜의 정식 메서드로 올린다 (위임을 통과하게)** - `9a56d27` (fix, tdd)
2. **Task 2: narrate()가 사적 속성 대신 프로토콜 메서드로 실패를 남기게 하고, 위임 모양 이중체로 증명한다** - `f93142f` (fix, tdd)
3. **Task 3: 서사 실패를 turn_flow가 받아 한 줄·한 기록·0 아닌 종료 코드로 마감한다** - `a7a45ba` (fix, tdd)

**Plan metadata:** (이 커밋 — SUMMARY/STATE/ROADMAP/03-UAT 반영)

_Note: 세 task 모두 tdd="true"였으나 각각 단일 커밋으로 RED+GREEN을 함께 담았다(계획 실행 시점의 판단, 세 커밋 메시지 본문에 시험·구현 변경이 함께 기술됨) — 03-06-PLAN.md 자체에 커밋 세분화를 요구하는 문구는 없다._

## Files Created/Modified

- `src/gptrpg/agents/providers/base.py` - `Provider` 프로토콜에 `note_result()` 추가, 도크스트링에 위임 어댑터 전달 요구 명시
- `src/gptrpg/agents/providers/openai_provider.py`, `anthropic_provider.py`, `gemini_provider.py` - 직접 어댑터: `note_result()`가 자기 `_last_result`에 대입
- `src/gptrpg/agents/providers/nim_provider.py`, `openrouter_provider.py` - 위임 어댑터: `note_result()`가 `self._delegate.note_result(result)`로 전파, 클래스 도크스트링에 "상태를 직접 속성으로 꽂으면 조용히 사라진다" 경고 추가
- `src/gptrpg/agents/master_gm.py` - `narrate()`의 실패 경로를 `provider.note_result(...)` 호출로 전환, 관례 의존 도크스트링을 실측 근거로 갱신
- `src/gptrpg/cli/turn_flow.py` - 서사 구간 예외 포착, `last_result()` 안전 도우미, 실패 시 stderr 한 줄 + 0 아닌 종료 코드, `RecordAiCall` 항상 제출
- `tests/test_providers.py` - 다섯 어댑터 순회 `note_result()`/위임 전파/미호출 시 `RuntimeError` 유지 회귀 4개
- `tests/test_master_gm.py` - 위임 모양 이중체 신설 + `narrate()` 실패/보존/정상경로 미호출 시험 확장
- `tests/conftest.py` - `FakeProvider`에 `note_result()` 구현 추가
- `tests/test_agents_retry.py` - `_StreamThenFailProvider`에 `note_result()` 추가(deviation, 아래 참고)
- `tests/test_turn_flow_failure.py` (신규) - 네 가지 실패 모양 회귀 5개 시험
- `.planning/phases/03-ai/03-UAT.md` - G-03-3 gap 상태를 `resolved`로 갱신, root_cause/resolution_note 보강

## Decisions Made

- **note_result()를 정식 프로토콜 메서드로 올린 것.** 03-03에서는 "새 프로토콜 메서드 추가는 범위 밖"이라 판단했었다. 이번 계획 단계에서 실제로 NIM/OpenRouter 이중체를 돌려본 결과, 그 판단이 틀렸음을 확인했다 — 사적 속성 직접 대입이 위임 구조를 정면으로 못 통과한다.
- **`_cmd_turn`의 예외 허용 목록을 넓히지 않은 것.** 서사 경계(`_turn_flow` 내부)에서만 예외를 잡는다. 실패의 의미(어떤 문장이 이미 나갔는지, 무엇을 기록해야 하는지)를 아는 곳이 거기뿐이기 때문.
- **실패 시에도 `RecordAiCall`을 항상 제출.** 실패 턴이 기록에서 사라지면 MEAS-02 집계가 성공 턴만 보고 실제보다 빠르게 나온다.
- **되감지 않는다.** 문장은 나오는 족족 그 자리에서 제출하는 기존 구조를 유지 — RIG-03(문장 단위 스트리밍)을 지킨다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `tests/test_agents_retry.py`의 `_StreamThenFailProvider`에 `note_result()` 추가**
- **Found during:** Task 3 (전체 스위트 검증 중)
- **Issue:** `narrate()`의 실패 경로가 `provider.note_result(...)`를 호출하도록 바뀌면서, 이 계획의 `files_modified` 목록 밖에 있던 기존 Provider 시험 이중체(`_StreamThenFailProvider`)가 `note_result()`를 구현하지 않아 `AttributeError`로 깨졌다
- **Fix:** 다른 시험 이중체들과 같은 모양으로 `note_result()`를 추가 (자기 `_last_result`에 대입)
- **Files modified:** `tests/test_agents_retry.py`
- **Verification:** `uv run pytest -q` 321개 전부 통과
- **Committed in:** `a7a45ba` (Task 3 커밋)

---

**Total deviations:** 1 auto-fixed (Rule 1 - 계획 범위 밖 기존 시험 이중체가 프로토콜 변경으로 깨진 것을 수정)
**Impact on plan:** 계획이 예견한 변화(narrate()의 호출 방식 전환)의 직접 파급 효과를 수습한 것 — 스코프 크리프 아님.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **G-03-3이 닫혔다.** 서사 스트림이 어떤 이유로든 실패해도 CLI가 raw traceback 없이 한 줄 메시지 + 0 아닌 종료 코드로 턴을 마감한다. 90초 정지 워치독의 `TimeoutError`도 같은 경로로 떨어진다(구조상 — 실제 네트워크 차단 재확인은 D4에서 human_judgment로 남겨둠).
- **Phase 03의 gap-closure 계획 두 개(03-05, 03-06)가 모두 완료됐다** — G-03-1(OpenRouter ASCII 헤더)과 G-03-3(narrate 실패 낙하 경로)이 모두 `resolved`. `03-UAT.md`에 남은 blocker 없음(다음 단계는 phase 수준 재검증).
- Anthropic/OpenAI/Gemini 세 제공자는 이번 gap-closure 전체에서 실제 네트워크로 검증되지 않은 채로 남아 있다(03-05 SUMMARY와 동일 — 사용자가 해당 API 키를 보유하지 않음).

---
*Phase: 03-ai*
*Completed: 2026-08-03*

## Self-Check: PASSED
- FOUND: tests/test_turn_flow_failure.py
- FOUND: src/gptrpg/agents/providers/base.py
- FOUND: 9a56d27 (fix(03-06): promote failure-envelope handoff to a Provider protocol method)
- FOUND: f93142f (fix(03-06): narrate() leaves failure envelopes via note_result(), not a private attribute)
- FOUND: a7a45ba (fix(03-06): narrate() failures land in turn_flow as a value, not a raw traceback)
