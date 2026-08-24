---
phase: 13
slug: scene-opening-and-targets
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-24
updated: 2026-08-25
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (`pyproject.toml` `[tool.pytest.ini_options]`, `asyncio_mode = "auto"`) · vitest (프런트, 순수 함수 전용 — RTL 안 씀) |
| **Config file** | `pyproject.toml` (`testpaths = ["tests"]`) · `frontend/vite.config.ts` |
| **Quick run command** | `.venv/bin/python -m pytest -q --tb=short -k <키워드>` · `cd frontend && npx vitest run <파일>` |
| **Full suite command** | `.venv/bin/python -m pytest -q --tb=short` (config.json의 `workflow.test_command`) · `cd frontend && npx tsc --noEmit && npm run build && npx vitest run` |
| **Estimated runtime** | 전체 pytest ~60초 · `-k` 좁힌 실행 ~3–13초 · 프런트 vitest ~5초 |

**층 계약 검사도 매 물결에 돈다:** `.venv/bin/python -m lint_imports` (`.importlinter` 계약 4건). 새 모듈(`rules_core/scenario.py`·`rulebooks/scenarios.py`)이 층을 거스르면 여기서 잡힌다.

---

## Sampling Rate

- **After every task commit:** 그 Task의 `<verify><automated>` 전부 (대개 `pytest -k` 한 줄 + 필요 시 `vitest run <파일>`)
- **After every plan wave:** `.venv/bin/python -m pytest -q --tb=short` 전체 + `lint_imports` + (프런트가 걸린 물결이면) `tsc --noEmit && npm run build && vitest run`
- **Before `/gsd-verify-work`:** 전체 스위트 초록 + `.venv/bin/python -c "import gptrpg.rulebooks.scenarios"`가 조용히 통과(등록 시점 검사가 실제 데이터를 통과)
- **Max feedback latency:** 13초 (좁힌 `-k` 실행 기준)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | SCENE-01, SCENE-02 | T-13-01/02/03/04/06 | 오프닝 라우트가 `proceed()`와 동일한 신원 대조를 하고, 슬롯이 실패해도 `finally`에서 풀린다 | integration | `pytest -q tests/test_scenario.py tests/test_scene_opening.py` | ❌ W0 (신규 2건) | ⬜ pending |
| 13-01-02 | 01 | 1 | SCENE-01 | — | 화면이 서버가 내려준 `scene_opened_seq`만 읽고 다시 계산하지 않는다 | unit(순수함수)+build | `cd frontend && npx vitest run src/session/openingView.test.ts` | ❌ W0 (신규) | ⬜ pending |
| 13-01-03 | 01 | 1 | SCENE-01, SCENE-02 | — | N/A (사람 확인) | manual | — (checkpoint) | — | ⬜ pending |
| 13-02-01 | 02 | 2 | SCENE-01 | T-13-07/08/09 | 겹친 요청이 제공자를 한 번만 부르고, 실패해도 슬롯이 풀린다 | integration | `pytest -q tests/test_gm_slot.py` | ❌ W0 (신규) | ⬜ pending |
| 13-02-02 | 02 | 2 | SCENE-01 | T-13-10 | 409가 화면에서 오류로 보이지 않는다 | build+unit | `cd frontend && npx tsc --noEmit && npx vitest run` | ✅ | ⬜ pending |
| 13-03-01 | 03 | 2 | SCENE-02 | T-13-14 | N/A (설계 결정) | manual | — (checkpoint:decision) | — | ⬜ pending |
| 13-03-02 | 03 | 2 | SCENE-01, SCENE-02 | — | 이관이 실행 중 동작을 안 바꾼다(기존 시험 전부 통과가 그 증거) | unit | `pytest -q tests/test_scenario.py tests/test_imagery.py tests/test_turn_tracer.py` | ✅ (확장) | ⬜ pending |
| 13-03-03 | 03 | 2 | SCENE-01, SCENE-02 | T-13-11/12/13/15 | **서술이 시나리오 원문을 못 본다**(ARCH-02) | integration | `pytest -q tests/test_scene_opening.py tests/test_situation_judge.py tests/test_narration_isolation.py` | ✅ (확장) | ⬜ pending |
| 13-04-01 | 04 | 3 | SCENE-03, SCENE-05 | T-13-16/18/19/20 | 이름 대조가 정규화 뒤 완전 일치 하나뿐이고, 옛 기록이 판 13에서도 접힌다 | unit | `pytest -q tests/test_scene_layers.py tests/test_event_schema_migration.py` | ❌ W0 (신규 1건) | ⬜ pending |
| 13-04-02 | 04 | 3 | SCENE-03 | T-13-17 | 2층이 세션 길이와 무관하게 상한 안쪽으로 묶인다(ARCH-06) | unit | `pytest -q tests/test_scene_layers.py tests/test_agent_context_caps.py` | ✅ (확장) | ⬜ pending |
| 13-04-03 | 04 | 3 | SCENE-03, SCENE-05 | T-13-16 | 웹 두 호출부 + CLI 한 자리가 같은 헬퍼를 쓴다 | integration | `pytest -q tests/test_scene_entity_judge.py tests/test_web_actions.py tests/test_cli.py` | ✅ (확장) | ⬜ pending |
| 13-05-01 | 05 | 4 | SCENE-04 | T-13-21/23/26 | AI가 낸 자유 문자열을 코드가 항상 재대조한다(ASVS V5) | unit | `pytest -q tests/test_action_classifier.py` | ✅ (확장) | ⬜ pending |
| 13-05-02 | 05 | 4 | SCENE-04 | T-13-22/24/25 | 확인/진행 시점의 대상은 사건에서 다시 읽는다(요청 본문 불신) · 종류 불명은 닫히는 쪽 | integration | `pytest -q tests/test_scene_target.py tests/test_web_actions.py` | ❌ W0 (신규) | ⬜ pending |
| 13-05-03 | 05 | 4 | SCENE-04 | T-13-22 | 명령줄이 웹과 같은 갈래로 간다 | integration | `pytest -q tests/test_scene_target.py -k cli` | ❌ W0 (신규) | ⬜ pending |
| 13-06-01 | 06 | 4 | SCENE-05 | T-13-28/30/31 | 내부 식별자를 응답에 안 싣고, 시나리오 조회 실패가 폴링을 500으로 안 만든다 | integration | `pytest -q tests/test_web_events.py -k roster` | ✅ (확장) | ⬜ pending |
| 13-06-02 | 06 | 4 | SCENE-05 | T-13-29 | 이름이 텍스트 노드로만 들어간다(`dangerouslySetInnerHTML` 없음) | build | `cd frontend && npx tsc --noEmit && npm run build && npx vitest run` | ✅ | ⬜ pending |
| 13-06-03 | 06 | 4 | SCENE-01..05 | — | N/A (사람 확인 — 단계 전체) | manual | — (checkpoint) | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

