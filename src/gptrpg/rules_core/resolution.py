"""2d6 판정 계산 — 순수 함수. 무작위는 Roller를 통해서만 얻는다."""

from collections.abc import Sequence
from dataclasses import dataclass

from gptrpg.rules_core.dice import Roller
from gptrpg.rules_core.entities import StatEntry
from gptrpg.rules_core.grading import DEFAULT_TARGET, Grade, grade_for_total
from gptrpg.rules_core.rulebook import ResourceAxisDecl, StatModifierBand

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


class UnknownStatForCheck(Exception):
    """캐릭터가 그 이름의 능력치(`StatEntry`)를 갖고 있지 않을 때 던진다.

    조용히 0을 돌려주면 능력치 없는 캐릭터가 능력치 낮은 캐릭터와 똑같이
    취급되어 판정 계산이 틀린 채로 넘어간다 — `UnsupportedModifier`가 세운
    "조용히 건너뛰지 않는다" 규율을 그대로 따른다.
    """

    def __init__(self, stat_name: str) -> None:
        super().__init__(f"캐릭터에 이름 {stat_name!r}인 능력치가 없다")
        self.stat_name = stat_name


class StatNotUsableInChecks(Exception):
    """축이 판정에 쓰이도록 선언되지 않았거나(`stat_usage`가 없음), 구간표가
    있는데 그 값에 맞는 구간이 없을 때 던진다(D-01).

    조용히 원값을 그대로 쓰면 룰북이 "이 축은 판정에 안 쓴다"고 선언한
    뜻이 무시된다 — `UnsupportedModifier`와 같은 이유로 예외로 실패시킨다.
    """

    def __init__(self, axis_name: str) -> None:
        super().__init__(
            f"축 {axis_name!r}은 판정에 쓰이도록 선언되지 않았거나(stat_usage 없음)"
            " 구간표가 이 값을 덮지 않는다"
        )
        self.axis_name = axis_name


@dataclass(frozen=True)
class StatCheckInput:
    """능력치 하나를 판정에 실을 준비가 끝난 결과 — `modifier`와 `target`
    중 어느 쪽에 실리는지는 축의 `stat_usage`가 정한다. 둘 다 동시에
    채워지지 않는다(`add_to_dice_total`이면 `modifier`만, `use_as_target`이면
    `target`만)."""

    modifier: Modifier | None
    target: int | None


def _stat_modifier_from_bands(
    value: int, bands: tuple[StatModifierBand, ...], axis_name: str
) -> int:
    """능력치 원값을 구간표로 보정치로 바꾼다. 어느 구간에도 안 맞으면
    `StatNotUsableInChecks` — 조용히 0이 되지 않는다."""
    for band in bands:
        if band.value_at_least is not None and value < band.value_at_least:
            continue
        if band.value_at_most is not None and value > band.value_at_most:
            continue
        return band.modifier
    raise StatNotUsableInChecks(axis_name)


def build_stat_check_input(
    character_stats: tuple[StatEntry, ...],
    stat_name: str,
    axes: tuple[ResourceAxisDecl, ...],
) -> StatCheckInput:
    """능력치 이름 하나를 판정에 실을 `Modifier`/`target`으로 조립한다
    (RULE-02/03, D-01).

    이 함수는 룰북 이름을 모른다 — `stat_usage` 값과 `stat_modifier_bands`만
    본다. `source` 문자열은 `f"stat:{stat_name}"` 하나로 고정한다 — 이 값이
    `CheckResolved.modifiers[].source`에 그대로 남아 D-04의 검산 근거가
    된다.
    """
    axis = next((a for a in axes if a.name == stat_name), None)
    if axis is None or axis.stat_usage is None:
        raise StatNotUsableInChecks(stat_name)

    stat = next((s for s in character_stats if s.name == stat_name), None)
    if stat is None:
        raise UnknownStatForCheck(stat_name)
    if stat.current is None:
        raise StatNotUsableInChecks(stat_name)

    value = stat.current
    if axis.stat_modifier_bands is not None:
        value = _stat_modifier_from_bands(value, axis.stat_modifier_bands, stat_name)

    if axis.stat_usage == "add_to_dice_total":
        return StatCheckInput(
            modifier=Modifier(type=FLAT, value=value, source=f"stat:{stat_name}"),
            target=None,
        )
    if axis.stat_usage == "use_as_target":
        return StatCheckInput(modifier=None, target=value)
    raise StatNotUsableInChecks(stat_name)  # pragma: no cover - Literal이 이미 막는다


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
