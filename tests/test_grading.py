"""등급 경계 본 동작 + 판정 계산(수정치 출처·재굴림·불변성) 테스트."""

import pytest

from gptrpg.rules_core.grading import grade_for_total
from gptrpg.rules_core.resolution import (
    FLAT,
    Modifier,
    UnsupportedModifier,
    resolve_2d6,
    reroll_2d6,
)


class ScriptedRoller:
    """정해진 눈을 넣은 순서 그대로 돌려주는 가짜 굴림 도구.

    `Roller`를 상속할 필요가 없다 — 구조적 타이핑(PEP 544)이라
    `roll_d6(self) -> int` 시그니처만 맞으면 통과한다.
    """

    def __init__(self, values):
        self._values = list(values)

    def roll_d6(self) -> int:
        return self._values.pop(0)


def test_grading_target_10_strong_hit_at_10_and_12():
    assert grade_for_total(10, target=10) == "strong_hit"
    assert grade_for_total(12, target=10) == "strong_hit"


def test_grading_target_10_weak_hit_at_7_8_9():
    assert grade_for_total(7, target=10) == "weak_hit"
    assert grade_for_total(8, target=10) == "weak_hit"
    assert grade_for_total(9, target=10) == "weak_hit"


def test_grading_target_10_miss_at_2_5_6():
    assert grade_for_total(2, target=10) == "miss"
    assert grade_for_total(5, target=10) == "miss"
    assert grade_for_total(6, target=10) == "miss"


def test_grading_target_shift_moves_boundary_together():
    """목표값을 11로 바꾸면 경계가 통째로 한 칸 밀린다."""
    assert grade_for_total(10, target=11) == "weak_hit"
    assert grade_for_total(11, target=11) == "strong_hit"


def test_resolve_2d6_preserves_roll_order_and_sums_flat_modifiers():
    roller = ScriptedRoller([3, 5])
    modifiers = [Modifier(type=FLAT, value=2, source="스킬")]
    outcome = resolve_2d6(roller, move="문을 부순다", modifiers=modifiers, target=10)
    assert outcome.rolls == (3, 5)
    assert outcome.total == 3 + 5 + 2


def test_resolve_2d6_preserves_each_modifier_value_and_source():
    roller = ScriptedRoller([4, 4])
    modifiers = [
        Modifier(type=FLAT, value=1, source="특성"),
        Modifier(type=FLAT, value=-2, source="부상"),
    ]
    outcome = resolve_2d6(roller, move="문을 부순다", modifiers=modifiers, target=10)
    assert outcome.modifiers[0].value == 1
    assert outcome.modifiers[0].source == "특성"
    assert outcome.modifiers[1].value == -2
    assert outcome.modifiers[1].source == "부상"


def test_check_outcome_attributes_cannot_be_reassigned():
    roller = ScriptedRoller([3, 3])
    outcome = resolve_2d6(roller, move="문을 부순다", modifiers=[], target=10)
    with pytest.raises(Exception):  # noqa: B017 - dataclasses.FrozenInstanceError
        outcome.total = 999


def test_reroll_2d6_appends_new_rolls_and_recomputes_from_them():
    roller = ScriptedRoller([2, 2, 6, 6])
    original = resolve_2d6(roller, move="문을 부순다", modifiers=[], target=10)
    rerolled = reroll_2d6(roller, original)
    assert rerolled.rolls == (2, 2, 6, 6)
    assert rerolled.rolls[:2] == original.rolls
    assert rerolled.total == 6 + 6
    assert rerolled.grade == grade_for_total(12, target=10)


def test_unsupported_modifier_type_raises():
    roller = ScriptedRoller([3, 3])
    modifiers = [Modifier(type="reroll", value=0, source="???")]
    with pytest.raises(UnsupportedModifier):
        resolve_2d6(roller, move="문을 부순다", modifiers=modifiers, target=10)
