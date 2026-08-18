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
from gptrpg.rules_core.reducer import OutOfOrderEvent, apply_event, fold, initial_state
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


def test_apply_resource_op_mismatched_form_and_operation_raises():
    """형태와 동작이 어긋나면(예: tag_list에 delta) 조용히 넘어가지 않고
    InvalidResourceChange다."""
    stat = StatEntry(name="가방", form="tag_list", tags=())
    op = ResourceOp(axis="가방", operation="delta", amount=1)

    with pytest.raises(InvalidResourceChange):
        apply_resource_op(stat, op)


def test_apply_resource_op_axis_mismatch_raises():
    stat = StatEntry(name="체력", form="numeric", current=10)
    op = ResourceOp(axis="STR", operation="delta", amount=1)

    with pytest.raises(InvalidResourceChange):
        apply_resource_op(stat, op)


def test_apply_resource_op_numeric_boundary_exactly_at_max_stays_at_max():
    """`current=20, max=20`에 `+1` → 20(경계 바로 위는 잘린다, QUAL-06 boundary)."""
    stat = StatEntry(name="체력", form="numeric", current=20, max=20)
    op = ResourceOp(axis="체력", operation="delta", amount=1)

    result = apply_resource_op(stat, op)

    assert result.current == 20


def test_apply_resource_op_numeric_boundary_reaching_max_exactly_is_normal():
    """`current=19, max=20`에 `+1` → 20(경계에 정확히 닿는 것은 정상,
    QUAL-06 boundary)."""
    stat = StatEntry(name="체력", form="numeric", current=19, max=20)
    op = ResourceOp(axis="체력", operation="delta", amount=1)

    result = apply_resource_op(stat, op)

    assert result.current == 20


def test_apply_resource_op_numeric_with_max_none_and_large_positive_amount():
    """`max=None`인 축에 `+1000`을 적용한 결과 `current`가 시작값 + 1000이다
    (QUAL-06 empty — 안 자른다)."""
    stat = StatEntry(name="STR", form="numeric", current=2)
    op = ResourceOp(axis="STR", operation="delta", amount=1000)

    result = apply_resource_op(stat, op)

    assert result.current == 1002


def test_apply_resource_op_numeric_negative_amount_goes_below_zero_unclamped():
    """`current=3`인 numeric 축에 `-10`을 적용한 결과 `current`가 `-7`이다
    (0 아래는 안 자른다)."""
    stat = StatEntry(name="체력", form="numeric", current=3)
    op = ResourceOp(axis="체력", operation="delta", amount=-10)

    result = apply_resource_op(stat, op)

    assert result.current == -7


# ---------------------------------------------------------------------------
# apply_resource_op — clock (11-VERIFICATION RULE-11 3/6, 아직 실제 룰북에
# 없다 — 시험 픽스처로만 덮는다)
# ---------------------------------------------------------------------------


def test_apply_resource_op_clock_advance_moves_forward_and_stops_at_max():
    """`clock` + `advance`: `current`가 칸수만큼 나아가고 `max`에서 멈춘다."""
    stat = StatEntry(name="위협 시계", form="clock", current=2, max=6)
    op = ResourceOp(axis="위협 시계", operation="advance", amount=3)

    result = apply_resource_op(stat, op)

    assert result.current == 5


def test_apply_resource_op_clock_advance_stops_at_max_when_it_would_overshoot():
    stat = StatEntry(name="위협 시계", form="clock", current=5, max=6)
    op = ResourceOp(axis="위협 시계", operation="advance", amount=10)

    result = apply_resource_op(stat, op)

    assert result.current == 6


def test_apply_resource_op_clock_advance_negative_steps_back_and_stops_at_zero():
    """음수 `advance`는 뒤로 물러나고 0에서 멈춘다(`StatEntry`가
    `0 <= current <= max`를 이미 강제한다)."""
    stat = StatEntry(name="위협 시계", form="clock", current=1, max=6)
    op = ResourceOp(axis="위협 시계", operation="advance", amount=-5)

    result = apply_resource_op(stat, op)

    assert result.current == 0


