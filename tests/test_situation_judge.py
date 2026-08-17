"""상황판단/서술 분리의 계약 시험 — ARCH-02·ARCH-05·ARCH-06 (09-02 Task 1).

`tests/test_clock_judge.py`의 패턴(호출 횟수·타임아웃을 기록하는 이중체)을
빌린다. 시나리오 원문 노출 여부는 `M0_THREAT_CLOCK`/`THREAT_CAST`를 직접
import해 실제 데이터와 대조한다 — 문자열을 이 파일에 다시 적지 않는다.
"""

import dataclasses
import json

import pytest

from gptrpg.agents import prompt_assembly
from gptrpg.agents.context import (
    ClockState,
    ContextCapExceeded,
    NarrationFacts,
    RECENT_TURNS_LIMIT,
    SITUATION_FACTS_LIMIT,
    TurnContext,
)
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.invoke import MAX_ATTEMPTS, SITUATION_TIMEOUT_S
from gptrpg.agents.situation_judge import SituationJudgment, judge_situation
from gptrpg.rulebooks.threat_clocks import M0_THREAT_CLOCK, THREAT_CAST


def _turn_ctx(*, clock_at_catastrophe: bool = False) -> TurnContext:
    if clock_at_catastrophe:
        clock_state = ClockState(
            clock_id="threat",
            segment_index=len(M0_THREAT_CLOCK.segment_descriptions),
            segment_count=len(M0_THREAT_CLOCK.segment_descriptions),
            threat_name=M0_THREAT_CLOCK.name,
            threat_identity=M0_THREAT_CLOCK.identity,
            threat_wants=M0_THREAT_CLOCK.wants,
            segment_descriptions=M0_THREAT_CLOCK.segment_descriptions,
            catastrophe_text=M0_THREAT_CLOCK.catastrophe,
        )
    else:
        clock_state = ClockState(
            clock_id="threat",
            segment_index=1,
            segment_count=len(M0_THREAT_CLOCK.segment_descriptions),
            threat_name=M0_THREAT_CLOCK.name,
            threat_identity=M0_THREAT_CLOCK.identity,
            threat_wants=M0_THREAT_CLOCK.wants,
            segment_descriptions=M0_THREAT_CLOCK.segment_descriptions,
            catastrophe_text=M0_THREAT_CLOCK.catastrophe,
        )
    return TurnContext(
        scene_entities=THREAT_CAST,
        party_state=(),
        actor_character_id=None,
        clock_state=clock_state,
        recent_turns=("플레이어: 문을 두드린다",),
    )


def _narration_facts(**overrides) -> NarrationFacts:
    base = dict(
        check_summary="hack_and_slash 판정 결과 miss (목표 10)",
        scene_summary="문이 부서지고 서늘한 바람이 흘러든다.",
        facts=("경비병이 쓰러졌다",),
        scene_entities=THREAT_CAST,
        party_state=(),
        actor_character_id=None,
        recent_turns=("플레이어: 문을 두드린다",),
        new_entities=(),
    )
    base.update(overrides)
    return NarrationFacts(**base)


# ---------------------------------------------------------------------------
# NarrationFacts — 타입으로 시계 상태 칸을 막는다(ARCH-02/ARCH-06)
# ---------------------------------------------------------------------------


def test_narration_facts_field_names_have_no_clock_state_slot():
    field_names = {f.name for f in dataclasses.fields(NarrationFacts)}
    assert "clock_state" not in field_names
    assert field_names == {
        "check_summary",
        "scene_summary",
        "facts",
        "scene_entities",
        "party_state",
        "actor_character_id",
        "recent_turns",
        "new_entities",
    }


def test_narration_facts_raises_when_facts_exceed_limit():
    with pytest.raises(ContextCapExceeded):
        _narration_facts(facts=tuple(f"사실 {i}" for i in range(SITUATION_FACTS_LIMIT + 1)))


def test_narration_facts_raises_when_recent_turns_exceed_limit():
    with pytest.raises(ContextCapExceeded):
        _narration_facts(recent_turns=tuple(f"턴 {i}" for i in range(RECENT_TURNS_LIMIT + 1)))


def test_narration_facts_at_the_limit_does_not_raise():
    _narration_facts(facts=tuple(f"사실 {i}" for i in range(SITUATION_FACTS_LIMIT)))
    _narration_facts(recent_turns=tuple(f"턴 {i}" for i in range(RECENT_TURNS_LIMIT)))


# ---------------------------------------------------------------------------
# build_gm_prompt — 서술 system에 시나리오 원문이 없다(ARCH-02)
# ---------------------------------------------------------------------------


def _combined_system(system: list[dict]) -> str:
    return "\n".join(block["text"] for block in system)


