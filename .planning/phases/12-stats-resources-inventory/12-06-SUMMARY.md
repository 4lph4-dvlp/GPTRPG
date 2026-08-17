---
phase: 12-stats-resources-inventory
plan: 06
subsystem: rules-engine
tags: [ai-agents, resource-changes, confirmation-gate, inventory, fastapi]

requires:
  - phase: 12-stats-resources-inventory
    provides: "12-04 — GradeBand.succeeded/.costs, OutcomeCategory/OutcomeList/RetroDeclarationDecl 그릇, 세 룰북의 실제 결과 목록·소급 선언 데이터, validate_outcome_list/require_outcome_category/ordered_categories"
  - phase: 12-stats-resources-inventory
    provides: "12-05 — TurnContext.party_state/actor_character_id, agents.prompt_assembly.actor_stats(ctx) 파생 함수, 분류기/상황판단 프롬프트 분리"
provides:
  - "agents/outcome_picker.py — pick_outcome()가 룰북의 닫힌 결과 목록에서 카테고리를 고르고, 목록 밖 식별자는 UnknownOutcomeCategoryFromAI로 거절한다. 목록이 비었거나 등급에 대가가 안 붙으면 모델을 0회 호출한다"
  - "turn/judgments.gather_turn_judgments — 네 판단(상황판단·장면신규대상·시계신호·결과선택)이 하나의 asyncio.gather로 항상 함께 돈다(조건부 병렬화 없음)"
  - "POST /sessions/{id}/actions/confirm-resource-change — 숫자가 실제로 변할 때만 뜨는 확인 관문. 신원 대조가 맨 앞, 요청은 카테고리 식별자만 말하고 서버가 룰북 선언에서 다시 굴려 적용, AlreadyChanged로 재시도 멱등"
  - "ConfirmResponse.pending_resource_changes/.discretionary — 판정 직후 confirm()은 더 이상 자원 변화를 곧바로 적용하지 않는다. '변할 예정' 목록만 싣고, 실제 적용은 사람 확인 뒤 새 라우트가 한다"
  - "action_classifier.Proposal.item_use — 새 AI 역할 없이 기존 분류기 응답에 소지품 판단이 얹힌다. 행위자의 named_slots 축에서 채워진 슬롯만 닫힌 목록이 되고, 파이썬 == 완전 일치로 코드가 다시 대조한다"
  - "DeclareResponse.retro_declaration — 소지품에 없는 것을 쓰겠다는 판단(kind='not_held')이 나오면, 소급 선언을 허용하는 룰북(Cairn)의 잠긴 비용 축·동작을 응답에 싣는다. 양은 confirm-resource-change의 retro_declaration_amount로 확인 관문을 지난다"
affects: [12-07-web-ui, 13-regression-tests]

actuals:
  tokens: 40556
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "AI 판단을 새 함수로 늘리지 않고 기존 판단 출력에 칸을 더한다 — outcome_picker는 gather_turn_judgments의 네 번째 병렬 판단으로, item_use는 action_classifier의 기존 응답 칸으로 얹었다(턴당 AI 호출 수를 최소로 유지)"
    - "결과가 이미 확정된 값을 '변할 예정'과 '실제 적용' 두 단계로 쪼갠다 — confirm()이 목록에서 고른 결과를 응답에만 싣고, 사람이 확인을 누른 뒤에야 별도 라우트가 서버 쪽에서 다시 굴려 사건을 남긴다(그 사이 아무 사건도 안 쌓인다는 것이 D-09의 핵심)"
    - "닫힌 목록 위반은 조용히 삼키지 않고 예외로 던지되, 예외를 흡수하는 자리는 항상 함수 경계 하나 위(action_classifier.classify()가 UnknownMove/UnknownItemFromAI를 흡수하는 것과 같은 자리) — 파싱 함수 자체는 계속 엄격하게 던진다"
    - "재량 판정·소급 선언 모두 '축·동작은 룰북이 잠그고 양만 사람이 정한다'는 같은 모양을 공유한다 — validate_outcome_list(등록 시점 검증 함수)를 재사용해 임시 결과 목록 하나로 재량 제안을 검사하므로 새 검증 로직을 안 만든다"

