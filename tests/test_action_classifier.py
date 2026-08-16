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
    MoveCandidate,
    Proposal,
    UnknownMove,
    classify,
)
from gptrpg.agents.context import ClockState, TurnContext
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.prompt_assembly import _format_moves, build_classifier_prompt
from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID, EXAMPLE_SINGLE_STAT_FOE
from gptrpg.rulebooks.moves import get_moves


def _ctx() -> TurnContext:
    return TurnContext(
        scene_entities=(EXAMPLE_SINGLE_STAT_FOE,),
        character_state=EXAMPLE_SINGLE_STAT_FOE.stats,
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
    assert field_names == frozenset({"candidates", "ai", "unknown_move", "no_check"})
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


