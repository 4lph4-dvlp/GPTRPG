"""d100 판정 계산(수정치 네 유형) 테스트.

`ScriptedPercentileRoller`는 `tests/test_resolution_edges.py`의
`ScriptedRoller` 관례를 따른다 — 상속 없이 구조적 타이핑(PEP 544)만으로
`PercentileRoller`를 만족하며, 호출 횟수를 셀 수 있다(보너스 다이스가
굴림 횟수를 실제로 늘렸는지 단언해야 하므로).
"""

import pytest

from gptrpg.event_log.replay_roller import ReplayExhausted, ReplayRoller
from gptrpg.rules_core.resolution import FLAT, Modifier, UnsupportedModifier
from gptrpg.rules_core.resolution_d100 import (
    BONUS_DICE,
    PUSH,
    PushNotPermitted,
    percentile_value,
    push_d100,
    resolve_d100,
)
from gptrpg.rulebooks.openquest import OPENQUEST_DIFFICULTY, OPENQUEST_GRADE_BANDS, difficulty_modifier


class ScriptedPercentileRoller:
    """미리 넣은 tens/units 목록을 순서대로 꺼내는 가짜 백분위 굴림 도구.

    `PercentileRoller`를 상속할 필요가 없다 — `roll_tens(self) -> int`/
    `roll_units(self) -> int` 시그니처만 맞으면 통과한다(PEP 544). 호출
    횟수를 세어, 보너스/페널티 다이스가 굴림 도구 호출 횟수를 실제로
    바꿨는지 단언할 수 있다.
    """

    def __init__(self, tens_values, units_values):
        self._tens = list(tens_values)
        self._units = list(units_values)
        self.tens_call_count = 0
        self.units_call_count = 0

    def roll_tens(self) -> int:
        self.tens_call_count += 1
        return self._tens.pop(0)

    def roll_units(self) -> int:
        self.units_call_count += 1
        return self._units.pop(0)


BANDS = OPENQUEST_GRADE_BANDS


# --- 목표값 변경 (TARGET_SHIFT) ---------------------------------------------


def test_target_shift_changes_target_not_roll():
    """+20짜리 TARGET_SHIFT를 붙이면 target만 바뀌고 total(굴림)은 그대로다."""
    roller = ScriptedPercentileRoller(tens_values=[5], units_values=[4])  # roll = 54
    modifiers = [Modifier(type="target_shift", value=20, source="난이도")]

    with_shift = resolve_d100(roller, "지각", modifiers, skill=40, bands=BANDS)
    assert with_shift.target == 60
    assert with_shift.total == 54
    assert with_shift.grade == "success"  # margin = 60-54 = 6 >= 0, doubles 아님

    roller2 = ScriptedPercentileRoller(tens_values=[5], units_values=[4])
    without_shift = resolve_d100(roller2, "지각", [], skill=40, bands=BANDS)
    assert without_shift.target == 40
    assert without_shift.total == 54
    assert without_shift.grade == "failure"  # margin = 40-54 = -14 < 0


def test_target_shift_multiple_sum():
    """TARGET_SHIFT 여러 개는 순합으로 더해진다."""
    roller = ScriptedPercentileRoller(tens_values=[3], units_values=[0])  # roll = 30
    modifiers = [
        Modifier(type="target_shift", value=50, source="쉬움"),
        Modifier(type="target_shift", value=-20, source="부상"),
    ]
    outcome = resolve_d100(roller, "지각", modifiers, skill=40, bands=BANDS)
    assert outcome.target == 70  # 40 + 50 - 20
    assert outcome.total == 30


# --- 숫자 가감 (FLAT) --------------------------------------------------------


