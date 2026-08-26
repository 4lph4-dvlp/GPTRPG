"""장면 대상 3층 조회·이름 정규화·명부 한 벌(D-13②/SCENE-03/SCENE-05,
Phase 13-04)의 순수 함수 시험 + 2층 적립(사건/액터) 시험.

`tests/test_scenario.py`의 구조 시험, `tests/test_session_actor.py`의
`_make_actor` 패턴을 그대로 빌린다. 함수가 아직 없으므로(이 시험을 먼저
쓰는 시점) 임포트 자체가 실패한다 — RED 확인은 이 계획의
`13-04-SUMMARY.md`에 그 출력을 그대로 옮겨 적는다.
"""

import unicodedata

import pytest

from gptrpg.event_log.store import EventStore
from gptrpg.rules_core.entities import Entity
from gptrpg.rules_core.reducer import EmergedEntityFold, apply_event, initial_state
from gptrpg.rules_core.scenario import (
    RosterRow,
    SceneLayerHit,
    normalize_entity_name,
    resolve_scene_layers,
    roster_rows,
)
from gptrpg.session_actor.actor import (
    EntityAlreadyEmerged,
    RecordEmergedEntity,
    SessionActor,
)
from gptrpg.turn.context import build_turn_context


class _FixedRoller:
    def roll_d6(self) -> int:
        raise AssertionError("이 시험은 주사위를 굴리지 않는다")


def _make_actor(tmp_db_path) -> tuple[EventStore, SessionActor]:
    store = EventStore(tmp_db_path)
    store.initialize()
    actor = SessionActor(store, "s1", _FixedRoller())
    actor.start()
    return store, actor


def _cast() -> tuple[Entity, ...]:
    return (
        Entity(entity_id="well-keeper", display_name="우물지기 이슬", rulebook_id="dungeonworld_like"),
        Entity(entity_id="chief", display_name="촌장 담녹", rulebook_id="dungeonworld_like"),
    )


def _fold(seq: int, name: str, kind: str) -> EmergedEntityFold:
    return EmergedEntityFold(seq=seq, name=name, kind=kind, normalized_name=normalize_entity_name(name))


# ---------------------------------------------------------------------------
# normalize_entity_name — SCENE-05 encoding
# ---------------------------------------------------------------------------


def test_normalize_entity_name_composed_and_decomposed_hangul_are_equal():
    composed = "이슬"
    decomposed = unicodedata.normalize("NFD", "이슬")
    assert normalize_entity_name(composed) == normalize_entity_name(decomposed)


def test_normalize_entity_name_strips_leading_and_trailing_whitespace_only():
    assert normalize_entity_name("이슬") == normalize_entity_name("  이슬  ")


def test_normalize_entity_name_keeps_middle_whitespace_significant():
    # 「우물 지기」와 「우물지기」는 다른 값이다 — 부분 겹침으로 합치지 않는다.
    assert normalize_entity_name("우물 지기") != normalize_entity_name("우물지기")


def test_normalize_entity_name_is_deterministic_across_repeated_calls():
    name = "홀린 아이 나울"
    assert normalize_entity_name(name) == normalize_entity_name(name)


# ---------------------------------------------------------------------------
# resolve_scene_layers — SCENE-03 ordering/adjacency/empty
# ---------------------------------------------------------------------------


def test_resolve_scene_layers_finds_name_in_cast_layer():
    hit = resolve_scene_layers("우물지기 이슬", cast=_cast(), emerged=())
    assert hit == SceneLayerHit(layer="scenario", name="우물지기 이슬", kind=None)


def test_resolve_scene_layers_finds_name_in_emerged_layer_only():
    emerged = (_fold(1, "검은 개", "thing"),)
    hit = resolve_scene_layers("검은 개", cast=_cast(), emerged=emerged)
    assert hit == SceneLayerHit(layer="emerged", name="검은 개", kind="thing")


def test_resolve_scene_layers_same_name_in_both_layers_scenario_wins():
    # SCENE-03 adjacency — 같은 이름이 두 층에 있으면 정확히 하나로 정해지고
    # 시나리오(1층)가 이긴다.
    emerged = (_fold(1, "우물지기 이슬", "person"),)
    hit = resolve_scene_layers("우물지기 이슬", cast=_cast(), emerged=emerged)
    assert hit.layer == "scenario"


