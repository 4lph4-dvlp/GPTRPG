"""d100 등급 산출의 행동 + 성질 테스트.

`tests/test_grading.py`(행동)와 `tests/test_resolution_edges.py`(엣지·성질)로
파일을 가른 Phase 1의 관례를 따라, 이 파일은 d100 등급 산출의 행동과 성질을
함께 담는다.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from gptrpg.rules_core.resolution_d100 import percentile_value, resolve_d100
from gptrpg.rules_core.rulebook import GradeBand, NoMatchingGradeBand, grade_for_margin
from gptrpg.rulebooks.openquest import OPENQUEST_GRADE_BANDS

BANDS = OPENQUEST_GRADE_BANDS


def _decompose(roll: int) -> tuple[int, int]:
    """1..100의 굴림값 하나를 (tens, units)로 분해한다. 100은 (0, 0)이다."""
    if roll == 100:
        return 0, 0
    return roll // 10, roll % 10


class ScriptedPercentileRoller:
    """`tests/test_resolution_d100.py`의 같은 이름 클래스와 동일한 관례."""

    def __init__(self, tens_values, units_values):
        self._tens = list(tens_values)
        self._units = list(units_values)

    def roll_tens(self) -> int:
        return self._tens.pop(0)

    def roll_units(self) -> int:
        return self._units.pop(0)


# --- 행동: 경계·인접 ---------------------------------------------------------


def test_grading_success_at_exact_skill_and_failure_one_above():
    """기술값과 정확히 같은 굴림은 성공, 한 칸 위는 실패다."""
    skill = 53
    roller_at = ScriptedPercentileRoller(tens_values=[5], units_values=[3])  # roll 53
    at_skill = resolve_d100(roller_at, "지각", [], skill=skill, bands=BANDS)
    assert at_skill.grade == "success"

    roller_above = ScriptedPercentileRoller(tens_values=[5], units_values=[4])  # roll 54
    one_above = resolve_d100(roller_above, "지각", [], skill=skill, bands=BANDS)
    assert one_above.grade == "failure"


def test_grading_doubles_success_is_critical():
    """두 눈이 같으면서 성공이면 크리티컬이다."""
    roller_crit = ScriptedPercentileRoller(tens_values=[5], units_values=[5])  # roll 55
    crit = resolve_d100(roller_crit, "지각", [], skill=55, bands=BANDS)  # margin=0
    assert crit.grade == "critical"


def test_grading_doubles_failure_is_fumble():
    """두 눈이 같으면서 실패면 펌블이다."""
    roller_fumble = ScriptedPercentileRoller(tens_values=[5], units_values=[5])  # roll 55
    fumble = resolve_d100(roller_fumble, "지각", [], skill=40, bands=BANDS)  # margin=-15
    assert fumble.grade == "fumble"


def test_grading_declaration_order_determines_critical_over_success():
    """선언 순서가 크리티컬을 성공보다 먼저 놓았기 때문에 doubles+성공이 크리티컬로 잡힌다.

    순서를 뒤집은 밴드 목록에서는 같은 margin/doubles 조합이 success로 잡힌다 —
    등급 판정이 순서에 의존한다는 것을 직접 보여준다.
    """
    success_first_bands = (
        GradeBand(name="success", counts_as_failure=False, margin_at_least=0),
        GradeBand(
            name="critical", counts_as_failure=False, margin_at_least=0, requires_doubles=True
        ),
        GradeBand(name="fumble", counts_as_failure=True, margin_at_most=-1, requires_doubles=True),
        GradeBand(name="failure", counts_as_failure=True),
    )
    band_with_normal_order = grade_for_margin(margin=0, is_doubles=True, bands=BANDS)
    band_with_success_first = grade_for_margin(margin=0, is_doubles=True, bands=success_first_bands)
    assert band_with_normal_order.name == "critical"
    assert band_with_success_first.name == "success"


def test_grading_no_matching_band_raises():
    """어느 밴드에도 안 맞는 선언(고의로 구멍 낸 밴드 목록)에서는 NoMatchingGradeBand가 난다."""
    holed_bands = (GradeBand(name="only-high", counts_as_failure=False, margin_at_least=10),)
    with pytest.raises(NoMatchingGradeBand):
        grade_for_margin(margin=5, is_doubles=False, bands=holed_bands)


# --- 성질: 빈틈·겹침 없음 ----------------------------------------------------


@given(
    roll=st.integers(min_value=1, max_value=100),
    skill=st.sampled_from([0, 1, 25, 50, 53, 75, 99, 100]),
)
def test_property_every_roll_and_skill_maps_to_exactly_one_openquest_band(roll, skill):
    """OpenQuest 네 밴드에 대해, 1..100의 모든 굴림값 x 대표 기술값에서
    정확히 하나의 밴드가 맞는다 — 빈틈도 겹침도 없다."""
    tens, units = _decompose(roll)
    is_doubles = tens == units
    margin = skill - roll
    band = grade_for_margin(margin, is_doubles, BANDS)
    assert band.name in {"critical", "success", "fumble", "failure"}


@given(
    skill=st.integers(min_value=-100, max_value=300),
    modifier_value=st.integers(min_value=-10_000, max_value=10_000),
)
def test_property_total_and_target_are_always_int(skill, modifier_value):
    """total·target이 언제나 int이고, 부동소수가 끼어드는 경로가 없다."""
    from gptrpg.rules_core.resolution import FLAT, Modifier

    roller = ScriptedPercentileRoller(tens_values=[4], units_values=[2])  # roll 42
    modifiers = [Modifier(type=FLAT, value=modifier_value, source="속성기반")]
    outcome = resolve_d100(roller, "지각", modifiers, skill=skill, bands=BANDS)
    assert type(outcome.total) is int
    assert type(outcome.target) is int
    assert outcome.total == percentile_value(4, 2) + modifier_value
    assert outcome.target == skill


# --- 수치 구간형 룰북 (성공조건 2 나머지 절반) --------------------------------

NUMERIC_BAND_RULEBOOK_BANDS = (
    GradeBand(name="3", counts_as_failure=False, margin_at_least=20),
    GradeBand(name="2", counts_as_failure=False, margin_at_least=0),
    GradeBand(name="1", counts_as_failure=True, margin_at_least=-20),
    GradeBand(name="0", counts_as_failure=True),
)
"""테스트 전용 수치 구간형 등급 선언 — 이름이 숫자 문자열이고, 경계가 순수
`margin_at_least`/`margin_at_most`만으로 표현된다. `requires_doubles`를 전혀
쓰지 않는다. `rulebooks/`에 세 번째 룰북으로 출하하지 않는다(M1로 미뤄짐) —
이 성질(이름 목록형·수치 구간형이 같은 GradeBand 구조로 둘 다 표현된다는 것)을
증명하는 테스트 안에서만 선언한다."""


def test_numeric_band_rulebook_passes_through_resolve_d100_without_code_change():
    """등급 이름이 숫자 문자열이고 경계가 순수 수치 구간뿐인 룰북 선언이
    코드 수정 없이 resolve_d100을 통과하고, 여유분에 따라 다른 이름이 나온다."""
    skill = 50

    roller_3 = ScriptedPercentileRoller(tens_values=[2], units_values=[0])  # roll 20, margin 30
    outcome_3 = resolve_d100(roller_3, "지각", [], skill=skill, bands=NUMERIC_BAND_RULEBOOK_BANDS)
    assert outcome_3.grade == "3"

    roller_2 = ScriptedPercentileRoller(tens_values=[4], units_values=[0])  # roll 40, margin 10
    outcome_2 = resolve_d100(roller_2, "지각", [], skill=skill, bands=NUMERIC_BAND_RULEBOOK_BANDS)
    assert outcome_2.grade == "2"

    roller_1 = ScriptedPercentileRoller(tens_values=[6], units_values=[0])  # roll 60, margin -10
    outcome_1 = resolve_d100(roller_1, "지각", [], skill=skill, bands=NUMERIC_BAND_RULEBOOK_BANDS)
    assert outcome_1.grade == "1"

    roller_0 = ScriptedPercentileRoller(tens_values=[9], units_values=[0])  # roll 90, margin -40
    outcome_0 = resolve_d100(roller_0, "지각", [], skill=skill, bands=NUMERIC_BAND_RULEBOOK_BANDS)
    assert outcome_0.grade == "0"