def test_flat_changes_total_not_target():
    """-10짜리 FLAT 수정치는 total만 바꾸고 target은 그대로다."""
    roller = ScriptedPercentileRoller(tens_values=[6], units_values=[0])  # roll = 60
    modifiers = [Modifier(type=FLAT, value=-10, source="부상")]
    outcome = resolve_d100(roller, "지각", modifiers, skill=100, bands=BANDS)
    assert outcome.total == 50  # 60 - 10
    assert outcome.target == 100


# --- 주사위 추가·제거 (BONUS_DICE) -------------------------------------------


def test_bonus_dice_rolls_tens_twice_and_keeps_smaller():
    """보너스 다이스 하나: 십의 자리를 두 번 굴리고, 작은 값이 채택된다."""
    roller = ScriptedPercentileRoller(tens_values=[7, 3], units_values=[9])
    modifiers = [Modifier(type=BONUS_DICE, value=1, source="유리함")]
    outcome = resolve_d100(roller, "지각", modifiers, skill=50, bands=BANDS)
    assert roller.tens_call_count == 2
    assert roller.units_call_count == 1
    assert outcome.rolls == (7, 3, 9)  # 굴린 십의 자리 둘 + 일의 자리 하나, 전부 남는다
    assert outcome.total == percentile_value(3, 9)  # 작은 3이 채택된다


def test_penalty_dice_rolls_tens_twice_and_keeps_larger():
    """페널티 다이스 하나: 같은 구조에서 큰 값이 채택된다."""
    roller = ScriptedPercentileRoller(tens_values=[2, 8], units_values=[1])
    modifiers = [Modifier(type=BONUS_DICE, value=-1, source="불리함")]
    outcome = resolve_d100(roller, "지각", modifiers, skill=50, bands=BANDS)
    assert roller.tens_call_count == 2
    assert outcome.rolls == (2, 8, 1)
    assert outcome.total == percentile_value(8, 1)  # 큰 8이 채택된다


def test_bonus_and_penalty_dice_sum_net_effect():
    """보너스 둘 + 페널티 하나가 함께 붙으면 순합 +1로 계산되어 십의 자리를 두 번 굴린다."""
    roller = ScriptedPercentileRoller(tens_values=[9, 4], units_values=[2])
    modifiers = [
        Modifier(type=BONUS_DICE, value=1, source="장비"),
        Modifier(type=BONUS_DICE, value=1, source="전술"),
        Modifier(type=BONUS_DICE, value=-1, source="부상"),
    ]
    outcome = resolve_d100(roller, "지각", modifiers, skill=50, bands=BANDS)
    assert roller.tens_call_count == 2  # 1 + abs(1) = 2
    assert outcome.total == percentile_value(4, 2)  # 순합 +1(보너스)이므로 작은 값 채택


def test_critical_uses_chosen_tens_not_discarded():
    """채택된 십의 자리가 일의 자리와 같으면 doubles다 — 버려진 십의 자리는 무관하다."""
    roller = ScriptedPercentileRoller(tens_values=[7, 3], units_values=[3])
    modifiers = [Modifier(type=BONUS_DICE, value=1, source="유리함")]
    outcome = resolve_d100(roller, "지각", modifiers, skill=50, bands=BANDS)
    # 채택된 3 == units 3 -> doubles, margin = 50 - 33 = 17 >= 0 -> critical
    assert outcome.total == 33
    assert outcome.grade == "critical"


def test_discarded_tens_matching_units_does_not_trigger_doubles():
    """버려진 십의 자리가 일의 자리와 같아도, 채택된 십의 자리가 다르면 doubles가 아니다."""
    roller = ScriptedPercentileRoller(tens_values=[9, 5], units_values=[5])
    modifiers = [Modifier(type=BONUS_DICE, value=-1, source="불리함")]
    outcome = resolve_d100(roller, "지각", modifiers, skill=50, bands=BANDS)
    # 채택(큰 값) = 9, 버려진 5 == units(5)지만 무관. 9 != 5 -> doubles 아님
    assert outcome.total == 95
    assert outcome.grade == "failure"  # margin = 50-95 = -45, doubles 아니므로 fumble 대상 아님


