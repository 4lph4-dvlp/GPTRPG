---
phase: 9
slug: agent-architecture
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-07
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1+ / pytest-asyncio 1.4.0+ (`asyncio_mode = "auto"`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`) |
| **Quick run command** | `uv run pytest tests/test_master_gm.py tests/test_action_classifier.py tests/test_session_actor_auto_advance.py tests/test_session_actor.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~unmeasured — full suite; researcher did not benchmark |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_master_gm.py tests/test_action_classifier.py tests/test_session_actor_auto_advance.py tests/test_session_actor.py -x`
- **After every plan wave:** Run `uv run pytest` (전체) + `import-linter`(`.importlinter` 계약 검사 — 새 코드가 `gptrpg.agents` → `event_log`/`session_actor` 레이어 경계를 어기지 않는지)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60s (내부 프로젝트, 소규모 스위트 — RESEARCH.md가 정확한 런타임을 재지 않았으므로 계획 단계에서 실측 후 조정)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-01-01 | TBD | 0 | ARCH-02 | V8 | 서술 프롬프트의 `system`에 페르소나 지시문·시나리오 원문이 없다 | unit | `pytest tests/test_prompt_assembly_scenario.py -x` | ✅ 기존, 확장 필요 | ⬜ pending |
| 09-01-02 | TBD | 0 | ARCH-02 | V8 | `narrate()`가 구조화된 사실 묶음을 받는다(문자열 한 줄이 아니다) | unit | `pytest tests/test_master_gm.py -x` | ✅ 기존, 확장 필요 | ⬜ pending |
| 09-01-03 | TBD | 0 | ARCH-03 | Tampering(D3 우회) | 배경 시계 조건 검사 산출물이 사건으로 기록되고 재생 시 같은 상태가 나온다(웹 경로) | integration | `pytest tests/test_web_actions.py -x` | ✅ 기존, 확장 필요 | ⬜ pending |
| 09-01-04 | TBD | 0 | ARCH-03 | Tampering(D3 우회) | CLI 경로에서도 배경 조건 검사 산출물이 유실 없이 기록된다(CLI 프로세스 생명주기 함정 회귀 방지) | integration | `pytest tests/test_turn_flow_failure.py -x` | ✅ 기존, 확장 필요 | ⬜ pending |
| 09-01-05 | TBD | 0 | ARCH-04 | — | 병렬 판단 두 조각(장면·시계)이 항상 함께 호출된다 — 런타임 조건부 병렬화가 없다 | unit | 신규 `tests/test_parallel_judgment.py` | ❌ Wave 0 | ⬜ pending |
| 09-01-06 | TBD | 0 | ARCH-05 | — | 한쪽 판단이 타임아웃/실패해도 턴이 끝까지 진행되고, 실패는 운영자 로그에만 남는다 | unit | 신규(`tests/test_agents_retry.py` 패턴 재사용, `FakeProvider`가 예외를 던지도록 설정) | ❌ Wave 0 (기존 패턴 확장) | ⬜ pending |
| 09-01-07 | TBD | 0 | ARCH-06 | V1 | 각 에이전트 역할이 정해진 문맥 칸만 받고 상한을 넘지 않는다 | unit | 신규 `tests/test_agent_context_caps.py` | ❌ Wave 0 | ⬜ pending |
| 09-01-08 | TBD | 0 | ARCH-04/05 | Elevation of Privilege(D14) | AI가 시계 칸 이동·판정 수치를 직접 결정하지 않는다 — `condition` 트리거는 판단 신호만 내고 실제 사건 기록·상태 변경은 `SessionActor`가 한다 | unit | `pytest tests/test_session_actor_auto_advance.py -x`(기존, `trigger="condition"` 케이스 확장) | ✅ 기존, 확장 필요 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Task IDs above are placeholders (09-01-NN) — the planner assigns real plan/task IDs; this table's Requirement/Behavior/Command columns are the binding contract, IDs will be reconciled when PLAN.md files exist.*

---

## Wave 0 Requirements

- [ ] `tests/test_parallel_judgment.py` — ARCH-04(정적 병렬 호출, 런타임 조건부 병렬화 없음) 회귀 방지
- [ ] `tests/test_agent_context_caps.py` — ARCH-06(역할별 문맥 상한) 회귀 방지
- [ ] `tests/test_web_actions.py`/`tests/test_turn_flow_failure.py`에 시계 조건 검사 배경 경로 케이스 추가 — ARCH-03의 "재생하면 같은 상태" 보장
- [ ] Framework install: 불필요 — pytest/pytest-asyncio 이미 dev 의존성에 있음

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|--------------------|
| CLI 경로(`gptrpg turn`)에서 배경 작업이 실제 운영 환경(서버처럼 오래 사는 프로세스가 아닌 1회성 프로세스)에서 유실되지 않는지 | ARCH-03 | RESEARCH.md가 지목한 구조적 함정(Pitfall #1) — `asyncio.run()` 기반 CLI는 await 안 된 백그라운드 태스크가 프로세스 종료와 함께 유실된다. 자동 테스트로는 "프로세스가 실제로 종료되는 타이밍"의 경합을 완전히 재현하기 어려워, 계획 단계에서 CLI가 배경 작업을 어떻게 처리할지(예: await 후 진행 vs 웹과 다른 전략) 확정한 뒤 수동으로 한 번 실제 CLI 실행을 확인 | `gptrpg turn` 명령으로 시계 조건을 만족하는 판정을 실행하고, 프로세스 종료 후 `.gptrpg/events.db`에 `clock_advanced`(trigger=condition) 사건이 실제로 남았는지 확인 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