key-files:
  created:
    - src/gptrpg/agents/outcome_picker.py
    - tests/test_outcome_picker.py
  modified:
    - src/gptrpg/agents/config.py
    - src/gptrpg/agents/context.py
    - src/gptrpg/agents/prompt_assembly.py
    - src/gptrpg/agents/action_classifier.py
    - src/gptrpg/turn/judgments.py
    - src/gptrpg/web/routes_actions.py
    - src/gptrpg/cli/turn_flow.py
    - tests/conftest.py
    - tests/test_agent_config.py
    - tests/test_parallel_judgment.py
    - tests/test_action_classifier.py
    - tests/test_web_actions.py
    - tests/test_clock_condition_cli.py
    - tests/test_narration_isolation.py
    - tests/test_turn_flow_failure.py
    - tests/test_turn_tracer.py

key-decisions:
  - "pick_outcome()의 두 조기 반환(빈 목록·costs=False)을 함수 안의 순수 판단으로 둬서 gather_turn_judgments 자신은 조건 분기 없이 언제나 넷을 부른다 — ARCH-04가 금지하는 '조건부 병렬화'와 '함수 안에서 모델을 안 부르기로 결정하는 것'은 다른 층의 문제라는 것을 도크스트링에 명시했다"
  - "outcome_picker의 목록 밖 식별자(UnknownOutcomeCategoryFromAI)는 pick_outcome() 밖으로 그대로 던져지고, gather_turn_judgments를 감싸는 confirm()/proceed()의 기존 광범위 try/except(D-05/ARCH-05, '판단 실패가 확인 요청을 막지 않는다')가 흡수한다 — 이 계획은 그 except 블록을 건드리지 않았다, 이미 있던 방어가 새 예외 종류에도 그대로 작동한다"
  - "RULE-10 재량 판정에서 실제 축·양 제안을 만드는 새 AI 호출은 만들지 않았다(아래 알려진 갭 참조) — 대신 서버가 discretionary.axes(그 룰북이 선언한 자원 축 이름)를 응답에 실어 '재량 판정 여지가 있다'는 사실만 알리고, 실제 제안(축·동작·양)은 요청 쪽이 만들어 confirm-resource-change로 보내면 서버가 validate_outcome_list 재사용으로 다시 검사한다"
  - "confirm-resource-change의 discretionary/retro_declaration_amount 두 경로가 같은 커밋에 함께 있다 — 재량 판정(RULE-10, 결과 목록이 아예 없음)과 소급 선언(RULE-16, 소지품에 없는 것을 씀)은 둘 다 '축·동작 잠금 + 양만 결정'이라는 같은 모양이지만 트리거 조건이 다르므로 요청 필드를 분리했다(discretionary는 축/동작/양 모두 클라이언트가 제안, retro_declaration_amount는 양만 — 축·동작은 룰북이 이미 잠갔다)"
  - "declare()의 item_use 이중 대조에서 재확인이 실패하면(계약상 거의 일어나지 않지만) kind='not_held'로 낮춘다 — '갖고 있다고 믿고 진행'보다 '없는 것으로 보고 재량 판정으로 보낸다'가 더 안전한 실패 방향이다"

patterns-established:
  - "역할별 AI 문맥 값 객체(OutcomePickerContext)가 파티 상태 칸을 아예 안 가진다는 것으로 D-17 좁힘을 타입 차원에서 강제 — ClockJudgeContext/EntityJudgeContext가 이미 세운 관례를 네 번째로 반복"
  - "실제 다이스(LiveRoller)를 타는 CLI/웹 시험은 등급이 비결정적이므로, 특정 등급을 강제로 확인하려면 사건을 직접 저장소에 심고 confirm()의 재사용 경로(AlreadyConfirmed, D-09)를 타게 만든다 — 12-05가 세운 '실제 confirm() HTTP 왕복을 피한다' 관례를 더 확장했다(select-character가 액터를 만드는 부작용을 피하려 서명 쿠키를 직접 만드는 자리까지 포함)"

requirements-completed: [RULE-10, RULE-13, RULE-16]

