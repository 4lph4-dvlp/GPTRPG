"""경계·인접·빈 입력·순서·정수성 엣지 테스트.

이 파일은 판정 코드(grading.py / resolution.py)를 고치지 않는다. 모서리만
단언한다 — 본 동작은 tests/test_grading.py 가 맡는다. 만약 어떤 단언이
통과하지 않는다면 그것은 테스트가 아니라 판정 코드를 고쳐야 한다는 신호다.

다루는 다섯 갈래:
  1. 경계     — 목표값 10 에서 합계 6·7·9·10 네 지점의 등급을 직접 단언
  2. 인접     — 성질 기반: 세 등급은 겹치지도 비지도 않고 바뀌는 지점이 정확히 두 곳
  3. 빈 입력  — 수정치가 빈 목록이거나 하나일 때 예외 없이 굴러간다
  4. 순서     — 같은 눈이 반복되어도 넣은 순서 그대로, 재굴림은 이어 붙인다
  5. 정수성   — 성질 기반: total 은 항상 정수이고 두 눈 합 + 수정치 합과 정확히 같다

규칙 코어(grading / resolution / dice)만 가져다 쓴다. 그 밖에 아무것도(import
포함) 건드리지 않는다.
"""

from hypothesis import given
from hypothesis import strategies as st

from gptrpg.rules_core.grading import WEAK_HIT_BAND, grade_for_total
from gptrpg.rules_core.resolution import (
    FLAT,
    Modifier,
    reroll_2d6,
    resolve_2d6,
)

GRADES = ("strong_hit", "weak_hit", "miss")


class ScriptedRoller:
    """정해진 눈을 넣은 순서 그대로 돌려주는 가짜 굴림 도구.

    `Roller` 를 상속할 필요가 없다 — 구조적 타이핑(PEP 544)이라
    `roll_d6(self) -> int` 시그니처만 맞으면 통과한다.
    """

    def __init__(self, values):
        self._values = list(values)

    def roll_d6(self) -> int:
        return self._values.pop(0)


# --- 1. 경계 (boundary) -----------------------------------------------------


def test_edge_boundary_target_10_four_points():
    """목표값 10 기준 합계 6·7·9·10 네 지점 각각의 등급을 직접 단언한다."""
    assert grade_for_total(6, target=10) == "miss"
    assert grade_for_total(7, target=10) == "weak_hit"
    assert grade_for_total(9, target=10) == "weak_hit"
    assert grade_for_total(10, target=10) == "strong_hit"


def test_edge_boundary_straddle_points_split_grades():
    """경계 바로 아래와 바로 위가 서로 다른 등급이다 — 이것이 이 테스트의 요지다."""
    assert grade_for_total(6, target=10) != grade_for_total(7, target=10)
    assert grade_for_total(9, target=10) != grade_for_total(10, target=10)


# --- 2. 인접 (adjacency) ----------------------------------------------------


@given(
    target=st.integers(min_value=-200, max_value=200),
    total=st.integers(min_value=-50_000, max_value=50_000),
)
def test_edge_adjacency_every_total_maps_to_exactly_one_grade(target, total):
    """넉넉한 정수 범위(2~12 를 크게 벗어나는 값까지)에서 세 등급 중 정확히 하나, 예외 없음."""
    assert grade_for_total(total, target) in GRADES


@given(target=st.integers(min_value=-200, max_value=200))
def test_edge_adjacency_grade_changes_at_exactly_two_points(target):
    """합계를 1씩 올릴 때 등급이 바뀌는 지점이 정확히 두 곳: target 과 target - WEAK_HIT_BAND.

    구간이 겹치지도 비지도 않는다는 뜻이다. 스캔 범위는 두 경계를 넉넉히 감싼다.
    """
    lo = target - WEAK_HIT_BAND - 8
    hi = target + 8
    prev = grade_for_total(lo, target)
    assert prev in GRADES
    change_points = []
    for total in range(lo + 1, hi + 1):
        cur = grade_for_total(total, target)
        assert cur in GRADES
        if cur != prev:
            change_points.append(total)
        prev = cur
    assert change_points == [target - WEAK_HIT_BAND, target]


