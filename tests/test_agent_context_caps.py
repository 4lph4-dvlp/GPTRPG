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
    ActorNotInParty,
    ClockJudgeContext,
    ClockState,
    CLOCK_JUDGE_RECENT_TURNS_LIMIT,
    ContextCapExceeded,
    ENTITY_JUDGE_RECENT_TURNS_LIMIT,
    EntityJudgeContext,
    NarrationFacts,
    NEW_ENTITY_LIMIT,
    PARTY_MEMBER_LIMIT,
    RECENT_TURNS_LIMIT,
    SCENE_ENTITY_LIMIT,
    SITUATION_FACTS_LIMIT,
    TooMuchContext,
    TurnContext,
)
from gptrpg.event_log.schema import ActionDeclared, EVENT_SCHEMA_VERSION, SceneEntityEmerged
from gptrpg.event_log.store import EventStore
from gptrpg.rules_core.entities import Entity
from gptrpg.rules_core.rulebook import ResourceAxisDecl
from gptrpg.rules_core.scenario import normalize_entity_name
from gptrpg.session_actor.projection import rebuild_state_from_events
from gptrpg.turn import judgments as judgments_module
from gptrpg.turn.clock_condition import build_clock_judge_context
from gptrpg.turn.context import build_turn_context

_SESSION_ID = "caps-test"


# ---------------------------------------------------------------------------
# 상한이 있다 — 각 값 객체가 자기 상한을 넘겼을 때 예외를 던진다
# ---------------------------------------------------------------------------