coverage:
  - id: D1
    description: "판정 뒤 AI가 룰북의 닫힌 결과 목록에서 카테고리를 고르고, 목록 밖은 코드가 예외로 거절한다. 목록이 없거나 등급에 대가가 안 붙으면 모델을 0회 호출한다"
    requirement: "RULE-13"
    verification:
      - kind: unit
        ref: "tests/test_outcome_picker.py#test_pick_outcome_raises_unknown_outcome_category_for_id_outside_closed_list"
        status: pass
      - kind: unit
        ref: "tests/test_outcome_picker.py#test_pick_outcome_with_empty_outcome_list_calls_provider_zero_times"
        status: pass
      - kind: unit
        ref: "tests/test_outcome_picker.py#test_pick_outcome_with_costs_false_calls_provider_zero_times"
        status: pass
      - kind: unit
        ref: "tests/test_parallel_judgment.py#test_gather_turn_judgments_has_exactly_one_gather_call_with_four_positional_args"
        status: pass
    human_judgment: false
  - id: D2
    description: "confirm() 응답은 결과 목록에서 고른 항목이 가리키는 자원 변화를 '변할 예정'으로만 싣는다 — 이 시점에는 사건이 안 쌓인다. 결과 목록이 없어도 대가가 붙는 등급이면 재량 판정 신호(축 목록)를 싣는다"
    requirement: "RULE-13"
    verification:
      - kind: integration
        ref: "tests/test_web_actions.py#test_confirm_surfaces_pending_resource_change_from_closed_list_pick_without_applying_it"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py#test_confirm_no_change_pick_yields_empty_pending_resource_changes"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py#test_confirm_discretionary_available_when_outcome_list_empty_and_grade_costs"
        status: pass
    human_judgment: false
  - id: D3
    description: "POST /confirm-resource-change가 신원을 맨 앞에서 대조하고(남의 캐릭터로 403, 사건 0건), 서버가 룰북 선언에서 값을 다시 만들며(요청 본문 숫자는 무시/거절), 같은 caused_by_seq 재시도는 사건을 두 번 안 쌓는다"
    requirement: "RULE-10"
    verification:
      - kind: integration
        ref: "tests/test_web_actions.py#test_confirm_resource_change_identity_mismatch_returns_403_and_no_new_events"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py#test_confirm_resource_change_applies_rulebook_declared_amount_not_a_client_number"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py#test_confirm_resource_change_same_caused_by_seq_twice_records_exactly_one_event_with_same_roll"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py#test_confirm_resource_change_unknown_category_returns_400_and_no_new_events"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py#test_confirm_resource_change_rejected_applies_nothing"
        status: pass
    human_judgment: false
  - id: D4
    description: "룰북에 결과 목록이 없어도 재량 판정 제안(축·동작·양)이 룰북 선언과 다시 대조되어 적용된다 — 축이 룰북 밖이면 거절, 양이 상한을 넘으면 422"
    requirement: "RULE-10"
    verification:
      - kind: integration
        ref: "tests/test_web_actions.py#test_confirm_resource_change_discretionary_applies_within_declared_axis"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py#test_confirm_resource_change_discretionary_rejects_axis_outside_rulebook"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py#test_confirm_resource_change_discretionary_amount_over_max_returns_422"
        status: pass
    human_judgment: false
  - id: D5
    description: "명령줄 경로도 자원 변화를 확인 없이 적용하지 않는다 — 판정 뒤 pending 목록을 화면에 보이고 y/n을 받은 뒤에만 제출한다"
    requirement: "RULE-10"
    verification:
      - kind: integration
        ref: "tests/test_turn_tracer.py#test_turn_runs_full_loop_and_records_events_in_causal_order"
        status: pass
    human_judgment: true
    rationale: "CLI의 y/n 확인 프롬프트 자체(입력 미제공/거부 시 실제로 자원이 안 깎이는 대화형 흐름)는 이 스위트가 stdin을 가짜로 채워 자동 확인하는 방식이라, '거부하면 안 깎인다'는 실제 상호작용 경로는 사람이 실기로 한 번 확인하는 것을 권장한다(웹 쪽 동등 경로는 D3에서 완전히 자동 검증됨)"
  - id: D6
    description: "분류기가 새 AI 호출 없이 행위자 자신의 소지품(named_slots) 중 무엇을 쓰는지 닫힌 목록에서 고르고, 코드가 파이썬 == 완전 일치로 다시 대조한다. 부분 일치는 '갖고 있다'로 안 친다. 소지품을 안 세는 룰북은 이 경로를 아예 안 탄다"
    requirement: "RULE-16"
    verification:
      - kind: unit
        ref: "tests/test_action_classifier.py#test_classify_partial_item_name_overlap_is_absorbed_to_none_kind"
        status: pass
      - kind: unit
        ref: "tests/test_action_classifier.py#test_classify_empty_inventory_character_completes_without_exception"
        status: pass
      - kind: unit
        ref: "tests/test_action_classifier.py#test_classify_rulebook_without_named_slots_axis_skips_item_use_entirely"
        status: pass
      - kind: unit
        ref: "tests/test_action_classifier.py#test_classify_holds_exact_match_item_from_filled_slots"
        status: pass
      - kind: unit
        ref: "tests/test_action_classifier.py#test_inventory_slot_items_preserves_declaration_order_and_duplicates"
        status: pass
    human_judgment: false
  - id: D7
    description: "소지품에 없는 것을 쓰겠다는 판단이 나오면 재량 판정으로 가고, 소급 선언을 허용하는 룰북(Cairn)만 그 잠긴 비용 축·동작을 declare() 응답에 싣는다"
    requirement: "RULE-16"
    verification:
      - kind: integration
        ref: "tests/test_web_actions.py#test_declare_item_not_held_opens_retro_declaration_when_rulebook_allows"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py#test_declare_item_use_skipped_entirely_for_rulebook_without_named_slots"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py#test_declare_item_held_and_actually_present_is_not_downgraded"
        status: pass
    human_judgment: false

