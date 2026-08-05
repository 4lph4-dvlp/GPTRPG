---
phase: 4
slug: experiment-tool
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-03
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded by `/gsd-plan-phase 4` from `04-RESEARCH.md` § Validation Architecture.
> Task-level rows are filled by `/gsd-validate-phase` once PLAN.md task IDs exist.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-asyncio 1.4.0 (already project dev dependencies) [VERIFIED: pyproject.toml] |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]`, `asyncio_mode = "auto"` (existing, from Phase 1) |
| **Quick run command** | `uv run pytest tests/test_web_*.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~10-20 seconds for the new web/reducer subset; full suite unchanged in profile from Phase 1-3 (FastAPI's `TestClient` is fully synchronous to call, no real network — no new slow I/O introduced) |

---

## Sampling Rate

- **After every task commit:** `uv run pytest tests/test_web_events.py tests/test_web_characters.py tests/test_reducer_fails_since_clock.py tests/test_session_actor_auto_advance.py tests/test_report.py -x` (fast subset touching new code)
- **After every plan wave:** `uv run pytest -q` (full suite — existing test files must stay green)
- **Before `/gsd-verify-work`:** Full suite green; additionally, a manual live QA pass with 2+ real browser tabs against a running `uvicorn` instance is required — D-38/D-40's polling cadence and disconnect-banner timing are not meaningfully unit-testable
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

Task IDs are assigned during planning; this table is seeded at the requirement level and
re-keyed to `04-{plan}-{task}` by `/gsd-validate-phase`.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | RIG-04 | — | 실패 카운터(`fails_since_clock`)가 3회 연속 실패 후 시계를 강제 진행시키고 0으로 초기화된다 (기존 누적 `failure_count`와는 다른 필드) | unit (reducer) | `uv run pytest tests/test_reducer_fails_since_clock.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | RIG-04 | — | `SessionActor`가 `ResolveCheck` 처리 직후 3회째 실패를 감지해 `AdvanceClock(trigger="fail_counter")`를 자동 주입하며, 단일 쓰기 큐(D-09)를 통해 직렬화된다 | integration (actor) | `uv run pytest tests/test_session_actor_auto_advance.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | RIG-05 | V4 | `GET /sessions/{id}/characters/{player_id}`가 올바른 읽기 전용 시트를 반환한다; 위조/추측된 character_id로 다른 사람의 시트를 보는 것은 허용된 위험(A5)이나 쓰기 권한으로 확장되어서는 안 된다 | integration (web, TestClient) | `uv run pytest tests/test_web_characters.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | RIG-07 | — | 폴링 엔드포인트가 `seq >= from_seq`인 사건만 반환한다 (경계 포함) | integration (web, TestClient) | `uv run pytest tests/test_web_events.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | RIG-07 | — | 새로고침/재접속 시 `from_seq=0`으로 전체 역사를 그대로 다시 받는다 (부분 재개 경로 없음, D-41) | integration (web, TestClient) | `uv run pytest tests/test_web_events.py -x` | ❌ W0 (같은 파일) | ⬜ pending |
| TBD | TBD | TBD | MEAS-01 | — | 자동 저장 JSON 리포트의 `total_tokens`/`turn_count`가 수기로 만든 픽스처 세션과 정확히 일치한다 | unit (report builder) | `uv run pytest tests/test_report.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | MEAS-03 | — | `failure_to_clock_ratio`가 올바르게 계산되며, `clock_advances == 0`(null) 경계 케이스도 처리한다 | unit (report builder) | `uv run pytest tests/test_report.py -x` | ❌ W0 (같은 파일) | ⬜ pending |
| TBD | TBD | TBD | (회귀) | V5 | 서사/`raw_text`가 프런트엔드에서 `textContent`로만 렌더링된다 (`innerHTML` 금지) — Phase 3까지는 터미널 출력뿐이라 없었던 반사형 XSS 표면이 이번 단계에서 처음 생긴다 | manual-only (이번 단계는 헤드리스 DOM 테스트 하네스를 두지 않음 — 화면 컴포넌트 설계는 M0 범위 밖) | — (`checkpoint:human-verify` in the plan) | n/a | ⬜ pending |
| TBD | TBD | TBD | (회귀) | — | 새 `gptrpg.web` 레이어가 `gptrpg.cli`와 co-equal로 import-linter에 추가되고, `rules_core`/`event_log`는 여전히 `web`을 모르는 방향으로만 참조된다 (D14 연장) | contract | `uv run lint-imports` | ❌ W0 (`.importlinter` 갱신 필요) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**터미널에서 브라우저로 넘어가며 처음 생기는 XSS 표면이 이 단계의 숨은 보안 위험이다.** RESEARCH.md Security Domain이 발견한 지점 — 서사 텍스트를 `innerHTML`로 꽂으면 AI가 생성했거나 플레이어가 입력한 문자열이 그대로 스크립트로 실행될 수 있다. 캐릭터 선택 쿠키(D-43)는 의도적으로 서명하지 않은 값이라(A5) 이 단계의 신원 확인은 "같은 방 네 명"이라는 신뢰 모델 안에서만 유효하다 — M1에서 실제 계정을 도입하기 전에는 이 패턴을 그대로 가져가면 안 된다.

---

## Wave 0 Requirements

- [ ] `tests/test_reducer_fails_since_clock.py` — RIG-04의 새 `GameState.fails_since_clock` 필드 커버 (기존 `tests/test_reducer_failure_count.py` 패턴 재사용)
- [ ] `tests/test_session_actor_auto_advance.py` — actor 레벨 자동 주입 커버 (기존 `tests/test_session_actor.py`의 `AdvanceClock` 테스트 패턴 재사용, 142-155/397-425행)
- [ ] `tests/test_web_events.py`, `tests/test_web_characters.py` — 신규, FastAPI `TestClient` 픽스처 필요
- [ ] `tests/test_report.py` — 신규, `build_report(state)` 순수 함수 단위 테스트
- [ ] `tests/conftest.py`에 `TestClient` 픽스처 추가
- [ ] `.importlinter` 갱신 — `gptrpg.web`을 `gptrpg.cli`와 co-equal 레이어로 추가; `pyproject.toml`의 `[tool.ruff.lint.per-file-ignores]`에 `"src/gptrpg/web/*" = ["TID251"]` 추가
- [ ] 프레임워크 설치: `uv add fastapi uvicorn` + `uv add --dev httpx` (pytest/pytest-asyncio는 이미 존재)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 폴링 지연(1-2초, D-38)과 "연결이 끊겼음" 배너(약 10초 연속 실패, D-40)의 실제 체감 타이밍 | RIG-07 | 브라우저 타이머·네트워크 타이밍에 의존하는 UX 효과라 순수 단위 테스트로 재기 어렵다 | 2개 이상의 실제 브라우저 탭으로 `uvicorn` 인스턴스를 띄우고, 한 탭에서 행동 후 나머지 탭에 반영되는지, 네트워크를 끊었다 붙였을 때 배너가 뜨고 사라지는지 육안 확인 |
| 캐릭터 선택 쿠키 지속(D-43) — 새로고침해도 같은 캐릭터가 자동 선택됨 | RIG-05 | 실제 브라우저 쿠키 저장·재전송 동작은 `TestClient`로 완전히 재현되지 않는다 | 브라우저에서 캐릭터 선택 후 새로고침하여 같은 캐릭터가 유지되는지 확인 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