def test_apply_resource_op_clock_rejects_operations_other_than_advance():
    stat = StatEntry(name="위협 시계", form="clock", current=1, max=6)
    op = ResourceOp(axis="위협 시계", operation="delta", amount=1)

    with pytest.raises(InvalidResourceChange):
        apply_resource_op(stat, op)


# ---------------------------------------------------------------------------
# apply_resource_op — named_slots (RULE-11 3/6)
# ---------------------------------------------------------------------------


def test_apply_resource_op_named_slots_fill_fills_first_empty_slot():
    """`named_slots` + `fill`: 첫 번째 빈 슬롯에 문자열을 넣는다."""
    stat = StatEntry(name="소지품", form="named_slots", slot_values=("검", None, None))
    op = ResourceOp(axis="소지품", operation="fill", amount="랜턴")

    result = apply_resource_op(stat, op)

    assert result.slot_values == ("검", "랜턴", None)


def test_apply_resource_op_named_slots_fill_raises_when_no_empty_slot():
    """빈 슬롯이 없으면 `InvalidResourceChange`."""
    stat = StatEntry(name="소지품", form="named_slots", slot_values=("검", "랜턴"))
    op = ResourceOp(axis="소지품", operation="fill", amount="밧줄")

    with pytest.raises(InvalidResourceChange):
        apply_resource_op(stat, op)


def test_apply_resource_op_named_slots_clear_empties_the_matching_slot():
    """`named_slots` + `clear`: 그 문자열과 완전히 같은 값이 든 첫 슬롯을 비운다."""
    stat = StatEntry(name="소지품", form="named_slots", slot_values=("검", "랜턴", None))
    op = ResourceOp(axis="소지품", operation="clear", amount="랜턴")

    result = apply_resource_op(stat, op)

    assert result.slot_values == ("검", None, None)


def test_apply_resource_op_named_slots_clear_raises_when_value_not_found():
    """없으면 `InvalidResourceChange`."""
    stat = StatEntry(name="소지품", form="named_slots", slot_values=("검", None))
    op = ResourceOp(axis="소지품", operation="clear", amount="방패")

    with pytest.raises(InvalidResourceChange):
        apply_resource_op(stat, op)


def test_apply_resource_op_named_slots_rejects_operations_other_than_fill_or_clear():
    stat = StatEntry(name="소지품", form="named_slots", slot_values=(None,))
    op = ResourceOp(axis="소지품", operation="delta", amount=1)

    with pytest.raises(InvalidResourceChange):
        apply_resource_op(stat, op)


# ---------------------------------------------------------------------------
# apply_resource_op — tag_list (RULE-11 3/6)
# ---------------------------------------------------------------------------


def test_apply_resource_op_tag_list_add_tag_appends_new_tag():
    """`tag_list` + `add_tag`: 없으면 뒤에 붙인다."""
    stat = StatEntry(name="상태 이상", form="tag_list", tags=("젖음",))
    op = ResourceOp(axis="상태 이상", operation="add_tag", amount="중독")

    result = apply_resource_op(stat, op)

    assert result.tags == ("젖음", "중독")


def test_apply_resource_op_tag_list_add_tag_does_not_duplicate_existing_tag():
    """이미 있으면 중복으로 붙이지 않는다(같은 태그가 두 번 있는 상태를
    만들지 않는다)."""
    stat = StatEntry(name="상태 이상", form="tag_list", tags=("젖음",))
    op = ResourceOp(axis="상태 이상", operation="add_tag", amount="젖음")

    result = apply_resource_op(stat, op)

    assert result.tags == ("젖음",)
    assert len(result.tags) == 1


