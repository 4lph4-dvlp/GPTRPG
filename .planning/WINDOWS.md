---
schema_version: 1
open_count: 0
waived_count: 1
fixed_count: 4
total_count: 5
last_updated: 2026-08-02T16:17:20.009Z
---

# Broken Windows Ledger

> Cross-phase defect register. `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 03 | deviation | .planning/phases/03-ai/03-01-SUMMARY.md |  | MEAS-02 marked complete at plan level but only the latency_ms/token measurement half is built — D-26 (5s dot-progress) and D-33 (15s check-result-first override) UX thresholds are 03-02/03-03 scope, not yet implemented | fixed |  | 2026-08-02T02:07:48.698Z | 2026-08-02T10:35:33.485Z |
| 2 | 03 | unrun-verify | src/gptrpg/agents/providers/openrouter_provider.py |  | OpenRouter 귀속 헤더(HTTP-Referer/X-Title)가 실제 모델 목록 조회에 필수인지(RESEARCH.md Open Question 1/가정 A4)는 OPENROUTER_API_KEY가 없어 03-02 Task 3에서 라이브로 확인되지 않았다 — 방어적으로 항상 부착만 해둔 상태 | fixed |  | 2026-08-02T07:22:20.202Z | 2026-08-02T16:17:19.709Z |
| 3 | 03 | unrun-verify | src/gptrpg/agents/invoke.py |  | 실제 제공자 SDK 다섯 개가 타임아웃을 어떤 예외 형으로 알리는지(TimeoutError/httpx.TimeoutException/APITimeoutError 등)는 call_with_one_retry의 종류-불문 catch가 실제로 그 예외를 잡는지를 실제 호출로만 확인할 수 있다(plan must_haves 백스톱 항목) — 이번 계획은 테스트 이중체로만 검증했고 실제 프로바이더 타임아웃은 라이브로 재현하지 않았다 | fixed |  | 2026-08-02T07:34:53.264Z | 2026-08-02T10:35:43.636Z |
| 4 | 03 | unrun-verify | src/gptrpg/agents/master_gm.py |  | STREAM_STALL_TIMEOUT_S(90s) 워치독이 실제로 멈춘 NIM 스트림에 대해 라이브로 발동하는 것은 확인되지 않았다 — 03-04 Task 3 재검증 배치에서 4턴 전부 정상 완주해 워치독이 필요 없었다(합성 이중체로만 시험됨). 실제 스톨을 다시 재현하지 못하면 이 값 자체가 적절한지도 라이브로 확인 불가 | waived | 사용자가 잔여 위험으로 받아들이기로 함 — 코드 레벨 완화(90초 정지 워치독)는 이미 구현·단위 테스트로 확인됨. 실제 네트워크 정지 재현은 G-03-3 버그 발견/수정에 밀려 진행하지 못함. iptables로 재현하는 절차는 안내되어 있으니 필요시 재개 가능 | 2026-08-02T10:36:05.782Z | 2026-08-02T16:17:20.009Z |
| 5 | 03 | unrun-verify | src/gptrpg/agents/action_classifier.py |  | _try_parse_json_array()의 <think>/코드펜스 벗기기 대체 경로가 실제 모델 응답에서 실제로 발동한 사례는 라이브로 확인되지 않았다 — 03-04 Task 3 재검증에서 D-35 번호 목록이 정상 작동했지만, 원문이 애초에 순수 JSON이었는지(원래 빠른 경로만 탔는지) 대체 파싱 경로가 실제로 실행됐는지는 구분되지 않는다 | fixed |  | 2026-08-02T10:36:05.933Z | 2026-08-02T16:17:19.863Z |

````json
[
  {
    "id": 1,
    "kind": "deviation",
    "phase": "03",
    "file": ".planning/phases/03-ai/03-01-SUMMARY.md",
    "line": null,
    "description": "MEAS-02 marked complete at plan level but only the latency_ms/token measurement half is built — D-26 (5s dot-progress) and D-33 (15s check-result-first override) UX thresholds are 03-02/03-03 scope, not yet implemented",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-02T02:07:48.698Z",
    "resolved_at": "2026-08-02T10:35:33.485Z"
  },
  {
    "id": 2,
    "kind": "unrun-verify",
    "phase": "03",
    "file": "src/gptrpg/agents/providers/openrouter_provider.py",
    "line": null,
    "description": "OpenRouter 귀속 헤더(HTTP-Referer/X-Title)가 실제 모델 목록 조회에 필수인지(RESEARCH.md Open Question 1/가정 A4)는 OPENROUTER_API_KEY가 없어 03-02 Task 3에서 라이브로 확인되지 않았다 — 방어적으로 항상 부착만 해둔 상태",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-02T07:22:20.202Z",
    "resolved_at": "2026-08-02T16:17:19.709Z"
  },
  {
    "id": 3,
    "kind": "unrun-verify",
    "phase": "03",
    "file": "src/gptrpg/agents/invoke.py",
    "line": null,
    "description": "실제 제공자 SDK 다섯 개가 타임아웃을 어떤 예외 형으로 알리는지(TimeoutError/httpx.TimeoutException/APITimeoutError 등)는 call_with_one_retry의 종류-불문 catch가 실제로 그 예외를 잡는지를 실제 호출로만 확인할 수 있다(plan must_haves 백스톱 항목) — 이번 계획은 테스트 이중체로만 검증했고 실제 프로바이더 타임아웃은 라이브로 재현하지 않았다",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-02T07:34:53.264Z",
    "resolved_at": "2026-08-02T10:35:43.636Z"
  },
  {
    "id": 4,
    "kind": "unrun-verify",
    "phase": "03",
    "file": "src/gptrpg/agents/master_gm.py",
    "line": null,
    "description": "STREAM_STALL_TIMEOUT_S(90s) 워치독이 실제로 멈춘 NIM 스트림에 대해 라이브로 발동하는 것은 확인되지 않았다 — 03-04 Task 3 재검증 배치에서 4턴 전부 정상 완주해 워치독이 필요 없었다(합성 이중체로만 시험됨). 실제 스톨을 다시 재현하지 못하면 이 값 자체가 적절한지도 라이브로 확인 불가",
    "status": "waived",
    "reason": "사용자가 잔여 위험으로 받아들이기로 함 — 코드 레벨 완화(90초 정지 워치독)는 이미 구현·단위 테스트로 확인됨. 실제 네트워크 정지 재현은 G-03-3 버그 발견/수정에 밀려 진행하지 못함. iptables로 재현하는 절차는 안내되어 있으니 필요시 재개 가능",
    "recorded_at": "2026-08-02T10:36:05.782Z",
    "resolved_at": "2026-08-02T16:17:20.009Z"
  },
  {
    "id": 5,
    "kind": "unrun-verify",
    "phase": "03",
    "file": "src/gptrpg/agents/action_classifier.py",
    "line": null,
    "description": "_try_parse_json_array()의 <think>/코드펜스 벗기기 대체 경로가 실제 모델 응답에서 실제로 발동한 사례는 라이브로 확인되지 않았다 — 03-04 Task 3 재검증에서 D-35 번호 목록이 정상 작동했지만, 원문이 애초에 순수 JSON이었는지(원래 빠른 경로만 탔는지) 대체 파싱 경로가 실제로 실행됐는지는 구분되지 않는다",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-02T10:36:05.933Z",
    "resolved_at": "2026-08-02T16:17:19.863Z"
  }
]
````
