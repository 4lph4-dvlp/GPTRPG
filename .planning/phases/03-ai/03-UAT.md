---
status: complete
phase: 03-ai
source: [03-VERIFICATION.md]
started: 2026-08-02T11:11:11.000Z
updated: 2026-08-03T00:00:00.000Z
---

## Current Test

[testing complete]

## Tests

### 1. OpenRouter 실제 키로 모델 목록·귀속 헤더 확인
expected: 모델 목록이 실제로 돌아온다 (RESEARCH.md 가정 A4가 참으로 확인됨)
result: pass
resolution: "G-03-1로 진단, 03-05-PLAN.md가 수정(X-Title ASCII 교체). 실제 OPENROUTER_API_KEY로 재확인 — 모델 목록 정상 조회, ascii codec 오류 재발 안 함(사용자 확인: \"모델 리스트도 잘 뜨고 정상적으로 저장도 됐어\")"

### 2. Anthropic/OpenAI/Gemini 실제 키로 모델 목록·판정·서사 스트리밍 확인
expected: 세 제공자 모두 모델 목록·판정·서사 스트리밍이 정상 동작한다 (이 단계 전체에서 실제 네트워크로 검증된 제공자는 NIM뿐 — 5개 중 1개만 실증됨)
result: skipped
reason: 사용자가 Anthropic/OpenAI/Gemini API 키를 보유하고 있지 않음

### 3. NIM 스트림 90초 정지 워치독 실제 발동 확인
expected: 90초 안에 TimeoutError로 낙하하고 이미 나온 문장은 보존된 채 턴이 실패로 마감된다 (22분 무한 정지 사고의 직접 수정이라 실제 재현 확인이 특히 중요)
result: skipped
reason: "이 시험 도중 발견된 실제 크래시(G-03-3 — narrate() 실패 시 turn_flow.py의 gm_provider.last_result() 무조건 호출이 raw traceback으로 터짐)는 03-06-PLAN.md로 수정·재검증 완료(324개 테스트 통과, 코드 재추적으로 5개 어댑터 전부 확인). 다만 이 시험이 원래 확인하려던 '실제 네트워크 정지에 90초 워치독이 발동하는가'는 크래시 수정에 밀려 끝내 실행하지 못함 — 사용자가 잔여 위험으로 받아들이기로 결정(WINDOWS.md id 4, waived)"

### 4. 추론형 모델의 &lt;think&gt;/코드펜스 대체 파싱 경로 실제 실행 확인
expected: 원문 그대로의 1차 파싱이 실패하고 2단계 대체 경로가 실제로 후보를 뽑아내는 사례를 로그·중간 출력으로 확인
result: skipped
reason: 임시 디버그 로그를 붙여 10회 반복 실행 — 매번 1차 경로(원문 그대로)로 성공, 2단계 대체 경로가 한 번도 실행되지 않음. 버그는 아님 — 이번 단계 실제 조사에서 밝혀진 진짜 실패 양상은 JSON 포맷 문제가 아니라 호출 자체의 실패(타임아웃)였던 것과 일치. 대체 경로 자체의 정확성은 여전히 합성 이중체로만 증명된 상태로 남음

## Summary

total: 4
passed: 1
issues: 0
pending: 0
skipped: 3
blocked: 0

## Gaps

- gap_id: G-03-1
  truth: "OpenRouter 실제 키로 모델 목록 조회가 귀속 헤더(HTTP-Referer/X-Title)와 함께 정상 동작한다"
  status: resolved        # was: failed
  resolved_by: 03-05-PLAN.md
  resolved_at: 2026-08-02
  reason: "User reported: 오류: 'openrouter' 모델 목록 조회 실패 — 'ascii' codec can't encode characters in position 10-11: ordinal not in range(128)"
  severity: blocker
  test: 1
  root_cause: "openrouter_provider.py의 _ATTRIBUTION_HEADERS에서 X-Title 값이 한글 문자열('GPTRPG M0 실험 도구')인데, HTTP 헤더는 ASCII만 허용해서 httpx가 요청을 인코딩할 때 UnicodeEncodeError로 터진다"
  artifacts:
    - path: "src/gptrpg/agents/providers/openrouter_provider.py"
      issue: "_ATTRIBUTION_HEADERS의 X-Title 값에 non-ASCII(한글) 문자열 사용"
  missing:
    - "X-Title 값을 ASCII로 교체하거나 RFC 8187 percent-encoding으로 인코딩"
    - "회귀 테스트: 헤더 값이 ASCII로 인코딩 가능함을 보장하는 단위 테스트 추가"
  debug_session: ""
  resolution_note: "03-05-PLAN.md Task 1이 X-Title을 ASCII 문자열('GPTRPG M0 Experiment Tool')로 교체하고 다섯 어댑터를 덮는 헤더 인코딩 가능성 회귀 시험을 추가. Task 2에서 사람이 실제 OPENROUTER_API_KEY로 `agents select`를 재실행해 모델 목록이 오류 없이 조회됨을 확인(nvidia/nemotron-nano-9b-v2:free 선택, 승인: \"approved\")."

