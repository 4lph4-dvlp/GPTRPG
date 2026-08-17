"""ARCH-02의 회귀 방지 그물 — 서술 프롬프트에 시나리오 원문이 다시 새면 이
파일이 먼저 빨간불이 된다 (09-02 Task 3).

`M0_THREAT_CLOCK`과 `THREAT_CAST`를 직접 import해 실제 시나리오 데이터와
대조한다 — 문자열을 이 파일에 다시 적지 않는다. 시나리오가 바뀌면 이 시험도
자동으로 새 값을 본다.

**짝이 되는 파일:** `tests/test_prompt_assembly_scenario.py`가 상황판단
프롬프트(`build_situation_prompt`)에 대해 정반대(시나리오 내용이 "있다")를
단언한다 — 이 파일은 서술 프롬프트(`build_gm_prompt`)에 대해 "없다"를
단언한다. 두 파일이 서로를 가리킨다.
"""

import dataclasses
import inspect

from gptrpg.agents import narration_guard, prompt_assembly
from gptrpg.agents.clock_judge import ClockSignal
from gptrpg.agents.context import ClockState, NarrationFacts
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.master_gm import chunk_sentences, narrate
from gptrpg.agents.outcome_picker import OutcomePick
from gptrpg.agents.scene_entity_judge import EntityJudgment
from gptrpg.agents.situation_judge import SituationJudgment
from gptrpg.rulebooks.threat_clocks import M0_THREAT_CLOCK, THREAT_CAST
from gptrpg.turn.judgments import TurnJudgments, build_narration_facts

_CHECK_SUMMARY = "hack_and_slash 판정 결과 miss (목표 10)"


def _turn_ctx_with_clock_at_catastrophe():
    """`_format_clock_state`가 파국 문장까지 전부 펼치는 상태 — 우회 검증에
    가장 넓은 노출 표면을 준다(파국 문장은 칸이 끝까지 가야만 펼쳐진다)."""
    from gptrpg.agents.context import TurnContext

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
    return TurnContext(
        scene_entities=THREAT_CAST,
        party_state=(),
        actor_character_id=None,
        clock_state=clock_state,
        recent_turns=(),
    )


def _narration_facts(**overrides) -> NarrationFacts:
    base = dict(
        check_summary=_CHECK_SUMMARY,
        scene_summary="문이 부서지고 서늘한 바람이 흘러든다.",
        facts=("경비병이 쓰러졌다",),
        scene_entities=THREAT_CAST,
        party_state=(),
        actor_character_id=None,
        recent_turns=(),
        new_entities=(),
    )
    base.update(overrides)
    return NarrationFacts(**base)


def _combined_system(system: list[dict]) -> str:
    return "\n".join(block["text"] for block in system)


# ---------------------------------------------------------------------------
# 시나리오 원문이 서술 system에 부분 문자열로도 없다
# ---------------------------------------------------------------------------


def test_narration_system_excludes_identity_wants_catastrophe_and_every_segment():
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


def test_narration_system_excludes_every_line_of_format_clock_state_output():
    """`_format_clock_state`가 실제로 펼치는 텍스트를 직접 불러 각 줄과
    대조한다 — 요약을 통한 우회로가 열렸는지 잡는 그물이다."""
    ctx = _turn_ctx_with_clock_at_catastrophe()
    clock_text = prompt_assembly._format_clock_state(ctx.clock_state)

    facts = _narration_facts()
    system, _messages = prompt_assembly.build_gm_prompt(
        rulebook_display_name="던전월드 계열", facts=facts
    )
    combined = _combined_system(system)

    lines = [line for line in clock_text.split("\n") if line.strip()]
    assert lines, "테스트 전제 확인: 포매터가 실제로 여러 줄을 만들어야 한다"
    for line in lines:
        assert line not in combined


# ---------------------------------------------------------------------------
# 타입으로 막는다 — 관례가 아니다
# ---------------------------------------------------------------------------


def test_narration_facts_has_no_clock_state_field():
    field_names = {f.name for f in dataclasses.fields(NarrationFacts)}
    assert "clock_state" not in field_names