각 계획의 첫 Task가 자기 시험 파일을 **먼저 빨갛게** 만든 뒤 구현한다(별도 Wave 0 물결을 세우지 않는다 — 이 저장소의 관례가 계획 안 TDD다).

- [ ] `tests/test_scenario.py` — `ScenarioDecl`/`OpeningDecl`/`validate_registered_scenarios` 구조 검사 (13-01 Task 1)
- [ ] `tests/test_scene_opening.py` — 오프닝 HTTP 종단 (13-01 Task 1, 13-03 Task 3이 확장)
- [ ] `frontend/src/session/openingView.ts` + `.test.ts` — 오프닝 발동 판단 순수 함수 (13-01 Task 2)
- [ ] `tests/test_gm_slot.py` — **제공자 호출 횟수**를 세는 겹침 재현 (13-02 Task 1)
- [ ] `tests/test_scene_layers.py` — 세 층 조회·이름 정규화·명부 (13-04 Task 1)
- [ ] `tests/test_scene_target.py` — 대상 지목의 열림/닫힘 결정론 (13-05 Task 2)

프레임워크 설치는 필요 없다 — pytest·vitest 둘 다 이미 있다.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 「명단 잠금 직후 빈 화면이 머무르는 순간이 있는가」 | SCENE-01 | 화면 전환의 **체감 시간**은 자동으로 못 잰다 — 사람이 그 순간을 보는 것이 유일한 판정 | 13-01 Task 3 항목 1 |
| 「긴 낭독문이 카드 폭 안에서 정상 줄바꿈되는가」 | SCENE-02 | 실제 브라우저 reflow가 필요하다(UI-SPEC E1 overflow/long-text backstop) | 13-01 Task 3 항목 2 |
| 「TRPG를 모르는 사람이 이 글만 읽고 첫 행동을 칠 수 있는가」 | SCENE-02 | **이것이 SCENE-02의 진짜 질문이다** — 다섯 요소가 「들어 있다」는 구조 검사가 답하지만 「행동할 수 있다」는 사람만 답한다 | 13-06 Task 3 항목 3 |
| 「거절당하는 느낌이 드는가」 | SCENE-04 | D-15의 결(세계가 대답 vs 시스템이 거절)은 문자열 검사로 못 잰다 | 13-06 Task 3 항목 5 |
| 「이야기에 나온 것이 명부에 다 있는가」 | SCENE-05 | 서사 텍스트와 명부의 대조는 사람이 읽어야 한다 — 자동화하면 이 계획이 금지한 이름 부분 일치를 뒷문으로 들인다 | 13-06 Task 3 항목 10 |
| D-08 검사 방식 선택 | SCENE-02 | 설계 결정 — 사장님이 고른다 | 13-03 Task 1 (checkpoint:decision) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (체크포인트 3건은 면제)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (신규 시험 파일 6건이 각 계획 첫 Task에 박혀 있다)
- [x] No watch-mode flags (`pytest -q` · `vitest run` — `--watch` 없음)
- [x] Feedback latency < 13s (좁힌 `-k` 실행 기준)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending (`/gsd-validate-phase 13`이 실행 뒤 상태를 `validated`로 올린다)