def test_apply_resource_op_tag_list_remove_tag_removes_matching_tag():
    """`tag_list` + `remove_tag`: 완전히 같은 문자열을 뗀다."""
    stat = StatEntry(name="상태 이상", form="tag_list", tags=("젖음", "중독"))
    op = ResourceOp(axis="상태 이상", operation="remove_tag", amount="젖음")

    result = apply_resource_op(stat, op)

    assert result.tags == ("중독",)


def test_apply_resource_op_tag_list_remove_tag_raises_when_not_found():
    """없으면 `InvalidResourceChange`."""
    stat = StatEntry(name="상태 이상", form="tag_list", tags=("젖음",))
    op = ResourceOp(axis="상태 이상", operation="remove_tag", amount="중독")

    with pytest.raises(InvalidResourceChange):
        apply_resource_op(stat, op)


def test_apply_resource_op_tag_list_rejects_operations_other_than_add_or_remove_tag():
    stat = StatEntry(name="상태 이상", form="tag_list", tags=())
    op = ResourceOp(axis="상태 이상", operation="fill", amount="젖음")

    with pytest.raises(InvalidResourceChange):
        apply_resource_op(stat, op)


# ---------------------------------------------------------------------------
# apply_resource_op — usage_die (RULE-11 3/6)
# ---------------------------------------------------------------------------


def test_apply_resource_op_usage_die_step_down_sets_target_sides():
    """`usage_die` + `step_down`: `current`(면수)가 룰북이 준 목표 면수로
    내려간다. `amount`가 목표 면수다."""
    stat = StatEntry(name="사용 주사위", form="usage_die", current=6)
    op = ResourceOp(axis="사용 주사위", operation="step_down", amount=4)

    result = apply_resource_op(stat, op)

    assert result.current == 4


def test_apply_resource_op_usage_die_step_down_applied_twice_in_sequence():
    """6 → 4 → 2 처럼, 같은 축에 `step_down`을 순서대로 두 번 적용하면
    누적이 아니라 목표 면수로 각각 갈아 끼워진다(절대값 연산, 순서
    의존적)."""
    stat = StatEntry(name="사용 주사위", form="usage_die", current=6)
    first = apply_resource_op(stat, ResourceOp(axis="사용 주사위", operation="step_down", amount=4))
    second = apply_resource_op(
        first, ResourceOp(axis="사용 주사위", operation="step_down", amount=2)
    )

    assert second.current == 2


def test_apply_resource_op_usage_die_deplete_sets_current_to_zero():
    """`usage_die` + `deplete`: `current`를 0으로 만든다(0이 소진이라는
    것은 `entities.py`가 이미 정한 규약)."""
    stat = StatEntry(name="사용 주사위", form="usage_die", current=6)
    op = ResourceOp(axis="사용 주사위", operation="deplete", amount=0)

    result = apply_resource_op(stat, op)

    assert result.current == 0


def test_apply_resource_op_usage_die_rejects_operations_other_than_step_down_or_deplete():
    stat = StatEntry(name="사용 주사위", form="usage_die", current=6)
    op = ResourceOp(axis="사용 주사위", operation="delta", amount=1)

    with pytest.raises(InvalidResourceChange):
        apply_resource_op(stat, op)


# ---------------------------------------------------------------------------
# apply_resource_op — none (어떤 동작도 적용할 수 없다)
# ---------------------------------------------------------------------------


def test_apply_resource_op_none_form_rejects_any_operation():
    """`none` 형태 축에는 어떤 동작도 적용할 수 없다 — `InvalidResourceChange`."""
    stat = StatEntry(name="소지품", form="none", none_kind="discretionary")
    op = ResourceOp(axis="소지품", operation="delta", amount=1)

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


