"""후보 개수가 화면 강도(`tier`)를 정확히 결정한다 — 숫자 임계값 없이.

`classify`를 `FakeProvider`로 직접 부른다(네트워크를 타지 않는다). 03-03이
이미 만든 「제공자 두 번 실패 -> 빈 후보」 경로도 여기서 `tier`가 `none`으로
떨어짐을 확인한다.
"""

import json
from dataclasses import fields

import pytest

from gptrpg.agents.action_classifier import (
    MAX_CANDIDATES,
    MoveCandidate,
    Proposal,
    UnknownMove,
    classify,
)
from gptrpg.agents.context import ClockState, TurnContext
from gptrpg.agents.envelope import AgentResult
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
# 후보 0·1·2·3·4개 -> 단계 none/single/several/several/several(3개로 잘림)
# ---------------------------------------------------------------------------


def test_zero_candidates_yields_none_tier(fake_provider):
    proposal = _classify_with_candidate_count(fake_provider, 0)
    assert proposal.tier == "none"
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
# 03-03이 만든 실패 경로(제공자 두 번 실패) -> tier == "none"
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


def test_provider_failure_after_retry_yields_none_tier():
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    proposal = classify(
        provider=_AlwaysFailsProvider(),
        model="fake-model",
        ctx=_ctx(),
        raw_text="아무 문장",
        moves=moves,
        rulebook_display_name="Dungeonworld-like",
    )
    assert proposal.tier == "none"
    assert proposal.candidates == ()
    assert proposal.ai.ok is False


# ---------------------------------------------------------------------------
# UnknownMove는 여전히 예외로 던져진다 (tier 계산과 무관 — 애초에 Proposal이
# 안 만들어진다)
# ---------------------------------------------------------------------------


def test_unknown_move_still_raises_regardless_of_tier_logic(fake_provider):
    fake_provider.complete_value = json.dumps([{"move": "fireball", "stat": "INT"}])
    with pytest.raises(UnknownMove):
        classify(
            provider=fake_provider,
            model="fake-model",
            ctx=_ctx(),
            raw_text="불덩이를 던진다",
            moves=get_moves(DUNGEONWORLD_LIKE_ID),
            rulebook_display_name="Dungeonworld-like",
        )


# ---------------------------------------------------------------------------
# Proposal에 신뢰도 칸이 없다 — 칸 목록을 코드로 고정한다 (entities.py의
# ENTITY_FIELD_NAMES 관례)
# ---------------------------------------------------------------------------


def test_proposal_field_names_have_no_confidence_slot():
    field_names = frozenset(f.name for f in fields(Proposal))
    assert field_names == frozenset({"candidates", "ai"})
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


def test_unknown_move_inside_think_block_wrapped_response_still_raises(fake_provider):
    raw = '<think>음...</think>\n[{"move": "fireball", "stat": "INT"}]'
    with pytest.raises(UnknownMove):
        _classify_with_raw_completion(fake_provider, raw)


def test_completely_unparseable_response_yields_none_tier_not_a_crash(fake_provider):
    proposal = _classify_with_raw_completion(fake_provider, "죄송하지만 판단할 수 없습니다.")
    assert proposal.tier == "none"
    assert proposal.candidates == ()


def test_non_list_json_response_yields_none_tier_not_a_crash(fake_provider):
    """모델이 배열이 아니라 단일 객체를 돌려줘도(형식 위반) 죽지 않는다."""
    proposal = _classify_with_raw_completion(fake_provider, '{"move": "hack_and_slash"}')
    assert proposal.tier == "none"
    assert proposal.candidates == ()