def test_resolve_scene_layers_both_layers_empty_returns_outside_not_none_not_exception():
    # SCENE-03 empty — 두 층이 모두 비어 있어도 조회가 결정론적으로 끝난다.
    hit = resolve_scene_layers("아무개", cast=(), emerged=())
    assert hit is not None
    assert hit == SceneLayerHit(layer="outside", name=None, kind=None)


def test_resolve_scene_layers_name_not_in_either_layer_returns_outside():
    hit = resolve_scene_layers("존재하지 않는 사람", cast=_cast(), emerged=(_fold(1, "검은 개", "thing"),))
    assert hit.layer == "outside"


def test_resolve_scene_layers_is_deterministic_across_repeated_calls():
    cast = _cast()
    emerged = (_fold(1, "검은 개", "thing"),)
    first = resolve_scene_layers("검은 개", cast=cast, emerged=emerged)
    second = resolve_scene_layers("검은 개", cast=cast, emerged=emerged)
    assert first == second


def test_resolve_scene_layers_normalizes_query_name_before_comparing():
    decomposed_query = unicodedata.normalize("NFD", "우물지기 이슬")
    hit = resolve_scene_layers(decomposed_query, cast=_cast(), emerged=())
    assert hit.layer == "scenario"


# ---------------------------------------------------------------------------
# roster_rows — D-17 명부 한 벌, SCENE-05 empty
# ---------------------------------------------------------------------------


def test_roster_rows_empty_cast_and_emerged_returns_empty_tuple():
    assert roster_rows(cast=(), emerged=()) == ()


def test_roster_rows_scenario_rows_come_first_with_kind_none():
    rows = roster_rows(cast=_cast(), emerged=())
    assert rows == (
        RosterRow(name="우물지기 이슬", kind=None, origin="scenario"),
        RosterRow(name="촌장 담녹", kind=None, origin="scenario"),
    )


def test_roster_rows_emerged_rows_follow_in_appearance_order_with_kind():
    emerged = (_fold(1, "검은 개", "thing"), _fold(2, "떠돌이 상인", "person"))
    rows = roster_rows(cast=(), emerged=emerged)
    assert rows == (
        RosterRow(name="검은 개", kind="thing", origin="emerged"),
        RosterRow(name="떠돌이 상인", kind="person", origin="emerged"),
    )


def test_roster_rows_overlap_keeps_exactly_one_scenario_row():
    emerged = (_fold(1, "우물지기 이슬", "person"),)
    rows = roster_rows(cast=_cast(), emerged=emerged)
    matching = [row for row in rows if row.name == "우물지기 이슬"]
    assert len(matching) == 1
    assert matching[0].origin == "scenario"


def test_roster_row_has_exactly_three_fields():
    import dataclasses

    field_names = {f.name for f in dataclasses.fields(RosterRow)}
    assert field_names == {"name", "kind", "origin"}


# ---------------------------------------------------------------------------
# 2층 적립 — 사건(scene_entity_emerged)·리듀서·액터(RecordEmergedEntity)
# ---------------------------------------------------------------------------


async def test_record_emerged_entity_appends_scene_entity_emerged_and_folds_state(tmp_db_path):
    store, actor = _make_actor(tmp_db_path)
    seq = await actor.submit(RecordEmergedEntity(name="검은 개", kind="thing"))
    events = store.read_events("s1")
    assert len(events) == 1
    assert events[0].event_type == "scene_entity_emerged"
    assert events[0].seq == seq
    assert actor.state.scene_entities_emerged == (
        EmergedEntityFold(seq=seq, name="검은 개", kind="thing", normalized_name="검은 개"),
    )
    await actor.stop()
    store.close()


async def test_record_emerged_entity_empty_name_is_rejected(tmp_db_path):
    from gptrpg.session_actor.actor import CommandRejected

    store, actor = _make_actor(tmp_db_path)
    with pytest.raises(CommandRejected):
        await actor.submit(RecordEmergedEntity(name="   ", kind="thing"))
    assert store.read_events("s1") == []
    await actor.stop()
    store.close()


