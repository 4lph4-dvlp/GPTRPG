"""2d6 판정 계산 — 순수 함수. 무작위는 Roller를 통해서만 얻는다."""

from collections.abc import Sequence
from dataclasses import dataclass

from gptrpg.rules_core.dice import Roller
from gptrpg.rules_core.grading import DEFAULT_TARGET, Grade, grade_for_total

FLAT = "flat"
"""숫자 가감 수정치 유형 이름. 2d6 판정 방식이 계산에 반영하는 유일한 유형이다."""


class UnsupportedModifier(Exception):
    """계산에 반영할 수 없는 수정치 유형이 들어왔을 때 던진다.

    조용히 건너뛰면 합계가 틀린 채로 판정이 끝나고, 그 틀린 값이 기록에
    남아 이후 어디서도 복원되지 않는다 — 그래서 예외로 실패시킨다.
    """

    def __init__(self, modifier_type: str, source: str, resolver: str = "resolve_2d6") -> None:
        super().__init__(
            f"{resolver} does not know how to apply modifier type "
            f"{modifier_type!r} from source {source!r}"
        )
        self.modifier_type = modifier_type
        self.source = source
        self.resolver = resolver


@dataclass(frozen=True)
class Modifier:
    """판정 총합에 영향을 주는 수정치 하나와 그 출처."""

    type: str
    value: int
    source: str


@dataclass(frozen=True)
class CheckOutcome:
    """판정 한 번의 계산 결과 전체 — 눈·수정치·목표값·등급을 모두 담는다."""

    move: str
    rolls: tuple[int, ...]
    modifiers: tuple[Modifier, ...]
    total: int
    target: int
    grade: Grade


def _flat_total(modifiers: Sequence[Modifier]) -> int:
    """숫자 가감 수정치의 합을 계산한다. 계산에 반영할 수 없는 유형이 섞여 있으면 예외로 실패한다."""
    total = 0
    for modifier in modifiers:
        if modifier.type != FLAT:
            raise UnsupportedModifier(modifier.type, modifier.source)
        total += modifier.value
    return total


def resolve_2d6(
    roller: Roller,
    move: str,
    modifiers: Sequence[Modifier],
    target: int = DEFAULT_TARGET,
) -> CheckOutcome:
    """굴림 도구로 2d6을 굴리고, flat 수정치를 더해 등급까지 산출한다."""
    rolls = (roller.roll_d6(), roller.roll_d6())
    total = sum(rolls) + _flat_total(modifiers)
    grade = grade_for_total(total, target)
    return CheckOutcome(
        move=move,
        rolls=rolls,
        modifiers=tuple(modifiers),
        total=total,
        target=target,
        grade=grade,
    )


def reroll_2d6(roller: Roller, previous: CheckOutcome) -> CheckOutcome:
    """앞선 판정 결과에 재굴림을 이어 붙인다.

    앞선 눈을 지우지 않는다 — 굴림 도구를 두 번 더 불러 새 눈 두 개를 얻고,
    `rolls`는 앞선 눈 뒤에 새 눈을 이어 붙인 것으로 만든다. `total`과
    `grade`는 새로 굴린 두 눈만으로 다시 계산한다. `modifiers`와 `target`은
    앞선 판정의 것을 그대로 물려받는다.
    """
    new_rolls = (roller.roll_d6(), roller.roll_d6())
    total = sum(new_rolls) + _flat_total(previous.modifiers)
    grade = grade_for_total(total, previous.target)
    return CheckOutcome(
        move=previous.move,
        rolls=previous.rolls + new_rolls,
        modifiers=previous.modifiers,
        total=total,
        target=previous.target,
        grade=grade,
    )