def test_narration_system_excludes_scenario_identity_wants_catastrophe_and_segments():
    facts = _narration_facts()
    system, _messages = prompt_assembly.build_gm_prompt(
        rulebook_display_name="던전월드 계열", facts=facts
    )
    combined = _combined_system(system)

    assert M0_THREAT_CLOCK.identity not in combined
    assert M0_THREAT_CLOCK.wants not in combined
    assert M0_THREAT_CLOCK.catastrophe not in combined
    for segment in M0_THREAT_CLOCK.segment_descriptions:
        assert segment not in combined


def test_narration_system_is_byte_identical_across_two_calls_same_scene():
    facts = _narration_facts()
    first, _ = prompt_assembly.build_gm_prompt(rulebook_display_name="던전월드 계열", facts=facts)
    second, _ = prompt_assembly.build_gm_prompt(rulebook_display_name="던전월드 계열", facts=facts)
    assert _combined_system(first) == _combined_system(second)


def test_narration_system_unchanged_when_only_turn_varying_fields_differ():
    """턴마다 달라지는 사실 묶음이 바뀌어도 `system`은 그대로다 — `messages`에만
    실린다는 것(DP-05)의 증거."""
    facts_a = _narration_facts(scene_summary="문이 부서진다.", facts=("경비병이 쓰러졌다",))
    facts_b = _narration_facts(scene_summary="완전히 다른 장면이다.", facts=("다른 사실",))

    system_a, _ = prompt_assembly.build_gm_prompt(rulebook_display_name="던전월드 계열", facts=facts_a)
    system_b, _ = prompt_assembly.build_gm_prompt(rulebook_display_name="던전월드 계열", facts=facts_b)

    assert _combined_system(system_a) == _combined_system(system_b)


# ---------------------------------------------------------------------------
# build_gm_prompt — new_entities(09-03, D-03 (a))가 turn 조각에 실린다
# ---------------------------------------------------------------------------


def test_new_entities_names_appear_in_narration_messages_when_present():
    facts = _narration_facts(new_entities=("부서진 등불", "낯선 파수꾼"))
    _system, messages = prompt_assembly.build_gm_prompt(
        rulebook_display_name="던전월드 계열", facts=facts
    )
    turn_text = messages[0]["content"]
    assert "부서진 등불" in turn_text
    assert "낯선 파수꾼" in turn_text


def test_new_entities_line_absent_when_empty_messages_shorter_than_when_present():
    """빈 목록 자리표시자가 매 턴 들어가면 모델이 그것을 소재로 착각한다 —
    비어 있으면 그 줄 자체가 안 들어간다는 것을 문자열 길이 차이로
    확인한다(문자열 부재만으로는 "줄 자체가 없다"를 증명하지 못한다 —
    자리표시자 문구도 빈 상태를 가리키는 문자열을 포함할 수 있으므로)."""
    empty_facts = _narration_facts(new_entities=())
    filled_facts = _narration_facts(new_entities=("부서진 등불",))

    _system, empty_messages = prompt_assembly.build_gm_prompt(
        rulebook_display_name="던전월드 계열", facts=empty_facts
    )
    _system, filled_messages = prompt_assembly.build_gm_prompt(
        rulebook_display_name="던전월드 계열", facts=filled_facts
    )

    assert len(empty_messages[0]["content"]) < len(filled_messages[0]["content"])


# ---------------------------------------------------------------------------
# build_situation_prompt — 지시문·시나리오 원문이 사라진 게 아니라 옮겨 왔다
# ---------------------------------------------------------------------------


def test_situation_system_includes_scenario_identity_and_wants():
    ctx = _turn_ctx()
    system, _messages = prompt_assembly.build_situation_prompt(
        rulebook_display_name="던전월드 계열",
        ctx=ctx,
        check_summary="hack_and_slash 판정 결과 miss (목표 10)",
    )
    combined = _combined_system(system)

    assert M0_THREAT_CLOCK.identity in combined
    assert M0_THREAT_CLOCK.wants in combined


def test_situation_system_includes_catastrophe_and_all_segments_when_clock_reached_the_end():
    """칸이 끝까지 가면 `_format_clock_state`가 지나온 칸 전부(=모든 칸
    설명)와 파국 문장을 함께 펼친다 — 상황판단 프롬프트에 실제로 그 값들이
    도달한다는 것을 실제 시나리오 데이터로 증명한다."""
    ctx = _turn_ctx(clock_at_catastrophe=True)
    system, _messages = prompt_assembly.build_situation_prompt(
        rulebook_display_name="던전월드 계열",
        ctx=ctx,
        check_summary="hack_and_slash 판정 결과 miss (목표 10)",
    )
    combined = _combined_system(system)

    assert M0_THREAT_CLOCK.catastrophe in combined
    for segment in M0_THREAT_CLOCK.segment_descriptions:
        assert segment in combined


