"""`roll_amount`(고정 정수/주사위식 → 정수+눈)와 세 굴림 도구의 `roll_die`
확장을 확인한다(D-06, 12-02 Task 1).

`ReplayRoller`(기록된 눈 목록)를 결정론적 굴림 도구로 쓴다 — `LiveRoller`는
범위 검사와 `ValueError` 갈래만 본다.
"""

import pytest

from gptrpg.event_log.replay_roller import ReplayExhausted, ReplayRoller
from gptrpg.rules_core.resource_change import (
    MAX_DICE_COUNT,
    MAX_DIE_SIDES,
    InvalidResourceChange,
    parse_dice_expr,
    roll_amount,
)
from gptrpg.session_actor.live_roller import LiveRoller


class _CountingRoller:
    """`roll_die` 호출 횟수를 세는 즉석 굴림 도구 — 상한 초과 시 굴림 도구를
    한 번도 안 부르는지 확인하는 데 쓴다."""

    def __init__(self, values: list[int]) -> None:
        self._values = iter(values)
        self.call_count = 0

    def roll_die(self, sides: int) -> int:
        self.call_count += 1
        return next(self._values)


# ---------------------------------------------------------------------------
# 고정 정수 — 굴림 도구를 부르지 않는다
# ---------------------------------------------------------------------------


def test_roll_amount_with_positive_int_returns_it_unchanged_with_no_rolls():
    roller = _CountingRoller([])
    result = roll_amount(roller, 6)
    assert result == (6, ())
    assert roller.call_count == 0


def test_roll_amount_with_negative_int_returns_it_unchanged_with_no_rolls():
    roller = _CountingRoller([])
    result = roll_amount(roller, -6)
    assert result == (-6, ())
    assert roller.call_count == 0


# ---------------------------------------------------------------------------
# 주사위식 — 굴림 도구를 통해서만 정수가 된다
# ---------------------------------------------------------------------------


def test_roll_amount_with_single_die_expression_rolls_once():
    roller = ReplayRoller([4])
    result = roll_amount(roller, "1d6")
    assert result == (4, (4,))


def test_roll_amount_with_negative_single_die_expression_negates_result_but_not_the_recorded_roll():
    """부호는 결과에만 붙는다 — 기록되는 눈은 굴린 값 그대로다."""
    roller = ReplayRoller([4])
    result = roll_amount(roller, "-1d6")
    assert result == (-4, (4,))


def test_roll_amount_with_multi_die_and_flat_modifier_sums_rolls_and_adds_flat():
    roller = ReplayRoller([3, 5])
    result = roll_amount(roller, "2d8+1")
    assert result == (3 + 5 + 1, (3, 5))


def test_roll_amount_with_multi_die_and_negative_flat_modifier():
    roller = ReplayRoller([6, 2])
    result = roll_amount(roller, "2d6-1")
    assert result == (6 + 2 - 1, (6, 2))


# ---------------------------------------------------------------------------
# 잘못된 문법 — InvalidResourceChange
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_expr", ["d6", "1d", "abc", ""])
def test_roll_amount_with_malformed_dice_expression_raises(bad_expr):
    roller = _CountingRoller([])
    with pytest.raises(InvalidResourceChange):
        roll_amount(roller, bad_expr)
    assert roller.call_count == 0


# ---------------------------------------------------------------------------
# 상한 초과 — InvalidResourceChange이고, 굴림 도구 호출 횟수가 0이다
# ---------------------------------------------------------------------------


def test_roll_amount_exceeding_max_dice_count_raises_without_rolling():
    roller = _CountingRoller([1] * 999)
    over_count = f"{MAX_DICE_COUNT + 1}d6"
    with pytest.raises(InvalidResourceChange):
        roll_amount(roller, over_count)
    assert roller.call_count == 0


def test_roll_amount_exceeding_max_die_sides_raises_without_rolling():
    roller = _CountingRoller([1])
    over_sides = f"1d{MAX_DIE_SIDES + 1}"
    with pytest.raises(InvalidResourceChange):
        roll_amount(roller, over_sides)
    assert roller.call_count == 0


def test_roll_amount_with_999d6_and_1d9999_both_exceed_limits_without_rolling():
    """acceptance criteria가 명시한 두 구체 사례 — 상한 초과 시 굴림 도구
    호출 횟수가 0이다."""
    roller_a = _CountingRoller([1] * 999)
    with pytest.raises(InvalidResourceChange):
        roll_amount(roller_a, "999d6")
    assert roller_a.call_count == 0

    roller_b = _CountingRoller([1])
    with pytest.raises(InvalidResourceChange):
        roll_amount(roller_b, "1d9999")
    assert roller_b.call_count == 0


