"""`resource_change.py`의 순수 함수(`apply_resource_op`·`resolve_character_stats`·
`depleted_axes`)와 `reducer.py`의 `resource_changed` 분기 접기, 그리고
「같은 caused_by_seq로 두 번 제출하면 두 번째가 AlreadyChanged로 단락되고
자원이 한 번만 깎인다」는 멱등성을 확인한다(RULE-04/05/06/09, D-05/D-65,
12-01).
"""

import asyncio

import pytest

from gptrpg.event_log.store import EventStore
from gptrpg.rules_core.entities import StatEntry
from gptrpg.rules_core.reducer import apply_event, initial_state
from gptrpg.rules_core.resource_change import (
    DepletedAxis,
    InvalidResourceChange,
    ResourceOp,
    apply_resource_op,
    depleted_axes,
    resolve_character_stats,
)
from gptrpg.session_actor.actor import (
    AlreadyChanged,
    RecordResourceChange,
    ResolveCheck,
    SessionActor,
)

# ---------------------------------------------------------------------------
# apply_resource_op
# ---------------------------------------------------------------------------


def test_apply_resource_op_subtracts_delta():
    stat = StatEntry(name="체력", form="numeric", current=20, max=20)
    op = ResourceOp(axis="체력", operation="delta", amount=-6)

    result = apply_resource_op(stat, op)

    assert result.current == 14


def test_apply_resource_op_clamps_at_max():
    """`max=20`인 축에 `+10`을 적용해도 결과 `current`가 20이다(QUAL-06)."""
    stat = StatEntry(name="체력", form="numeric", current=14, max=20)
    op = ResourceOp(axis="체력", operation="delta", amount=10)

    result = apply_resource_op(stat, op)

    assert result.current == 20


def test_apply_resource_op_does_not_clamp_when_max_is_none():
    """`max`가 `None`인 축(STR 등)은 자르지 않는다 — 상한이 없다는 뜻이지
    0이라는 뜻이 아니다."""
    stat = StatEntry(name="STR", form="numeric", current=2)
    op = ResourceOp(axis="STR", operation="delta", amount=100)

    result = apply_resource_op(stat, op)

    assert result.current == 102


def test_apply_resource_op_does_not_clamp_below_zero():
    """0 아래로 내려간 값은 자르지 않는다 — 뜻은 룰북이 정한다(D-08)."""
    stat = StatEntry(name="체력", form="numeric", current=5, max=20)
    op = ResourceOp(axis="체력", operation="delta", amount=-10)

    result = apply_resource_op(stat, op)

    assert result.current == -5


def test_apply_resource_op_on_non_numeric_form_raises():
    """이 계획이 다루는 form은 numeric뿐이다 — 나머지는 InvalidResourceChange다."""
    stat = StatEntry(name="가방", form="tag_list", tags=())
    op = ResourceOp(axis="가방", operation="delta", amount=1)

    with pytest.raises(InvalidResourceChange):
        apply_resource_op(stat, op)


def test_apply_resource_op_axis_mismatch_raises():
    stat = StatEntry(name="체력", form="numeric", current=10)
    op = ResourceOp(axis="STR", operation="delta", amount=1)

    with pytest.raises(InvalidResourceChange):
        apply_resource_op(stat, op)


# ---------------------------------------------------------------------------
# resolve_character_stats
# ---------------------------------------------------------------------------


def test_resolve_character_stats_folds_ops_in_order_preserving_axis_declaration_order():
    starting = (
        StatEntry(name="체력", form="numeric", current=20, max=20),
        StatEntry(name="STR", form="numeric", current=2),
    )
    ops = {
        "체력": (
            ResourceOp(axis="체력", operation="delta", amount=-6),
            ResourceOp(axis="체력", operation="delta", amount=-6),
        )
    }

    result = resolve_character_stats(starting, ops)

    assert [stat.name for stat in result] == ["체력", "STR"]
    assert result[0].current == 8
    assert result[1].current == 2  # 이력이 없는 축은 시작값 그대로


def test_resolve_character_stats_with_no_ops_returns_starting_values_unchanged():
    """자원 변화 사건이 하나도 없는 세션에서는 시작값을 그대로 돌려준다
    (RULE-06 empty)."""
    starting = (StatEntry(name="체력", form="numeric", current=20, max=20),)

    result = resolve_character_stats(starting, {})

    assert result == starting


# ---------------------------------------------------------------------------
# depleted_axes
# ---------------------------------------------------------------------------


def test_depleted_axes_finds_zero_or_below_with_effect_ref():
    stats = (
        StatEntry(
            name="체력",
            form="numeric",
            current=0,
            max=20,
            depleted_effect_ref="dungeonworld_like.hp_depleted",
        ),
        StatEntry(name="STR", form="numeric", current=2),
    )

    result = depleted_axes(stats)

    assert result == (DepletedAxis(axis="체력", effect_ref="dungeonworld_like.hp_depleted"),)


def test_depleted_axes_ignores_positive_current():
    stats = (
        StatEntry(
            name="체력",
            form="numeric",
            current=5,
            max=20,
            depleted_effect_ref="dungeonworld_like.hp_depleted",
        ),
    )

    assert depleted_axes(stats) == ()


