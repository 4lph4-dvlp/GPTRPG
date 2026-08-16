"""ARCH-06을 네 값 객체 전부에 대해 잡는 회귀 방지 그물 (09-03 Task 3).

`TurnContext`/`ClockJudgeContext`/`EntityJudgeContext`/`NarrationFacts` 네
값 객체가 ① 각자 상한을 넘기면 던진다 ② 각자 다른 칸만 갖는다 ③ 세션 사건
개수가 늘어도 파생 문맥의 주입량이 늘지 않는다는 것을 고정한다. 09-RESEARCH.md
가 Wave 0 격차로 남긴 두 항목(구문 층 회귀 그물·상한 회귀 그물) 중 후자를
이 파일이 닫는다.
"""

import ast
from pathlib import Path

import pytest

from gptrpg.agents import prompt_assembly
from gptrpg.agents.context import (
    ClockJudgeContext,
    ClockState,
    CLOCK_JUDGE_RECENT_TURNS_LIMIT,
    ContextCapExceeded,
    ENTITY_JUDGE_RECENT_TURNS_LIMIT,
    EntityJudgeContext,
    NarrationFacts,
    NEW_ENTITY_LIMIT,
    RECENT_TURNS_LIMIT,
    SITUATION_FACTS_LIMIT,
    TooMuchContext,
    TurnContext,
)
from gptrpg.event_log.schema import ActionDeclared, EVENT_SCHEMA_VERSION
from gptrpg.event_log.store import EventStore
from gptrpg.rules_core.entities import Entity
from gptrpg.rules_core.rulebook import ResourceAxisDecl
from gptrpg.turn import judgments as judgments_module
from gptrpg.turn.clock_condition import build_clock_judge_context
from gptrpg.turn.context import build_turn_context

_SESSION_ID = "caps-test"


# ---------------------------------------------------------------------------
# 상한이 있다 — 각 값 객체가 자기 상한을 넘겼을 때 예외를 던진다
# ---------------------------------------------------------------------------


def _turn_context(*, recent_turns: tuple[str, ...]) -> TurnContext:
    return TurnContext(
        scene_entities=(),
        character_state=(),
        clock_state=ClockState(clock_id="threat", segment_index=0, segment_count=4),
        recent_turns=recent_turns,
    )


def _clock_judge_context(*, recent_turns: tuple[str, ...]) -> ClockJudgeContext:
    return ClockJudgeContext(
        clock_position="0/4",
        next_segment_description="",
        recent_turns=recent_turns,
        check_summary="c",
    )


def _entity_judge_context(*, recent_turns: tuple[str, ...]) -> EntityJudgeContext:
    return EntityJudgeContext(
        scene_entities=(),
        recent_turns=recent_turns,
        check_summary="c",
    )


def _narration_facts(**overrides) -> NarrationFacts:
    base = dict(
        check_summary="c",
        scene_summary="s",
        facts=(),
        scene_entities=(),
        character_state=(),
        recent_turns=(),
        new_entities=(),
    )
    base.update(overrides)
    return NarrationFacts(**base)


def test_turn_context_raises_too_much_context_over_recent_turns_limit():
    with pytest.raises(TooMuchContext):
        _turn_context(recent_turns=tuple(f"턴 {i}" for i in range(RECENT_TURNS_LIMIT + 1)))


def test_turn_context_at_recent_turns_limit_does_not_raise():
    _turn_context(recent_turns=tuple(f"턴 {i}" for i in range(RECENT_TURNS_LIMIT)))


def test_clock_judge_context_raises_context_cap_exceeded_over_recent_turns_limit():
    with pytest.raises(ContextCapExceeded):
        _clock_judge_context(
            recent_turns=tuple(f"턴 {i}" for i in range(CLOCK_JUDGE_RECENT_TURNS_LIMIT + 1))
        )