async def test_record_emerged_entity_unknown_kind_is_rejected(tmp_db_path):
    from gptrpg.session_actor.actor import CommandRejected

    store, actor = _make_actor(tmp_db_path)
    with pytest.raises(CommandRejected):
        await actor.submit(RecordEmergedEntity(name="검은 개", kind="monster"))
    assert store.read_events("s1") == []
    await actor.stop()
    store.close()


async def test_record_emerged_entity_duplicate_normalized_name_raises_already_emerged(
    tmp_db_path,
):
    store, actor = _make_actor(tmp_db_path)
    first_seq = await actor.submit(RecordEmergedEntity(name="검은 개", kind="thing"))
    with pytest.raises(EntityAlreadyEmerged) as excinfo:
        await actor.submit(RecordEmergedEntity(name="  검은 개  ", kind="thing"))
    assert excinfo.value.prior.seq == first_seq
    assert len(store.read_events("s1")) == 1
    await actor.stop()
    store.close()


def test_reducer_scene_entity_emerged_branch_does_not_double_append_same_normalized_name():
    # 리듀서 자체의 마지막 방어선 — 액터를 거치지 않고 직접 apply_event를
    # 두 번 불러도(가상의 이중 기록) 2층에는 하나만 남는다.
    state = initial_state("s1")
    state = apply_event(
        state,
        "scene_entity_emerged",
        {"seq": 1, "name": "검은 개", "kind": "thing", "normalized_name": "검은 개"},
    )
    state = apply_event(
        state,
        "scene_entity_emerged",
        {"seq": 2, "name": "검은 개", "kind": "thing", "normalized_name": "검은 개"},
    )
    assert len(state.scene_entities_emerged) == 1


def test_reducer_scene_entity_emerged_preserves_appearance_order():
    state = initial_state("s1")
    state = apply_event(
        state,
        "scene_entity_emerged",
        {"seq": 1, "name": "검은 개", "kind": "thing", "normalized_name": "검은 개"},
    )
    state = apply_event(
        state,
        "scene_entity_emerged",
        {"seq": 2, "name": "떠돌이 상인", "kind": "person", "normalized_name": "떠돌이 상인"},
    )
    assert [item.name for item in state.scene_entities_emerged] == ["검은 개", "떠돌이 상인"]


# ---------------------------------------------------------------------------
# build_turn_context 3층 조립 — Task 2 (SCENE-03 adjacency/회귀)
# ---------------------------------------------------------------------------


def test_build_turn_context_scenario_none_emerged_none_is_byte_identical_regression(
    tmp_db_path,
):
    # scenario=None·emerged_entities=None이면(기존 CLI 경로) 지금과 한
    # 글자도 다르지 않은 TurnContext가 나온다(Task 2 회귀 증거).
    store = EventStore(str(tmp_db_path))
    store.initialize()
    try:
        ctx = build_turn_context(store, "s1", "dungeonworld_like")
    finally:
        store.close()

    from gptrpg.rulebooks import threat_clocks

    assert ctx.scene_entities == threat_clocks.THREAT_CAST


def test_build_turn_context_merges_cast_and_emerged_without_scenario(tmp_db_path):
    store = EventStore(str(tmp_db_path))
    store.initialize()
    try:
        emerged = (_fold(1, "검은 개", "thing"),)
        ctx = build_turn_context(
            store, "s1", "dungeonworld_like", emerged_entities=emerged
        )
    finally:
        store.close()

    from gptrpg.rulebooks import threat_clocks

    names = [entity.display_name for entity in ctx.scene_entities]
    assert names == [*[e.display_name for e in threat_clocks.THREAT_CAST], "검은 개"]


def test_build_turn_context_drops_emerged_entity_overlapping_cast_name(tmp_db_path):
    from gptrpg.rulebooks import threat_clocks

    overlapping_name = threat_clocks.THREAT_CAST[0].display_name
    store = EventStore(str(tmp_db_path))
    store.initialize()
    try:
        emerged = (_fold(1, overlapping_name, "person"),)
        ctx = build_turn_context(
            store, "s1", "dungeonworld_like", emerged_entities=emerged
        )
    finally:
        store.close()

    # SCENE-03 adjacency가 조립부에서도 성립한다 — 이름이 정확히 한 번만
    # 나온다.
    matching = [e for e in ctx.scene_entities if e.display_name == overlapping_name]
    assert len(matching) == 1


