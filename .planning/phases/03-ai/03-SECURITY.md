---
phase: 03
slug: ai
status: verified
threats_open: 0
asvs_level: 1
created: 2026-08-03
---

# Phase 03 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| 플레이어 자유 텍스트 → LLM 프롬프트 | 신뢰할 수 없는 입력이 `raw_text`로 들어와 그대로 모델 프롬프트의 턴 조각이 된다 (ASVS V5) | 플레이어 발화 텍스트 |
| 로컬 프로세스 → 제공자 API | 환경 변수의 API 키와 세션 문맥이 외부 서비스(Anthropic/OpenAI/Gemini/NIM/OpenRouter)로 나간다 | API 키, 프롬프트 문맥 |
| PyPI → 로컬 환경 | 제공자 SDK 패키지(`anthropic`/`openai`/`google-genai`)를 설치한다 | 서드파티 패키지 |
| CLI 저장 파일 → 로컬 디스크 | `agents select`가 역할별 provider/model 선택을 `.gptrpg/agents.json`에 영속화한다 | provider/model 이름 (API 키는 제외) |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-03-01 | Tampering/EoP | `agents/action_classifier.py` | medium | mitigate | 모델 출력을 `known_move_ids`와 대조해 `UnknownMove`로 거부; `ResolveCheck.modifiers`/`.target`은 CLI 인자에서만 옴; 사람 확인이 한 겹 더 있음 (RIG-01) | closed |
| T-03-02 | Info Disclosure | `agents/providers/__init__.py` | high | mitigate | API 키는 `get_provider` 한 곳에서만 환경 변수로 읽고 예외 메시지/기록 어디에도 값이 남지 않음 — `AiInvoked`는 제공자·모델 이름만 기록 | closed |
| T-03-03 | Tampering | `rules_core` 경계 | high | mitigate | `.importlinter` 계약 3 — `gptrpg.agents`가 사건 저장소/세션 액터/`sqlite3`를 참조 못함. `uv run lint-imports` 매 커밋 검사, 3/3 계약 유지 확인 | closed |
| T-03-04 | DoS (자기부담) | `agents/invoke.py` | medium | mitigate | `MAX_ATTEMPTS=2` — 무한 재시도 없음 | closed |
| T-03-05 | Info Disclosure | 제공자 노출면 | low | accept | 운영자 본인 계정, 관찰용 실험 도구 — PLAN.md에 근거 기록 | accepted |
| T-03-SC | Tampering (공급망) | 제공자 SDK 패키지 | high | mitigate | Task 1 체크포인트로 사람이 PyPI 공식 GitHub 조직 확인; `uv pip list`로 공식 패키지만 설치됨 재확인 | closed |
| T-03-02b | Info Disclosure | `agents/config.py` | high | mitigate | `save_config`가 `{provider, model}`만 기록, 키 값 저장 안 함 — 테스트로 고정 | closed |
| T-03-06 | Info Disclosure | `cli/main.py` (`agents show`) | high | mitigate | provider/model 이름만 출력, 키 값 없음 — 테스트로 고정 | closed |
| T-03-07 | Spoofing | `providers/__init__.py` | medium | mitigate | 알 수 없는 provider 이름은 `UnknownProvider`/`InvalidAgentConfig`로 거부, 조용한 폴백 없음 | closed |
| T-03-SC-b | Tampering (공급망) | `openai`/`google-genai` 패키지 | high | mitigate | T-03-SC와 동일 검증, 03-01 Task 1에서 이미 공식 확인됨 | closed |
| T-03-05b | Info Disclosure | 5개 제공자 노출면 | low | accept | 5개 중 실제 사용은 2개뿐 — PLAN.md에 근거 기록 | accepted |
| T-03-04b | DoS (자기부담) | `agents/invoke.py` | high | mitigate | `MAX_ATTEMPTS=2` 강제 — 두 번째 실패 후 정확히 멈춤을 테스트로 고정 | closed |
| T-03-01b | Tampering/EoP | `agents/action_classifier.py` | medium | mitigate | `UnknownMove` 검사가 재시도 이후에 실행됨을 테스트로 고정 | closed |
| T-03-08 | Repudiation | `agents/invoke.py` | high | mitigate | 두 번 다 실패해도 예외 대신 실패 `AgentResult`를 반환, `RecordAiCall`로 기록됨 | closed |
| T-03-09 | Info Disclosure | `agents/invoke.py` | high | mitigate | `last_error_text = str(exc)` — 헤더·환경변수 값 섞이지 않음 | closed |
| T-03-01c | EoP | `cli/turn_flow.py` | high | mitigate | 세 갈래(single/several/none) 전부 사람 확인이 먼저 있어야 진행, `none` 갈래는 `ConfirmAction` 자체를 제출 안 함 | closed |
| T-03-10 | Tampering | `cli/turn_flow.py` | medium | mitigate | 잘못된 입력에 재입력 루프 — 테스트로 고정 | closed |
| T-03-08b | Repudiation | `cli/turn_flow.py` | high | mitigate | 거부/무브없음 경우 확인 사건 없이 선언 사건만 남음을 테스트로 고정 | closed |
| T-03-11 | Info Disclosure | 확인 화면 전체 | low | mitigate | 어떤 화면에도 소수점 확신도 숫자 없음 — 테스트로 고정 | closed |
| T-03-05-01 | Info Disclosure | OpenRouter 귀속 헤더 | low | accept | 고정 공개 식별 문자열, 세션/사용자 데이터 아님 — PLAN.md에 근거 기록 | accepted |
| T-03-05-02 | Info Disclosure | `agents/config.py` (`_select_one_role`) | low | mitigate | 오류 경로가 예외 메시지를 그대로 출력하지만 키 값 미포함 관례 유지 — 기존 테스트로 고정 | closed |
| T-03-05-SC | Tampering (공급망) | 03-05 변경분 | low | accept | 03-05는 `pyproject.toml` 의존성 변경 없음 — `git log` 확인 | accepted |
| T-03-06-01 | DoS | `agents/master_gm.py` | medium | mitigate | 90초 정지 워치독의 `TimeoutError`를 `narrate()`가 내부에서 잡아 실패 봉투로 낙하; `turn_flow.py`도 방어적으로 한 번 더 감쌈 | closed |
| T-03-06-02 | Info Disclosure | `cli/turn_flow.py` | low | mitigate | 실패 시 `str(exc)`만 출력, 스택트레이스/설정값 미노출 | closed |
| T-03-06-03 | Tampering | `agents/providers/base.py` | low | mitigate | `note_result()`는 비정상 종료 전용으로 문서화, 성공 시 호출 안 됨을 테스트로 고정 | closed |
| T-03-06-04 | Repudiation | `cli/turn_flow.py` | medium | mitigate | 성공/실패 양쪽 다 `RecordAiCall`이 무조건 제출됨 | closed |
| T-03-06-SC | Tampering (공급망) | 03-06 변경분 | low | accept | 03-06은 `pyproject.toml` 의존성 변경 없음 — `git log` 확인 | accepted |

*Status: open · closed · open — below high 임계값 (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-1 | T-03-05 | 운영자 본인 계정으로 돌리는 관찰용 실험 도구 — 매칭/공유 없음 | PLAN.md (03-01) | 2026-08-02 |
| AR-2 | T-03-05b | 5개 제공자 노출면 중 실제 사용은 2개(NIM, OpenRouter)뿐 — 나머지는 코드만 존재, 키 없으면 선택 화면에도 안 뜸 | PLAN.md (03-02) | 2026-08-02 |
| AR-3 | T-03-05-01 | OpenRouter 귀속 헤더(HTTP-Referer/X-Title)는 고정 공개 문자열 — 세션/사용자 데이터 아님 | PLAN.md (03-05) | 2026-08-02 |
| AR-4 | T-03-05-SC | 03-05는 의존성 변경 없이 헤더 문자열만 수정 | PLAN.md (03-05) | 2026-08-02 |
| AR-5 | T-03-06-SC | 03-06은 의존성 변경 없이 프로토콜 메서드·예외 처리만 추가 | PLAN.md (03-06) | 2026-08-02 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-03 | 27 | 27 (22 mitigate + 5 accept) | 0 | gsd-security-auditor |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-03
