"""후보 개수 + `no_check` 신호가 화면 강도(`tier`)를 정확히 결정한다 —
숫자 임계값 없이, 네 갈래로(D-11, 11-05).

`classify`를 `FakeProvider`로 직접 부른다(네트워크를 타지 않는다). 03-03이
이미 만든 「제공자 두 번 실패 -> 빈 후보」 경로도 여기서 `tier`가 `unclear`로
떨어짐을 확인한다(옛 `"none"`을 개명한 값 — 뜻이 좁아졌다).
"""

import json
from dataclasses import fields

import pytest

from gptrpg.agents.action_classifier import (
    MAX_CANDIDATES,
    NO_CHECK_SIGNAL,
    NO_TARGET,
    MoveCandidate,
    Proposal,
    TargetClaim,
    UnknownItemFromAI,
    UnknownMove,
    _inventory_slot_items,
    _parse_item_use,
    _parse_target,
    classify,
)
from gptrpg.agents.context import (
    ITEM_NOT_IN_INVENTORY,
    NO_ITEM_USED,
    ClockState,
    ItemUseClaim,
    TurnContext,
)
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.prompt_assembly import _format_moves, build_classifier_prompt
from gptrpg.rules_core.entities import Entity, StatEntry
from gptrpg.rules_core.scenario import normalize_entity_name
from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID, EXAMPLE_SINGLE_STAT_FOE
from gptrpg.rulebooks.moves import get_moves


def _ctx() -> TurnContext:
    return TurnContext(
        scene_entities=(EXAMPLE_SINGLE_STAT_FOE,),
        party_state=(EXAMPLE_SINGLE_STAT_FOE,),
        actor_character_id=EXAMPLE_SINGLE_STAT_FOE.entity_id,
        clock_state=ClockState(clock_id="threat", segment_index=0, segment_count=6),
        recent_turns=(),
    )


def _classify_with_candidate_count(fake_provider, count: int) -> Proposal:
    """FakeProvider가 정확히 `count`개짜리 후보 목록을 돌려주도록 만든 뒤 classify를 부른다."""
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    payload = [{"move": moves[i].move_id, "stat": moves[i].default_stat} for i in range(count)]
    fake_provider.complete_value = json.dumps(payload)
    return classify(
        provider=fake_provider,
        model="fake-model",
        ctx=_ctx(),
        raw_text="아무 문장",
        moves=moves,
        rulebook_display_name="Dungeonworld-like",
    )


# ---------------------------------------------------------------------------
# MAX_CANDIDATES 상수
# ---------------------------------------------------------------------------


def test_max_candidates_is_three():
    assert MAX_CANDIDATES == 3


# ---------------------------------------------------------------------------
# 후보 0·1·2·3·4개 -> 단계 unclear/single/several/several/several(3개로 잘림)
# ---------------------------------------------------------------------------


def test_zero_candidates_yields_unclear_tier(fake_provider):
    proposal = _classify_with_candidate_count(fake_provider, 0)
    assert proposal.tier == "unclear"
    assert proposal.candidates == ()


def test_one_candidate_yields_single_tier(fake_provider):
    proposal = _classify_with_candidate_count(fake_provider, 1)
    assert proposal.tier == "single"
    assert len(proposal.candidates) == 1


def test_two_candidates_yields_several_tier(fake_provider):
    proposal = _classify_with_candidate_count(fake_provider, 2)
    assert proposal.tier == "several"
    assert len(proposal.candidates) == 2


def test_three_candidates_yields_several_tier(fake_provider):
    proposal = _classify_with_candidate_count(fake_provider, 3)
    assert proposal.tier == "several"
    assert len(proposal.candidates) == 3


def test_four_candidates_are_truncated_to_three_and_yield_several_tier(fake_provider):
    proposal = _classify_with_candidate_count(fake_provider, 4)
    assert proposal.tier == "several"
    assert len(proposal.candidates) == MAX_CANDIDATES == 3


# ---------------------------------------------------------------------------
# `no_check` 신호(RULE-15, D-11) — "굴릴 필요 없음"과 "못 알아들었음"이
# 여기서 처음으로 갈라진다.
# ---------------------------------------------------------------------------


def test_no_check_signal_yields_no_check_tier(fake_provider):
    """후보 없이 `{"no_check": true}` 신호만 오면 tier가 `no_check`다."""
    fake_provider.complete_value = json.dumps([{NO_CHECK_SIGNAL: True}])
    proposal = classify(
        provider=fake_provider,
        model="fake-model",
        ctx=_ctx(),
        raw_text="문을 연다",
        moves=get_moves(DUNGEONWORLD_LIKE_ID),
        rulebook_display_name="Dungeonworld-like",
    )
    assert proposal.tier == "no_check"
    assert proposal.candidates == ()
    assert proposal.unknown_move is None


