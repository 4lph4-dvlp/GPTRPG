"""판정 눈이 어떻게 합계가 되는지를 「역할 붙은 조각」의 순서 있는 목록으로
만든다 — 화면은 이 조각을 그대로 그리고 다시 계산하지 않는다(D-08/D-09).

`rules_core` 형제 모듈만 import한다 — `event_log`·`web`·`rulebooks`를
참조하지 않고 사건의 필드값만 인자로 받는다(`.importlinter` contract:2가
이 모듈을 `web` 두 라우터가 다 쓰게 해 주는 근거).

**역할(role) 이름은 자유 문자열이다.** `Literal`을 쓰지 않는다 — 이
저장소가 등급 이름(`Grade`, `event_log/schema.py:120-124`)에서 이미 같은
판단을 했다. 고정 목록으로는 두 번째 룰북을 표현할 수 없어 자유 문자열로
넓히고 권위를 룰북 선언에 준 판단을 그대로 따른다(D-10). 세 번째·네 번째
룰북(폭발 주사위, 성공 개수 세기)이 들어와도 이 모듈의 역할 이름 상수를
안 늘려도 된다 — 그 룰북 전용 생성기가 제 역할 이름을 스스로 고른다.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from gptrpg.rules_core.resolution import FLAT, Modifier
from gptrpg.rules_core.resolution_d100 import BONUS_DICE, percentile_value
from gptrpg.rules_core.rulebook import D100_ROLL_UNDER, D20_ROLL_UNDER, TWO_D6

ROLL_OVER = "roll_over"
"""판정 방향 — 목표를 넘어야 성공."""

ROLL_UNDER = "roll_under"
"""판정 방향 — 목표를 밑돌아야 성공."""

ROLE_DIE = "die"
ROLE_TENS = "tens"
ROLE_UNITS = "units"
ROLE_PERCENTILE = "percentile"
ROLE_FLAT = "flat"

_DIRECTIONS: dict[str, str] = {
    TWO_D6: ROLL_OVER,
    D100_ROLL_UNDER: ROLL_UNDER,
    D20_ROLL_UNDER: ROLL_UNDER,
}


class UnknownResolutionMethod(Exception):
    """모르는 판정 방식 이름으로 방향이나 계산 줄을 물었을 때 던진다."""

    def __init__(self, resolution_method: str) -> None:
        super().__init__(f"모르는 판정 방식이다: {resolution_method!r}")
        self.resolution_method = resolution_method


class MalformedRollRecord(Exception):
    """눈 개수가 판정 방식의 구조와 안 맞을 때 던진다 — 조용히 잘라 쓰지 않는다."""

    def __init__(self, resolution_method: str, rolls: Sequence[int], reason: str) -> None:
        super().__init__(
            f"{resolution_method!r} 판정의 눈 {list(rolls)!r}을 계산 줄로 만들 수 없다: {reason}"
        )
        self.resolution_method = resolution_method
        self.rolls = tuple(rolls)
        self.reason = reason


def direction_for(resolution_method: str) -> str:
    """판정 방식 이름으로 판정 방향을 찾는다 — 이름 접미사를 짐작하지 않는다."""
    direction = _DIRECTIONS.get(resolution_method)
    if direction is None:
        raise UnknownResolutionMethod(resolution_method)
    return direction


@dataclass(frozen=True)
class CalculationSegment:
    """계산 줄 하나를 이루는 조각 — 역할·값·출처·버려짐 여부."""

    role: str
    value: int
    source: str | None = None
    discarded: bool = False


@dataclass(frozen=True)
class CalculationRow:
    """조각의 순서 있는 목록 하나. 다시 굴림이 있으면 줄이 여럿이고 합계는
    마지막 줄에만 붙는다(D-12) — 이번 계획은 줄이 하나뿐인 보통 판정만 만든다."""

    segments: tuple[CalculationSegment, ...]
    total: int | None = None


@dataclass(frozen=True)
class CheckCalculation:
    """계산 줄 전체 — 줄 목록 + 합계 + 목표값 + 방향."""

    rows: tuple[CalculationRow, ...]
    total: int
    target: int
    direction: str


def _flat_segments(modifiers: Sequence[Modifier]) -> tuple[CalculationSegment, ...]:
    """`FLAT` 수정치만 조각으로 옮긴다 — `TARGET_SHIFT`·`BONUS_DICE`·`PUSH`는
    목표값·굴림 개수에 이미 반영돼 있어 합계 계산 순서에 나타나지 않는다."""
    return tuple(
        CalculationSegment(role=ROLE_FLAT, value=modifier.value, source=modifier.source)
        for modifier in modifiers
        if modifier.type == FLAT
    )


def _build_two_d6(
    *, rolls: Sequence[int], modifiers: Sequence[Modifier], total: int, target: int
) -> CheckCalculation:
    if len(rolls) != 2:
        raise MalformedRollRecord(TWO_D6, rolls, f"2d6은 눈이 정확히 2개여야 한다 (받음 {len(rolls)}개)")
    segments = tuple(CalculationSegment(role=ROLE_DIE, value=roll) for roll in rolls)
    segments += _flat_segments(modifiers)
    row = CalculationRow(segments=segments, total=total)
    return CheckCalculation(rows=(row,), total=total, target=target, direction=ROLL_OVER)


def _build_d100_roll_under(
    *, rolls: Sequence[int], modifiers: Sequence[Modifier], total: int, target: int
) -> CheckCalculation:
    # 채택된 십의 자리는 `dice_delta`(BONUS_DICE 합)의 부호로 정해진다
    # (resolution_d100.py:124-137) — 첫 값을 항상 채택으로 가정하지 않는다
    # (RESEARCH Pitfall 4). 이번 계획은 dice_delta == 0(십의 자리 하나)인
    # 경우만 만든다 — 여러 개일 때의 discarded=True는 12.2-03이 채운다.
    dice_delta = sum(modifier.value for modifier in modifiers if modifier.type == BONUS_DICE)
    if dice_delta != 0:
        raise MalformedRollRecord(
            D100_ROLL_UNDER, rolls, "BONUS_DICE가 있는 판정(여러 십의 자리)은 이 빌더가 아직 못 만든다"
        )
    if len(rolls) != 2:
        raise MalformedRollRecord(
            D100_ROLL_UNDER, rolls, f"d100_roll_under는 눈이 정확히 2개여야 한다 (받음 {len(rolls)}개)"
        )
    tens, units = rolls[0], rolls[1]
    segments = (
        CalculationSegment(role=ROLE_TENS, value=tens),
        CalculationSegment(role=ROLE_UNITS, value=units),
        CalculationSegment(role=ROLE_PERCENTILE, value=percentile_value(tens, units)),
    )
    segments += _flat_segments(modifiers)
    row = CalculationRow(segments=segments, total=total)
    return CheckCalculation(rows=(row,), total=total, target=target, direction=ROLL_UNDER)


_BUILDERS: dict[str, Callable[..., CheckCalculation]] = {
    TWO_D6: _build_two_d6,
    D100_ROLL_UNDER: _build_d100_roll_under,
}
"""`session_actor.actor._RESOLVERS`와 같은 모양·같은 열쇠 집합이어야 한다
— 굴릴 수 있는 방식은 반드시 그릴 수도 있다."""


def build_check_calculation(
    *,
    resolution_method: str,
    rolls: Sequence[int],
    modifiers: Sequence[Modifier],
    total: int,
    target: int,
) -> CheckCalculation:
    """눈·수정치·합계·목표값으로 계산 줄을 만든다 — 계산을 새로 하지 않고
    이미 계산된 `total`/`target`을 그대로 옮긴다."""
    builder = _BUILDERS.get(resolution_method)
    if builder is None:
        raise UnknownResolutionMethod(resolution_method)
    return builder(rolls=rolls, modifiers=modifiers, total=total, target=target)