- gap_id: G-03-3
  truth: "90초 안에 TimeoutError로 낙하하고 이미 나온 문장은 보존된 채 턴이 실패로 마감된다"
  status: resolved        # was: failed
  resolved_by: 03-06-PLAN.md
  resolved_at: 2026-08-02
  reason: "User reported: 네트워크 차단 전, 서사 스트리밍 도중(문장 2개 출력, 14초 경과) RuntimeError('complete() 또는 stream()을 먼저 불러야 last_result()를 부를 수 있다')가 raw traceback으로 터짐. turn_flow.py:336의 gm_provider.last_result() 무조건 호출이 stream() 실패 후 상태 없음과 충돌"
  severity: blocker
  test: 3
  root_cause: "turn_flow.py의 _turn_flow()가 narrate() 호출 실패 여부와 무관하게 그 뒤에서 gm_provider.last_result()를 무조건 호출한다(약 336번째 줄). narrate()의 스트림이 중간에 실패하면(정지·연결 오류 등) provider의 complete()/stream() 내부 상태가 last_result를 채우지 못한 채로 남는데, 이 경우를 감지하지 않고 그대로 호출해 RuntimeError가 처리되지 않은 채 터진다 — 원래 검증하려던 90초 워치독보다 앞서, narrate() 실패 전반에 대한 낙하 경로 자체가 없다는 더 근본적인 문제. **계획 단계에서 실측으로 드러난 절반의 진실:** 사용자가 쓰던 NIM은 위임 어댑터(NimProvider가 OpenAIProvider에 위임)라, narrate()의 실패 경로가 `provider._last_result = ...`로 직접 속성을 꽂아도 위임 어댑터에서는 아무도 읽지 않는 새 속성 하나만 만들고 값이 사라졌다 — UAT 진단에는 없던 실제 크래시 원인. `master_gm.py` 도크스트링의 '다섯 어댑터 전부가 `_last_result`를 공유한다'는 진술이 다섯 중 둘(nim/openrouter)에 대해 거짓이었다."
  artifacts:
    - path: "src/gptrpg/cli/turn_flow.py"
      issue: "narrate() 실패 이후에도 gm_provider.last_result()를 무조건 호출 (약 336번째 줄)"
    - path: "src/gptrpg/agents/master_gm.py"
      issue: "narrate()는 스트림 실패 시 예외를 던지지만, 호출부(turn_flow.py)가 이 실패를 감지하고 낙하하는 경로가 없다"
  missing:
    - "narrate() 실패(TimeoutError 포함 모든 스트림 실패)를 turn_flow.py에서 감지해 last_result() 호출을 건너뛰고 무브 없음/서사 실패 경로로 낙하"
    - "실패 시에도 이미 스트리밍되어 출력된 문장은 그대로 보존"
    - "회귀 테스트: narrate()가 스트림 도중 예외를 던지는 이중체로 전체 턴 플로우를 실행해 raw traceback 없이 우아하게 낙하하는지 확인"
  debug_session: ""
  resolution_note: "03-06-PLAN.md가 두 층을 함께 고쳤다. 층 1(Task 1·2): `Provider` 프로토콜에 `note_result()`를 정식 메서드로 추가하고 다섯 어댑터 전부가 구현하게 해, narrate()의 실패 경로가 `provider._last_result` 직접 대입 대신 `provider.note_result(...)`를 부르게 바꿨다 — 위임 어댑터(nim/openrouter)에서도 값이 위임 대상까지 도달한다. 위임 모양 이중체(NimProvider와 같은 구조)로 이 사슬을 실제로 시험해 회귀를 잡는다(tests/test_master_gm.py). 층 2(Task 3): `_turn_flow()`의 서사 구간 전체를 `except Exception`으로 감싸고, `gm_provider.last_result()`의 무조건 호출을 실패 시 합성 껍데기를 만들어 돌려주는 도우미로 교체 — 제공자가 프로토콜을 어겨도(예: note_result()가 값을 버림) CLI는 죽지 않는다. RecordAiCall은 성공·실패 어느 쪽에서도 항상 제출되고, 실패 시 표준오류 한 줄 + 0 아닌 종료 코드로 턴을 마감한다. 이미 나온 문장은 되감지 않는다. 회귀 테스트 4개를 tests/test_turn_flow_failure.py에 추가(조각 하나 후 stream() 예외 / note_result() 규약 위반 이중체 / 첫 조각 전 매번 실패 / narrate 이름 자체를 실패 생성기로 교체) — 전부 raw traceback 없이 0 아닌 종료 코드로 낙하함을 확인."
