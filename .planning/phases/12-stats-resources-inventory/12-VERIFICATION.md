---
phase: 12-stats-resources-inventory
verified: 2026-08-18T15:00:00Z
status: passed
score: 8/8 로드맵 성공 기준 verified (요구사항 16개 전부 SATISFIED)
behavior_unverified: 0
overrides_applied: 0
deferred:
  - truth: "판정 검산 화면(CheckBreakdown.tsx)이 어느 룰북에서든 정확한 합계를 보여준다"
    addressed_in: "Phase 12.2"
    evidence: "ROADMAP.md 'Phase 12.2: 판정 합계를 서버가 보낸다' — CR-02(d100 롤언더에서 자릿수를 그대로 더해 틀린 합계를 보여주는 문제)를 명시적으로 이어받아 새로 만들어진 단계. 현재 실제로 쓰는 룰북(던전월드류, 2d6)에서는 계산이 맞으므로 급하지 않다고 로드맵 자신이 판단함"
  - truth: "서사가 방금 일어난 자원 변화의 뜻을 안다 — 「보이는데 뜻이 없으면 소용없다」"
    addressed_in: "Phase 13.1"
    evidence: ".planning/todos/pending/2026-08-18-narration-blind-to-resource-change.md, ROADMAP.md 'Phase 13.1: GM이 이야기를 이끈다' 본문에 같은 파일이 명시적으로 인용됨"
  - truth: "성공해도 시계가 나빠지는 쪽으로만 기록되지 않는다(진행 시계)"
    addressed_in: "Phase 13.1"
    evidence: ".planning/todos/pending/2026-08-18-no-clock-for-good-progress.md, ROADMAP.md 'Phase 13.1' 본문에 같은 파일이 명시적으로 인용됨"
---

# Phase 12: 능력치 · 자원 변화 · 소지품 Verification Report

**Phase Goal:** 능력치가 판정에 실제로 반영되고, 판정 결과가 자원을 실제로 바꾸며, 소지품이
서사에 실제로 걸린다 — 그리고 그 모든 변화가 사건 기록에 남아 재생된다
**Verified:** 2026-08-18
**Status:** passed
**Re-verification:** No — initial verification

## 결론 먼저

7개 계획(12-01~12-07) 전부가 실제 코드에 반영되어 있고, 로드맵이 정한 성공 기준 8개가
전부 코드·테스트·(사장님이 직접 진행한) 4인 실제 플레이로 확인된다. 파이썬 시험 1138건,
프런트엔드 시험 14건, ruff, import-linter 4개 계약 전부 이 검증 시점에 제가 직접 다시
돌려서 통과를 확인했습니다 — 인계 문서가 주장한 숫자와 일치합니다.

2026-08-18 실제 플레이에서 나온 결함 3건(캐릭터가 안 가진 축을 조용히 깎는 문제, 위협
시계 문구가 항상 "실패"라고 거짓말하는 문제, 재량 판정·소급 선언이 세션을 영구히 깨뜨릴
수 있던 문제)은 커밋 `44ed73f`·`1ad6dcd`·`e851333`으로 고쳐졌고, 셋 다 회귀 시험이
붙어 있는 것을 제가 직접 읽고 실행해 확인했습니다. 코드 리뷰가 남긴 결함 중 CR-02(d100
검산 화면이 틀린 합계를 보여줌)는 새 단계(Phase 12.2)로 정식으로 미뤄졌고, WR-01·IN-01~03은
아직 안 고쳐졌지만 이번 단계의 성공 기준 중 어느 것도 어기지 않는 부수적 결함입니다(아래
"아직 안 고쳐진 것" 절 참조).

**한 가지 확인이 필요한 문제를 발견했습니다:** `.planning/REQUIREMENTS.md`에서 RULE-02·
RULE-03·RULE-04·RULE-05 네 항목이 여전히 `[ ] Pending`으로 표시되어 있는데, 실제로는
12-01 계획에서 전부 구현되고 시험까지 통과한 상태입니다. 아래 "요구사항 대조" 절에서
자세히 다룹니다.

