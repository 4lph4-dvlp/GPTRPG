"""d100 판정 한 번이 명령 -> 룰북 선언 -> 순수 함수 -> CheckOutcome ->
check_resolved 사건 -> 저장 -> 재구성까지 실제로 도는 것을 증명하는 트레이서.

`ScriptedPercentileRoller`는 `tests/test_resolution_edges.py`의 `ScriptedRoller`
관례를 따른다 — 상속 없이 구조적 타이핑(PEP 544)만으로 `PercentileRoller`를
만족한다.
"""

import pytest

from gptrpg.rules_core.resolution import Modifier
from gptrpg.rules_core.resolution_d100 import percentile_value
from gptrpg.rulebooks.openquest import OPENQUEST_ID
from gptrpg.session_actor.actor import CommandRejected, ResolveCheck, SessionActor
from gptrpg.session_actor.projection import rebuild_state


class ScriptedPercentileRoller:
    """미리 넣은 tens/units 목록을 순서대로 꺼내는 가짜 백분위 굴림 도구.

    `PercentileRoller`를 상속할 필요가 없다 — `roll_tens(self) -> int`/
    `roll_units(self) -> int` 시그니처만 맞으면 통과한다(PEP 544).
    """

    def __init__(self, tens_values, units_values):
        self._tens = list(tens_values)
        self._units = list(units_values)

    def roll_tens(self) -> int:
        return self._tens.pop(0)

    def roll_units(self) -> int:
        return self._units.pop(0)


def _make_actor(tmp_db_path, roller):
    from gptrpg.event_log.store import EventStore

    store = EventStore(tmp_db_path)
    store.initialize()
    actor = SessionActor(store, "s1", roller)
    actor.start()
    return store, actor


async def test_openquest_success_check_records_and_reconstructs(tmp_db_path):
    roller = ScriptedPercentileRoller(tens_values=[3], units_values=[4])
    store, actor = _make_actor(tmp_db_path, roller)
    try:
        seq = await actor.submit(
            ResolveCheck(
                move="perceive",
                modifiers=(),
                target=50,
                rulebook_id=OPENQUEST_ID,
            )
        )
    finally:
        await actor.stop()

    assert seq == 0
    events = store.read_events("s1")
    assert len(events) == 1
    event = events[0]
    assert event.event_type == "check_resolved"
    assert event.grade == "success"
    assert event.rolls == [3, 4]
    assert event.target == 50
    assert event.counts_as_failure is False
    assert event.modifiers == []

    state = rebuild_state(store, "s1")
    store.close()
    assert state.check_count == 1
    assert state.failure_count == 0
    assert state.last_grade == "success"


async def test_openquest_doubles_over_skill_is_fumble_and_counts_as_failure(tmp_db_path):
    roller = ScriptedPercentileRoller(tens_values=[7], units_values=[7])
    store, actor = _make_actor(tmp_db_path, roller)
    try:
        await actor.submit(
            ResolveCheck(
                move="perceive",
                modifiers=(),
                target=50,
                rulebook_id=OPENQUEST_ID,
            )
        )
    finally:
        await actor.stop()

    events = store.read_events("s1")
    event = events[0]
    assert event.grade == "fumble"
    assert event.counts_as_failure is True

    state = rebuild_state(store, "s1")
    store.close()
    assert state.failure_count == 1


def test_percentile_value_reads_zero_zero_as_one_hundred():
    assert percentile_value(0, 0) == 100
    assert percentile_value(0, 0) != 0


async def test_unknown_rulebook_id_is_rejected_and_appends_nothing(tmp_db_path):
    roller = ScriptedPercentileRoller(tens_values=[3], units_values=[4])
    store, actor = _make_actor(tmp_db_path, roller)
    next_seq_before = store.next_seq("s1")
    try:
        with pytest.raises(CommandRejected):
            await actor.submit(
                ResolveCheck(
                    move="perceive",
                    modifiers=(),
                    target=50,
                    rulebook_id="no_such_rulebook",
                )
            )
    finally:
        await actor.stop()
        store.close()

    verify_store_events = _read_events_fresh(tmp_db_path)
    assert verify_store_events == []
    assert next_seq_before == 0


def _read_events_fresh(tmp_db_path):
    from gptrpg.event_log.store import EventStore

    store = EventStore(tmp_db_path)
    store.initialize()
    try:
        return store.read_events("s1")
    finally:
        store.close()


async def test_existing_two_d6_path_without_rulebook_id_behaves_like_phase_1(tmp_db_path):
    class _FixedD6Roller:
        def __init__(self, values):
            self._values = iter(values)

        def roll_d6(self) -> int:
            return next(self._values)

    store, actor = _make_actor(tmp_db_path, _FixedD6Roller([3, 4]))
    try:
        seq = await actor.submit(
            ResolveCheck(
                move="문을 부순다",
                modifiers=(Modifier(type="flat", value=1, source="힘"),),
            )
        )
    finally:
        await actor.stop()

    assert seq == 0
    events = store.read_events("s1")
    assert events[0].event_type == "check_resolved"

    state = rebuild_state(store, "s1")
    store.close()
    assert state.check_count == 1