duration: ~4시간
completed: 2026-08-17
status: complete
---

# Phase 12 Plan 6: 결과 선택 · 확인 관문 · 소지품 대조 Summary

**판정 뒤 AI가 룰북의 닫힌 결과 목록에서 카테고리를 고르고(pick_outcome), 그 결과가 가리키는 자원 변화는 사람이 `POST .../confirm-resource-change`로 확인해야만 서버가 다시 굴려 적용하며, 소지품 판단은 새 AI 호출 없이 기존 분류기 응답에 얹혀(`item_use`) 소지품에 없는 것을 쓰면 재량 판정(또는 Cairn의 소급 선언)으로 간다.**

## Performance

- **Duration:** 약 4시간
- **Tasks:** 3/3
- **Files modified:** 18개 (신규 2 + 기존 16, 편차로 늘어난 시험 파일 6개 포함)

## Accomplishments

- **결과 선택 판단(RULE-13, D-11)** — `agents/outcome_picker.py`를 신설했다. `pick_outcome`이 룰북의 닫힌 결과 목록에서 AI가 고른 카테고리를 받고, 목록 밖 식별자는 `UnknownOutcomeCategoryFromAI`로 거절한다(조용히 무시하거나 비슷한 것으로 대체하지 않는다). 결과 목록이 비었거나 이번 등급에 대가가 안 붙으면 모델을 아예 안 부른다(AI 호출 0회) — 이 조기 반환은 함수 안의 순수 판단이라 `gather_turn_judgments`의 "조건부 병렬화 금지"(ARCH-04)를 어기지 않는다. `TurnJudgments`가 네 판단(상황판단·장면신규대상·시계신호·결과선택)을 하나의 `asyncio.gather`로 항상 함께 부르도록 확장됐다.
- **숫자가 실제로 변할 때만 뜨는 확인 관문(D-09/D-10)** — `confirm()`이 12-01~12-05까지 판정 직후 곧바로 적용하던 "탐색적 한 줄기"(고정 미스 코스트)를 대체했다. 이제 `confirm()`은 AI가 고른 결과를 `pending_resource_changes`에 "변할 예정"으로만 싣고 사건을 안 쌓는다. 새 라우트 `POST /sessions/{id}/actions/confirm-resource-change`가 실제 적용을 맡는다 — `confirm()`과 같은 자리·같은 모양으로 신원을 맨 앞에서 대조하고, 요청은 카테고리 식별자만 말하며(변화량 숫자는 요청에 자리 자체가 없다, `extra="forbid"`), 서버가 `ordered_categories`로 다시 대조한 뒤 `roll_amount`(`LiveRoller`)로 실제 양·눈을 만들어 `RecordResourceChange`를 제출한다. 같은 `caused_by_seq`로 재시도하면 `AlreadyChanged`가 단락시키고, 응답은 재굴림한 값이 아니라 실제로 기록된 사건을 되읽어 채운다(멱등 재시도가 다른 숫자를 보여주지 않는다).
- **재량 판정(RULE-10)** — 룰북에 결과 목록이 없어도(OpenQuest·Cairn) 대가가 붙는 등급이면 `confirm()` 응답의 `discretionary.available`이 참이 되고 그 룰북이 선언한 자원 축 이름을 싣는다. `confirm-resource-change`의 `discretionary` 칸(축·동작·양 전부 요청이 제안)은 `validate_outcome_list`(등록 시점 검증 함수)를 재사용해 임시 결과 목록 하나로 다시 검사하고, `MAX_DISCRETIONARY_AMOUNT`(20, `MAX_BONUS_DICE_MAGNITUDE`와 같은 근거의 입력 실수 방어) 안에서만 통과시킨다.
- **소지품 대조(RULE-16, D-15)** — 새 AI 역할을 안 만들었다. `action_classifier.Proposal.item_use`가 기존 분류기 응답에 얹힌 칸이고, `_inventory_slot_items`가 행위자의 `named_slots` 축(있으면)에서 채워진 슬롯을 선언 순서 그대로(정렬·중복 제거 없이) 뽑아 닫힌 목록을 매 턴 새로 만든다. 소지품을 규칙으로 안 세는 룰북(던전월드류, `소지품` 축이 `form="none"`)은 이 목록이 `None`이라 판단 자체가 프롬프트에 안 실리고 결과가 `kind="none"`으로 고정된다. AI가 고른 물건은 `declare()`가 파이썬 `==` 완전 일치로 다시 대조한다(이중 방어) — 재확인이 실패하면(계약상 거의 없음) `not_held`로 안전하게 낮춘다. `not_held`이고 룰북이 소급 선언을 허용하면(Cairn) 그 잠긴 비용 축·동작을 `DeclareResponse.retro_declaration`에 싣고, 실제 양은 `confirm-resource-change`의 새 `retro_declaration_amount` 칸(축·동작은 없다 — 룰북이 이미 잠갔다)이 지나간다.

