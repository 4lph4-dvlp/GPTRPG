---
phase: 5
slug: 1
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-03
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded by `/gsd-plan-phase 5` from `05-RESEARCH.md` § Validation Architecture.
> Task-level rows are filled by `/gsd-validate-phase` once PLAN.md task IDs exist.
>
> **이 단계의 특성:** 요구사항 6개 중 코드로 자동 검증 가능한 것은 EXP-01뿐이다. EXP-02/03/04·MEAS-05/06은
> 실제 두 세션(사람 넷, 1주 간격)이 코드 밖에서 진행되는 운영 활동이라 "Full suite green"이 이 단계의
> 완료 게이트가 아니다 — 코드 변경분(시나리오 데이터 주입)만 자동 검증되고, 나머지는 세션 자체가 검증이다.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥9.1.1 + pytest-asyncio ≥1.4.0 (already project dev dependencies) [VERIFIED: pyproject.toml] |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (existing, from Phase 1) |
| **Quick run command** | `uv run pytest tests/test_turn_tracer.py tests/test_web_actions.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~3-8 seconds — measured this session: 388 passed in 3.22s test time (8.3s wall incl. `uv` startup) [VERIFIED: `time uv run pytest -q` run 2026-08-03]. New tests add a handful of pure in-memory dataclass/string assertions — no new slow I/O. |

---

## Sampling Rate

- **After every task commit:** `uv run pytest tests/test_turn_tracer.py tests/test_web_actions.py -q` (fast subset touching new/changed code)
- **After every plan wave:** `uv run pytest -q` (full suite — all existing 388 tests must stay green)
- **Before `/gsd-verify-work`:** Full suite green for the code slice; additionally, EXP-02/03/04 and MEAS-05/06 require the two actual sessions (1 week apart) to have run and the hand-written observation records to exist — no command substitutes for this
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

Task IDs are assigned during planning; this table is seeded at the requirement level and
re-keyed to `05-{plan}-{task}` by `/gsd-validate-phase`.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | EXP-01 | — | `PLACEHOLDER_CLOCK_SEGMENT_COUNT == 4` (was 6); `build_turn_context`가 시나리오 캐스트를 `scene_entities`로 반환한다 | unit | `uv run pytest tests/test_turn_tracer.py -q` (기존 파일 확장) | ✅ 기존 파일 확장 | ⬜ pending |
| TBD | TBD | TBD | EXP-01 | V5 | `_format_clock_state`/`_session_block_text`가 시나리오 이름·위협 정체를 포함한 텍스트를 반환하고, **같은 칸에서 두 번 호출해도 byte-identical**(캐싱 불변식 위반 없음) | unit | 신규 `tests/test_prompt_assembly_scenario.py` | ❌ W0 신설 필요 | ⬜ pending |
| TBD | TBD | TBD | EXP-01 | — | 룰북(무브 10개)·캐릭터 4개 그릇은 이미 충족 — 코드 변경 없음 | — | 해당 없음 | 해당 없음 | ⬜ pending |
| TBD | TBD | TBD | EXP-04 | — | 캐릭터 만들기 구두 안내 대본 문서가 7가지 동작을 던전월드 계열 스탯에 맞게 구체화해 존재한다 | manual-only | — (대본 자체가 산출물) | ❌ W0 (문서 신설) | ⬜ pending |
| TBD | TBD | TBD | MEAS-05 | — | 1세션 종료 손글씨 리캡 3~5줄 템플릿/절차가 준비되어 있다 | manual-only | — | ❌ W0 (문서 신설) | ⬜ pending |
| TBD | TBD | TBD | MEAS-06 | — | 애착 질문("당신 캐릭터 어떤 사람이에요?") 문구가 대본에 포함되고, 기록란이 준비되어 있다 | manual-only | — | ❌ W0 (문서 신설, EXP-04 대본과 결합 가능) | ⬜ pending |
| TBD | TBD | TBD | EXP-02 | — | 참가자 4명(경험자 2+비경험자 2) 모집 완료, 관찰 전용 원칙 준비 | manual-only | — | 해당 없음 (운영) | ⬜ pending |
| TBD | TBD | TBD | EXP-03 | — | 1세션→정확히 1주 간격→2세션 실제 진행, 참석 인원·완주 여부 기록 | manual-only | — | 해당 없음 (운영) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**이 단계의 숨은 보안/견고성 위험은 침입이 아니라 캐싱 불변식 붕괴다.** RESEARCH.md Common Pitfalls #1 —
시나리오 콘텐츠를 `_format_clock_state`에 붙이면서 세션 ID·타임스탬프 등 호출마다 달라지는 값을 실수로
섞으면 프롬프트 캐싱이 매번 깨지고 원가가 3.7배로 뛴다(D-58 무료 모델 제약과 직결). 두 번째 위험은
RESEARCH.md Security Domain V5 — `ClockState`의 신규 `str`/`tuple[str, ...]` 필드가 기본값(빈 문자열)인
채로 프롬프트에 흘러가면 `"위협 시계: : 1/4"` 같은 깨진 문자열이 생길 수 있다.

---

## Wave 0 Requirements

- [ ] `tests/test_prompt_assembly_scenario.py` — 시나리오 콘텐츠가 실제로 프롬프트 텍스트에 반영되고, 같은 칸에서 두 번 호출 시 byte-identical인지 확인. `tests/test_turn_tracer.py`의 기존 `test_classifier_system_prompt_is_byte_identical_across_calls_with_different_text` 패턴 재사용 가능
- [ ] `tests/test_turn_tracer.py` 확장 — `PLACEHOLDER_CLOCK_SEGMENT_COUNT`가 4로 바뀐 뒤에도 기존 트레이서 테스트가 통과하는지, 칸 수 하드코딩이 남아있지 않은지 확인
- [ ] 비경험자 캐릭터 만들기 구두 안내 대본 문서 (신규, 코드 아님) — EXP-04·MEAS-06
- [ ] 손글씨 리캡 템플릿/절차 메모 (신규, 코드 아님) — MEAS-05
- [ ] 관찰 기록 양식(참석 인원·완주 여부·애착 질문 답변·자유 텍스트 마찰 사례) — EXP-02/03, MEAS-06, Phase 6 HYP-04 원천 데이터
- Framework install: 불필요 — 이미 설치됨

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|--------------------|
| 참가자 4명(경험자 2+비경험자 2) 모집, 진행자 개입 없이 관찰만 | EXP-02 | 코드가 할 수 없는 운영 활동 — 실제 사람을 모으는 일 | 사용자가 직접 모집; 세션 중 관찰자(사용자 본인, D-56)가 진행에 개입하지 않았는지 스스로 확인 |
| 1세션(3~4시간) → 정확히 1주 간격 → 2세션(3~4시간) 실제 진행, 참석·완주 여부 기록 | EXP-03 | 실제 시간 경과와 실제 사람 참여가 필요 — 코드로 시뮬레이션 불가 | 세션 종료 후 참석 인원·완주 또는 흐지부지 여부를 관찰자가 주관적으로 기록(D-53, 엄격한 기준 시간 없음) |
| 비경험자 2명이 화면 없이 안내만 받아 30분 안에 캐릭터 생성, 직후 애착 질문 답변 기록 | EXP-04, MEAS-06 | 화면을 만들지 않기로 확정(EXP-04) — 구두 진행 자체가 설계의 일부 | 진행자가 구두 안내 대본을 그대로 읽으며 진행, 소요 시간과 애착 질문 답변을 손으로 기록 |
| 1세션 종료 리캡을 손으로 써서 2세션 시작 시 참가자가 읽고 이어감 | MEAS-05 | 자동 요약은 명시적으로 스코프 밖(D-54, M1 이관) | 관찰자가 세션 직후 3~5줄 요약을 써서 메신저로 공유; 2세션 시작 시 참가자가 이것만 읽고 이어갈 수 있었는지 확인 |
| 세션 도중 OpenRouter 무료 티어 요청 한도(하루 50~1000회, 결제 이력에 따라 다름)로 막히지 않음 | EXP-03 (완주 위협) | 실시간 API 요금제 정책이라 코드로 보증 불가 | 첫 세션 전 드라이런에서 `agents show`로 provider/모델 확인 + 결제 이력 10달러 이상 확보(RESEARCH.md Pitfall 2) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