def test_clock_judge_context_at_recent_turns_limit_does_not_raise():
    _clock_judge_context(recent_turns=tuple(f"턴 {i}" for i in range(CLOCK_JUDGE_RECENT_TURNS_LIMIT)))


def test_entity_judge_context_raises_context_cap_exceeded_over_recent_turns_limit():
    with pytest.raises(ContextCapExceeded):
        _entity_judge_context(
            recent_turns=tuple(f"턴 {i}" for i in range(ENTITY_JUDGE_RECENT_TURNS_LIMIT + 1))
        )


def test_entity_judge_context_at_recent_turns_limit_does_not_raise():
    _entity_judge_context(recent_turns=tuple(f"턴 {i}" for i in range(ENTITY_JUDGE_RECENT_TURNS_LIMIT)))


def test_narration_facts_raises_context_cap_exceeded_over_facts_limit():
    with pytest.raises(ContextCapExceeded):
        _narration_facts(facts=tuple(f"사실 {i}" for i in range(SITUATION_FACTS_LIMIT + 1)))


def test_narration_facts_raises_context_cap_exceeded_over_recent_turns_limit():
    with pytest.raises(ContextCapExceeded):
        _narration_facts(recent_turns=tuple(f"턴 {i}" for i in range(RECENT_TURNS_LIMIT + 1)))


def test_narration_facts_raises_context_cap_exceeded_over_new_entities_limit():
    with pytest.raises(ContextCapExceeded):
        _narration_facts(new_entities=tuple(f"대상 {i}" for i in range(NEW_ENTITY_LIMIT + 1)))


def test_resource_treatment_lines_over_limit_raises():
    """`form == "none"`인 축이 `RESOURCE_TREATMENT_LINES_LIMIT`을 넘으면
    조용히 잘라내지 않고 `ContextCapExceeded`를 던진다(D-66/ARCH-06,
    11-07) — 기존 상한 시험들과 같은 모양이다."""
    over_limit_axes = tuple(
        ResourceAxisDecl(name=f"축{i}", form="none", none_kind="discretionary")
        for i in range(prompt_assembly.RESOURCE_TREATMENT_LINES_LIMIT + 1)
    )
    with pytest.raises(ContextCapExceeded):
        prompt_assembly._format_resource_treatment(over_limit_axes)


def test_resource_treatment_lines_at_limit_does_not_raise():
    at_limit_axes = tuple(
        ResourceAxisDecl(name=f"축{i}", form="none", none_kind="discretionary")
        for i in range(prompt_assembly.RESOURCE_TREATMENT_LINES_LIMIT)
    )
    prompt_assembly._format_resource_treatment(at_limit_axes)


# ---------------------------------------------------------------------------
# 각자 다른 것을 받는다 — 네 값 객체의 필드 이름 집합
# ---------------------------------------------------------------------------


def _field_names(cls) -> set[str]:
    import dataclasses

    return {f.name for f in dataclasses.fields(cls)}


def test_narration_facts_has_no_clock_state_field():
    assert "clock_state" not in _field_names(NarrationFacts)


def test_clock_judge_context_has_no_character_state_or_scene_entities_field():
    field_names = _field_names(ClockJudgeContext)
    assert "character_state" not in field_names
    assert "scene_entities" not in field_names


def test_entity_judge_context_has_no_clock_state_or_character_state_field():
    field_names = _field_names(EntityJudgeContext)
    assert "clock_state" not in field_names
    assert "character_state" not in field_names


def test_turn_context_is_the_only_one_with_all_four_fields():
    assert _field_names(TurnContext) == {
        "scene_entities",
        "character_state",
        "clock_state",
        "recent_turns",
    }


# ---------------------------------------------------------------------------
# 세션 길이에 비례해 늘지 않는다 — 저장소 사건이 아주 많아도 파생 문맥의
# 최근 대화 개수는 각자 상한 이하로 고정된다
# ---------------------------------------------------------------------------