## 목표 달성 — 관찰 가능한 진실 (로드맵 성공 기준 8개)

| # | 성공 기준 | 상태 | 근거 |
|---|---|---|---|
| 1 | 같은 행동이라도 능력치가 높은 캐릭터가 유리하다 — 변환 규칙은 룰북이 선언, 플랫폼 코드에 특정 룰북의 변환식이 안 박힌다 | ✓ VERIFIED | `rules_core/rulebook.py:35` `StatUsage = Literal["add_to_dice_total", "use_as_target"]` + `StatModifierBand`; `rules_core/resolution.py:137` `build_stat_check_input`이 룰북 이름을 모른 채 `StatEntry.current`만으로 `Modifier`/`target`을 조립. `tests/test_resolution_stat_modifier.py` 통과 |
| 2 | 판정 결과가 자원을 실제로 바꾸고, 사건 기록에 남아 재생하면 같은 상태 — 파이썬 상수는 「시작 값」, 지금 값은 기록을 접어 나온다 | ✓ VERIFIED | `event_log/schema.py:19` `EVENT_SCHEMA_VERSION = 8` + `ResourceChanged`(:392); `reducer.py`의 `character_resource_ops`/`resource_change_by_cause` + `resource_changed` 분기(:316-344, 판올림과 같은 커밋 `9c2c348`); `web/routes_characters.py`의 시트 조회가 `resolve_character_stats`로 접은 값을 돌려줌(`tests/test_web_characters.py`) |
| 3 | 결과 카테고리를 닫힌 목록에서 먼저 고른 뒤에야 서술을 쓴다 — 목록 없는 룰북은 재량 판정, 빈 목록이 정상값 | ✓ VERIFIED | `rules_core/rulebook.py`의 `OutcomeCategory`/`OutcomeList`/`NO_CHANGE_CATEGORY_ID`(:203-271); `agents/outcome_picker.py`의 `pick_outcome`이 목록 밖 식별자를 `UnknownOutcomeCategoryFromAI`로 거절, 목록이 비었거나 대가가 안 붙으면 모델을 0회 호출. `tests/test_outcome_picker.py`, `tests/test_rulebook.py` 통과 |
| 4 | 「성공했는가」와 「대가가 붙는가」가 서로 다른 두 축 | ✓ VERIFIED | `GradeBand.succeeded`/`.costs`가 `counts_as_failure`와 독립된 세 번째 칸; 세 룰북 11개 등급이 실제로 채움. `tests/test_rulebook.py::test_succeeded_and_counts_as_failure_can_both_be_true_registration_not_rejected` 통과 |
| 5 | 소지품에 없는 것을 쓰면 재량 판정으로 간다 — 소급 선언을 허용하는 룰북은 비용 축도 선언 | ✓ VERIFIED | `action_classifier.py`의 `Proposal.item_use`(파이썬 `==` 완전 일치 대조); Cairn `CAIRN_RETRO_DECLARATION = RetroDeclarationDecl(allowed=True, cost_axis="Inventory", operation="fill")`. `tests/test_action_classifier.py`, `tests/test_web_actions.py::test_declare_item_not_held_opens_retro_declaration_when_rulebook_allows` 통과. **주의:** 이 경로에서 실제로 발견된 구조적 결함(CR-01, 아래 참조)은 `e851333`으로 고쳐짐 |
| 6 | 캐릭터 시트가 지금 상태를 보여주고, 자원이 크게 깎이면 화면에서 바로 보이며, 최대치를 못 넘는다. AI는 파티 전원의 상태를 본다 | ✓ VERIFIED | `frontend/src/components/ResourceChangeBadge.tsx`의 `changeIntensity` (문턱 상수 없는 연속값, 단조성 시험 `ResourceChangeBadge.test.ts`); `apply_resource_op`의 `max` 자르기(`tests/test_reducer_resource_change.py`); `agents/context.py`의 `TurnContext.party_state`. **사장님이 실제 4-브라우저 플레이로 6번 항목을 직접 PASS 확인**(12-07-SUMMARY.md coverage D1~D5) |
| 7 | 사건 순서가 어긋나면 조용히 안 넘어가고, 형식 표시 빠짐과 진짜 구버전 기록이 구분되며, 세션1 실기록 재생 회귀 픽스처가 있다 | ✓ VERIFIED | `reducer.py`의 `OutOfOrderEvent`, `event_log/schema.py`의 `CorruptEventRecord`; `tests/fixtures/session1_events.jsonl`(895건, 판 2)·`session1_expected_state.json`이 저장소에 커밋됨. `tests/test_event_schema_migration.py -k fixture` 4건을 이번에 직접 실행해 통과 확인(스킵 없이) |
| 8 | 「자원이 얼마나 바뀌는가」 선언 형식이 효과 표현(D7) 첫 원자 연산으로 자랄 수 있는 모양 | ✓ VERIFIED | 12-01이 「축·동작·양」 세 칸 형식을 `delta` 동작 하나로 세우고, 12-02가 같은 형식 위에 `advance`/`fill`/`clear`/`add_tag`/`remove_tag`/`step_down`/`deplete` 일곱을 추가해(`ResourceOperation` 8값) 실제로 자랄 수 있음을 실증. `tests/test_reducer_resource_change.py`의 형태별 시험 통과 |