# --- 0과 0 (percentile_value 경계) ------------------------------------------


def test_zero_zero_rolled_reads_as_one_hundred_and_is_doubles():
    roller = ScriptedPercentileRoller(tens_values=[0], units_values=[0])
    outcome = resolve_d100(roller, "지각", [], skill=50, bands=BANDS)
    assert outcome.total == 100
    assert outcome.grade == "fumble"  # margin = 50-100 = -50 <= -1, doubles


# --- 모르는 수정치 유형 -------------------------------------------------------


def test_unknown_modifier_type_raises_unsupported_modifier():
    roller = ScriptedPercentileRoller(tens_values=[5], units_values=[5])
    modifiers = [Modifier(type="unknown_type", value=0, source="출처")]
    with pytest.raises(UnsupportedModifier) as exc_info:
        resolve_d100(roller, "지각", modifiers, skill=50, bands=BANDS)
    assert exc_info.value.modifier_type == "unknown_type"
    assert exc_info.value.source == "출처"


def test_push_modifier_has_no_effect_on_resolve_d100_calculation():
    """PUSH 표식은 resolve_d100의 계산에는 아무 효과가 없다(조용한 건너뛰기가 아니라 명시된 의미)."""
    roller = ScriptedPercentileRoller(tens_values=[5], units_values=[4])
    modifiers = [Modifier(type=PUSH, value=0, source="룰북")]
    outcome = resolve_d100(roller, "지각", modifiers, skill=60, bands=BANDS)
    assert outcome.total == 54
    assert outcome.target == 60
    assert outcome.modifiers == tuple(modifiers)


# --- OpenQuest 난이도 다섯 단계 ----------------------------------------------


def test_openquest_difficulty_five_levels_shift_target_by_declared_value():
    for name, value in OPENQUEST_DIFFICULTY.items():
        roller = ScriptedPercentileRoller(tens_values=[1], units_values=[0])  # roll = 10
        modifier = difficulty_modifier(name)
        outcome = resolve_d100(roller, "지각", [modifier], skill=50, bands=BANDS)
        assert outcome.target == 50 + value


def test_openquest_difficulty_declares_five_named_levels():
    assert set(OPENQUEST_DIFFICULTY) == {"easy", "simple", "normal", "difficult", "hard"}
    assert OPENQUEST_DIFFICULTY["easy"] == 50
    assert OPENQUEST_DIFFICULTY["simple"] == 20
    assert OPENQUEST_DIFFICULTY["normal"] == 0
    assert OPENQUEST_DIFFICULTY["difficult"] == -20
    assert OPENQUEST_DIFFICULTY["hard"] == -50


# --- 푸시 롤 (D-23) ----------------------------------------------------------


def test_push_d100_appends_new_rolls_without_erasing_previous():
    roller = ScriptedPercentileRoller(tens_values=[5], units_values=[5])
    modifiers = [Modifier(type=PUSH, value=0, source="룰북")]
    original = resolve_d100(roller, "지각", modifiers, skill=50, bands=BANDS)
    assert original.rolls == (5, 5)

    push_roller = ScriptedPercentileRoller(tens_values=[2], units_values=[0])
    pushed = push_d100(push_roller, original, BANDS)
    assert pushed.rolls == original.rolls + (2, 0)
    assert pushed.rolls[:2] == original.rolls


def test_push_d100_recomputes_total_and_grade_from_new_roll_only():
    roller = ScriptedPercentileRoller(tens_values=[9], units_values=[9])
    modifiers = [Modifier(type=PUSH, value=0, source="룰북")]
    original = resolve_d100(roller, "지각", modifiers, skill=50, bands=BANDS)
    assert original.grade == "fumble"  # margin = 50-99 = -49, doubles

    push_roller = ScriptedPercentileRoller(tens_values=[3], units_values=[0])
    pushed = push_d100(push_roller, original, BANDS)
    assert pushed.total == 30  # 새 눈만으로: percentile_value(3, 0)
    assert pushed.grade == "success"  # margin = 50-30 = 20 >= 0, doubles 아님