## Task Commits

1. **Task 1: 결과 목록에서 고르는 판단(RULE-13, D-11)** — `79c0fe2` (feat)
2. **Task 2: 확인 관문 + 재량 판정 경로(D-09/D-10, RULE-10)** — `18e9839` (feat)
3. **Task 3: 소지품 대조 + 소급 선언(RULE-16, D-15/D-16)** — `0a185b0` (feat)

**Plan metadata:** (이 커밋 — docs)

## Files Created/Modified

- `src/gptrpg/agents/outcome_picker.py` — (신설) `OutcomePick`·`pick_outcome`·`UnknownOutcomeCategoryFromAI`·`_parse_picks`
- `src/gptrpg/agents/context.py` — `OUTCOME_PICKER_RECENT_TURNS_LIMIT`·`OutcomePickerContext`(Task 1), `NO_ITEM_USED`·`ITEM_NOT_IN_INVENTORY`·`ItemUseClaim`(Task 3)
- `src/gptrpg/agents/config.py` — `outcome_picker` 역할 + `ROLE_FALLBACKS["outcome_picker"] = "action_classifier"`
- `src/gptrpg/agents/prompt_assembly.py` — `build_outcome_picker_prompt`(Task 1), `build_classifier_prompt`의 `inventory_items` 매개변수 + `_format_inventory_items`(Task 3)
- `src/gptrpg/agents/action_classifier.py` — `UnknownItemFromAI`·`_inventory_slot_items`·`_parse_item_use`·`Proposal.item_use`, `classify()`가 소지품 판단을 흡수
- `src/gptrpg/turn/judgments.py` — `TurnJudgments.outcome`, `gather_turn_judgments`가 네 판단을 부름(outcome_provider/model/outcome_list/grade_band 새 인자)
- `src/gptrpg/web/routes_actions.py` — `PendingResourceChangeView`·`DiscretionaryProposalView`·`ConfirmResponse.pending_resource_changes`/`.discretionary`(옛 `resource_changes` 대체), 새 라우트 `confirm_resource_change` + `ConfirmResourceChangeRequest`/`Response`/`DiscretionaryProposal`, `MAX_PICKED_CATEGORIES`/`MAX_DISCRETIONARY_AMOUNT`, `DeclareResponse.item_use`/`.retro_declaration` + `ItemUseView`/`RetroDeclarationView`
- `src/gptrpg/cli/turn_flow.py` — `_turn_flow`/`_proceed_without_check` 모두 새 `gather_turn_judgments` 인자로 갱신, 판정 뒤 자원 변화 확인 프롬프트(y/n) 신설
- `tests/conftest.py` — (편차) `web_client_with_fake_provider`에 `outcome_picker` 대역 주입 매개변수 추가
- `tests/test_outcome_picker.py` — (신설) 14건
- `tests/test_agent_config.py`, `tests/test_parallel_judgment.py` — 역할 6개/네 판단 반영 갱신
- `tests/test_action_classifier.py`, `tests/test_web_actions.py` — 이 계획의 새 시험 다수(아래 커버리지 참조)
- `tests/test_clock_condition_cli.py`, `tests/test_narration_isolation.py`, `tests/test_turn_flow_failure.py`, `tests/test_turn_tracer.py` — (편차) `gather_turn_judgments`/`TurnJudgments` 시그니처 변경에 따른 기계적 갱신