**점수:** 8/8 로드맵 성공 기준 verified, 행위-미확인(present-but-unverified) 항목 0건.

## 아직 안 고쳐진 것 — 판단 결과

`12-REVIEW.md`(2026-08-18 코드 리뷰)가 남긴 항목 중 이번 검증 시점에도 남아 있는 것:

| ID | 내용 | 이번 단계 성공 기준을 어기는가 | 판단 |
|---|---|---|---|
| WR-01 | 분류기가 AI가 낸 `stat` 이름을 룰북 축 목록과 미리 대조하지 않아, 확인은 됐지만 판정으로 못 나아가는 막다른 선언이 생길 수 있다 | 아니오 — "능력치 없는 캐릭터로 확인하면 400"이라는 12-01의 진짜 요구(조용한 0 방지)는 실제로 지켜진다. 다만 사건이 하나 먼저 기록된 뒤에 막혀, 그 턴을 포기해야 하는 나쁜 UX가 남는다 | 차단 아님. 다음 코드 리뷰나 13.1 이전에 고치는 것을 권장 |
| IN-01 | `usage_die`의 `step_down`이 실제로 내려가는지 검증하지 않는다 | 아니오 — 저장소의 세 룰북 어느 것도 `usage_die` 형태를 아직 선언 안 해, 현재 밟을 수 있는 경로가 없다 | 차단 아님. 그 형태를 쓰는 룰북이 생길 때 함께 |
| IN-02 | `ResourceChangeDecl`/`ResourceOp`가 생성 시점에 `operation` 여덟 값 검사를 안 한다 | 아니오 — 등록 시점(`validate_outcome_list`)과 폴딩 시점(`apply_resource_op`) 두 안전망이 이미 하류에서 걸러낸다 | 차단 아님 |
| IN-03 | 판정 이후 서술 처리 블록이 웹 confirm/proceed·CLI 네 곳에 거의 그대로 중복된다 | 아니오 — 다만 이 중복이 실제로 CR-03(CLI가 웹의 새 방어를 못 따라간 것)의 원인이었다는 것이 리뷰 자체가 지적한 사실 | 차단 아님이지만 구조적 위험. 다음 정리 때 공유 헬퍼로 뽑는 것을 권장 |

**CR-01·CR-02·CR-03의 처리 결과(코드로 직접 재확인):**

