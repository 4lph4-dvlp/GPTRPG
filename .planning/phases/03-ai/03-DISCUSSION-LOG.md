# Phase 3: AI 진행자 한 턴 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-02
**Phase:** 3-AI 진행자 한 턴
**Areas discussed:** 화면 형태, 에이전트 응답 껍데기 + 타임아웃·재시도, 모델·제공자 선택, 재량 판정 확인 화면의 표현

---

## 화면 형태

| Option | Description | Selected |
|--------|-------------|----------|
| CLI 확장 | Phase 1·2가 만든 명령줄 도구를 확장 — AI 턴 루프 자체가 도는지를 최소 비용으로 증명 | ✓ |
| 최소 단일 플레이어 웹 화면 | 브라우저에서 문장을 치고 제안·확인·서사를 보는 화면을 지금 시작 | |
| 웹 화면이지만 실시간 스트리밍은 다음 단계로 | 브라우저 화면은 지금 만들되 서사 스트리밍 연결은 Phase 4로 미룸 | |

**User's choice:** CLI 확장
**Notes:** 없음

| Option | Description | Selected |
|--------|-------------|----------|
| 점 세기 | 상태 업데이트 없이 '...'이 한 자씩 늘어나는 방식 | ✓ |
| 텍스트 메시지 | "(AI 응답 대기 중…)" 같은 한 줄 메시지 출력 | |
| 안 보여줘도 됨 | 이번 단계에서는 진행 표시 자체를 생략 | |

**User's choice:** 점 세기
**Notes:** 없음

---

## 에이전트 응답 껍데기 + 타임아웃·재시도

| Option | Description | Selected |
|--------|-------------|----------|
| 2초 (v1 제안값) | 문장 입력 → 확인 표시 0.5초 목표에 맞춘 짧은 안전망 | |
| 5초 | 여유를 더 주는 값 | ✓ |
| 지금 안 정함 | 실측해서 정함 | |

**User's choice:** action_classifier 타임아웃 5초 (master_gm은 D33이 이미 15초로 확정)
**Notes:** 없음

| Option | Description | Selected |
|--------|-------------|----------|
| 한 번 재시도 후 실패 처리 | v1의 지수 백오프 최대 2회는 실험 도구에 과함 | ✓ |
| 재시도 없이 바로 실패 처리 | 가장 단순 | |
| 오류 종류별로 다르게 | v1의 MODEL_ERROR/VALIDATION_FAILED 구분 유지 | |

**User's choice:** 한 번 재시도 후 실패 처리
**Notes:** 없음

| Option | Description | Selected |
|--------|-------------|----------|
| 자동으로 '판정 없이 진행'으로 떨어짐 | 재량 판정 계층의 3번째 분류(무브 없음)와 같은 경로 | ✓ |
| 오류 메시지 보여주고 다시 치라고 함 | 플레이어가 문장을 다시 치게 함 | |

**User's choice:** 자동으로 '판정 없이 진행'으로 떨어짐
**Notes:** 없음

| Option | Description | Selected |
|--------|-------------|----------|
| 성공/실패 + 값 + 걸린 시간·토큰 수 | AiInvoked 사건이 이미 담는 값들을 호출 직후 담는 임시 그릇 | ✓ |
| v1 껍데기 그대로 | error_code·fallback_suggestion 포함 | |

**User's choice:** 성공/실패 + 값 + 걸린 시간·토큰 수
**Notes:** 없음

---

## 모델·제공자 선택

| Option | Description | Selected |
|--------|-------------|----------|
| Anthropic Claude | 한국어 서사 품질을 직접 재야 하므로 특정 제공자에 강한 이유가 없다면 현재 개발 환경과 맞추는 것이 유리 | |
| OpenAI GPT | 시장 벤치마크 상위권이지만 한국어 서사 품질은 이번 실험이 직접 재는 변수 | |
| 자유 응답 | 사용자가 직접 구체적 요구사항을 서술 | ✓ |