def _append_many_action_declared(store: EventStore, session_id: str, count: int) -> None:
    start_seq = store.next_seq(session_id)
    for i in range(count):
        seq = start_seq + i
        store.append(
            ActionDeclared(
                event_type="action_declared",
                session_id=session_id,
                seq=seq,
                schema_version=EVENT_SCHEMA_VERSION,
                recorded_at=f"2026-01-01T00:00:{seq % 60:02d}.000Z",
                caused_by_seq=None,
                player_id="p1",
                character_id="p1",
                raw_text=f"행동 {seq}",
            )
        )


def _derived_recent_turns_counts(store: EventStore, session_id: str) -> dict[str, int]:
    ctx = build_turn_context(store, session_id, "dungeonworld_like")
    check_summary = "hack_and_slash 판정 결과 miss (목표 10)"
    clock_judge_ctx = build_clock_judge_context(ctx, check_summary)
    entity_judge_ctx = judgments_module._build_entity_judge_context(ctx, check_summary)
    return {
        "turn_context": len(ctx.recent_turns),
        "clock_judge_context": len(clock_judge_ctx.recent_turns),
        "entity_judge_context": len(entity_judge_ctx.recent_turns),
    }


def test_derived_context_recent_turns_stay_at_or_under_each_own_cap(tmp_db_path):
    store = EventStore(str(tmp_db_path))
    store.initialize()
    try:
        _append_many_action_declared(store, _SESSION_ID, RECENT_TURNS_LIMIT * 5)
        counts = _derived_recent_turns_counts(store, _SESSION_ID)
    finally:
        store.close()

    assert counts["turn_context"] <= RECENT_TURNS_LIMIT
    assert counts["clock_judge_context"] <= CLOCK_JUDGE_RECENT_TURNS_LIMIT
    assert counts["entity_judge_context"] <= ENTITY_JUDGE_RECENT_TURNS_LIMIT


def test_derived_context_recent_turns_do_not_grow_when_event_count_doubles(tmp_db_path):
    store = EventStore(str(tmp_db_path))
    store.initialize()
    try:
        _append_many_action_declared(store, _SESSION_ID, RECENT_TURNS_LIMIT * 5)
        counts_before = _derived_recent_turns_counts(store, _SESSION_ID)

        _append_many_action_declared(
            store, _SESSION_ID + "-more", RECENT_TURNS_LIMIT * 10
        )
        # 같은 세션에 더 많은 사건을 쌓아도(세션 길이 증가) 파생 문맥의
        # 최근 대화 개수는 그대로다 — 늘어난 세션의 사건 개수와 무관하게
        # 상한이 고정 창(window)으로 작동한다는 증거.
        _append_many_action_declared(store, _SESSION_ID, RECENT_TURNS_LIMIT * 5)
        counts_after = _derived_recent_turns_counts(store, _SESSION_ID)
    finally:
        store.close()

    assert counts_after == counts_before


# ---------------------------------------------------------------------------
# 저장소를 훑는 경로가 없다 — .importlinter 계약과 별개로 이 시험에서도
# 한 번 더 단언한다(계약 파일이 조용히 지워지는 회귀를 잡는다)
# ---------------------------------------------------------------------------


def _imported_module_names(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_no_module_under_agents_imports_event_log_or_session_actor():
    import gptrpg.agents as agents_pkg

    agents_dir = Path(agents_pkg.__file__).parent
    offenders: list[str] = []
    for py_file in agents_dir.rglob("*.py"):
        imported = _imported_module_names(py_file)
        forbidden = {
            name
            for name in imported
            if name == "gptrpg.event_log"
            or name.startswith("gptrpg.event_log.")
            or name == "gptrpg.session_actor"
            or name.startswith("gptrpg.session_actor.")
        }
        if forbidden:
            offenders.append(f"{py_file}: {sorted(forbidden)}")

    assert offenders == [], "\n".join(offenders)