- **CR-01**(재량 판정·소급 선언이 문자열 값이 필요한 축에서 세션을 영구히 깨뜨림) —
  `e851333`로 고쳐짐. `web/routes_actions.py:1336-1341`에서 사건을 쓰기 전에
  `resolve_character_stats`를 드라이런으로 불러 `InvalidResourceChange`를 400으로
  앞당긴다. 회귀 시험 `tests/test_reducer_resource_change.py::test_resolve_character_stats_rejects_int_amount_on_a_slot_axis`를 이번에 직접 실행해 통과 확인.
- **CR-02**(`CheckBreakdown.tsx`가 d100 눈을 자릿수 그대로 더해 틀린 합계) — **안 고쳐짐,
  의도적으로.** 코드를 직접 읽어 `rollTotal + modifierTotal` 계산이 그대로 남아 있는 것을
  확인했습니다. `ROADMAP.md`에 새 단계 "Phase 12.2: 판정 합계를 서버가 보낸다"가 이 문제를
  명시적으로 이어받아 생성되어 있어 **정식으로 이연된 것**으로 판단합니다(현재 실제로 쓰는
  던전월드류(2d6)에서는 계산이 맞으므로 사용자가 지금 당장 잘못된 숫자를 보고 있지는
  않습니다).
- **CR-03**(CLI가 웹의 축 소유권 방어를 안 갖고 있음) — `e851333`로 고쳐짐. CLI는 이제
  축 소유 여부를 검증할 수단이 없다는 사실 자체를 인정하고, 결과 목록이 가리키는 자원
  변화를 **적용하지 않고 그 이유를 출력**한다(`cli/turn_flow.py:780-787`, 코드 직접
  확인).

## 요구사항 대조 (RULE-02~10·13·14·16, QUAL-01·02·06, TEST-04 — 16개 전부)

| 요구사항 | 소유 계획 | REQUIREMENTS.md 표시 | 코드 근거 | 판정 |
|---|---|---|---|---|
| RULE-02 | 12-01 | **[ ] Pending** (불일치) | `build_stat_check_input`, `tests/test_resolution_stat_modifier.py` 7건 통과 | SATISFIED — 문서만 안 갱신됨 |
| RULE-03 | 12-01 | **[ ] Pending** (불일치) | `StatUsage`가 `rules_core`에만 있고 룰북 이름·변환식 상수 없음(grep 확인) | SATISFIED — 문서만 안 갱신됨 |
| RULE-04 | 12-01 | **[ ] Pending** (불일치) | `ResourceChanged` 사건 + `reducer.py` 분기, `tests/test_reducer_resource_change.py` | SATISFIED — 문서만 안 갱신됨 |
| RULE-05 | 12-01 | **[ ] Pending** (불일치) | `resource_change.py`가 순수 함수만, AI가 수치를 만드는 경로 없음(층 계약 4개 kept) | SATISFIED — 문서만 안 갱신됨 |
| RULE-06 | 12-01·12-07 | [x] Complete | `_current_stats`/`_current_party_state`가 사건을 접어 반환, `StatusPane` 재폴링 | SATISFIED |
| RULE-07 | 12-07 | [x] Complete | `ResourceChangeBadge`/`changeIntensity`, 사장님 4-브라우저 실측 PASS | SATISFIED (아래 "RULE-07 판단" 참조) |
| RULE-08 | 12-05 | [x] Complete | `TurnContext.party_state`, `tests/test_prompt_assembly_scenario.py` | SATISFIED |
| RULE-09 | 12-01·12-02 | [x] Complete | `ResourceOperation` 8값, 여섯 형태 전부 시험됨 | SATISFIED |
| RULE-10 | 12-06 | [x] Complete | `confirm-resource-change`의 `discretionary` 경로, `tests/test_web_actions.py` | SATISFIED |
| RULE-13 | 12-04·12-06 | [x] Complete | `OutcomeList`/`pick_outcome` | SATISFIED |
| RULE-14 | 12-04 | [x] Complete | `GradeBand.succeeded`/`.costs` | SATISFIED |
| RULE-16 | 12-04·12-06 | [x] Complete | `RetroDeclarationDecl`, `item_use` 대조 | SATISFIED |
| QUAL-01 | 12-02 | [x] Complete | `OutOfOrderEvent` | SATISFIED |
| QUAL-02 | 12-02 | [x] Complete | `CorruptEventRecord` | SATISFIED |
| QUAL-06 | 12-02 | [x] Complete | `apply_resource_op`의 `max` 자르기 | SATISFIED |
| TEST-04 | 12-03 | [x] Complete | `tests/fixtures/session1_*`, CI 상시 회귀 4건 | SATISFIED |

