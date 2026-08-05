---
phase: 2
slug: two-rulebooks-one-vessel
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-01
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded by `/gsd-plan-phase 2` from `02-RESEARCH.md` § Validation Architecture.
> Task-level rows are filled by `/gsd-validate-phase` once PLAN.md task IDs exist.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥9.1.1 + hypothesis ≥6.164.0 [VERIFIED: pyproject.toml] |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]` (existing, from Phase 1) |
| **Quick run command** | `uv run pytest -q` |
| **Full suite command** | `uv run pytest && uv run lint-imports && uv run ruff check .` |
| **Estimated runtime** | ~10-15 seconds (pure-Python unit tests, no network/server — same profile as Phase 1) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q` (module-scoped where possible)
- **After every plan wave:** Run `uv run pytest && uv run lint-imports && uv run ruff check .`
- **Before `/gsd-verify-work`:** Full suite green AND existing Phase 1 regression suite (106+ tests) unchanged
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

Task IDs are assigned during planning; this table is seeded at the requirement level and
re-keyed to `{N}-{plan}-{task}` by `/gsd-validate-phase`.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | 02-01 | 1 | RIG-08a | T-02-02 | d100 판정이 2d6과 같은 `CheckOutcome`/`CheckResolved` 모양으로 돈다 (명령→사건→재구성 끝-대-끝) | unit | `uv run pytest tests/test_tracer_d100.py -x` | ❌ W0 | ⬜ pending |
| TBD | 02-01 | 1 | (Pitfall 1) | T-02-03 | 실패 집계가 등급 이름이 아니라 룰북 선언 신호로 계산되고, 판 1 기록도 같은 숫자로 접힌다 | unit | `uv run pytest tests/test_reducer_failure_count.py -x` | ❌ W0 | ⬜ pending |
| TBD | 02-02 | 2 | RIG-08b | T-02-07 | 등급 집합이 코드에 고정 안 됨 — 이름 목록형·수치 구간형 선언이 둘 다 통과한다 | unit + hypothesis | `uv run pytest tests/test_grading_d100.py -x` | ❌ W0 | ⬜ pending |
| TBD | 02-02 | 2 | RIG-08c | T-02-06 | 수정치 4유형(FLAT/보너스다이스/목표값변경/푸시)이 전부 계산 결과에 반영된다 | unit + hypothesis | `uv run pytest tests/test_resolution_d100.py -k modifier -x` | ❌ W0 | ⬜ pending |
| TBD | 02-03 | 2 | RIG-08d | T-02-09 | OpenQuest 적(상태값 10개)과 2d6 계열 적(1개)이 같은 `Entity`/`StatEntry` 그릇에 들어간다 | unit | `uv run pytest tests/test_entities.py -x` | ❌ W0 | ⬜ pending |
| TBD | 02-04 | 3 | RIG-08 | T-02-12 | 명령줄에서 룰북을 골라 판정하고 재생하면 그 룰북의 등급 이름이 나온다 | unit | `uv run pytest tests/test_cli.py -x` | ✓ 이미 존재 (확장) | ⬜ pending |
| TBD | 02-04 | 3 | HYP-03 | T-02-13 | 두 번째 룰북을 넣으며 실제로 고친 곳/참은 곳이 `02-INTERFACE-CHANGES.md`에 기록된다 | manual-only | — (사람이 문서를 읽고 판단, 02-04 Task 3 체크포인트) | ❌ W0 | ⬜ pending |
| TBD | 02-01 | 1 | (회귀) | — | 기존 2d6 판정·사건 재생·경계 계약 142개가 전부 그대로 통과한다 | regression | `uv run pytest` (전체) | ✓ 이미 존재 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**`reducer.py`의 `grade == "miss"` 하드코딩이 이 단계의 숨은 회귀 위험이다.** RESEARCH.md Pitfall 1이 발견한 지점 — `tests/conftest.py`의 `fake_session_log`(`failure_count=2`)가 이 계산에 의존한다. d100 판정 사건을 넣었을 때 `miss_count`가 조용히 틀어지지 않는지 확인하는 테스트가 Wave 0 갭에 반드시 포함되어야 한다.

---

## Wave 0 Requirements

- [ ] `tests/test_tracer_d100.py` — RIG-08a 커버, 명령→룰북 선언→순수 함수→사건→재구성 끝-대-끝 (02-01 Task 2)
- [ ] `tests/test_reducer_failure_count.py` — Pitfall 1(등급 이름 하드코딩) 회귀 방지 + 판 1 해석 경로 (02-01 Task 3)
- [ ] `tests/test_resolution_d100.py` — RIG-08c 커버, 수정치 네 유형·푸시 롤·재생 (02-02 Task 1~3)
- [ ] `tests/test_grading_d100.py` — RIG-08b 커버, `hypothesis`로 등급 구간이 연속·배타적인지 증명 + 수치 구간형 룰북 (02-02 Task 3)
- [ ] `tests/test_entities.py` — RIG-08d 커버, D-20/D-21 `Entity`/`StatEntry` 신규 모듈 (02-03 Task 1~2)
- [ ] `tests/test_cli.py` 확장 — 룰북 선택 왕복 (02-04 Task 1)
- [ ] `02-INTERFACE-CHANGES.md` — HYP-03의 산출물 (테스트가 아니라 문서 자체가 검증 대상, 02-04 Task 2~3)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `02-INTERFACE-CHANGES.md`가 "고친 곳"과 "고치지 않고 버틴 곳"을 실제로 명확히 기록했다 | HYP-03 (성공 조건 5) | "명확히 기록된다"는 사람이 읽고 판단하는 문구 — 자동 검증 불가 | 사람이 문서를 열어 두 항목(고친 곳/참은 곳)이 실제로 존재하고 이유가 붙어 있는지 확인 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