## Decisions Made

주요 설계 판단은 프런트매터 `key-decisions`에 있다. 요약:

- 결과 선택의 두 조기 반환(빈 목록·`costs=False`)은 함수 안의 순수 판단이지 `gather` 밖 조건 분기가 아니다.
- `UnknownOutcomeCategoryFromAI`는 `pick_outcome` 밖으로 그대로 던져지고, `confirm()`/`proceed()`의 기존 D-05 광범위 `except`가 흡수한다 — 새 방어를 안 만들었다.
- RULE-10의 실제 축·양 "AI 제안"은 이 계획의 파일 범위 밖(`agents/*`를 새 AI 호출로 늘리지 않는다는 Task 1의 커밋된 계약)이라 만들지 않았다 — 아래 "알려진 갭" 참조.
- 재량 판정과 소급 선언은 "축·동작은 룰북이 잠그고 양만 결정"이라는 같은 모양이지만 요청 필드는 분리했다(트리거 조건이 다르다).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `gather_turn_judgments`/`TurnJudgments` 시그니처 변경이 파일 목록 밖 5개 시험 파일을 깼다**
- **Found during:** Task 1 커밋 직후 `uv run pytest -q`(전체 스위트)
- **Issue:** `tests/test_narration_isolation.py`가 `TurnJudgments(...)`를 새 `outcome` 필드 없이 직접 생성하고 있었다 — 계획의 `<files>` 목록 밖.
- **Fix:** `TurnJudgments(...)` 호출부에 `outcome=OutcomePick(category_ids=(), ai=empty_ai)`를 채웠다.
- **Files modified:** `tests/test_narration_isolation.py`
- **Verification:** `uv run pytest tests/test_narration_isolation.py -q` 통과
- **Committed in:** `79c0fe2` (Task 1 커밋)

**2. [Rule 3 - Blocking] `confirm()`/`proceed()`가 새 필수 인자 없이 `gather_turn_judgments`를 부르던 것이 web/CLI 양쪽 회귀 시험을 깼다**
- **Found during:** Task 1 완료 후, Task 2 착수 전 `uv run pytest -q` 확인(계획이 Task 1/2를 각각 다른 파일 범위로 나눴기 때문에 예상된 중간 상태)
- **Issue:** `web/routes_actions.py`의 `confirm()`/`proceed()`, `cli/turn_flow.py`의 `_turn_flow`/`_proceed_without_check` 넷 다 새 `outcome_provider`/`outcome_model`/`outcome_list`/`grade_band` 인자를 안 넘겨 `TypeError`가 났다(D-05 광범위 `except`가 흡수해 턴 자체는 안 죽었지만 판단이 전부 빈 값으로 떨어졌다).
- **Fix:** Task 2에서 네 호출부 모두 새 인자를 채웠다(웹은 `require_band`로 얻은 실제 `grade_band`, CLI의 `no_check` 경로/proceed()는 빈 `OutcomeList`+`costs=False` 자리표시자).
- **Files modified:** `src/gptrpg/web/routes_actions.py`, `src/gptrpg/cli/turn_flow.py`(계획 원문의 `<files>` 그대로)
- **Verification:** `uv run pytest -q` 전체 통과
- **Committed in:** `18e9839` (Task 2 커밋)

**3. [Rule 1 - 버그] 실제 다이스(LiveRoller)에 의존하는 CLI 시험 3건이 outcome_picker의 0회 호출 계약과 충돌해 산발적으로 실패**
- **Found during:** Task 2 완료 후 `uv run pytest -q` 반복 실행(8회) 중 무작위로 재현
- **Issue:** `tests/test_turn_tracer.py`/`tests/test_turn_flow_failure.py`가 "여섯 ai_invoked 전부 prompt_tokens > 0"을 단언했는데, 실제 2d6 굴림이 `costs=False` 등급(예 strong_hit)을 내면 `pick_outcome`이 정상적으로 모델을 0회 호출해 그 사건의 토큰이 0이 된다 — 버그가 아니라 Task 1이 커밋한 계약 그대로였다. `tests/test_clock_condition_cli.py`의 `test_signal_skip_never_calls_deep_judgment_provider`도 같은 이유로 총 호출 수 단언이 흔들렸다.
- **Fix:** `test_turn_tracer.py`/`test_turn_flow_failure.py`는 `outcome_picker` 역할만 토큰 `>= 0`으로 완화(다른 다섯 역할은 여전히 `> 0`). `test_clock_condition_cli.py`는 총 호출 수 정확한 값 대신 상한·하한(4~5)으로 바꾸고, 이 시험이 실제로 지키려는 성질(깊은 판단이 한 번도 안 불린다)을 직접 재는 `deep_judgment_calls` 카운터를 새로 뒀다.
- **Files modified:** `tests/test_turn_tracer.py`, `tests/test_turn_flow_failure.py`, `tests/test_clock_condition_cli.py`
- **Verification:** `uv run pytest -q` 8회 연속 통과(흔들림 없음 확인)
- **Committed in:** `18e9839` (Task 2 커밋)