**ORPHANED 요구사항 없음** — 이 단계에 배정된 16개 요구사항이 계획 일곱 개의 `requirements`
필드에 정확히 나뉘어 들어가 있고, REQUIREMENTS.md의 Phase 12 매핑과도 정확히 일치합니다.

### 발견한 문제: RULE-02~05가 완료됐는데 REQUIREMENTS.md에 안 찍혀 있다

`.planning/REQUIREMENTS.md` 78~81행이 RULE-02·RULE-03·RULE-04·RULE-05를 여전히
`[ ]`(Pending)로 표시하고, 336~339행의 표에도 "Pending"으로 남아 있습니다. 그런데:

- 12-01-PLAN.md의 `requirements`에 이 넷이 전부 있고, `must_haves.truths`에 각각의
  진실이 구체적으로 적혀 있습니다.
- 12-01-SUMMARY.md의 `requirements-completed: [RULE-02, RULE-03, RULE-04, RULE-05, RULE-06, RULE-09]`와
  `coverage` 절 D1~D6이 각 요구사항을 실제 통과한 시험 이름과 함께 명시합니다.
- 제가 직접 코드를 읽고 `tests/test_resolution_stat_modifier.py`·
  `tests/test_reducer_resource_change.py`를 확인해 구현이 실재함을 검증했습니다.

`109b6ac` 커밋 메시지를 보면 12-01을 완료 처리하면서 **RULE-09만** "12-02가 나머지를
증명할 때까지 체크 안 함"이라고 명시적으로 남겼습니다 — RULE-02~05에는 그런 유보 사유가
전혀 없습니다. 이후 12-02~12-07의 어떤 커밋도 REQUIREMENTS.md의 이 네 줄을 건드리지
않았습니다(git log로 확인). **단순 누락으로 보입니다.**

이것이 "요구사항 조기 완료 표시" 함정의 반대 방향입니다 — 조기 완료가 아니라 **완료된 것을
못 찍은** 경우입니다. 기능적으로는 문제가 없지만, REQUIREMENTS.md를 근거로 다음 마일스톤
범위를 판단하면 이미 끝난 일을 다시 계획하게 될 위험이 있어 지금 고치는 것을 권장합니다.

### RULE-07을 완료로 둘 것인가 — 직접적인 답

요구사항 문구 그대로("자원이 크게 깎이면 화면에서 바로 보인다")는 **만족됩니다.**
`ResourceChangeBadge`가 실제로 존재하고 문턱 상수 없이 연속값으로 세기를 계산하며,
사장님이 4명 실제 플레이로 "작게/크게 각각 알아챌 수 있는지, 큰 쪽이 더 강한지"를 직접
PASS로 확인했습니다.

사장님이 12-07 확인 관문에서 남긴 더 깊은 판단 — "**보이는데 뜻이 없으면 소용이 없다**"
(방어구가 깎였는데 왜 깎였는지 서사가 말하지 않음) — 은 **RULE-07의 문구가 묻는 것과 다른
질문**입니다. RULE-07은 "보이는가"를 묻고, 그 판단은 "보이는 것이 서사와 이어지는가"를
묻습니다. 이 두 번째 질문은 `.planning/todos/pending/2026-08-18-narration-blind-to-resource-change.md`로
정식으로 기록되어 Phase 13.1이 이어받는 것으로 로드맵에 명시되어 있습니다.

