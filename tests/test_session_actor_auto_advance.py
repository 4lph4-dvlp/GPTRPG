"""실패 3회에 `SessionActor`가 스스로 위협 시계를 돌리고 집계를 남긴다 (RIG-04, D-44).

`tests/test_session_actor.py`와 같은 픽스처 결로 쓴다 — `_FixedRoller`로 판정
결과를 고정하고, `SessionRegistry(store).get_or_create(...)` 대신 여기서는
`clock_id`/`report_dir`를 직접 넘길 수 있어야 하므로 `SessionActor`를 바로
만든다.

2d6 등급 경계(`grading.grade_for_total`): target=10, weak_hit_band=3 →
total < 7 이면 miss(counts_as_failure=True), total >= 7이면 성공 등급이다.
`_FAILING_ROLL = [1, 1]`(합계 2, miss) / `_SUCCESS_ROLL = [6, 6]`(합계 12,
strong_hit)로 원하는 결과를 고정한다.
"""

import json

import pytest

from gptrpg.event_log.store import EventStore
from gptrpg.rules_core.resolution import Modifier
from gptrpg.session_actor.actor import (
    AdvanceClock,
    AUTO_ADVANCE_FAILURE_THRESHOLD,
    CommandRejected,
    ResolveCheck,
    SessionActor,
)
from gptrpg.session_actor.projection import rebuild_state


class _FixedRoller:
    """테스트용 고정 눈 도구."""

    def __init__(self, values: list[int]) -> None:
        self._values = iter(values)

    def roll_d6(self) -> int:
        return next(self._values)


_FAILING_ROLL = [1, 1]  # 합계 2 -> miss (counts_as_failure=True)
_SUCCESS_ROLL = [6, 6]  # 합계 12 -> strong_hit (counts_as_failure=False)


def _make_actor(tmp_db_path, values: list[int], report_dir=None) -> tuple[EventStore, SessionActor]:
    store = EventStore(tmp_db_path)
    store.initialize()
    actor = SessionActor(store, "s1", _FixedRoller(values), report_dir=report_dir)
    actor.start()
    return store, actor


def _resolve_check() -> ResolveCheck:
    return ResolveCheck(move="문을 부순다", modifiers=(Modifier(type="flat", value=0, source="없음"),))


async def test_two_failures_do_not_trigger_clock_advance(tmp_db_path):
    store, actor = _make_actor(tmp_db_path, values=_FAILING_ROLL * 2)
    try:
        await actor.submit(_resolve_check())
        await actor.submit(_resolve_check())
    finally:
        await actor.stop()

    events = store.read_events("s1")
    store.close()
    assert not any(e.event_type == "clock_advanced" for e in events)


async def test_third_failure_triggers_exactly_one_clock_advanced_with_fail_counter_trigger(
    tmp_db_path,
):
    store, actor = _make_actor(tmp_db_path, values=_FAILING_ROLL * 3)
    try:
        await actor.submit(_resolve_check())
        await actor.submit(_resolve_check())
        third_seq = await actor.submit(_resolve_check())
    finally:
        await actor.stop()

    events = store.read_events("s1")
    store.close()

    clock_events = [e for e in events if e.event_type == "clock_advanced"]
    assert len(clock_events) == 1
    assert clock_events[0].trigger == "fail_counter"
    assert clock_events[0].segment_index == 1  # 직전 값(0) + 1
    assert clock_events[0].caused_by_seq == third_seq


async def test_submit_returns_the_check_seq_not_the_auto_generated_clock_seq(tmp_db_path):
    store, actor = _make_actor(tmp_db_path, values=_FAILING_ROLL * 3)
    try:
        await actor.submit(_resolve_check())
        await actor.submit(_resolve_check())
        third_seq = await actor.submit(_resolve_check())
    finally:
        await actor.stop()

    events = store.read_events("s1")
    store.close()

    check_events = [e for e in events if e.event_type == "check_resolved"]
    assert third_seq == check_events[2].seq
    clock_events = [e for e in events if e.event_type == "clock_advanced"]
    assert third_seq != clock_events[0].seq