def _turn_context(
    *,
    recent_turns: tuple[str, ...],
    party_state: tuple[Entity, ...] = (),
    scene_entities: tuple[Entity, ...] = (),
) -> TurnContext:
    return TurnContext(
        scene_entities=scene_entities,
        party_state=party_state,
        actor_character_id=None,
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
        party_state=(),
        actor_character_id=None,
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


# ---------------------------------------------------------------------------
# 파티 상한(PARTY_MEMBER_LIMIT, D-18/ARCH-06/T-12-23, 12-05) — 요약이 아니라
# 절대 안전 밸브다. 인원의 출처는 `Rulebook.party_size_range`와 방장 확정
# (D-01, 12.1)이고, 정상 파티 크기에서는 이 상한에 절대 안 걸린다.
# ---------------------------------------------------------------------------


def _party_of(count: int) -> tuple[Entity, ...]:
    return tuple(
        Entity(
            entity_id=f"party.member{i}",
            display_name=f"구성원{i}",
            rulebook_id="dungeonworld_like",
        )
        for i in range(count)
    )


def _scene_entities_of(count: int) -> tuple[Entity, ...]:
    return tuple(
        Entity(
            entity_id=f"scene.member{i}",
            display_name=f"장면대상{i}",
            rulebook_id="dungeonworld_like",
        )
        for i in range(count)
    )


def test_turn_context_raises_context_cap_exceeded_over_scene_entity_limit():
    with pytest.raises(ContextCapExceeded):
        _turn_context(recent_turns=(), scene_entities=_scene_entities_of(SCENE_ENTITY_LIMIT + 1))


def test_turn_context_at_scene_entity_limit_does_not_raise():
    _turn_context(recent_turns=(), scene_entities=_scene_entities_of(SCENE_ENTITY_LIMIT))


def test_turn_context_raises_context_cap_exceeded_over_party_member_limit():
    with pytest.raises(ContextCapExceeded):
        _turn_context(recent_turns=(), party_state=_party_of(PARTY_MEMBER_LIMIT + 1))


def test_turn_context_at_party_member_limit_does_not_raise():
    _turn_context(recent_turns=(), party_state=_party_of(PARTY_MEMBER_LIMIT))


def test_narration_facts_raises_context_cap_exceeded_over_party_member_limit():
    with pytest.raises(ContextCapExceeded):
        _narration_facts(party_state=_party_of(PARTY_MEMBER_LIMIT + 1))


def test_narration_facts_at_party_member_limit_does_not_raise():
    _narration_facts(party_state=_party_of(PARTY_MEMBER_LIMIT))


def test_context_module_source_does_not_claim_the_real_party_is_four():
    """12.1-05 — 룰북 하나(넷짜리 파티)가 플랫폼 코드에 새어 든 문구가
    다시 들어오면 즉시 붉게 된다(D-01, 12.1-CONTEXT.md가 명시적으로 지목한
    자리). 인원의 출처는 이제 `Rulebook.party_size_range`와 방장 확정이고,
    `PARTY_MEMBER_LIMIT`은 절대 안전 밸브일 뿐이다."""
    import gptrpg.agents.context as context_module

    source = Path(context_module.__file__).read_text(encoding="utf-8")
    assert "실제 파티는 넷이다" not in source


# ---------------------------------------------------------------------------
# actor_stats(ctx) — 파티에서 행위자 한 명을 뽑는 파생 함수(D-17, 12-05 Task 2).
# `prompt_assembly.actor_stats`가 실제로 구현하지만, 이 예외 갈래는
# `TurnContext`/`ActorNotInParty`(둘 다 이 파일이 이미 다루는 값 객체)와
# 직접 엮인 성질이라 이 파일에서 같이 고정한다.
# ---------------------------------------------------------------------------


def test_actor_stats_finds_actor_by_exact_entity_id_match():
    actor = Entity(entity_id="party.actor", display_name="행위자", rulebook_id="dungeonworld_like")
    ctx = TurnContext(
        scene_entities=(),
        party_state=(actor,),
        actor_character_id="party.actor",
        clock_state=ClockState(clock_id="threat", segment_index=0, segment_count=4),
        recent_turns=(),
    )
    assert prompt_assembly.actor_stats(ctx) is actor.stats


def test_actor_stats_raises_actor_not_in_party_when_id_missing_from_party():
    actor = Entity(entity_id="party.actor", display_name="행위자", rulebook_id="dungeonworld_like")
    ctx = TurnContext(
        scene_entities=(),
        party_state=(actor,),
        actor_character_id="누군가-다른-이름",
        clock_state=ClockState(clock_id="threat", segment_index=0, segment_count=4),
        recent_turns=(),
    )
    with pytest.raises(ActorNotInParty):
        prompt_assembly.actor_stats(ctx)


def test_actor_stats_returns_empty_tuple_when_actor_id_none_and_party_empty():
    ctx = TurnContext(
        scene_entities=(),
        party_state=(),
        actor_character_id=None,
        clock_state=ClockState(clock_id="threat", segment_index=0, segment_count=4),
        recent_turns=(),
    )
    assert prompt_assembly.actor_stats(ctx) == ()


def test_actor_stats_raises_actor_not_in_party_when_id_none_but_party_nonempty():
    """「누가 행동했는지 모른다」를 조용히 넘기지 않는다(T-12-25)."""
    actor = Entity(entity_id="party.actor", display_name="행위자", rulebook_id="dungeonworld_like")
    ctx = TurnContext(
        scene_entities=(),
        party_state=(actor,),
        actor_character_id=None,
        clock_state=ClockState(clock_id="threat", segment_index=0, segment_count=4),
        recent_turns=(),
    )
    with pytest.raises(ActorNotInParty):
        prompt_assembly.actor_stats(ctx)


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


def test_clock_judge_context_has_no_party_state_or_scene_entities_field():
    """12-05 이후로도 시계 판단은 파티 상태를 받지 않는다(D-17) — 옛
    `character_state`가 새 `party_state`로 바뀌었으니 그물도 새 이름으로
    다시 친다(D-03 재고정 규율)."""
    field_names = _field_names(ClockJudgeContext)
    assert "party_state" not in field_names
    assert "actor_character_id" not in field_names
    assert "scene_entities" not in field_names


def test_entity_judge_context_has_no_clock_state_or_party_state_field():
    field_names = _field_names(EntityJudgeContext)
    assert "clock_state" not in field_names
    assert "party_state" not in field_names
    assert "actor_character_id" not in field_names


def test_turn_context_is_the_only_one_with_all_five_fields():
    """칸이 넷에서 다섯으로 다시 고정됐다(12-05) — 옛 `character_state`
    한 칸이 `party_state`·`actor_character_id` 두 칸으로 갈렸다. 이 시험
    함수는 지워지지 않고 새 목록으로 다시 고정됐다(11-CONTEXT D-03)."""
    assert _field_names(TurnContext) == {
        "scene_entities",
        "party_state",
        "actor_character_id",
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
# 장면 대상 2층(SCENE_ENTITY_LIMIT, D-12/D-20, Phase 13-04) — 확정 목록이
# 세션 길이(사건 개수)와 무관하게 AI에게 넘기는 양은 고정 상한 안쪽으로
# 묶인다. 기록(사건)에는 전부 남지만(별도로 확인, test_scene_layers.py) 이
# 시험은 build_turn_context()가 조립한 TurnContext.scene_entities만 본다.
# ---------------------------------------------------------------------------


def _append_many_scene_entity_emerged(store: EventStore, session_id: str, count: int) -> None:
    start_seq = store.next_seq(session_id)
    for i in range(count):
        seq = start_seq + i
        # 이름을 seq로 고유하게 만든다 — 같은 세션에 두 번째로 부르면
        # (session-length 증가 시험) 이름이 겹쳐 리듀서 중복 방지에
        # 걸러지고 실제로는 하나도 안 늘어나는 거짓 통과를 막는다.
        name = f"즉흥대상{seq}"
        store.append(
            SceneEntityEmerged(
                event_type="scene_entity_emerged",
                session_id=session_id,
                seq=seq,
                schema_version=EVENT_SCHEMA_VERSION,
                recorded_at=f"2026-01-01T00:00:{seq % 60:02d}.000Z",
                caused_by_seq=None,
                name=name,
                kind="thing",
                normalized_name=normalize_entity_name(name),
            )
        )


def test_scene_entities_emerged_layer_stays_bounded_regardless_of_session_length(
    tmp_db_path,
):
    session_id = "scene-entity-caps-test"
    store = EventStore(str(tmp_db_path))
    store.initialize()
    try:
        _append_many_scene_entity_emerged(store, session_id, SCENE_ENTITY_LIMIT * 5)
        state = rebuild_state_from_events(session_id, store.read_events(session_id))
        ctx_small = build_turn_context(
            store, session_id, "dungeonworld_like", emerged_entities=state.scene_entities_emerged
        )

        _append_many_scene_entity_emerged(store, session_id + "-more", SCENE_ENTITY_LIMIT * 20)
        _append_many_scene_entity_emerged(store, session_id, SCENE_ENTITY_LIMIT * 5)
        state_after = rebuild_state_from_events(session_id, store.read_events(session_id))
        ctx_large = build_turn_context(
            store,
            session_id,
            "dungeonworld_like",
            emerged_entities=state_after.scene_entities_emerged,
        )
    finally:
        store.close()

    # 이 호출에는 scenario=None(1층은 기존 THREAT_CAST) — 2층만 늘어나도
    # 최종 scene_entities 길이가 SCENE_ENTITY_LIMIT 이하로 묶인다.
    assert len(ctx_small.scene_entities) <= SCENE_ENTITY_LIMIT
    assert len(ctx_large.scene_entities) <= SCENE_ENTITY_LIMIT
    # 사건 자체는 세션이 커질수록 늘어난다 — 잘리는 것은 AI에게 넘기는
    # 양뿐이지 기록이 아니다(D-12/D-20).
    assert len(state_after.scene_entities_emerged) > len(state.scene_entities_emerged)


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