# ---------------------------------------------------------------------------
# judge_situation — D-05/ARCH-05 실패 계약 + 강건 파싱 + 상한 자르기
# ---------------------------------------------------------------------------


class _SituationJudgeStub:
    """`situation_judge` 판단 시험 전용 이중체 — 호출 횟수·타임아웃을 기록하고,
    `fail_times`번까지는 예외를 던진 뒤 `complete_value`를 돌려준다."""

    name = "situation-judge-stub"

    def __init__(self, *, fail_times: int = 0, complete_value: str = "[]") -> None:
        self.fail_times = fail_times
        self.complete_value = complete_value
        self.call_count = 0
        self.timeouts: list[float] = []

    def list_models(self) -> list[str]:
        return ["stub-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        self.call_count += 1
        self.timeouts.append(timeout_s)
        if self.call_count <= self.fail_times:
            raise RuntimeError("situation judge provider unavailable")
        return AgentResult(
            ok=True, value=self.complete_value, elapsed_ms=3, prompt_tokens=2, completion_tokens=2
        )

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        raise NotImplementedError("situation_judge는 스트리밍하지 않는다")

    def last_result(self) -> AgentResult:
        raise NotImplementedError("이 이중체는 complete()만 시험한다")


def test_judge_situation_both_attempts_fail_yields_empty_judgment_without_raising():
    provider = _SituationJudgeStub(fail_times=99)
    judgment = judge_situation(
        provider=provider,
        model="stub-model",
        ctx=_turn_ctx(),
        check_summary="hack_and_slash 판정 결과 miss (목표 10)",
        rulebook_display_name="던전월드 계열",
    )
    assert isinstance(judgment, SituationJudgment)
    assert judgment.scene_summary == ""
    assert judgment.facts == ()
    assert judgment.ai.ok is False


def test_judge_situation_calls_provider_exactly_max_attempts_when_failing():
    provider = _SituationJudgeStub(fail_times=99)
    judge_situation(
        provider=provider,
        model="stub-model",
        ctx=_turn_ctx(),
        check_summary="hack_and_slash 판정 결과 miss (목표 10)",
        rulebook_display_name="던전월드 계열",
    )
    assert provider.call_count == MAX_ATTEMPTS


def test_judge_situation_uses_situation_timeout():
    provider = _SituationJudgeStub()
    judge_situation(
        provider=provider,
        model="stub-model",
        ctx=_turn_ctx(),
        check_summary="hack_and_slash 판정 결과 miss (목표 10)",
        rulebook_display_name="던전월드 계열",
    )
    assert provider.timeouts == [SITUATION_TIMEOUT_S]


def test_judge_situation_think_block_and_code_fence_wrapped_json_still_parses():
    raw = (
        "<think>이번 판정으로 경비병이 쓰러졌다</think>\n"
        '```json\n[{"scene_summary": "경비병이 쓰러진다.", "facts": ["경비병이 쓰러졌다"]}]\n```'
    )
    provider = _SituationJudgeStub(complete_value=raw)
    judgment = judge_situation(
        provider=provider,
        model="stub-model",
        ctx=_turn_ctx(),
        check_summary="hack_and_slash 판정 결과 miss (목표 10)",
        rulebook_display_name="던전월드 계열",
    )
    assert judgment.scene_summary == "경비병이 쓰러진다."
    assert judgment.facts == ("경비병이 쓰러졌다",)


def test_judge_situation_completely_broken_response_yields_empty_judgment_not_a_crash():
    provider = _SituationJudgeStub(complete_value="이건 JSON이 전혀 아닙니다")
    judgment = judge_situation(
        provider=provider,
        model="stub-model",
        ctx=_turn_ctx(),
        check_summary="hack_and_slash 판정 결과 miss (목표 10)",
        rulebook_display_name="던전월드 계열",
    )
    assert judgment.scene_summary == ""
    assert judgment.facts == ()


def test_judge_situation_truncates_facts_over_limit_without_raising():
    over_limit_facts = [f"사실 {i}" for i in range(SITUATION_FACTS_LIMIT + 3)]
    raw = json.dumps([{"scene_summary": "장면.", "facts": over_limit_facts}])
    provider = _SituationJudgeStub(complete_value=raw)
    judgment = judge_situation(
        provider=provider,
        model="stub-model",
        ctx=_turn_ctx(),
        check_summary="hack_and_slash 판정 결과 miss (목표 10)",
        rulebook_display_name="던전월드 계열",
    )
    assert len(judgment.facts) == SITUATION_FACTS_LIMIT
    assert judgment.facts == tuple(over_limit_facts[:SITUATION_FACTS_LIMIT])