async def test_after_auto_advance_fails_since_clock_resets_and_can_trigger_again(tmp_db_path):
    store, actor = _make_actor(tmp_db_path, values=_FAILING_ROLL * 6)
    try:
        for _ in range(3):
            await actor.submit(_resolve_check())
        assert actor.state.fails_since_clock == 0
        assert actor.state.clock_segment == 1

        for _ in range(3):
            await actor.submit(_resolve_check())
        assert actor.state.fails_since_clock == 0
        assert actor.state.clock_segment == 2

        events = store.read_events("s1")
    finally:
        await actor.stop()
        store.close()

    clock_events = [e for e in events if e.event_type == "clock_advanced"]
    assert len(clock_events) == 2


async def test_success_checks_never_advance_the_clock(tmp_db_path):
    store, actor = _make_actor(tmp_db_path, values=_SUCCESS_ROLL * 10)
    try:
        for _ in range(10):
            await actor.submit(_resolve_check())
    finally:
        await actor.stop()

    events = store.read_events("s1")
    store.close()
    assert not any(e.event_type == "clock_advanced" for e in events)


async def test_report_snapshot_updates_after_each_submitted_command(tmp_db_path, tmp_path):
    report_dir = tmp_path / "reports"
    store, actor = _make_actor(tmp_db_path, values=_FAILING_ROLL * 3, report_dir=report_dir)
    try:
        await actor.submit(_resolve_check())
        report_after_first = json.loads((report_dir / "s1.json").read_text(encoding="utf-8"))
        assert report_after_first["failure_count"] == 1
        assert report_after_first["clock_advances"] == 0

        await actor.submit(_resolve_check())
        await actor.submit(_resolve_check())
        report_after_third = json.loads((report_dir / "s1.json").read_text(encoding="utf-8"))
        assert report_after_third["failure_count"] == 3
        assert report_after_third["clock_advances"] == 1
    finally:
        await actor.stop()
        store.close()


async def test_unwritable_report_dir_does_not_block_submit_or_event_recording(tmp_db_path, tmp_path):
    # report_dir 자리에 이미 평범한 파일이 있으면 write_report의 mkdir이 실패한다 —
    # 이 상황에서도 submit은 정상 순번을 돌려주고 사건은 기록에 남아야 한다.
    unwritable = tmp_path / "not_a_directory"
    unwritable.write_text("이미 파일이다")

    store, actor = _make_actor(tmp_db_path, values=_FAILING_ROLL, report_dir=unwritable)
    try:
        seq = await actor.submit(_resolve_check())
    finally:
        await actor.stop()

    events = store.read_events("s1")
    store.close()
    assert seq == 0
    assert len(events) == 1
    assert events[0].event_type == "check_resolved"


async def test_invalid_command_still_rejected_with_report_dir_configured(tmp_db_path, tmp_path):
    """자동 진행/자동 저장 훅이 들어와도 기존 거부 경로가 깨지지 않는다."""
    store, actor = _make_actor(tmp_db_path, values=[], report_dir=tmp_path / "reports")
    try:
        with pytest.raises(CommandRejected):
            await actor.submit(
                ResolveCheck(move="", modifiers=(), rulebook_id="unknown-rulebook")
            )
    finally:
        await actor.stop()
        store.close()


def test_auto_advance_failure_threshold_constant_is_three():
    assert AUTO_ADVANCE_FAILURE_THRESHOLD == 3


async def test_advancing_clock_past_segment_count_is_never_rejected(tmp_db_path):
    """위협 시계에 코드 상한선이 없다는 D-47을 테스트로 못박는다.

    전체 칸 수(4)보다 많은 다섯 번을 `AdvanceClock`으로 밀어 넣어도 다섯 번
    전부 받아들여지고, 재구성된 상태의 `clock_segment`가 5가 된다 — 파국
    도달을 코드가 막는 조건문이 어디에도 없다는 것을 이 테스트가 잡는다.
    """
    store, actor = _make_actor(tmp_db_path, values=[])
    try:
        for segment_index in range(1, 6):
            await actor.submit(
                AdvanceClock(clock_id="threat", segment_index=segment_index, trigger="condition")
            )
    finally:
        await actor.stop()

    state = rebuild_state(store, "s1")
    store.close()
    assert state.clock_segment == 5