def test_resolve_character_stats_applies_ops_in_recorded_order_and_order_changes_result():
    """같은 축에 연산 세 개가 순서대로 쌓였으면 그 순서대로 적용한다 —
    `step_down`처럼 순서를 바꾸면 결과가 달라지는 연산으로 이 사실을
    확인한다(RULE-09 ordering)."""
    starting = (StatEntry(name="사용 주사위", form="usage_die", current=6),)
    forward_ops = {
        "사용 주사위": (
            ResourceOp(axis="사용 주사위", operation="step_down", amount=4),
            ResourceOp(axis="사용 주사위", operation="step_down", amount=2),
        )
    }
    reversed_ops = {
        "사용 주사위": (
            ResourceOp(axis="사용 주사위", operation="step_down", amount=2),
            ResourceOp(axis="사용 주사위", operation="step_down", amount=4),
        )
    }

    forward_result = resolve_character_stats(starting, forward_ops)
    reversed_result = resolve_character_stats(starting, reversed_ops)

    assert forward_result[0].current == 2
    assert reversed_result[0].current == 4
    assert forward_result[0].current != reversed_result[0].current


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


def test_depleted_axes_usage_die_is_depleted_only_at_exactly_zero():
    """`usage_die`는 `current == 0`일 때만 소진이다."""
    depleted = StatEntry(
        name="사용 주사위",
        form="usage_die",
        current=0,
        depleted_effect_ref="cairn.usage_die_depleted",
    )
    not_depleted = StatEntry(
        name="사용 주사위 2",
        form="usage_die",
        current=2,
        depleted_effect_ref="cairn.usage_die_depleted",
    )

    result = depleted_axes((depleted, not_depleted))

    assert result == (DepletedAxis(axis="사용 주사위", effect_ref="cairn.usage_die_depleted"),)


def test_depleted_axes_clock_is_depleted_when_current_reaches_max():
    """`clock`은 `current >= max`(칸이 다 찼다)일 때 소진이다."""
    full = StatEntry(
        name="위협 시계", form="clock", current=6, max=6, depleted_effect_ref="threat.clock_full"
    )
    not_full = StatEntry(
        name="위협 시계 2", form="clock", current=3, max=6, depleted_effect_ref="threat.clock_full"
    )

    result = depleted_axes((full, not_full))

    assert result == (DepletedAxis(axis="위협 시계", effect_ref="threat.clock_full"),)


def test_depleted_axes_named_slots_is_depleted_when_no_empty_slot_remains():
    """`named_slots`는 빈 슬롯이 0개일 때(전부 찼다) 소진이다."""
    full = StatEntry(
        name="소지품",
        form="named_slots",
        slot_values=("검", "랜턴"),
        depleted_effect_ref="cairn.inventory_full",
    )
    not_full = StatEntry(
        name="소지품 2",
        form="named_slots",
        slot_values=("검", None),
        depleted_effect_ref="cairn.inventory_full",
    )

    result = depleted_axes((full, not_full))

    assert result == (DepletedAxis(axis="소지품", effect_ref="cairn.inventory_full"),)


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


# ---------------------------------------------------------------------------
# fold — 순번이 어긋나면 조용히 넘어가지 않고 예외로 멈춘다(QUAL-01, Task 3)
# ---------------------------------------------------------------------------


def _declared(seq: int) -> tuple[str, dict]:
    """`fold`의 순번 검사만 확인하는 최소 payload — `apply_event`의
    `action_declared` 갈래는 `seq` 말고는 아무 것도 요구하지 않는다."""
    return ("action_declared", {"seq": seq})


def test_fold_empty_event_list_returns_initial_state_without_exception():
    """`fold(session_id, [])` → 예외 없이 `initial_state(session_id)`."""
    state = fold("s1", [])
    assert state == initial_state("s1")


def test_fold_consecutive_sequence_numbers_is_normal():
    """`[0, 1, 2]`는 정상 — 바로 다음 순번(맞닿음)은 어긋남이 아니다."""
    state = fold("s1", [_declared(0), _declared(1), _declared(2)])
    assert state.last_seq == 2


def test_fold_gapped_sequence_numbers_is_normal():
    """`[0, 2, 5]`는 정상 — 사이가 비어 있는 것은 어긋남이 아니다(가시성
    필터 등으로 건너뛴 사건이 있을 수 있다)."""
    state = fold("s1", [_declared(0), _declared(2), _declared(5)])
    assert state.last_seq == 5