def test_narrate_signature_has_no_ctx_or_check_summary():
    params = set(inspect.signature(narrate).parameters)
    assert "ctx" not in params
    assert "check_summary" not in params
    assert "facts" in params


# ---------------------------------------------------------------------------
# 우회로 검사 — 상황판단 요약을 통한 노출은 구조로 완전히 막을 수 없다
# ---------------------------------------------------------------------------


def test_situation_summary_can_carry_scenario_text_verbatim_into_narration_messages():
    """**이 시험은 실패가 아니라 명시적 경고다.** ARCH-02가 없애는 것은
    "서술이 진행자 지시문·시나리오 원문을 받을 칸 자체가 없다"는 구조적
    노출면(`system`)이다 — 상황판단이 스스로 시나리오 문장을 요약이 아니라
    그대로 `scene_summary`/`facts`에 옮겨 담으면, 그 문장은 합법적인 경로
    (`build_narration_facts` -> `build_gm_prompt`의 `messages`)를 통해 서술
    호출까지 그대로 도달한다 — 코드로 완전히 막을 수 없다(모델이 무엇을
    "요약"이라 부를지는 런타임 값이다). **이 경로의 실제 방어는 Phase 10의
    출력 검증 필터다 — 이 단계는 구조적 노출면만 없앤다.** 이 시험이 Phase
    10에 넘기는 미해결 항목의 근거다(T-09-08).
    """
    empty_ai = AgentResult(ok=True, value=None, elapsed_ms=1, prompt_tokens=1, completion_tokens=1)
    situation_judgment = SituationJudgment(
        scene_summary=M0_THREAT_CLOCK.identity,  # 상황판단이 원문을 그대로 옮겨 담았다고 가정
        facts=(M0_THREAT_CLOCK.wants,),
        ai=empty_ai,
    )
    judgments = TurnJudgments(
        situation=situation_judgment,
        entity=EntityJudgment(entities=(), ai=empty_ai),
        clock=ClockSignal(should_check=False, why="", ai=empty_ai),
        outcome=OutcomePick(category_ids=(), ai=empty_ai),
    )

    ctx = _turn_ctx_with_clock_at_catastrophe()
    facts = build_narration_facts(ctx=ctx, check_summary=_CHECK_SUMMARY, judgments=judgments)
    _system, messages = prompt_assembly.build_gm_prompt(
        rulebook_display_name="던전월드 계열", facts=facts
    )
    turn_text = messages[-1]["content"]

    # 우회 경로가 실제로 열려 있다는 것을 증명으로 남긴다(단언 실패가 아니다).
    assert M0_THREAT_CLOCK.identity in turn_text
    assert M0_THREAT_CLOCK.wants in turn_text


# ---------------------------------------------------------------------------
# 스트리밍 무변경 증거 — chunk_sentences는 이 계획 전후로 같은 입력에 같은
# 출력을 낸다.
# ---------------------------------------------------------------------------


def test_chunk_sentences_behavior_is_unchanged():
    result = list(chunk_sentences(["문장 하나. 문장 둘! 문장 셋?"]))
    assert result == ["문장 하나.", "문장 둘!", "문장 셋?"]

    mid_cut = list(chunk_sentences(["이것은 하나의 문장이다", "."]))
    assert mid_cut == ["이것은 하나의 문장이다."]

    whitespace_only = list(chunk_sentences(["   ", "\n\n"]))
    assert whitespace_only == []


# ---------------------------------------------------------------------------
# SAFE-01 델타·문장 경계 — 생각 블록 방어(10-01 Task 3, TEST-03).
# `narration_guard.inspect_sentence`를 직접 불러 판정 경계를 못박는다 —
# `chunk_sentences`(델타 경계 담당)와 지연 버퍼의 `think_open`(문장 경계
# 담당)이 서로 다른 구역을 지킨다는 것을 이 절이 구분해 보여준다.
# ---------------------------------------------------------------------------