**User's choice:** "Claude, Nvidia NIM, Openrouter, Gemini, OpenAI 5개의 주요 제공자의 API 키를 선택적으로 환경 변수로 입력 받고, 프로그램이 시작될 때 존재하는 API 키를 기반으로 프로바이더를 그 중 선택할 수 있고, 프로바이더 선택 후 모델 선택 화면에서 해당 프로바이더가 제공하는 모델들 실시간 리스트를 나열해서 선택할 수 있게 하자."
**Notes:** D19("에이전트별 모델 분리 + 제공자 추상화 계층을 M0에 넣는다")를 다섯 제공자·실시간 모델 목록까지 구체화한 답변.

| Option | Description | Selected |
|--------|-------------|----------|
| 각자 따로 선택 | action_classifier와 master_gm이 서로 다른 제공자·모델을 가질 수 있음 | ✓ |
| 하나로 묶기 | 두 에이전트가 같은 제공자·모델을 공유 | |

**User's choice:** 각자 따로 선택
**Notes:** 없음

| Option | Description | Selected |
|--------|-------------|----------|
| 한 번 고르면 파일로 저장 | 설정값 파일에 적어두고 다음 실행부터는 묻지 않음 | ✓ |
| 매 실행마다 물어본다 | 유연하지만 플레이어가 실험 중 마주칠 화면은 아님 | |

**User's choice:** 한 번 고르면 파일로 저장
**Notes:** 없음

---

## 재량 판정 확인 화면의 표현

| Option | Description | Selected |
|--------|-------------|----------|
| 한 줄 제안 + [Enter=확인 / n=아니오] | 설계 문서의 확인 문구를 CLI 텍스트로 그대로 옮김 | ✓ |
| 무브·능력치를 명령어 인자로 바로 받음 | `confirm --move ... --stat ...` 형태 | |

**User's choice:** 한 줄 제안 + [Enter=확인 / n=아니오]
**Notes:** 없음

| Option | Description | Selected |
|--------|-------------|----------|
| 번호 목록에서 숫자 입력 | 후보 2~3개를 번호로 나열, "판정 없이 진행"도 항상 후보 말미에 포함 | ✓ |
| 첫 번째 후보로 자동 선택되고 바꿀 것만 쓰게 | 입력을 줄이지만 "나란히 제시"라는 설계 표현과 약간 멀어짐 | |

**User's choice:** 번호 목록에서 숫자 입력
**Notes:** 없음

| Option | Description | Selected |
|--------|-------------|----------|
| 다음 턴에 직접 판정 명령을 치게 함 | 기존 `roll` 서브커맨드를 재사용, 새 되돌리기 경로 없음 | ✓ |
| "판정 없이 진행" 바로 뒤에 질문을 하나 더 내밀어 확인 | 같은 턴 안에서 한 번 더 확인 | |

**User's choice:** 다음 턴에 직접 판정 명령을 치게 함
**Notes:** 없음

| Option | Description | Selected |
|--------|-------------|----------|
| 안 보여줌 — UI 강도만 바뀐다 | §4.7 "신뢰도는 UI 강도로만 쓴다" 원문을 그대로 따름 | ✓ |
| 괄호로 작게 함께 보여줌 | 디버그용으로 유용하지만 임계값 개념을 되살릴 여지 | |

**User's choice:** 안 보여줌 — UI 강도만 바뀐다
**Notes:** 없음

---

## Claude's Discretion

- 다섯 제공자 각각의 실시간 모델 목록 조회 API 형태
- 프롬프트 조립 순서(영구 고정 → 세션 고정 → 턴마다 변함)의 구체적 구현
- action_classifier의 신뢰도 판정 기준(무엇을 "높음"으로 볼지)
- 재시도 사이 대기 시간
- CLI 서브커맨드 이름과 정확한 인자 형태
- 제공자·모델 선택 결과를 저장할 파일 형식과 위치

## Deferred Ideas

- 실제 웹 멀티플레이어 화면(RIG-07) — Phase 4
- 서사의 실시간 웹 스트리밍 전송 — Phase 4
- v1의 전체 AgentResult<T> 껍데기(error_code, fallback_suggestion 등) — 필요해지면 M1
- 하트비트 주기·재연결 시 이어붙이기 — Phase 4(RIG-07)와 함께
- 자동화율이 플레이하면서 올라가는 홈브루 승격 기능 — M1 이후