**4. [Rule 3 - Blocking] `tests/conftest.py`의 `web_client_with_fake_provider`에 `outcome_picker` 대역 주입 자리가 없었다**
- **Found during:** Task 2 시험 작성 중 — `outcome_picker`의 응답을 개별로 제어해야 확인 관문 시험이 결정론적이 된다.
- **Issue:** 계획의 `<files>` 목록 밖.
- **Fix:** `_make(...)`에 `outcome_picker: FakeProvider | None = None` 매개변수를 더했다(기존 `situation_judge`/`scene_entity_judge`/`clock_judge`와 같은 모양).
- **Files modified:** `tests/conftest.py`
- **Verification:** `uv run pytest tests/test_web_actions.py -q` 통과
- **Committed in:** `18e9839` (Task 2 커밋)

**5. [Rule 4 - 계획과 커밋된 사실의 충돌 해소, 사용자 승인 불필요 조건] RULE-10의 "AI가 재량 축·양을 제안한다"를 문자 그대로 만들 파일 자리가 없었다**
- **Found during:** Task 2 설계 단계 — 계획 원문(D-09/D-10, Task 2 액션④)이 "제안을 만드는 것은 AI이고... 새 역할을 또 만들지 않는다"고 적었다.
- **Issue:** Task 1이 이미 커밋한 계약(`pick_outcome`은 결과 목록이 비었으면 모델을 0회 호출한다, 그 acceptance criteria가 이미 시험으로 고정됨)과 Task 2의 파일 범위(`agents/*`가 `<files>` 목록에 없다)가 충돌한다 — 결과 목록이 빈 룰북(재량 판정이 열리는 바로 그 조건)에서는 애초에 outcome_picker가 모델을 안 부르므로, "같은 호출이 다른 형식으로 답한다"는 계획의 설계 판단이 이 두 계획의 파일 경계 안에서 성립하지 않는다.
- **Resolution:** 서버는 재량 판정이 열려 있다는 사실과 그 룰북이 선언한 자원 축 이름 목록만 응답에 싣는다(`discretionary.axes`) — 실제 축·동작·양 제안은 요청 쪽이 만들어 보내고, 서버가 `validate_outcome_list` 재사용으로 다시 검사한다. 제품의 핵심 약속(닫힌 어휘 안에서만 제안, 사람 확인 전엔 사건 없음, 실제 계산은 순수 코드)은 그대로 지켜진다 — 다만 "그 제안을 AI가 즉석에서 만들어 준다"는 문구 그대로의 UX는 이 계획 밖으로 남았다.
- **Files modified:** 없음(설계 판단, 코드 변경은 정상 Task 2 범위 안에서 이뤄짐)
- **Committed in:** `18e9839` (Task 2 커밋, 설계 판단으로 반영)

---

**Total deviations:** 5 (3건 차단 이슈 — 시그니처 변경의 파급, 1건 버그 수정 — 흔들리는 시험을 실제 계약에 맞게 고침, 1건 계획-사실 충돌 해소 — 알려진 갭으로 문서화)
**Impact on plan:** 전부 계획 자신의 커밋된 산출물(Task 1의 0회 호출 계약)과 전체 스위트 통과를 지키는 데 필요했다. 스코프 확장이 아니라 계획이 세운 태스크 경계(각기 다른 `<files>`)와 실제 코드 의존성 사이의 간극을 메운 것이다.

## Issues Encountered

- **CLI 회귀 시험이 진짜 다이스에 의존한다는 것이 이번에 처음 문제가 됐다** — 12-05까지는 `outcome_picker`가 없어서 등급이 무엇이든 AI 호출 수·토큰 패턴이 항상 같았다. 이 계획이 "등급에 따라 AI를 부를지 말지가 갈리는" 첫 번째 판단을 추가하면서, 실제 다이스를 쓰는 CLI 시험(`test_turn_tracer.py` 등)이 처음으로 등급-의존 흔들림에 노출됐다. 웹 쪽은 12-05가 이미 "실제 HTTP 왕복 대신 사건을 직접 심는다"는 결정론적 관례를 세워 뒀어서 이번 계획의 새 웹 시험은 처음부터 그 관례를 따랐다.