def test_push_d100_inherits_modifiers_and_target_from_previous():
    roller = ScriptedPercentileRoller(tens_values=[9], units_values=[0])
    modifiers = [
        Modifier(type=PUSH, value=0, source="룰북"),
        Modifier(type="target_shift", value=20, source="난이도"),
    ]
    original = resolve_d100(roller, "지각", modifiers, skill=40, bands=BANDS)
    assert original.target == 60

    push_roller = ScriptedPercentileRoller(tens_values=[1], units_values=[0])
    pushed = push_d100(push_roller, original, BANDS)
    assert pushed.target == 60
    assert pushed.modifiers == original.modifiers


def test_push_d100_reapplies_flat_modifier_to_new_total():
    roller = ScriptedPercentileRoller(tens_values=[5], units_values=[5])
    modifiers = [
        Modifier(type=PUSH, value=0, source="룰북"),
        Modifier(type=FLAT, value=5, source="스킬"),
    ]
    original = resolve_d100(roller, "지각", modifiers, skill=50, bands=BANDS)
    assert original.total == 60  # 55 + 5

    push_roller = ScriptedPercentileRoller(tens_values=[2], units_values=[0])
    pushed = push_d100(push_roller, original, BANDS)
    assert pushed.total == 25  # percentile_value(2,0)=20 + FLAT 5


def test_push_d100_without_push_modifier_raises_push_not_permitted():
    roller = ScriptedPercentileRoller(tens_values=[5], units_values=[5])
    original = resolve_d100(roller, "지각", [], skill=50, bands=BANDS)

    push_roller = ScriptedPercentileRoller(tens_values=[2], units_values=[0])
    with pytest.raises(PushNotPermitted):
        push_d100(push_roller, original, BANDS)


def test_push_d100_twice_in_a_row_keeps_appending_rolls():
    roller = ScriptedPercentileRoller(tens_values=[5], units_values=[5])
    modifiers = [Modifier(type=PUSH, value=0, source="룰북")]
    original = resolve_d100(roller, "지각", modifiers, skill=50, bands=BANDS)
    assert len(original.rolls) == 2

    push_roller_1 = ScriptedPercentileRoller(tens_values=[3], units_values=[1])
    once = push_d100(push_roller_1, original, BANDS)
    assert len(once.rolls) == 4

    push_roller_2 = ScriptedPercentileRoller(tens_values=[7], units_values=[7])
    twice = push_d100(push_roller_2, once, BANDS)
    assert len(twice.rolls) == 6
    assert twice.rolls == (5, 5, 3, 1, 7, 7)


# --- 재생 (replay) -----------------------------------------------------------


def test_resolve_d100_replays_from_recorded_rolls_with_bonus_dice():
    """보너스 다이스로 눈이 세 개 기록된 판정도 재생하면 같은 결과가 나온다."""
    original_roller = ScriptedPercentileRoller(tens_values=[7, 3], units_values=[9])
    modifiers = [Modifier(type=BONUS_DICE, value=1, source="유리함")]
    original = resolve_d100(original_roller, "지각", modifiers, skill=50, bands=BANDS)
    assert original.rolls == (7, 3, 9)

    replay = ReplayRoller(original.rolls)
    replayed = resolve_d100(replay, "지각", modifiers, skill=50, bands=BANDS)
    assert replayed.rolls == original.rolls
    assert replayed.total == original.total
    assert replayed.grade == original.grade


def test_resolve_d100_replay_exhausted_after_recorded_rolls_consumed():
    replay = ReplayRoller([5, 5])
    resolve_d100(replay, "지각", [], skill=50, bands=BANDS)
    with pytest.raises(ReplayExhausted):
        replay.roll_tens()
