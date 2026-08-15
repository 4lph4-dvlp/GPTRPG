---
phase: 11
slug: rulebook-vocabulary
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-15
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
>
> Seeded from `11-RESEARCH.md` § Validation Architecture. The Per-Task Verification Map is
> filled once PLAN.md files exist (`/gsd-validate-phase`).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (`pyproject.toml:51-53` — `[tool.pytest.ini_options]`, `testpaths = ["tests"]`, `asyncio_mode = "auto"`) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_entities.py tests/test_rulebook.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~10-30 seconds (full suite) |

**프론트엔드 주의:** 이 저장소에 프론트엔드 자동 테스트 프레임워크가 없다(`find frontend -iname "*.test.*"` 0건).
RULE-12 성공 기준 2(「완전히 사라진다」)의 화면 쪽 검증은 **서버 응답 계약 테스트**로 커버한다 —
응답 JSON에 해당 축 이름이 문자열로도 등장하지 않는지 단언한다. 프론트엔드 렌더링 자체의
자동 회귀는 Phase 16(프론트엔드 전면 감사) 범위다.

---

## Sampling Rate

- **After every task commit:** Run the task's `-k` filtered command from the map below
- **After every plan wave:** Run `uv run pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green **AND** `import-linter` clean
  (`.importlinter:5-22` contract 1 — `rules_core` must not import
  `time / random / os / socket / datetime / secrets / sqlite3 / asyncio / pathlib / urllib / http`)
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| {N}-01-01 | 01 | 1 | REQ-{XX} | T-{N}-01 / — | {expected secure behavior or "N/A"} | unit | `{command}` | ✅ / ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

### Requirement → Behavior coverage (from RESEARCH.md, pre-plan)

| Req ID | Behavior that must be proven | Test Type | Automated Command |
|--------|------------------------------|-----------|-------------------|
| RULE-11 | 여섯 표현 형태 모두 `StatEntry`로 유효 구성 (형태별 정합성 검증 포함) | unit | `uv run pytest tests/test_entities.py -k form -x` |
| RULE-11 | `STAT_ENTRY_FIELD_NAMES` 고정 시험이 **재고정**된다 (삭제 아님 — D-03) | unit | `uv run pytest tests/test_entities.py -k stat_entry_field_names -x` |
| RULE-12 | `form=="none"` 축이 **서버 응답 자체에서** 제외된다 (축 이름이 JSON에 문자열로도 없다) | integration | `uv run pytest tests/test_web_characters.py -k none_axis_excluded -x` |
| RULE-12 | 「값이 0」 / 「개념 없음」 / 「빠뜨림」 셋이 서로 구분되고 서로 바뀌지 않는다 | unit | `uv run pytest tests/test_entities.py -k zero_vs_absent -x` |
| RULE-12 | 룰북이 자원 축 선언을 빠뜨리면 등록/임포트가 실패한다 (D-02) | unit | `uv run pytest tests/test_rulebook.py -k missing_resource_axes -x` |
| RULE-15 | 판정 트리거 목록이 **빈 것이 정상값** — 등록·조회가 정상 동작한다 | unit | `uv run pytest tests/test_rulebook.py -k empty_move_list_is_valid -x` |
| RULE-15 | 분류기 네 갈래가 후보 개수·no-check 신호·UnknownMove 흡수 조합에서 올바르게 계산된다 | unit | `uv run pytest tests/test_action_classifier.py -k tier -x` |
| QUAL-03 | **기존 두 룰북이 새 등록 검증을 통과한다** (회귀 — D-15 해석의 핵심) | unit | `uv run pytest tests/test_rulebook.py -k existing_rulebooks_pass_validation -x` |
| QUAL-03 | 가려진 밴드(앞 밴드가 완전히 덮음)는 등록 거부 | unit | `uv run pytest tests/test_rulebook.py -k shadowed_band_rejected -x` |
| QUAL-03 | 구멍(어떤 결과값도 못 잡음)은 등록 거부 | unit | `uv run pytest tests/test_rulebook.py -k hole_rejected -x` |
| QUAL-03 | **단순 겹침은 거부되지 않는다** (D-15 해석 회귀) | unit | `uv run pytest tests/test_rulebook.py -k simple_overlap_is_legal -x` |
| D-14 | 세 번째 룰북이 **플랫폼 코드 수정 없이** 데이터만으로 등록된다 | integration | `uv run pytest tests/test_rulebook.py -k third_rulebook -x` |

---

## Wave 0 Requirements

- [ ] `tests/test_rulebook.py` — **신설.** 지금 없다. `grade_for_margin`/`GradeBand`는
      `tests/test_grading_d100.py`에서 d100 판정 경로를 **통해서만** 간접 시험된다.
      QUAL-03의 등록 시점 검증은 판정 경로와 독립적으로 시험해야 한다
- [ ] `tests/test_entities.py` — `test_stat_entry_field_names_are_exactly_four`(25행) ·
      `test_entity_field_names_are_exactly_four`(31행) **재작성**(삭제 아님 — D-03)
- [ ] `tests/test_action_classifier.py` — 네 갈래 tier 시험 추가 (기존 tier 시험 64~88행 옆에)
- [ ] `tests/test_web_characters.py` — **존재 여부 미확인.** 계획 단계가 실제 존재 여부와
      현재 커버리지를 먼저 확인할 것

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 자원 축이 하나도 없는 룰북에서 캐릭터 판이 「고장 난 것처럼」 보이지 않는지 | RULE-12 (성공 기준 2) | 「사람이 오해하지 않는가」는 자동 단언 대상이 아니다 (CONTEXT.md Claude's Discretion) | 축 없는 룰북으로 세션 시작 → 캐릭터 판을 열어 빈 회색 패널이 아니라 의도된 화면이 나오는지 눈으로 확인 |
| 여섯 표현 형태가 화면에 실제로 그려지는지 | RULE-11 | 프론트엔드 자동 테스트 프레임워크가 저장소에 없다 (Phase 16 범위) | 여섯 형태를 각각 쓰는 룰북/캐릭터로 `StatusPane`을 열어 형태별 렌더링 확인 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `import-linter` contract 1 clean (`rules_core` 순수성 유지)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
