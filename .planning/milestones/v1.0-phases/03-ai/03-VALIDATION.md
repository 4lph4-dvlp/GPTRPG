---
phase: 3
slug: ai
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-02
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded by `/gsd-plan-phase 3` from `03-RESEARCH.md` § Validation Architecture.
> Task-level rows are filled by `/gsd-validate-phase` once PLAN.md task IDs exist.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-asyncio ≥1.4.0 (already a dev dependency) [VERIFIED: pyproject.toml:26] |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]`, `asyncio_mode = "auto"` (existing, from Phase 1) |
| **Quick run command** | `uv run pytest tests/test_agents.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~10-15 seconds for the fast subset; full suite unchanged in profile from Phase 1/2 (no real network calls — `FakeProvider` fixture stands in for all LLM calls) |

---

## Sampling Rate

- **After every task commit:** `uv run pytest tests/test_agents.py tests/test_action_classifier.py tests/test_master_gm.py -x` (fast subset touching new code)
- **After every plan wave:** `uv run pytest` (full suite — existing 15+ test files must stay green)
- **Before `/gsd-verify-work`:** Full suite green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

Task IDs are assigned during planning; this table is seeded at the requirement level and
re-keyed to `{N}-{plan}-{task}` by `/gsd-validate-phase`.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | RIG-01 | V5 | Classifier proposes move+stat; confirm is required before roll proceeds; player can reject (자동 확정 금지) | unit (mock provider) | `uv run pytest tests/test_action_classifier.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | RIG-01 | — | High/low/no-move UI tiers (D-34/D-35/D-36) show the right prompt shape without exposing the confidence number (D-37) | unit (CLI output capture) | `uv run pytest tests/test_cli.py -k confirm_tiers -x` | ❌ W0 (extends existing `test_cli.py`) | ⬜ pending |
| TBD | TBD | TBD | RIG-03 | — | Narration streams as multiple `NarrationAppended` events (chunk_index 0, 1, 2…), not one giant blob | unit (mock provider streaming a multi-sentence fixture) | `uv run pytest tests/test_master_gm.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | MEAS-02 | V5 | `RecordAiCall`'s `latency_ms` is populated with a real measured duration; retry-then-fail path (D-27/28) still records one `ai_invoked` event matching the D-30 envelope minimum | unit (mock provider that times out once) | `uv run pytest tests/test_agents_retry.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | MEAS-02 | — | 5s threshold triggers CLI dot-progress (D-26) | manual-only | — (`checkpoint:human-verify` in the plan) | n/a | ⬜ pending |
| TBD | TBD | TBD | MEAS-04 | — | `ActionDeclared.raw_text` + `ActionConfirmed.system_suggestion`/`player_confirmed` round-trip correctly through a full classify→confirm cycle | integration (reuses existing `SessionActor` test harness) | `uv run pytest tests/test_session_actor.py -k ai_turn -x` | ❌ W0 (extends existing file, `RecordAiCall` coverage already at line 149) | ⬜ pending |
| TBD | TBD | TBD | (회귀) | — | `rules_core`가 여전히 AI를 모른다 — `.importlinter`의 새 `gptrpg.agents` 레이어가 `gptrpg.cli` 위에서만 참조되고 아래로 내려가지 않는다 (D14) | contract | `uv run lint-imports` | ❌ W0 (`.importlinter` 갱신 필요) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**API 키 유출과 프롬프트 인젝션이 이 단계의 숨은 보안 위험이다.** RESEARCH.md Security Domain이 발견한 지점 — API 키는 `AiInvoked`의 어떤 필드에도, D-33 영속 파일에도 절대 쓰이면 안 된다(provider/model 이름만 저장). 플레이어의 자유 텍스트가 LLM 프롬프트로 들어가는 지점(V5)은 `rules_core`가 LLM 출력을 수치 진실로 취급하지 않는다는 기존 경계(D14)로 이미 완화되어 있다 — 이 경계가 이번 단계에서도 깨지지 않는지 회귀 테스트가 확인해야 한다.

---

## Wave 0 Requirements

- [ ] `tests/test_action_classifier.py` — RIG-01 커버 (제안 모양, confirm 게이팅)
- [ ] `tests/test_master_gm.py` — RIG-03 커버 (문장 단위 스트리밍)
- [ ] `tests/test_agents_retry.py` — MEAS-02의 재시도-후-실패 경로(D-27/28/29) + 응답 껍데기 최소 규격(D-30) 커버
- [ ] `tests/conftest.py` 추가 — `FakeProvider` 픽스처(인메모리, 결정적, 실제 네트워크 호출 없음), `Provider` 프로토콜을 구현해 위 세 신규 테스트 파일이 전부 실제 LLM API를 치지 않도록 함
- [ ] `.importlinter` 갱신 — `gptrpg.agents` 레이어를 `gptrpg.cli` 위에 추가해 `rules_core`가 AI를 계속 모르게 함 (D14)
- [ ] 프레임워크 설치: 불필요 — pytest/pytest-asyncio가 이미 pyproject.toml dev 그룹에 있음

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 첫 글자가 5초를 넘으면 CLI에 점 세기(dots) 진행 표시가 뜬다 (D-26) | MEAS-02 (성공 조건 3) | 터미널 타이밍에 의존하는 UX 효과라 순수 함수 단위 테스트로 재기 어렵다 | 응답이 느린 provider(또는 인위적 지연)로 CLI를 실행해 5초 지점에서 점이 늘어나는지 육안으로 확인 |
| 15초를 넘으면 판정 결과(주사위·성공/실패·시계 변화)가 먼저 나가고 서사가 뒤이어 붙는다 | MEAS-02 (성공 조건 3) | 두 단계 출력 순서가 실제 터미널 렌더링 순서로 확인돼야 한다 | 15초 이상 지연되는 provider로 CLI를 실행해 판정 결과가 서사보다 먼저 출력되는지 확인 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