def test_fold_duplicate_sequence_number_raises_out_of_order_event():
    """`[0, 1, 1]`은 `OutOfOrderEvent` — 같은 순번이 두 번(겹침)은 정상
    진행이 아니다."""
    with pytest.raises(OutOfOrderEvent) as exc_info:
        fold("s1", [_declared(0), _declared(1), _declared(1)])
    assert exc_info.value.expected_after == 1
    assert exc_info.value.got == 1


def test_fold_regressing_sequence_number_raises_out_of_order_event():
    """`[0, 2, 1]`은 `OutOfOrderEvent` — 되돌아가는 순번은 어긋남이다."""
    with pytest.raises(OutOfOrderEvent) as exc_info:
        fold("s1", [_declared(0), _declared(2), _declared(1)])
    assert exc_info.value.expected_after == 2
    assert exc_info.value.got == 1


def test_fold_folding_same_event_list_twice_gives_same_result():
    """같은 사건 목록으로 `fold`를 두 번 부르면 두 결과가 같다 — 중간
    저장을 쓰지 않으므로 접기 자체가 멱등이다(QUAL-01 idempotency)."""
    events = [_declared(0), _declared(1), _declared(2)]
    first = fold("s1", events)
    second = fold("s1", events)
    assert first == second


# ---------------------------------------------------------------------------
# 2026-08-18 코드 리뷰 CR-01 회귀 — 「쓰기 전 시연 적용」이 막는 것.
#
# 재량 판정·소급 선언의 `amount`는 요청 모델에서 `int`로 못박혀 있는데,
# `named_slots`(Cairn의 `Inventory` — 소급 선언이 유일하게 물려 있는 축)와
# `tag_list`는 **문자열** 양이 필요하다. 축 이름·형태·동작 세 검사는 전부
# 통과하고 양의 타입만 어긋난다.
#
# 고치기 전에는 사건이 먼저 기록되고 **그 뒤** 시트를 접을 때 터졌다. 시트
# 조립이 세션의 캐릭터 전원을 한 번에 접으므로 한 사람의 잘못된 기록 하나가
# 그 세션의 모든 요청을 영구히 500으로 만들었다.
#
# 지금 이 조합은 웹 경로에서 **도달 불가**다 — 출하되는 캐릭터 중 칸 형태
# 축을 가진 사람이 없어(`PLAYER_CHARACTERS`는 전부 numeric),
# `require_axes_on_character`가 먼저 막는다. 칸 형태 축을 가진 캐릭터가
# 생기는 순간(Cairn 계열) 열리므로, 그 앞을 지키는 것이 라우트의 시연
# 적용이다. 그래서 이 시험은 웹이 아니라 **그 시연이 쓰는 함수 자체**를
# 직접 확인한다 — 웹으로 쓰면 축 검사에 걸려 엉뚱한 이유로 통과한다.
# ---------------------------------------------------------------------------


def test_resolve_character_stats_rejects_int_amount_on_a_slot_axis():
    """칸 형태 축에 숫자 양을 접으면 `InvalidResourceChange`로 멈춘다 —
    라우트가 사건을 쓰기 전에 이 함수를 시연 삼아 부르는 이유다."""
    stats = (
        StatEntry(name="Inventory", form="named_slots", slot_values=(None, None, None)),
    )
    ops = {"Inventory": (ResourceOp(axis="Inventory", operation="fill", amount=1),)}

    with pytest.raises(InvalidResourceChange):
        resolve_character_stats(stats, ops)

    # 같은 자리에 문자열 양이면 정상으로 접힌다 — 막은 것이 「칸 형태 전부」가
    # 아니라 「양의 타입이 어긋난 경우」임을 이 짝이 보인다.
    ok = resolve_character_stats(
        stats, {"Inventory": (ResourceOp(axis="Inventory", operation="fill", amount="밧줄"),)}
    )
    assert "밧줄" in ok[0].slot_values