**결론: RULE-07은 Complete로 그대로 두는 것이 맞다고 판단합니다.** 다만 이 서사 단절
문제를 "이미 끝난 일"로 착각하지 않도록, 13.1이 반드시 이 지점부터 시작해야 한다는 것을
이 보고서에 다시 못박습니다.

## 필수 산출물 검증

| 산출물 | 기대 역할 | 상태 | 근거 |
|---|---|---|---|
| `src/gptrpg/rules_core/resource_change.py` | 「축·동작·양」 원자 연산 | ✓ VERIFIED | 존재, 8개 동작 전부 구현, `apply_resource_op`/`resolve_character_stats`/`depleted_axes` 전부 시험됨 |
| `src/gptrpg/rules_core/rulebook.py`의 `StatUsage`/`OutcomeList`/`GradeBand.costs`/`RetroDeclarationDecl` | 룰북 선언 어휘 | ✓ VERIFIED | 세 룰북(dungeonworld_like/openquest/cairn)이 실제로 채운 데이터로 등록 시점 검증을 통과함 |
| `src/gptrpg/event_log/schema.py`의 `ResourceChanged` + `EVENT_SCHEMA_VERSION=8` | 판정 뒤 자원 변화 사건 기록 | ✓ VERIFIED | 판 올리기와 `reducer.py` 분기가 같은 커밋(`9c2c348`)에 있음, 하위 호환 시험 통과 |
| `src/gptrpg/agents/outcome_picker.py` | 결과 카테고리 AI 선택 | ✓ VERIFIED | `pick_outcome`, 목록 밖 거절, 0회 호출 갈래 시험됨 |
| `src/gptrpg/web/routes_actions.py`의 `POST .../confirm-resource-change` | 확인 관문 | ✓ VERIFIED | 신원 대조·멱등·드라이런 검증(CR-01 수정 포함) 전부 코드로 확인 |
| `frontend/src/components/CheckBreakdown.tsx` | 판정 검산 화면 | ⚠️ HOLLOW (부분) | 존재·wired 되어 있으나 d100 룰북에서 계산이 틀림(CR-02) — Phase 12.2로 정식 이연 |
| `frontend/src/components/ResourceChangeBadge.tsx` | 자원 변화 알림 | ✓ VERIFIED | `changeIntensity` 단조성 시험 + 실제 4-브라우저 확인 |
| `tests/fixtures/session1_events.jsonl`/`session1_expected_state.json` | 회귀 픽스처 | ✓ VERIFIED | 저장소에 커밋, CI에서 스킵 없이 4건 실행 확인 |
| `scripts/export_session_fixture.py` | 픽스처 재생성 절차 | ✓ VERIFIED | 존재, 결정적 재생성 확인은 12-03-SUMMARY.md의 수동 확인 절차로 기록됨(diff -q 동일) |

## 핵심 연결(Key Link) 검증

| From | To | Via | 상태 |
|---|---|---|---|
| `Entity.stats` (캐릭터 시작값) | `build_stat_check_input` → `ResolveCheck.stat` → `CheckResolved.modifiers[].source` | `session_actor/actor.py`의 `_prepare_resolve_check` | ✓ WIRED |
| `EVENT_SCHEMA_VERSION=8` | `GameEvent` 유니온 → `reducer.apply_event`의 `resource_changed` 분기 | 같은 커밋 `9c2c348` | ✓ WIRED |
| `GameState.character_resource_ops` | `resolve_character_stats` → `routes_characters.get_character_sheet` | `web/routes_characters.py` | ✓ WIRED |
| `Rulebook.outcome_list` | `pick_outcome` → `confirm()` 응답의 `pending_resource_changes` → `POST confirm-resource-change` | `web/routes_actions.py`, `ChatPane.tsx` | ✓ WIRED |
| `TurnContext.party_state` | `_session_block_text_with_party`(상황판단·서술 전용) / `actor_stats(ctx)`(분류기 전용) | `agents/prompt_assembly.py` | ✓ WIRED (두 갈래가 실제로 분리되어 있음을 코드로 확인) |
| `ConfirmResponse.modifiers`/`.total`/`.target` | `CheckBreakdown` | `frontend/src/panes/ChatPane.tsx` | ⚠️ WIRED but `.total`은 여전히 항상 `null`(12-01의 알려진 갭, 화면이 직접 재계산 — CR-02 원인) |