def test_candidate_wins_when_no_check_signal_arrives_together(fake_provider):
    """후보 1개와 `no_check` 신호가 같은 응답에 함께 오면 후보가 이긴다
    (RULE-15 adjacency) — tier는 `single`이지 `no_check`가 아니다."""
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    fake_provider.complete_value = json.dumps(
        [
            {"move": moves[0].move_id, "stat": moves[0].default_stat},
            {NO_CHECK_SIGNAL: True},
        ]
    )
    proposal = classify(
        provider=fake_provider,
        model="fake-model",
        ctx=_ctx(),
        raw_text="아무 문장",
        moves=moves,
        rulebook_display_name="Dungeonworld-like",
    )
    assert proposal.tier == "single"
    assert len(proposal.candidates) == 1
    assert proposal.candidates[0].move == moves[0].move_id


def test_unknown_move_absorption_never_yields_no_check_tier(fake_provider):
    """목록 밖 이름 흡수는 `no_check` 신호가 같이 왔어도 `unclear`로만
    간다 — 계약 위반이 신호보다 우선한다(SAFE-07/10-05 흡수 계약,
    T-11-16)."""
    fake_provider.complete_value = json.dumps(
        [
            {"move": "fireball", "stat": "INT"},
            {NO_CHECK_SIGNAL: True},
        ]
    )
    proposal = classify(
        provider=fake_provider,
        model="fake-model",
        ctx=_ctx(),
        raw_text="불덩이를 던진다",
        moves=get_moves(DUNGEONWORLD_LIKE_ID),
        rulebook_display_name="Dungeonworld-like",
    )
    assert proposal.tier == "unclear"
    assert proposal.candidates == ()
    assert proposal.unknown_move == "fireball"


# ---------------------------------------------------------------------------
# 03-03이 만든 실패 경로(제공자 두 번 실패) -> tier == "unclear"
# ("모델이 못 고름"과 "모델이 응답을 못 함"이 같은 단계로 합쳐진다)
# ---------------------------------------------------------------------------


