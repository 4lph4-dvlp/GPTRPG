"""재생용 굴림 도구가 기록된 눈을 그대로 되먹이는지, 소진 시 분명히 실패하는지 확인한다."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from gptrpg.event_log.replay_roller import ReplayExhausted, ReplayRoller, rolls_from_events
from gptrpg.event_log.schema import CheckResolved, ModifierRecord, utc_now_iso
from gptrpg.rules_core.resolution import Modifier, resolve_2d6
from gptrpg.rules_core.resolution_d100 import resolve_d100
from gptrpg.rules_core.resource_change import roll_amount
from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID
from gptrpg.rulebooks.openquest import OPENQUEST_GRADE_BANDS, OPENQUEST_ID
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


def test_replaying_same_recorded_rolls_twice_gives_same_roll_amount_result():
    """같은 눈 목록을 되먹이면 `roll_amount` 결과(정수+눈)가 두 번 다
    같다 — 재생 일치가 주사위식 양에도 성립한다(D-06)."""
    recorded_rolls = [3, 5, 2, 6]

    first_run = ReplayRoller(list(recorded_rolls))
    second_run = ReplayRoller(list(recorded_rolls))

    first_result = roll_amount(first_run, "2d8+1")
    second_result = roll_amount(second_run, "2d8+1")

    assert first_result == second_result


def test_replaying_same_recorded_rolls_twice_gives_same_keep_highest_result():
    """`4d6k3`(D22 원문 예시, 12.1-02)도 같은 눈을 되먹이면 항상 같은
    합계를 낸다 — keep 표기가 결정성을 깨지 않는다(D-04)."""
    recorded_rolls = [2, 6, 1, 4]

    first_run = ReplayRoller(list(recorded_rolls))
    second_run = ReplayRoller(list(recorded_rolls))

    first_result = roll_amount(first_run, "4d6k3")
    second_result = roll_amount(second_run, "4d6k3")

    assert first_result == second_result
    assert first_result == (6 + 4 + 2, (2, 6, 1, 4))  # 낮은 1을 뺀 높은 셋


# ---------------------------------------------------------------------------
# D-04 — 저장된 합계가 규칙 코어를 다시 흘려 나온 값과 어긋나지 않는다.
#
# 나중에 누가 계산을 고쳐도 사건에 남은 합계와 어긋나면 여기서 터진다.
# 커밋된 판 2 픽스처는 열지 않는다 — 판 2 기록에는 대조할 합계가 없다
# (RESEARCH Pitfall 3). `.gptrpg/events.db`도 열지 않는다 — gitignore
# 대상이라 시험이 조용히 건너뛰어지는 함정을 `test_event_schema_migration.py`
# 도크스트링이 이미 경고했다.
# ---------------------------------------------------------------------------


def test_replay_matches_stored_total_for_2d6():
    live = LiveRoller()
    modifiers = [Modifier(type="flat", value=2, source="stat:STR")]

    outcome = resolve_2d6(live, "hack_and_slash", modifiers, target=10)
    event = CheckResolved(
        session_id="s1",
        seq=0,
        schema_version=10,
        caused_by_seq=None,
        recorded_at=utc_now_iso(),
        event_type="check_resolved",
        move=outcome.move,
        rolls=list(outcome.rolls),
        modifiers=[
            ModifierRecord(type=m.type, value=m.value, source=m.source) for m in outcome.modifiers
        ],
        target=outcome.target,
        grade=outcome.grade,
        counts_as_failure=False,
        person_id="p1",
        character_id="bram",
        total=outcome.total,
        rulebook_id=DUNGEONWORLD_LIKE_ID,
    )

    replay = ReplayRoller(event.rolls)
    replayed = resolve_2d6(replay, event.move, modifiers, target=event.target)

    assert replayed.total == event.total


def test_replay_matches_stored_total_for_d100():
    live = LiveRoller()
    modifiers = [Modifier(type="flat", value=5, source="stat:STR")]

    outcome = resolve_d100(live, "melee", modifiers, skill=50, bands=OPENQUEST_GRADE_BANDS)
    event = CheckResolved(
        session_id="s1",
        seq=0,
        schema_version=10,
        caused_by_seq=None,
        recorded_at=utc_now_iso(),
        event_type="check_resolved",
        move=outcome.move,
        rolls=list(outcome.rolls),
        modifiers=[
            ModifierRecord(type=m.type, value=m.value, source=m.source) for m in outcome.modifiers
        ],
        target=outcome.target,
        grade=outcome.grade,
        counts_as_failure=False,
        person_id="p1",
        character_id="bram",
        total=outcome.total,
        rulebook_id=OPENQUEST_ID,
    )

    replay = ReplayRoller(event.rolls)
    replayed = resolve_d100(
        replay, event.move, modifiers, skill=50, bands=OPENQUEST_GRADE_BANDS
    )

    assert replayed.total == event.total