## 행위 스팟체크 — 이번 검증 시점에 직접 실행

| 검사 | 명령 | 결과 | 상태 |
|---|---|---|---|
| 전체 파이썬 시험 | `.venv/bin/python -m pytest -q` | 1138 passed | ✓ PASS |
| ruff | `.venv/bin/python -m ruff check src tests scripts` | All checks passed | ✓ PASS |
| import-linter | `.venv/bin/lint-imports` | 4 kept, 0 broken | ✓ PASS |
| 프런트 타입체크 | `npx tsc --noEmit` | 오류 없음 | ✓ PASS |
| 프런트 시험 | `npm run test` | 3 files, 14 passed | ✓ PASS |
| 세션1 회귀 픽스처(스킵 없이) | `pytest tests/test_event_schema_migration.py -k fixture` | 4 passed, 0 skipped | ✓ PASS |
| CR-01 회귀 시험 | `pytest tests/test_reducer_resource_change.py::test_resolve_character_stats_rejects_int_amount_on_a_slot_axis` | 1 passed | ✓ PASS |

## 안티패턴 스캔

이번 단계가 건드린 34개 소스 파일(12-REVIEW.md 목록과 동일)에서 `TBD`/`FIXME`/`XXX`/
`TODO`/`HACK`/`PLACEHOLDER` 디버트 마커를 검색했으나 **0건**입니다. `return null` 3곳은
전부 정당한 조건부 렌더링(변화 없음/미확인/`form=="none"` 도달 불가 갈래)이고 서사·데이터가
비어 보이게 만드는 스텁이 아님을 코드 문맥으로 확인했습니다.

## 사람 확인이 필요한 항목

없음. 로드맵 성공 기준 8개 전부가 코드·테스트로 검증되거나, 화면 상호작용이 필요한 부분은
2026-08-18에 사장님이 실제 4-브라우저 플레이로 이미 확인을 마쳤고 그 결과가
12-07-SUMMARY.md의 `coverage` 절에 PASS로 기록되어 있습니다. 제가 이번 검증에서 다시
요구할 새로운 사람 확인 항목은 없습니다.

## 이연 항목(Deferred)

| # | 항목 | 이어받는 단계 | 근거 |
|---|---|---|---|
| 1 | 판정 검산 화면이 어느 룰북에서든 정확하다(d100 포함) | Phase 12.2 | ROADMAP.md에 새 단계로 명시적 생성, CR-02를 직접 인용 |
| 2 | 서사가 자원 변화의 뜻을 안다 | Phase 13.1 | 로드맵 본문이 해당 todo 파일을 직접 인용 |
| 3 | 성공해도 나빠지는 쪽으로만 시계가 도는 문제 | Phase 13.1 | 로드맵 본문이 해당 todo 파일을 직접 인용 |

## 권고 사항 (차단 아님)

1. `.planning/REQUIREMENTS.md`의 RULE-02·RULE-03·RULE-04·RULE-05를 `[x] Complete`로
   갱신하고 336~339행 표도 "Complete"로 맞출 것을 권장합니다 — 구현·시험이 이미 끝나
   있습니다.
2. WR-01(분류기가 AI의 `stat` 값을 미리 검증 안 함)을 다음 코드 리뷰나 13.1 착수 전에
   고치는 것을 권장합니다 — 지금은 플레이어가 막다른 선언에 갇히는 정도지만, 룰북이
   늘어날수록 오타 확률이 늘어납니다.

---

_Verified: 2026-08-18_
_Verifier: Claude (gsd-verifier)_