class _AlwaysFailsProvider:
    """`complete`를 부를 때마다 예외를 던지는 이중체 — 03-03의 재시도 층이 두 번
    다 잡아 실패 껍데기로 떨어뜨린다."""

    name = "always-fails"

    def list_models(self) -> list[str]:
        return ["fake-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        raise TimeoutError("일부러 실패")

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        raise TimeoutError("일부러 실패")

    def last_result(self) -> AgentResult:
        raise RuntimeError("호출된 적 없음")


def test_provider_failure_after_retry_yields_unclear_tier():
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    proposal = classify(
        provider=_AlwaysFailsProvider(),
        model="fake-model",
        ctx=_ctx(),
        raw_text="아무 문장",
        moves=moves,
        rulebook_display_name="Dungeonworld-like",
    )
    assert proposal.tier == "unclear"
    assert proposal.candidates == ()
    assert proposal.ai.ok is False


def test_provider_failure_yields_unclear_not_no_check():
    """제공자 호출이 두 번 다 실패해도 `no_check`는 기본값 `False`로
    남는다 — 응답이 없는 상황이 "판정 없이 진행해도 됨"으로 읽히지
    않는다(T-11-17)."""
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    proposal = classify(
        provider=_AlwaysFailsProvider(),
        model="fake-model",
        ctx=_ctx(),
        raw_text="아무 문장",
        moves=moves,
        rulebook_display_name="Dungeonworld-like",
    )
    assert proposal.no_check is False
    assert proposal.tier == "unclear"
    assert proposal.tier != "no_check"


# ---------------------------------------------------------------------------
# UnknownMove(SAFE-07/D-12, 10-05) — 두 층으로 나뉜다:
# `_parse_candidates`는 여전히 계약 위반을 예외로 던진다(계약 유지 확인).
# `classify()`는 그 예외를 함수 경계에서 흡수해 「무브 없음」과 같은 모양의
# `Proposal`로 돌려준다(새 동작 확인) — 2026-08-12 Phase 9 UAT에서 관찰된
# "플레이어 문장이 안내 없이 사라지는" 결함을 여기서 닫는다.
# ---------------------------------------------------------------------------


def test_parse_candidates_still_raises_unknown_move_directly(fake_provider):
    """`_parse_candidates` 자체는 계약 위반을 여전히 예외로 던진다 — 흡수는
    받는 쪽(`classify`)에서만 일어나고, 위반 자체를 감추지 않는다."""
    from gptrpg.agents.action_classifier import _parse_candidates

    known_move_ids = frozenset(m.move_id for m in get_moves(DUNGEONWORLD_LIKE_ID))
    with pytest.raises(UnknownMove) as exc_info:
        _parse_candidates(json.dumps([{"move": "fireball", "stat": "INT"}]), known_move_ids)
    assert exc_info.value.move_id == "fireball"


def test_classify_absorbs_unknown_move_into_unclear_tier_proposal(fake_provider):
    """`classify()`는 목록 밖 이름에 대해 예외 없이 `tier == "unclear"`인
    `Proposal`을 돌려주고, `unknown_move`에 그 이름을 남긴다."""
    fake_provider.complete_value = json.dumps([{"move": "fireball", "stat": "INT"}])
    proposal = classify(
        provider=fake_provider,
        model="fake-model",
        ctx=_ctx(),
        raw_text="불덩이를 던진다",
        moves=get_moves(DUNGEONWORLD_LIKE_ID),
        rulebook_display_name="Dungeonworld-like",
    )
    assert proposal.tier == "unclear"
    assert proposal.candidates == ()
    assert proposal.unknown_move == "fireball"


def test_classify_empty_array_leaves_unknown_move_none(fake_provider):
    """빈 배열 응답은 「못 골랐다」다 — `unknown_move`가 `None`으로 남아
    「목록 밖 이름을 냈다」와 기록에서 구분된다."""
    fake_provider.complete_value = "[]"
    proposal = classify(
        provider=fake_provider,
        model="fake-model",
        ctx=_ctx(),
        raw_text="아무 문장",
        moves=get_moves(DUNGEONWORLD_LIKE_ID),
        rulebook_display_name="Dungeonworld-like",
    )
    assert proposal.tier == "unclear"
    assert proposal.unknown_move is None


def test_classify_provider_failure_after_retry_also_leaves_unknown_move_none():
    """제공자 호출 자체가 두 번 다 실패한 경우도 「못 골랐다」다 — 계약
    위반(모델이 응답은 했지만 목록 밖 이름을 냄)과 혼동되지 않는다."""
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    proposal = classify(
        provider=_AlwaysFailsProvider(),
        model="fake-model",
        ctx=_ctx(),
        raw_text="아무 문장",
        moves=moves,
        rulebook_display_name="Dungeonworld-like",
    )
    assert proposal.tier == "unclear"
    assert proposal.unknown_move is None


def test_classify_multiple_unknown_moves_keeps_only_the_first_and_no_candidates_survive(
    fake_provider,
):
    """목록 밖 이름이 여러 개면 처음 만난 것 하나만 `unknown_move`에 담기고,
    그 응답의 후보는 하나도 살아남지 않는다(부분 신뢰 금지) — 앞선 항목이
    닫힌 목록 안이어도 마찬가지다."""
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    fake_provider.complete_value = json.dumps(
        [
            {"move": moves[0].move_id, "stat": moves[0].default_stat},
            {"move": "fireball", "stat": "INT"},
            {"move": "teleport", "stat": "INT"},
        ]
    )
    proposal = classify(
        provider=fake_provider,
        model="fake-model",
        ctx=_ctx(),
        raw_text="아무 문장",
        moves=moves,
        rulebook_display_name="Dungeonworld-like",
    )
    assert proposal.tier == "unclear"
    assert proposal.candidates == ()
    assert proposal.unknown_move == "fireball"


def test_classify_case_variant_move_name_is_treated_as_unknown_move(fake_provider):
    """대소문자만 다른 이름은 목록 밖으로 판정된다(기존 frozenset 정확 대조
    보존, SAFE-07 adjacency edge)."""
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    variant = moves[0].move_id.upper()
    assert variant != moves[0].move_id  # 실제로 다른 문자열인지 먼저 확인
    fake_provider.complete_value = json.dumps([{"move": variant, "stat": moves[0].default_stat}])
    proposal = classify(
        provider=fake_provider,
        model="fake-model",
        ctx=_ctx(),
        raw_text="아무 문장",
        moves=moves,
        rulebook_display_name="Dungeonworld-like",
    )
    assert proposal.tier == "unclear"
    assert proposal.unknown_move == variant


def test_classify_whitespace_padded_move_name_is_treated_as_unknown_move(fake_provider):
    """앞뒤 공백이 붙은 이름은 목록 밖으로 판정된다(SAFE-07 adjacency edge)."""
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    variant = f"  {moves[0].move_id}  "
    fake_provider.complete_value = json.dumps([{"move": variant, "stat": moves[0].default_stat}])
    proposal = classify(
        provider=fake_provider,
        model="fake-model",
        ctx=_ctx(),
        raw_text="아무 문장",
        moves=moves,
        rulebook_display_name="Dungeonworld-like",
    )
    assert proposal.tier == "unclear"
    assert proposal.unknown_move == variant


def test_classify_unicode_normalization_variant_move_name_is_treated_as_unknown_move(
    fake_provider,
):
    """정규화 형태만 다른 이름(코드포인트가 다른 결합 문자 형태)도 목록
    밖으로 판정된다 — 이름 비교는 파이썬 str 코드포인트 동등성이며 새
    유니코드 정규화를 도입하지 않는다(SAFE-07 encoding edge)."""
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    variant = moves[0].move_id + "́"  # 결합 급상승 악센트 하나를 덧붙인다
    fake_provider.complete_value = json.dumps([{"move": variant, "stat": moves[0].default_stat}])
    proposal = classify(
        provider=fake_provider,
        model="fake-model",
        ctx=_ctx(),
        raw_text="아무 문장",
        moves=moves,
        rulebook_display_name="Dungeonworld-like",
    )
    assert proposal.tier == "unclear"
    assert proposal.unknown_move == variant


def test_classify_unknown_move_does_not_increase_provider_call_count(fake_provider):
    """흡수는 재시도를 유발하지 않는다 — 목록 밖 이름이 와도 제공자 호출
    횟수는 정상 경로와 똑같이 한 번이다(`_parse_candidates`가
    `call_with_one_retry` 밖에서 불리기 때문)."""
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    fake_provider.complete_value = json.dumps(
        [{"move": moves[0].move_id, "stat": moves[0].default_stat}]
    )
    classify(
        provider=fake_provider,
        model="fake-model",
        ctx=_ctx(),
        raw_text="아무 문장",
        moves=moves,
        rulebook_display_name="Dungeonworld-like",
    )
    normal_path_calls = len(fake_provider.calls)

    fake_provider.complete_value = json.dumps([{"move": "fireball", "stat": "INT"}])
    classify(
        provider=fake_provider,
        model="fake-model",
        ctx=_ctx(),
        raw_text="아무 문장",
        moves=moves,
        rulebook_display_name="Dungeonworld-like",
    )
    unknown_move_path_calls = len(fake_provider.calls) - normal_path_calls

    assert unknown_move_path_calls == normal_path_calls == 1


# ---------------------------------------------------------------------------
# Proposal에 신뢰도 칸이 없다 — 칸 목록을 코드로 고정한다 (entities.py의
# ENTITY_FIELD_NAMES 관례)
# ---------------------------------------------------------------------------


def test_proposal_field_names_have_no_confidence_slot():
    field_names = frozenset(f.name for f in fields(Proposal))
    assert field_names == frozenset(
        {"candidates", "ai", "unknown_move", "no_check", "item_use", "target"}
    )
    for name in field_names:
        assert "confidence" not in name
        assert "score" not in name


def test_move_candidate_field_names_have_no_confidence_slot():
    field_names = frozenset(f.name for f in fields(MoveCandidate))
    assert field_names == frozenset({"move", "stat"})


# ---------------------------------------------------------------------------
# 실제 모델(특히 추론형 — NIM의 Nemotron 계열)은 "JSON 배열로만 응답하라"는
# 지시를 어기고 <think> 추론 블록·마크다운 코드펜스·설명 문장을 JSON
# 앞뒤에 덧붙이는 일이 흔하다. 03-04 라이브 검증(Task 3)에서 애매한 문장이
# 정확히 이 경로를 타면서 "무브 없음"으로 조용히 떨어지는 것이 관찰됐다 —
# 원문 그대로 `json.loads`만 시도하던 예전 파싱은 이런 입력을 전부
# 빈 후보(= "무브 없음")로 오인했다.
# ---------------------------------------------------------------------------


def _classify_with_raw_completion(fake_provider, raw_text: str) -> Proposal:
    """FakeProvider가 정확히 `raw_text`를 그대로 돌려주게 만든 뒤 classify를 부른다."""
    fake_provider.complete_value = raw_text
    return classify(
        provider=fake_provider,
        model="fake-model",
        ctx=_ctx(),
        raw_text="아무 문장",
        moves=get_moves(DUNGEONWORLD_LIKE_ID),
        rulebook_display_name="Dungeonworld-like",
    )


def test_think_block_wrapped_json_array_still_parses(fake_provider):
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    raw = (
        "<think>플레이어 문장이 애매하다. hack_and_slash나 defy_danger가 "
        "둘 다 어울릴 수 있겠다.</think>\n"
        f'[{{"move": "{moves[0].move_id}", "stat": "{moves[0].default_stat}"}}, '
        f'{{"move": "{moves[1].move_id}", "stat": "{moves[1].default_stat}"}}]'
    )
    proposal = _classify_with_raw_completion(fake_provider, raw)
    assert proposal.tier == "several"
    assert len(proposal.candidates) == 2
    assert proposal.candidates[0].move == moves[0].move_id


def test_markdown_code_fence_wrapped_json_array_still_parses(fake_provider):
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    raw = f'```json\n[{{"move": "{moves[0].move_id}", "stat": "{moves[0].default_stat}"}}]\n```'
    proposal = _classify_with_raw_completion(fake_provider, raw)
    assert proposal.tier == "single"
    assert proposal.candidates[0].move == moves[0].move_id


def test_prose_before_and_after_json_array_still_parses(fake_provider):
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    raw = (
        "다음은 어울리는 후보입니다:\n"
        f'[{{"move": "{moves[0].move_id}", "stat": "{moves[0].default_stat}"}}]\n'
        "이상입니다."
    )
    proposal = _classify_with_raw_completion(fake_provider, raw)
    assert proposal.tier == "single"
    assert proposal.candidates[0].move == moves[0].move_id


def test_unknown_move_inside_think_block_wrapped_response_is_absorbed_not_raised(fake_provider):
    """<think> 블록을 벗겨낸 뒤 드러난 목록 밖 이름도 10-05부터는 `classify()`
    경계에서 흡수된다(더 이상 예외로 새 나가지 않는다)."""
    raw = '<think>음...</think>\n[{"move": "fireball", "stat": "INT"}]'
    proposal = _classify_with_raw_completion(fake_provider, raw)
    assert proposal.tier == "unclear"
    assert proposal.unknown_move == "fireball"


def test_completely_unparseable_response_yields_unclear_tier_not_a_crash(fake_provider):
    proposal = _classify_with_raw_completion(fake_provider, "죄송하지만 판단할 수 없습니다.")
    assert proposal.tier == "unclear"
    assert proposal.candidates == ()


def test_non_list_json_response_yields_unclear_tier_not_a_crash(fake_provider):
    """모델이 배열이 아니라 단일 객체를 돌려줘도(형식 위반) 죽지 않는다."""
    proposal = _classify_with_raw_completion(fake_provider, '{"move": "hack_and_slash"}')
    assert proposal.tier == "unclear"
    assert proposal.candidates == ()


# ---------------------------------------------------------------------------
# 분류기 지시문(prompt_assembly.build_classifier_prompt) — 「안 맞음」과
# 「필요 없음」이 세 갈래로 나뉘어 있고, 무브 목록이 빈 룰북에서도 예외 없이
# 조립된다(11-05 Task 2).
# ---------------------------------------------------------------------------


def test_classifier_prompt_mentions_the_no_check_signal():
    """지시문의 `permanent` 블록에 `NO_CHECK_SIGNAL` 문자열이 들어 있다 —
    지시문과 파서가 같은 신호 문자열을 쓴다는 것이 이 시험으로 고정된다."""
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    system, _messages = build_classifier_prompt(
        rulebook_display_name="Dungeonworld-like",
        moves=moves,
        ctx=_ctx(),
        raw_text="문을 연다",
    )
    permanent_text = system[0]["text"]
    assert NO_CHECK_SIGNAL in permanent_text
    assert "필요 없" in permanent_text or "필요가 없" in permanent_text


def test_classifier_prompt_handles_empty_move_list():
    """무브 목록이 빈 튜플이어도 예외 없이 조립되고, 「목록 없음」 표시가
    결과 문자열에 남는다 — 「목록이 잘려서 안 왔나」로 읽히지 않는다
    (RULE-15 empty)."""
    system, _messages = build_classifier_prompt(
        rulebook_display_name="Cairn-like",
        moves=(),
        ctx=_ctx(),
        raw_text="문을 연다",
    )
    permanent_text = system[0]["text"]
    assert "무브 목록:\n" in permanent_text
    assert _format_moves(()) in permanent_text
    assert _format_moves(()) != ""


def test_format_moves_renders_none_default_stat_as_situational_choice():
    """`MoveDecl.default_stat`이 `None`이면 "상황에 맞게 고른다"로 렌더링된다
    — AI가 "없다"가 아니라 "자유롭게 고르는 자리"로 읽어야 한다
    (`.planning/todos/completed/2026-08-15-move-default-stat-optional.md`)."""
    from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID
    from gptrpg.rulebooks.moves import get_moves

    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    defy_danger = next(move for move in moves if move.move_id == "defy_danger")
    assert defy_danger.default_stat is None

    rendered = _format_moves((defy_danger,))
    assert "상황에 맞게 고른다" in rendered
    assert "None" not in rendered




# ---------------------------------------------------------------------------
# 12-06 Task 3: 소지품 대조(RULE-16) — _inventory_slot_items
# ---------------------------------------------------------------------------


def test_inventory_slot_items_returns_none_when_no_named_slots_axis():
    """소지품을 규칙으로 안 세는 룰북(던전월드류 예시 개체는 named_slots
    축이 아예 없다) — 대조할 목록 자체가 없다는 것이 `None`으로 나타난다."""
    assert _inventory_slot_items(EXAMPLE_SINGLE_STAT_FOE.stats) is None


def test_inventory_slot_items_returns_empty_tuple_when_all_slots_empty():
    stats = (StatEntry(name="Inventory", form="named_slots", slot_values=(None, None, None)),)
    assert _inventory_slot_items(stats) == ()


def test_inventory_slot_items_preserves_declaration_order_and_duplicates():
    """같은 물건이 두 칸에 있어도 정렬·중복 제거를 하지 않는다 — 선언
    순서 그대로가 "첫 칸이 쓰인다" 규칙의 근거다."""
    stats = (
        StatEntry(
            name="Inventory",
            form="named_slots",
            slot_values=("횃불", "장검", "횃불", None),
        ),
    )
    assert _inventory_slot_items(stats) == ("횃불", "장검", "횃불")


# ---------------------------------------------------------------------------
# 12-06 Task 3: _parse_item_use — 닫힌 목록 대조
# ---------------------------------------------------------------------------


def test_parse_item_use_exact_match_yields_held():
    raw = json.dumps([{"item": "장검"}])
    claim = _parse_item_use(raw, frozenset({"장검", "랜턴"}))
    assert claim == ItemUseClaim(item="장검", kind="held")


def test_parse_item_use_no_item_used_marker_yields_none_kind():
    raw = json.dumps([{"item": NO_ITEM_USED}])
    claim = _parse_item_use(raw, frozenset({"장검"}))
    assert claim == ItemUseClaim(item=None, kind="none")


def test_parse_item_use_not_in_inventory_marker_yields_not_held():
    raw = json.dumps([{"item": ITEM_NOT_IN_INVENTORY}])
    claim = _parse_item_use(raw, frozenset({"장검"}))
    assert claim == ItemUseClaim(item=None, kind="not_held")


def test_parse_item_use_no_item_key_present_defaults_to_none_kind():
    raw = json.dumps([{"move": "hack_and_slash", "stat": "STR"}])
    claim = _parse_item_use(raw, frozenset({"장검"}))
    assert claim == ItemUseClaim(item=None, kind="none")


def test_parse_item_use_partial_name_overlap_raises_unknown_item():
    """슬롯에는 "낡고 녹슨 장검"이 있고 모델이 "장검"만 돌려주면 완전
    일치가 아니므로 `UnknownItemFromAI`다 — 「갖고 있다」로 안 친다."""
    raw = json.dumps([{"item": "장검"}])
    with pytest.raises(UnknownItemFromAI) as excinfo:
        _parse_item_use(raw, frozenset({"낡고 녹슨 장검"}))
    assert excinfo.value.item_name == "장검"


# ---------------------------------------------------------------------------
# 12-06 Task 3: classify() — 소지품 대조 통합
# ---------------------------------------------------------------------------


def _named_slots_actor(slot_values: tuple) -> Entity:
    return Entity(
        entity_id="test.adventurer",
        display_name="시험용 모험가",
        rulebook_id="cairn",
        stats=(
            StatEntry(name="STR", form="numeric", current=10),
            StatEntry(name="Inventory", form="named_slots", slot_values=slot_values),
        ),
    )


def _ctx_for(entity: Entity) -> TurnContext:
    return TurnContext(
        scene_entities=(entity,),
        party_state=(entity,),
        actor_character_id=entity.entity_id,
        clock_state=ClockState(clock_id="threat", segment_index=0, segment_count=6),
        recent_turns=(),
    )


def test_classify_partial_item_name_overlap_is_absorbed_to_none_kind(fake_provider):
    actor = _named_slots_actor(("낡고 녹슨 장검", None, None))
    fake_provider.complete_value = json.dumps(
        [{"move": "parley", "stat": "CHA"}, {"item": "장검"}]
    )
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    proposal = classify(
        provider=fake_provider,
        model="fake-model",
        ctx=_ctx_for(actor),
        raw_text="장검을 휘두른다",
        moves=moves,
        rulebook_display_name="Cairn",
    )
    assert proposal.item_use.kind == "none"
    assert proposal.item_use.item is None


def test_classify_empty_inventory_character_completes_without_exception(fake_provider):
    actor = _named_slots_actor((None, None, None))
    fake_provider.complete_value = json.dumps([{"item": ITEM_NOT_IN_INVENTORY}])
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    proposal = classify(
        provider=fake_provider,
        model="fake-model",
        ctx=_ctx_for(actor),
        raw_text="가방을 뒤진다",
        moves=moves,
        rulebook_display_name="Cairn",
    )
    assert proposal.item_use.kind in ("none", "not_held")


def test_classify_rulebook_without_named_slots_axis_skips_item_use_entirely(fake_provider):
    """소지품을 세지 않는 룰북(던전월드류, `form="none"`)에서는 프롬프트에
    소지품 지시문이 없고 결과가 항상 `kind="none"`이다(11-CONTEXT D-09)."""
    fake_provider.complete_value = json.dumps([{"move": "hack_and_slash", "stat": "STR"}])
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    proposal = classify(
        provider=fake_provider,
        model="fake-model",
        ctx=_ctx(),  # EXAMPLE_SINGLE_STAT_FOE — named_slots 축이 없다
        raw_text="문을 두드린다",
        moves=moves,
        rulebook_display_name="Dungeonworld-like",
    )
    assert proposal.item_use == ItemUseClaim(item=None, kind="none")
    permanent_text, session_text = (block["text"] for block in fake_provider.calls[0][0])
    assert "소지품" not in permanent_text
    assert "소지품" not in session_text


def test_classify_holds_exact_match_item_from_filled_slots(fake_provider):
    actor = _named_slots_actor(("장검", None, None))
    fake_provider.complete_value = json.dumps(
        [{"move": "hack_and_slash", "stat": "STR"}, {"item": "장검"}]
    )
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    proposal = classify(
        provider=fake_provider,
        model="fake-model",
        ctx=_ctx_for(actor),
        raw_text="장검을 휘두른다",
        moves=moves,
        rulebook_display_name="Cairn",
    )
    assert proposal.item_use == ItemUseClaim(item="장검", kind="held")


# ---------------------------------------------------------------------------
# 13-05 Task 1: _parse_target — 대상 판단(SCENE-04, D-13①)
#
# `_parse_item_use`와의 핵심 차이: 목록 밖은 예외 흡수가 아니라 정상
# 반환(`presence="unknown"`)이다 — SCENE-04가 다루라고 요구하는 정당한
# 갈래이기 때문이다.
# ---------------------------------------------------------------------------


def test_parse_target_silence_yields_none_presence():
    """`target` 키가 있는 원소가 아예 없으면 침묵을 "대상 없음"으로 읽는다."""
    raw = json.dumps([{"move": "parley", "stat": "CHA"}])
    claim = _parse_target(raw, {})
    assert claim == TargetClaim(name=None, presence="none", kind=None)


def test_parse_target_empty_array_yields_none_presence():
    claim = _parse_target("[]", {})
    assert claim == TargetClaim(name=None, presence="none", kind=None)


def test_parse_target_empty_string_yields_none_presence():
    raw = json.dumps([{"target": ""}])
    claim = _parse_target(raw, {})
    assert claim == TargetClaim(name=None, presence="none", kind=None)


def test_parse_target_whitespace_only_yields_none_presence():
    raw = json.dumps([{"target": "   "}])
    claim = _parse_target(raw, {})
    assert claim == TargetClaim(name=None, presence="none", kind=None)


def test_parse_target_no_target_marker_yields_none_presence():
    raw = json.dumps([{"target": NO_TARGET}])
    claim = _parse_target(raw, {})
    assert claim == TargetClaim(name=None, presence="none", kind=None)


def test_parse_target_exact_match_in_allowed_list_yields_known():
    allowed = {normalize_entity_name("우물지기 이슬"): "우물지기 이슬"}
    raw = json.dumps([{"target": "우물지기 이슬"}])
    claim = _parse_target(raw, allowed)
    assert claim == TargetClaim(name="우물지기 이슬", presence="known", kind=None)


def test_parse_target_normalization_difference_still_matches_known(fake_provider):
    """분해형 한글·앞뒤 공백만 다른 값도 목록의 **원본 이름**으로 정해진다
    (D-19) — 「우물지기 이슬」과 「이슬」이 갈라지는 것을 구조로 막는다."""
    import unicodedata

    decomposed = unicodedata.normalize("NFD", "우물지기 이슬")
    allowed = {normalize_entity_name("우물지기 이슬"): "우물지기 이슬"}
    raw = json.dumps([{"target": f"  {decomposed} "}])
    claim = _parse_target(raw, allowed)
    assert claim.presence == "known"
    assert claim.name == "우물지기 이슬"


def test_parse_target_not_in_allowed_list_yields_unknown_not_an_exception():
    """목록 밖은 예외가 아니라 정상 반환이다 — `_parse_item_use`와의 핵심 차이."""
    raw = json.dumps([{"target": "검은 개", "target_kind": "person"}])
    claim = _parse_target(raw, {})
    assert claim == TargetClaim(name="검은 개", presence="unknown", kind="person")


def test_parse_target_unknown_thing_kind():
    raw = json.dumps([{"target": "부서진 등불", "target_kind": "thing"}])
    claim = _parse_target(raw, {})
    assert claim == TargetClaim(name="부서진 등불", presence="unknown", kind="thing")


def test_parse_target_unknown_missing_kind_yields_none_kind():
    raw = json.dumps([{"target": "검은 개"}])
    claim = _parse_target(raw, {})
    assert claim == TargetClaim(name="검은 개", presence="unknown", kind=None)


def test_parse_target_unknown_invalid_kind_value_yields_none_kind():
    """`target_kind`가 닫힌 두 값 밖이면 `presence="unknown"`이어도
    `kind=None`이다 — 임의로 person/thing 중 하나로 지어내지 않는다."""
    raw = json.dumps([{"target": "검은 개", "target_kind": "monster"}])
    claim = _parse_target(raw, {})
    assert claim.presence == "unknown"
    assert claim.kind is None


def test_parse_target_malformed_element_is_skipped_not_a_crash():
    raw = json.dumps([{"target": 123}, {"target": "검은 개"}])
    claim = _parse_target(raw, {})
    assert claim.presence == "unknown"
    assert claim.name == "검은 개"


# ---------------------------------------------------------------------------
# 13-05 Task 1: classify() — 대상 통합
# ---------------------------------------------------------------------------


def test_classify_allowed_targets_none_skips_target_check_entirely(fake_provider):
    """`allowed_targets=None`(기본값, `ScenarioDecl.target_check is False`인
    시나리오가 이 경로를 쓴다)이면 프롬프트에 대상 칸이 안 붙고 결과는
    항상 `presence="none"`이다 — 모델이 뭐라고 답하든 상관없다(D-22)."""
    fake_provider.complete_value = json.dumps(
        [{"move": "parley", "stat": "CHA", "target": "우물지기 이슬"}]
    )
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    proposal = classify(
        provider=fake_provider,
        model="fake-model",
        ctx=_ctx(),
        raw_text="설득한다",
        moves=moves,
        rulebook_display_name="Dungeonworld-like",
    )
    assert proposal.target == TargetClaim(name=None, presence="none", kind=None)
    permanent_text, _session_text = (block["text"] for block in fake_provider.calls[0][0])
    assert "target_kind" not in permanent_text


def test_classify_allowed_targets_provided_known_target(fake_provider):
    allowed = {normalize_entity_name("우물지기 이슬"): "우물지기 이슬"}
    fake_provider.complete_value = json.dumps(
        [{"move": "parley", "stat": "CHA", "target": "우물지기 이슬"}]
    )
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    proposal = classify(
        provider=fake_provider,
        model="fake-model",
        ctx=_ctx(),
        raw_text="이슬을 설득한다",
        moves=moves,
        rulebook_display_name="Dungeonworld-like",
        allowed_targets=allowed,
    )
    assert proposal.target == TargetClaim(name="우물지기 이슬", presence="known", kind=None)


def test_classify_provider_failure_leaves_target_default(fake_provider):
    """제공자 실패 경로에서는 대상도 기본값 그대로다 — 응답이 없는 상황이
    「대상을 골랐다」로 새지 않는다."""

    class _AlwaysFails:
        name = "fake"

        def list_models(self):
            return []

        def complete(self, **kwargs):
            return AgentResult(ok=False, value=None, elapsed_ms=1, prompt_tokens=0, completion_tokens=0)

    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    proposal = classify(
        provider=_AlwaysFails(),
        model="fake-model",
        ctx=_ctx(),
        raw_text="아무 문장",
        moves=moves,
        rulebook_display_name="Dungeonworld-like",
        allowed_targets={"이슬": "우물지기 이슬"},
    )
    assert proposal.target == TargetClaim(name=None, presence="none", kind=None)


def test_classify_unknown_move_absorption_still_carries_target(fake_provider):
    """무브 목록 위반(`UnknownMove`)이 흡수돼도 대상 판단은 독립적으로
    살아남는다 — 대상 판단은 무브 판단과 별개다."""
    fake_provider.complete_value = json.dumps(
        [{"move": "no-such-move"}, {"target": "우물지기 이슬"}]
    )
    allowed = {normalize_entity_name("우물지기 이슬"): "우물지기 이슬"}
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    proposal = classify(
        provider=fake_provider,
        model="fake-model",
        ctx=_ctx(),
        raw_text="아무 문장",
        moves=moves,
        rulebook_display_name="Dungeonworld-like",
        allowed_targets=allowed,
    )
    assert proposal.unknown_move == "no-such-move"
    assert proposal.tier == "unclear"
    assert proposal.target == TargetClaim(name="우물지기 이슬", presence="known", kind=None)


def test_classify_tier_is_unaffected_by_target_value(fake_provider):
    """대상이 무엇이든(known/unknown/none) 같은 후보 목록이면 같은
    `tier`가 나온다 — 대상은 `tier` 계산에 끼어들지 않는다."""
    moves = get_moves(DUNGEONWORLD_LIKE_ID)

    def _tier_for(target_element: dict | None) -> str:
        payload = [{"move": "parley", "stat": "CHA"}]
        if target_element is not None:
            payload.append(target_element)
        fake_provider.complete_value = json.dumps(payload)
        return classify(
            provider=fake_provider,
            model="fake-model",
            ctx=_ctx(),
            raw_text="문장",
            moves=moves,
            rulebook_display_name="Dungeonworld-like",
            allowed_targets={},
        ).tier

    tiers = {
        _tier_for(None),
        _tier_for({"target": NO_TARGET}),
        _tier_for({"target": "검은 개", "target_kind": "person"}),
    }
    assert tiers == {"single"}


def test_classifier_prompt_mentions_target_selection_when_allowed_targets_given():
    system, _messages = build_classifier_prompt(
        rulebook_display_name="Dungeonworld-like",
        moves=get_moves(DUNGEONWORLD_LIKE_ID),
        ctx=_ctx(),
        raw_text="아무 문장",
        allowed_targets={"이슬": "우물지기 이슬"},
    )
    permanent_text = system[0]["text"]
    assert NO_TARGET in permanent_text
    assert "target_kind" in permanent_text


def test_classifier_prompt_omits_target_selection_when_allowed_targets_is_none():
    system, _messages = build_classifier_prompt(
        rulebook_display_name="Dungeonworld-like",
        moves=get_moves(DUNGEONWORLD_LIKE_ID),
        ctx=_ctx(),
        raw_text="아무 문장",
        allowed_targets=None,
    )
    permanent_text = system[0]["text"]
    assert "target_kind" not in permanent_text