# --- 3. 빈 입력 (empty) -----------------------------------------------------


def test_edge_empty_modifiers_yield_sum_of_eyes_and_empty_tuple():
    """수정치가 빈 목록일 때 예외 없이 끝나고 total 은 두 눈의 합, modifiers 는 빈 튜플."""
    roller = ScriptedRoller([4, 6])
    outcome = resolve_2d6(roller, move="문을 부순다", modifiers=[], target=10)
    assert outcome.rolls == (4, 6)
    assert outcome.total == 4 + 6
    assert outcome.modifiers == ()


def test_edge_empty_single_modifier_preserved_in_order():
    """수정치가 하나짜리일 때도 그 하나의 value 와 source 가 그대로 보존된다."""
    roller = ScriptedRoller([3, 3])
    single = [Modifier(type=FLAT, value=2, source="스킬")]
    outcome = resolve_2d6(roller, move="문을 부순다", modifiers=single, target=10)
    assert outcome.total == 3 + 3 + 2
    assert outcome.modifiers == (single[0],)
    assert outcome.modifiers[0].value == 2
    assert outcome.modifiers[0].source == "스킬"


# --- 4. 순서 (ordering) -----------------------------------------------------


def test_edge_ordering_repeated_values_preserve_insertion_order():
    """같은 눈이 반복되는 목록(세 번 연속 같은 값)도 정렬 없이 넣은 순서 그대로.

    재굴림 뒤 rolls 앞부분은 원본과 같고 뒤에 새 눈이 이어 붙는다 — 덮어쓰지 않는다.
    """
    roller = ScriptedRoller([6, 6, 6, 1])
    original = resolve_2d6(roller, move="문을 부순다", modifiers=[], target=10)
    assert original.rolls == (6, 6)
    rerolled = reroll_2d6(roller, original)
    assert rerolled.rolls == (6, 6, 6, 1)
    assert rerolled.rolls[:2] == original.rolls


def test_edge_ordering_same_eyes_twice_give_identical_outcomes():
    """같은 눈 목록으로 두 번 계산하면 두 결과가 항상 같다."""
    eyes = [3, 4]
    first = resolve_2d6(ScriptedRoller(list(eyes)), move="m", modifiers=[], target=10)
    second = resolve_2d6(ScriptedRoller(list(eyes)), move="m", modifiers=[], target=10)
    assert first == second


# --- 5. 정수성 (integer) ----------------------------------------------------


@given(
    eye_a=st.integers(min_value=1, max_value=6),
    eye_b=st.integers(min_value=1, max_value=6),
    mod_values=st.lists(
        st.integers(min_value=-10_000, max_value=10_000),
        min_size=0,
        max_size=5,
    ),
)
def test_edge_integer_total_is_exact_sum_of_eyes_and_flat_modifiers(
    eye_a, eye_b, mod_values
):
    """total 은 항상 정수이고 두 눈의 합 + 수정치 값들의 합과 정확히 같다.

    아주 큰 양수/음수 수정치로 합계가 2~12 를 크게 벗어나도 등급 산출이 예외 없이
    동작한다. 부동소수·나눗셈·반올림이 관여할 여지가 없으므로 반올림 규칙 자체가
    존재하지 않는다는 것이 이 테스트의 요지다.
    """
    roller = ScriptedRoller([eye_a, eye_b])
    modifiers = [
        Modifier(type=FLAT, value=v, source=f"src{i}") for i, v in enumerate(mod_values)
    ]
    outcome = resolve_2d6(roller, move="문을 부순다", modifiers=modifiers, target=10)
    expected = eye_a + eye_b + sum(mod_values)
    assert outcome.total == expected
    assert type(outcome.total) is int
    assert outcome.grade in GRADES