def test_think_open_marker_split_across_two_deltas_still_merges_to_one_sentence():
    """여는 표식이 델타 두 개에 걸쳐 쪼개져 들어오는 스트림 — `chunk_sentences`의
    버퍼 합치기가 이 경우를 이미 흡수한다는 것을 실제로 확인한다(SAFE-01 원문).
    """
    result = list(
        chunk_sentences(["문이 열린다. <thi", "nk>몰래 생각한다</think> 다시 이야기로."])
    )
    assert result == ["문이 열린다.", "<think>몰래 생각한다</think> 다시 이야기로."]

    verdict = narration_guard.inspect_sentence(result[1], next_sentence=None, source_texts=())
    assert verdict.disposition == "blocked"
    assert verdict.reason == "think_block"


def test_think_open_and_close_markers_in_different_sentences_are_caught_by_delay_buffer():
    """여는 표식과 닫는 표식이 서로 다른 문장에 있는 스트림 — `chunk_sentences`는
    못 잡고(각 문장이 그 자체로는 완결돼 보인다) 한 문장 지연 버퍼(`think_open`
    상태 전달)가 잡는 경우다. 두 방어의 담당 구역이 다르다는 것을 이 시험이
    구분해 보여준다(D-01의 핵심 근거)."""
    sentence1 = "문이 열린다."
    sentence2 = "<think>몰래 생각한다."
    sentence3 = "다음 문장도 이어서 생각 중이다</think> 다시 이야기로 돌아온다."

    verdict1 = narration_guard.inspect_sentence(sentence1, next_sentence=sentence2, source_texts=())
    assert verdict1.disposition == "clean"

    verdict2 = narration_guard.inspect_sentence(
        sentence2, next_sentence=sentence3, source_texts=(), think_open=verdict1.think_open
    )
    assert verdict2.disposition == "blocked"
    assert verdict2.reason == "think_block"
    assert verdict2.think_open is True  # 이 문장 안에서 안 닫혔다

    verdict3 = narration_guard.inspect_sentence(
        sentence3, next_sentence=None, source_texts=(), think_open=verdict2.think_open
    )
    assert verdict3.disposition == "blocked"
    assert verdict3.think_open is False  # 이 문장 안에서 닫혔다


def test_think_close_marker_never_arrives_keeps_blocking_subsequent_sentences():
    """닫는 표식이 영영 안 오는 스트림 — `think_open` 상태가 남아 이후 문장이
    계속 걸린다."""
    sentence1 = "<think>몰래 생각을 시작한다."
    verdict1 = narration_guard.inspect_sentence(
        sentence1, next_sentence="다음 문장.", source_texts=()
    )
    assert verdict1.disposition == "blocked"
    assert verdict1.think_open is True

    sentence2 = "이 문장은 순수한 이야기지만 아직 안 닫혔다."
    verdict2 = narration_guard.inspect_sentence(
        sentence2, next_sentence=None, source_texts=(), think_open=verdict1.think_open
    )
    assert verdict2.disposition == "blocked"
    assert verdict2.think_open is True  # 여전히 안 닫혔다

    sentence3 = "세 번째 문장도 마찬가지로 걸려야 한다."
    verdict3 = narration_guard.inspect_sentence(
        sentence3, next_sentence=None, source_texts=(), think_open=verdict2.think_open
    )
    assert verdict3.disposition == "blocked"


def test_think_markers_are_case_insensitive():
    """표식이 대문자·소문자 섞여 오는 경우 — 기존 정규식의 `IGNORECASE`가
    그대로 살아 있다."""
    sentence = "<THINK>몰래 이렇게 생각한다</Think> 그리고 이어진다."
    verdict = narration_guard.inspect_sentence(sentence, next_sentence=None, source_texts=())
    assert verdict.disposition == "blocked"
    assert verdict.reason == "think_block"


def test_think_markers_absent_never_blocks_a_normal_sentence():
    """표식이 하나도 없는 정상 서사는 한 문장도 안 걸린다(오탐 방지) — "생각"이라는
    낱말이나 홑화살괄호가 섞여도 실제 `<think>` 표식이 아니면 통과한다."""
    for sentence in (
        "문이 요란하게 부서진다.",
        "그는 생각에 잠겼다.",
        "이것은 <생각> 아니다.",
    ):
        verdict = narration_guard.inspect_sentence(sentence, next_sentence=None, source_texts=())
        assert verdict.disposition == "clean", sentence