def test_build_turn_context_over_scene_entity_limit_keeps_the_latest_emerged(
    tmp_db_path,
):
    from gptrpg.agents.context import SCENE_ENTITY_LIMIT
    from gptrpg.rulebooks import threat_clocks

    remaining_budget = SCENE_ENTITY_LIMIT - len(threat_clocks.THREAT_CAST)
    assert remaining_budget > 0, "이 시험은 캐스트가 상한보다 작다고 전제한다"
    emerged = tuple(
        _fold(i, f"즉흥대상{i}", "thing") for i in range(remaining_budget + 3)
    )
    store = EventStore(str(tmp_db_path))
    store.initialize()
    try:
        ctx = build_turn_context(
            store, "s1", "dungeonworld_like", emerged_entities=emerged
        )
    finally:
        store.close()

    emerged_names_in_ctx = [
        e.display_name
        for e in ctx.scene_entities
        if e.display_name.startswith("즉흥대상")
    ]
    expected_latest = [fold.name for fold in emerged[-remaining_budget:]]
    assert emerged_names_in_ctx == expected_latest
    assert len(ctx.scene_entities) == SCENE_ENTITY_LIMIT


# ---------------------------------------------------------------------------
# record_emerged_entities 헬퍼 — D-13②/D-05/ARCH-05 (Task 3)
# ---------------------------------------------------------------------------


class _StubActorAlwaysRejectsUnexpectedly:
    """`.submit()`이 매번 알 수 없는 예외를 던지는 이중체 — 적립 실패가
    턴을 막지 않는지(D-05/ARCH-05) 확인한다."""

    def __init__(self) -> None:
        self.calls: list = []

    async def submit(self, command):
        self.calls.append(command)
        raise RuntimeError("액터 큐가 일부러 실패한다")


def _judgments_with_new_entity(name: str, kind: str):
    from gptrpg.agents.envelope import AgentResult
    from gptrpg.agents.scene_entity_judge import EntityJudgment, NewEntity
    from gptrpg.turn.judgments import TurnJudgments

    ai = AgentResult(ok=True, value="[]", elapsed_ms=1, prompt_tokens=1, completion_tokens=1)

    class _StubSituation:
        pass

    class _StubClock:
        pass

    class _StubOutcome:
        pass

    return TurnJudgments(
        situation=_StubSituation(),
        entity=EntityJudgment(entities=(NewEntity(name=name, kind=kind),), ai=ai),
        clock=_StubClock(),
        outcome=_StubOutcome(),
    )


async def test_record_emerged_entities_submission_failure_does_not_raise(tmp_db_path, capsys):
    from gptrpg.turn.emerged_entities import record_emerged_entities

    actor = _StubActorAlwaysRejectsUnexpectedly()
    judgments = _judgments_with_new_entity("검은 개", "thing")

    # 예외를 안 던진다는 것 자체가 단언이다 — 여기까지 도달하면 통과.
    await record_emerged_entities(actor, judgments, cast=(), emerged=(), caused_by_seq=None)
    assert len(actor.calls) == 1

    captured = capsys.readouterr()
    assert "경고" in captured.err


async def test_record_emerged_entities_skips_names_overlapping_cast():
    from gptrpg.turn.emerged_entities import record_emerged_entities

    class _StubActorNeverCalled:
        async def submit(self, command):
            raise AssertionError("1층과 겹치는 이름은 제출하면 안 된다")

    actor = _StubActorNeverCalled()
    judgments = _judgments_with_new_entity("우물지기 이슬", "person")

    await record_emerged_entities(
        actor, judgments, cast=_cast(), emerged=(), caused_by_seq=None
    )


async def test_record_emerged_entities_treats_already_emerged_as_success():
    from gptrpg.turn.emerged_entities import record_emerged_entities

    class _StubActorAlreadyEmerged:
        async def submit(self, command):
            raise EntityAlreadyEmerged(
                EmergedEntityFold(seq=1, name="검은 개", kind="thing", normalized_name="검은 개")
            )

    actor = _StubActorAlreadyEmerged()
    judgments = _judgments_with_new_entity("검은 개", "thing")

    # EntityAlreadyEmerged가 다시 던져지지 않는다는 것 자체가 단언이다.
    await record_emerged_entities(actor, judgments, cast=(), emerged=(), caused_by_seq=None)