def test_depleted_axes_ignores_axes_without_effect_ref():
    stats = (StatEntry(name="체력", form="numeric", current=0, max=20),)

    assert depleted_axes(stats) == ()


# ---------------------------------------------------------------------------
# reducer.apply_event("resource_changed", ...)
# ---------------------------------------------------------------------------


def test_apply_event_resource_changed_appends_ops_and_records_cause():
    state = initial_state("s1")
    payload = {
        "seq": 0,
        "caused_by_seq": 5,
        "character_id": "bram",
        "changes": [
            {"axis": "체력", "operation": "delta", "amount": -6, "rolls": [], "before": 20, "after": 14}
        ],
        "category_id": None,
        "source": "outcome_list",
    }

    state = apply_event(state, "resource_changed", payload)

    assert state.last_seq == 0
    ops = state.character_resource_ops[("bram", "체력")]
    assert len(ops) == 1
    assert ops[0].amount == -6
    assert state.resource_change_by_cause[5] == 0


def test_apply_event_resource_changed_appends_to_existing_history():
    state = initial_state("s1")
    payload1 = {
        "seq": 0,
        "caused_by_seq": 5,
        "character_id": "bram",
        "changes": [
            {"axis": "체력", "operation": "delta", "amount": -6, "rolls": [], "before": 20, "after": 14}
        ],
        "category_id": None,
        "source": "outcome_list",
    }
    payload2 = {
        "seq": 1,
        "caused_by_seq": 9,
        "character_id": "bram",
        "changes": [
            {"axis": "체력", "operation": "delta", "amount": -3, "rolls": [], "before": 14, "after": 11}
        ],
        "category_id": None,
        "source": "outcome_list",
    }
    state = apply_event(state, "resource_changed", payload1)
    state = apply_event(state, "resource_changed", payload2)

    ops = state.character_resource_ops[("bram", "체력")]
    assert [op.amount for op in ops] == [-6, -3]
    assert state.resource_change_by_cause == {5: 0, 9: 1}


def test_pre_schema_8_records_have_no_resource_changed_events():
    """판 7 이하로 쓰인 옛 기록에는 `resource_changed` 사건이 없으므로
    하위 호환은 자동이다 — `resource_changed` 분기를 한 번도 안 거친
    상태는 안전한 기본값(빈 dict)이다."""
    state = initial_state("s1")
    assert state.character_resource_ops == {}
    assert state.resource_change_by_cause == {}


# ---------------------------------------------------------------------------
# 멱등성 — 같은 caused_by_seq로 두 번 제출하면 두 번째가 AlreadyChanged로
# 단락되고 자원이 한 번만 깎인다
# ---------------------------------------------------------------------------


class _FixedRoller:
    def __init__(self, values: list[int]) -> None:
        self._values = iter(values)

    def roll_d6(self) -> int:
        return next(self._values)


async def _run_idempotency_scenario(tmp_db_path) -> tuple:
    store = EventStore(tmp_db_path)
    store.initialize()
    actor = SessionActor(store, "s1", _FixedRoller([3, 4] * 20))
    actor.start()
    try:
        resolve_seq = await actor.submit(
            ResolveCheck(
                move="문을 부순다",
                modifiers=(),
                person_id="bram",
                character_id="bram",
            )
        )
        first_seq = await actor.submit(
            RecordResourceChange(
                character_id="bram",
                changes=(ResourceOp(axis="체력", operation="delta", amount=-6),),
                source="outcome_list",
                caused_by_seq=resolve_seq,
            )
        )
        with pytest.raises(AlreadyChanged) as exc_info:
            await actor.submit(
                RecordResourceChange(
                    character_id="bram",
                    changes=(ResourceOp(axis="체력", operation="delta", amount=-6),),
                    source="outcome_list",
                    caused_by_seq=resolve_seq,
                )
            )
        return first_seq, exc_info.value.resource_seq, actor.state
    finally:
        await actor.stop()


def test_idempotent_resubmission_is_short_circuited_and_resource_dropped_once(tmp_db_path):
    """같은 `caused_by_seq`로 두 번 제출하면 `resource_changed` 사건이
    정확히 하나만 기록된다."""
    first_seq, second_attempt_seq, state = asyncio.run(_run_idempotency_scenario(tmp_db_path))

    assert first_seq == second_attempt_seq
    ops = state.character_resource_ops[("bram", "체력")]
    assert len(ops) == 1


# ---------------------------------------------------------------------------
# 빈 변화 목록 — 사건을 아예 안 쓴다(RULE-04/05/09 empty)
# ---------------------------------------------------------------------------


async def _run_empty_changes_scenario(tmp_db_path):
    from gptrpg.session_actor.actor import CommandRejected

    store = EventStore(tmp_db_path)
    store.initialize()
    actor = SessionActor(store, "s1", _FixedRoller([3, 4] * 20))
    actor.start()
    try:
        with pytest.raises(CommandRejected):
            await actor.submit(
                RecordResourceChange(character_id="bram", changes=(), source="outcome_list")
            )
        return store.read_events("s1")
    finally:
        await actor.stop()


def test_empty_changes_is_rejected_and_no_event_is_written(tmp_db_path):
    events = asyncio.run(_run_empty_changes_scenario(tmp_db_path))
    assert events == []
