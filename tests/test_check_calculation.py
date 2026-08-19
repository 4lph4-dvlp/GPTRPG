"""판정 눈이 합계가 되는 과정을 조각으로 만드는 빌더 시험 (Phase 12.2, D-08/D-09/D-10).

`_BUILDERS`와 `session_actor.actor._RESOLVERS`의 열쇠 집합이 같다는
불변식을 포함한다 — 굴릴 수 있는 방식은 반드시 그릴 수도 있어야 한다.
"""

import pytest

from gptrpg.rules_core.check_calculation import (
    ROLE_DIE,
    ROLE_FLAT,
    ROLE_PERCENTILE,
    ROLE_TENS,
    ROLE_UNITS,
    ROLL_OVER,
    ROLL_UNDER,
    MalformedRollRecord,
    UnknownResolutionMethod,
    _BUILDERS,
    build_check_calculation,
    direction_for,
)
from gptrpg.rules_core.resolution import FLAT, Modifier
from gptrpg.rules_core.resolution_d100 import BONUS_DICE
from gptrpg.rules_core.rulebook import D100_ROLL_UNDER, D20_ROLL_UNDER, TWO_D6
from gptrpg.session_actor.actor import _RESOLVERS


def test_direction_for_two_d6_is_roll_over():
    assert direction_for(TWO_D6) == ROLL_OVER


def test_direction_for_d100_and_d20_roll_under_is_roll_under():
    assert direction_for(D100_ROLL_UNDER) == ROLL_UNDER
    assert direction_for(D20_ROLL_UNDER) == ROLL_UNDER


def test_direction_for_unknown_method_raises():
    with pytest.raises(UnknownResolutionMethod):
        direction_for("no_such_method")


def test_every_resolver_has_a_segment_builder():
    """굴릴 수 있는 판정 방식은 반드시 그릴 수도 있다."""
    assert set(_BUILDERS.keys()) == set(_RESOLVERS.keys())


def test_build_two_d6_orders_die_then_flat_segments():
    modifiers = (Modifier(type=FLAT, value=2, source="stat:STR"),)
    calc = build_check_calculation(
        resolution_method=TWO_D6, rolls=[4, 3], modifiers=modifiers, total=9, target=10
    )
    assert calc.direction == ROLL_OVER
    assert calc.total == 9
    assert calc.target == 10
    assert len(calc.rows) == 1
    row = calc.rows[0]
    assert row.total == 9
    roles = [segment.role for segment in row.segments]
    assert roles == [ROLE_DIE, ROLE_DIE, ROLE_FLAT]
    values = [segment.value for segment in row.segments]
    assert values == [4, 3, 2]
    assert row.segments[-1].source == "stat:STR"


def test_build_d100_roll_under_percentile_is_37_not_10():
    modifiers = (Modifier(type=FLAT, value=2, source="difficulty:hard"),)
    calc = build_check_calculation(
        resolution_method=D100_ROLL_UNDER, rolls=[3, 7], modifiers=modifiers, total=39, target=55
    )
    assert calc.direction == ROLL_UNDER
    assert calc.total == 39
    assert calc.target == 55
    row = calc.rows[0]
    roles = [segment.role for segment in row.segments]
    assert roles == [ROLE_TENS, ROLE_UNITS, ROLE_PERCENTILE, ROLE_FLAT]
    values = [segment.value for segment in row.segments]
    assert values == [3, 7, 37, 2]
    assert 10 not in values


def test_target_shift_and_bonus_dice_do_not_become_segments():
    """TARGET_SHIFT·PUSH·BONUS_DICE(0 합)는 조각으로 안 나온다."""
    modifiers = (
        Modifier(type=FLAT, value=1, source="s"),
        Modifier(type="target_shift", value=5, source="difficulty:hard"),
    )
    calc = build_check_calculation(
        resolution_method=D100_ROLL_UNDER, rolls=[1, 2], modifiers=modifiers, total=13, target=60
    )
    roles = [segment.role for segment in calc.rows[0].segments]
    assert "target_shift" not in roles
    assert roles.count(ROLE_FLAT) == 1


def test_two_d6_malformed_roll_count_raises():
    with pytest.raises(MalformedRollRecord):
        build_check_calculation(
            resolution_method=TWO_D6, rolls=[1, 2, 3], modifiers=(), total=6, target=8
        )


def test_d100_malformed_roll_count_raises():
    with pytest.raises(MalformedRollRecord):
        build_check_calculation(
            resolution_method=D100_ROLL_UNDER, rolls=[1], modifiers=(), total=1, target=50
        )


def test_d100_with_bonus_dice_not_yet_supported_raises_malformed():
    modifiers = (Modifier(type=BONUS_DICE, value=1, source="bonus"),)
    with pytest.raises(MalformedRollRecord):
        build_check_calculation(
            resolution_method=D100_ROLL_UNDER,
            rolls=[3, 5, 7],
            modifiers=modifiers,
            total=57,
            target=60,
        )


def test_unknown_resolution_method_raises():
    with pytest.raises(UnknownResolutionMethod):
        build_check_calculation(
            resolution_method="no_such_method", rolls=[1, 2], modifiers=(), total=3, target=8
        )
