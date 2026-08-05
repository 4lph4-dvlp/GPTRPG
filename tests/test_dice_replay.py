"""재생용 굴림 도구가 기록된 눈을 그대로 되먹이는지, 소진 시 분명히 실패하는지 확인한다."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from gptrpg.event_log.replay_roller import ReplayExhausted, ReplayRoller, rolls_from_events
from gptrpg.rules_core.resolution import Modifier, resolve_2d6
from gptrpg.session_actor.live_roller import LiveRoller


class _RecordedEvent:
    """rolls_from_events가 요구하는 최소 모양(seq, rolls)만 흉내내는 가짜 사건."""

    def __init__(self, seq: int, rolls: list[int]) -> None:
        self.seq = seq
        self.rolls = rolls


def test_live_roller_always_returns_one_to_six():
    roller = LiveRoller()
    for _ in range(200):
        value = roller.roll_d6()
        assert 1 <= value <= 6


def test_replay_reproduces_three_checks_recorded_from_live_rolls():
    live = LiveRoller()
    modifiers = [Modifier(type="flat", value=1, source="테스트")]

    original_outcomes = [
        resolve_2d6(live, "문을 부순다", modifiers, target=10) for _ in range(3)
    ]
    events = [
        _RecordedEvent(seq=index, rolls=list(outcome.rolls))
        for index, outcome in enumerate(original_outcomes)
    ]
    recorded_rolls = rolls_from_events(events)

    replay = ReplayRoller(recorded_rolls)
    for original in original_outcomes:
        replayed = resolve_2d6(replay, "문을 부순다", modifiers, target=10)
        assert replayed.rolls == original.rolls
        assert replayed.total == original.total
        assert replayed.grade == original.grade


def test_replay_roller_raises_replay_exhausted_when_rolls_run_out():
    replay = ReplayRoller([3, 4])
    replay.roll_d6()
    replay.roll_d6()
    with pytest.raises(ReplayExhausted):
        replay.roll_d6()


@given(
    roll_pairs=st.lists(
        st.tuples(st.integers(min_value=1, max_value=6), st.integers(min_value=1, max_value=6)),
        min_size=1,
        max_size=5,
    ),
    modifier_value=st.integers(min_value=-5, max_value=5),
)
def test_replaying_same_recorded_rolls_twice_is_always_deterministic(roll_pairs, modifier_value):
    flat_rolls = [roll for pair in roll_pairs for roll in pair]
    modifiers = [Modifier(type="flat", value=modifier_value, source="속성기반")]

    first_run = ReplayRoller(list(flat_rolls))
    second_run = ReplayRoller(list(flat_rolls))

    first_outcomes = [
        resolve_2d6(first_run, "테스트", modifiers, target=10) for _ in roll_pairs
    ]
    second_outcomes = [
        resolve_2d6(second_run, "테스트", modifiers, target=10) for _ in roll_pairs
    ]

    assert first_outcomes == second_outcomes