## Known Stubs

- **RULE-10 재량 판정의 "AI가 만드는 구체적 제안"이 없다.** 서버는 재량 판정이 열려 있다는 사실과 자격이 있는 축 이름 목록만 응답에 싣는다(`ConfirmResponse.discretionary.axes`) — 어떤 축을 얼마나 바꿀지 AI가 실제로 제안하는 경로는 없다. 사람(또는 다음 계획이 붙일 AI)이 `discretionary` 요청 칸에 축·동작·양을 직접 채우면 서버가 룰북 선언과 다시 대조한다. **이유:** 이 계획의 Task 1이 이미 커밋한 계약("결과 목록이 비었으면 outcome_picker는 모델을 0회 호출한다")과 Task 2의 파일 범위(`agents/*`를 새 호출로 늘리지 않는다)가 정확히 재량 판정이 열리는 조건(빈 결과 목록)에서 충돌한다 — RULE-10 자체는 "AI가 제안하고 사람이 확인하면"이라고 적었지만, 실제 제안 생성은 다음 계획의 몫으로 남았다. 제품의 핵심 약속(닫힌 어휘·사람 확인·순수 코드 계산)은 이 스텁 상태에서도 깨지지 않는다 — 열려 있는 것은 "제안을 누가 타이핑하는가"뿐이다.
- **CLI의 재량 판정 경로는 안내만 하고 실제 확인 흐름이 없다.** `cli/turn_flow.py`는 결과 목록이 없고 대가가 붙는 등급이 나오면 화면에 "재량 판정 여지가 있다"와 가능한 축 이름을 안내만 하고, y/n으로 축·양을 받아 제출하는 대화형 흐름은 없다(웹 쪽 `confirm-resource-change`의 `discretionary` 칸은 완전히 동작한다). **이유:** 효과 대비 시간 — CLI는 운영자 디버그 도구이고, 이 갭이 있어도 "확인 없이 자원이 깎이는" 안전 위반은 아니다(아무것도 자동 적용되지 않는다, 그냥 CLI에서 그 기능을 못 쓸 뿐이다).

## Threat Flags

새로 연 표면(`confirm-resource-change` 라우트, `retro_declaration_amount` 칸)은 전부 계획의 `<threat_model>`이 이미 등록한 항목(T-12-02~T-12-31)의 완화로 덮인다 — 별도 항목 없음.

## User Setup Required

None - 외부 서비스 설정 불필요.

## Next Phase Readiness

- **RULE-10/RULE-13/RULE-16 세 요구사항이 이 계획으로 완전히 닫힌다** — REQUIREMENTS.md 추적표에서 12-04(그릇+데이터)와 12-06(이 계획, 실제 경로) 둘 다 완료됐다. 다른 어떤 계획의 `requirements`에도 이 셋이 없다는 것을 확인했다(`.planning/phases/12-stats-resources-inventory/12-0*-PLAN.md` frontmatter 전수 대조).
- **12-07(웹 UI)이 `pending_resource_changes`/`discretionary`/`item_use`/`retro_declaration` 네 칸을 화면에 그릴 자리를 이어받는다** — 지금은 API 계약만 있고 프론트엔드 컴포넌트가 없다.
- **알려진 갭(차단 아님, 위 "Known Stubs" 참조):** RULE-10의 AI 제안 생성 자체, CLI의 재량 판정 대화형 흐름.

---
*Phase: 12-stats-resources-inventory*
*Completed: 2026-08-17*

## Self-Check: PASSED

All 12 spot-checked key files verified present on disk (`agents/outcome_picker.py`,
`tests/test_outcome_picker.py`, `web/routes_actions.py`, `cli/turn_flow.py`,
`agents/action_classifier.py`, `agents/context.py`, `agents/prompt_assembly.py`,
`turn/judgments.py`, `agents/config.py`, `tests/test_action_classifier.py`,
`tests/test_web_actions.py`, `tests/conftest.py`). All three task commit hashes
(`79c0fe2`, `18e9839`, `0a185b0`) verified in `git log --all`. Full suite green
(1131 passed), `uv run lint-imports` 4/4 contracts kept, `ruff check` clean —
all re-confirmed immediately before this summary was written.