# ---------------------------------------------------------------------------
# keep 표기(12.1-02, D-04) — parse_dice_expr
# ---------------------------------------------------------------------------


def test_parse_dice_expr_with_keep_highest_returns_count_sides_keep_and_flat():
    assert parse_dice_expr("4d6k3") == (4, 6, 3, True, 0)


def test_parse_dice_expr_with_keep_lowest_returns_keep_highest_false():
    assert parse_dice_expr("4d6kl3") == (4, 6, 3, False, 0)


def test_parse_dice_expr_without_keep_returns_none_for_keep_count():
    assert parse_dice_expr("1d6") == (1, 6, None, True, 0)


def test_parse_dice_expr_with_keep_exceeding_roll_count_raises():
    with pytest.raises(InvalidResourceChange):
        parse_dice_expr("4d6k5")


def test_parse_dice_expr_with_keep_count_over_max_dice_count_raises():
    with pytest.raises(InvalidResourceChange):
        parse_dice_expr(f"{MAX_DICE_COUNT + 1}d6k3")


def test_parse_dice_expr_with_flat_modifier_after_keep():
    assert parse_dice_expr("4d6k3+1") == (4, 6, 3, True, 1)


# ---------------------------------------------------------------------------
# roll_amount에 keep 표기 — D22 원문 예시 4d6k3(넷 굴려 높은 셋)
# ---------------------------------------------------------------------------


def test_roll_amount_with_keep_highest_sums_only_top_k_but_returns_all_rolls():
    """`4d6k3` — 합계는 높은 셋의 합, 반환된 눈 튜플은 네 개 전부다(D-04)."""
    roller = ReplayRoller([1, 5, 3, 6])
    total, rolls = roll_amount(roller, "4d6k3")
    assert rolls == (1, 5, 3, 6)  # 굴린 순서 그대로, 전부
    assert total == 5 + 3 + 6  # 낮은 1을 뺀 높은 셋


def test_roll_amount_with_keep_lowest_sums_only_bottom_k():
    roller = ReplayRoller([1, 5, 3, 6])
    total, rolls = roll_amount(roller, "4d6kl3")
    assert rolls == (1, 5, 3, 6)
    assert total == 1 + 5 + 3  # 높은 6을 뺀 낮은 셋


def test_roll_amount_with_keep_and_replay_is_deterministic():
    """같은 눈을 되먹이면 `4d6k3`의 합계가 항상 같다(D-04, ReplayRoller)."""
    recorded = [2, 4, 6, 1]
    first = roll_amount(ReplayRoller(list(recorded)), "4d6k3")
    second = roll_amount(ReplayRoller(list(recorded)), "4d6k3")
    assert first == second


def test_roll_amount_with_2d8_plus_1_still_reads_as_ndm_flat_no_keep():
    """하위 호환 — 기존 `NdM±flat` 식은 keep 없이 그대로 동작한다."""
    roller = ReplayRoller([3, 5])
    total, rolls = roll_amount(roller, "2d8+1")
    assert (total, rolls) == (3 + 5 + 1, (3, 5))


# ---------------------------------------------------------------------------
# LiveRoller.roll_die — 실제 범위·예외 갈래만
# ---------------------------------------------------------------------------


def test_live_roller_roll_die_always_within_range():
    roller = LiveRoller()
    for _ in range(200):
        value = roller.roll_die(6)
        assert 1 <= value <= 6


def test_live_roller_roll_die_with_larger_sides_stays_within_range():
    roller = LiveRoller()
    for _ in range(200):
        value = roller.roll_die(20)
        assert 1 <= value <= 20


@pytest.mark.parametrize("bad_sides", [0, -1])
def test_live_roller_roll_die_with_non_positive_sides_raises(bad_sides):
    roller = LiveRoller()
    with pytest.raises(ValueError):
        roller.roll_die(bad_sides)


# ---------------------------------------------------------------------------
# ReplayRoller — 세 메서드가 같은 반복자를 공유한다
# ---------------------------------------------------------------------------


def test_replay_roller_roll_die_shares_iterator_with_roll_d6_and_roll_tens():
    replay = ReplayRoller([3, 5, 2])
    assert replay.roll_d6() == 3
    assert replay.roll_die(8) == 5
    assert replay.roll_tens() == 2


def test_replay_roller_roll_die_raises_replay_exhausted_when_rolls_run_out():
    replay = ReplayRoller([3])
    replay.roll_die(6)
    with pytest.raises(ReplayExhausted):
        replay.roll_die(6)


@pytest.mark.parametrize("bad_sides", [0, -1])
def test_replay_roller_roll_die_with_non_positive_sides_raises_value_error(bad_sides):
    replay = ReplayRoller([3])
    with pytest.raises(ValueError):
        replay.roll_die(bad_sides)
