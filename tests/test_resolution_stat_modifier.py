"""`build_stat_check_input`이 능력치 이름 하나를 판정에 실을 `Modifier`/
`target`으로 조립하는 다섯 갈래를 확인한다(RULE-02/03, D-01, 12-01).

이 함수는 룰북 이름을 모른다 — `ResourceAxisDecl.stat_usage`/
`stat_modifier_bands`만 본다. 시험도 그 경계를 지켜 특정 룰북 상수를
쓰지 않고 이 파일 안에서 축·캐릭터 상태값을 직접 짓는다.
"""

import pytest

from gptrpg.rules_core.entities import StatEntry
from gptrpg.rules_core.resolution import (
    FLAT,
    Modifier,
    StatCheckInput,
    StatNotUsableInChecks,
    UnknownStatForCheck,
    build_stat_check_input,
)
from gptrpg.rules_core.rulebook import ResourceAxisDecl, StatModifierBand


def test_add_to_dice_total_usage_becomes_flat_modifier():
    """`stat_usage="add_to_dice_total"`인 축은 능력치 원값이 `FLAT`
    수정치가 되고 `target`은 `None`이다. `source`는 `f"stat:{이름}"`
    하나로 고정된다(D-04 검산 근거)."""
    axes = (ResourceAxisDecl(name="STR", form="numeric", stat_usage="add_to_dice_total"),)
    stats = (StatEntry(name="STR", form="numeric", current=2),)

    result = build_stat_check_input(stats, "STR", axes)

    assert result == StatCheckInput(
        modifier=Modifier(type=FLAT, value=2, source="stat:STR"), target=None
    )


def test_use_as_target_usage_becomes_target_value():
    """`stat_usage="use_as_target"`인 축은 능력치 원값이 그대로 `target`이
    되고 `modifier`는 `None`이다."""
    axes = (ResourceAxisDecl(name="기술", form="numeric", stat_usage="use_as_target"),)
    stats = (StatEntry(name="기술", form="numeric", current=55),)

    result = build_stat_check_input(stats, "기술", axes)

    assert result == StatCheckInput(modifier=None, target=55)


def test_axis_without_stat_usage_declared_raises():
    """축은 존재하지만 `stat_usage`가 선언되지 않았으면
    `StatNotUsableInChecks`다 — 룰북이 「이 축은 판정에 안 쓴다」고
    말한 것을 조용히 무시하지 않는다."""
    axes = (ResourceAxisDecl(name="체력", form="numeric"),)
    stats = (StatEntry(name="체력", form="numeric", current=20, max=20),)

    with pytest.raises(StatNotUsableInChecks) as exc_info:
        build_stat_check_input(stats, "체력", axes)
    assert exc_info.value.axis_name == "체력"


def test_character_without_the_named_stat_raises_unknown_stat():
    """캐릭터에 그 이름의 축이 없으면 `UnknownStatForCheck`다 — 조용히
    0을 돌려주지 않는다(RULE-02 empty)."""
    axes = (ResourceAxisDecl(name="STR", form="numeric", stat_usage="add_to_dice_total"),)
    stats: tuple[StatEntry, ...] = ()

    with pytest.raises(UnknownStatForCheck) as exc_info:
        build_stat_check_input(stats, "STR", axes)
    assert exc_info.value.stat_name == "STR"


def test_stat_modifier_bands_replace_raw_value():
    """`stat_modifier_bands`가 선언되어 있으면 원값이 아니라 구간표가
    돌려주는 보정치를 쓴다."""
    axes = (
        ResourceAxisDecl(
            name="STR",
            form="numeric",
            stat_usage="add_to_dice_total",
            stat_modifier_bands=(
                StatModifierBand(value_at_least=None, value_at_most=-1, modifier=-1),
                StatModifierBand(value_at_least=0, value_at_most=1, modifier=0),
                StatModifierBand(value_at_least=2, value_at_most=None, modifier=1),
            ),
        ),
    )
    stats = (StatEntry(name="STR", form="numeric", current=2),)

    result = build_stat_check_input(stats, "STR", axes)

    assert result.modifier == Modifier(type=FLAT, value=1, source="stat:STR")


def test_stat_modifier_bands_boundary_and_adjacent_values_differ():
    """구간 경계값과 그 바로 양옆이 서로 다른 보정치를 돌려준다(RULE-02/03
    boundary)."""
    axes = (
        ResourceAxisDecl(
            name="STR",
            form="numeric",
            stat_usage="add_to_dice_total",
            stat_modifier_bands=(
                StatModifierBand(value_at_least=None, value_at_most=1, modifier=0),
                StatModifierBand(value_at_least=2, value_at_most=None, modifier=1),
            ),
        ),
    )
    below = build_stat_check_input(
        (StatEntry(name="STR", form="numeric", current=1),), "STR", axes
    )
    at_boundary = build_stat_check_input(
        (StatEntry(name="STR", form="numeric", current=2),), "STR", axes
    )
    assert below.modifier.value == 0
    assert at_boundary.modifier.value == 1
    assert below.modifier.value != at_boundary.modifier.value


def test_stat_modifier_bands_value_outside_every_band_raises():
    """어느 구간에도 안 맞는 값은 조용히 0이 되지 않고 예외로 멈춘다
    (RULE-02/03 boundary)."""
    axes = (
        ResourceAxisDecl(
            name="STR",
            form="numeric",
            stat_usage="add_to_dice_total",
            stat_modifier_bands=(StatModifierBand(value_at_least=0, value_at_most=1, modifier=0),),
        ),
    )
    stats = (StatEntry(name="STR", form="numeric", current=5),)

    with pytest.raises(StatNotUsableInChecks):
        build_stat_check_input(stats, "STR", axes)
