"""판정 눈이 합계가 되는 과정을 조각으로 만드는 빌더 시험 (Phase 12.2, D-08/D-09/D-10).

`_BUILDERS`와 `session_actor.actor._RESOLVERS`의 열쇠 집합이 같다는
불변식을 포함한다 — 굴릴 수 있는 방식은 반드시 그릴 수도 있어야 한다.

**버려진 눈 표시(D-11)와 다시 굴림 줄 나눔(D-12)은 지금 브라우저에서
도달할 수 없다.** `reroll_2d6`/`push_d100`은 시험에서만 불리고, `BONUS_DICE`
수정치를 만드는 제품 코드가 저장소에 하나도 없다(12.2-03-PLAN.md 「조사가
확정한 것」). 이 파일의 보너스·페널티·다시 굴림 시험이 두 표시의 유일한
검증 수단이다.
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


def test_d100_bonus_dice_with_insufficient_rolls_still_raises_malformed():
    """12.2-01은 BONUS_DICE 자체를 아예 못 만들었지만, 이제는 만들되 눈
    개수가 구조와 안 맞으면(십의 자리가 모자라면) 여전히 거부한다."""
    modifiers = (Modifier(type=BONUS_DICE, value=1, source="bonus"),)
    with pytest.raises(MalformedRollRecord):
        build_check_calculation(
            resolution_method=D100_ROLL_UNDER,
            rolls=[3, 7],  # dice_delta=1이면 십의 자리 2개+일의 자리 1개(3개) 필요
            modifiers=modifiers,
            total=37,
            target=60,
        )


# --- 버려진 눈 표시(D-11) -----------------------------------------------------


def test_bonus_dice_marks_the_larger_tens_as_discarded():
    """보너스 다이스: 작은 십의 자리가 채택되고, 큰 것이 버려짐 표시된다."""
    modifiers = (Modifier(type=BONUS_DICE, value=1, source="유리함"),)
    calc = build_check_calculation(
        resolution_method=D100_ROLL_UNDER,
        rolls=[3, 8, 7],
        modifiers=modifiers,
        total=37,
        target=60,
    )
    assert len(calc.rows) == 1
    segments = calc.rows[0].segments
    tens_segments = [s for s in segments if s.role == ROLE_TENS]
    assert [s.value for s in tens_segments] == [3, 8]
    assert [s.discarded for s in tens_segments] == [False, True]
    percentile = next(s for s in segments if s.role == ROLE_PERCENTILE)
    assert percentile.value == 37
    assert calc.rows[0].total == 37


def test_penalty_dice_marks_the_smaller_tens_as_discarded():
    """페널티 다이스: 큰 십의 자리가 채택되고, 작은 것(배열의 첫 값)이
    버려짐 표시된다 — 첫 값을 채택으로 가정하면 여기서 틀린다."""
    modifiers = (Modifier(type=BONUS_DICE, value=-1, source="불리함"),)
    calc = build_check_calculation(
        resolution_method=D100_ROLL_UNDER,
        rolls=[3, 8, 7],
        modifiers=modifiers,
        total=87,
        target=60,
    )
    segments = calc.rows[0].segments
    tens_segments = [s for s in segments if s.role == ROLE_TENS]
    assert [s.value for s in tens_segments] == [3, 8]
    assert tens_segments[0].discarded is True
    assert tens_segments[1].discarded is False
    percentile = next(s for s in segments if s.role == ROLE_PERCENTILE)
    assert percentile.value == 87


def test_tied_tens_values_discard_only_the_later_duplicate():
    """채택 후보가 같은 값 둘이면 앞 자리가 채택되고, 채택 조각은 정확히 하나다."""
    modifiers = (Modifier(type=BONUS_DICE, value=1, source="유리함"),)
    calc = build_check_calculation(
        resolution_method=D100_ROLL_UNDER,
        rolls=[5, 5, 7],
        modifiers=modifiers,
        total=57,
        target=60,
    )
    tens_segments = [s for s in calc.rows[0].segments if s.role == ROLE_TENS]
    assert [s.discarded for s in tens_segments] == [False, True]
    assert sum(1 for s in tens_segments if not s.discarded) == 1


# --- 다시 굴림 줄 나눔(D-12) ---------------------------------------------------


def test_reroll_2d6_splits_into_two_rows_with_total_on_the_last():
    modifiers = (Modifier(type=FLAT, value=2, source="stat:STR"),)
    calc = build_check_calculation(
        resolution_method=TWO_D6, rolls=[4, 3, 6, 5], modifiers=modifiers, total=13, target=10
    )
    assert len(calc.rows) == 2
    assert calc.total == 13
    first, second = calc.rows
    assert [s.value for s in first.segments] == [4, 3]
    assert first.total is None
    assert [s.value for s in second.segments] == [6, 5, 2]
    assert second.total == 13


def test_push_d100_splits_into_two_rows_with_total_on_the_last():
    modifiers = (Modifier(type=FLAT, value=2, source="difficulty:hard"),)
    calc = build_check_calculation(
        resolution_method=D100_ROLL_UNDER,
        rolls=[8, 2, 3, 7],
        modifiers=modifiers,
        total=39,
        target=60,
    )
    assert len(calc.rows) == 2
    first, second = calc.rows
    assert [s.role for s in first.segments] == [ROLE_TENS, ROLE_UNITS, ROLE_PERCENTILE]
    assert [s.value for s in first.segments] == [8, 2, 82]
    assert first.total is None
    assert [s.role for s in second.segments] == [ROLE_TENS, ROLE_UNITS, ROLE_PERCENTILE, ROLE_FLAT]
    assert [s.value for s in second.segments] == [3, 7, 37, 2]
    assert second.total == 39
    assert calc.total == 39


def test_ordinary_check_still_has_exactly_one_row():
    """다시 굴림이 없는 보통 판정은 줄이 하나다 — 회귀 없음."""
    calc = build_check_calculation(
        resolution_method=TWO_D6, rolls=[4, 3], modifiers=(), total=7, target=10
    )
    assert len(calc.rows) == 1
    calc_d100 = build_check_calculation(
        resolution_method=D100_ROLL_UNDER, rolls=[3, 7], modifiers=(), total=37, target=60
    )
    assert len(calc_d100.rows) == 1


def test_unknown_resolution_method_raises():
    with pytest.raises(UnknownResolutionMethod):
        build_check_calculation(
            resolution_method="no_such_method", rolls=[1, 2], modifiers=(), total=3, target=8
        )
