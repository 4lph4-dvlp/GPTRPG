"""자원 변화 「축 · 동작 · 양」 — 순수 함수. 무작위·시간·파일·네트워크를 쓰지
않는다(`.importlinter` contract:1). 무작위는 `DieRoller`를 통해서만 받는다
— `rules_core` 안에서 `random`/`secrets`를 직접 import하는 자리는 없다
(`roll_amount`가 그 유일한 통로다, D-06).

D-05가 확정한 형식이다: 판정 결과가 자원을 얼마나 바꾸는지는 항상 이 세
칸짜리 항목의 목록으로 적힌다. `ResourceOperation`은 이번 계획에서
`"delta"` 하나뿐이다 — **동작 이름만 늘리면** 「상태를 붙인다」·「이동시킨다」
같은 나머지 원자 연산이 이 형식 위에 그대로 자란다(RULE-09, 로드맵 성공
기준 8). 12-02가 `roll_amount`(주사위식 양)와 나머지 동작 이름들을 이
모듈에 더한다.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Literal

from gptrpg.rules_core.dice import DieRoller
from gptrpg.rules_core.entities import StatEntry

ResourceOperation = Literal["delta"]
"""변화량이 표현하는 원자 연산의 이름 — 이번 계획은 `"delta"`(더하고 뺀다)
하나뿐이다. 12-02가 나머지 일곱을 더한다. 동작 이름이 늘어도 「축 · 동작 ·
양」 세 칸짜리 모양 자체는 안 바뀐다(D-05) — 룰북 데이터·사건 기록·이
모듈의 폴딩 함수 세 곳이 동시에 새 이름을 알게 되는 것이 유일한 변화다."""

MAX_DICE_COUNT = 20
"""주사위식 한 개당 굴릴 수 있는 최대 개수(D-06, T-12-09). 이 상한을 넘는
굴림 호출은 계산이 아니라 입력 실수로 본다 —
`resolution_d100.MAX_BONUS_DICE_MAGNITUDE`가 세운 것과 같은 형식의
방어다."""

MAX_DIE_SIDES = 1000
"""주사위식 한 개의 최대 면수(D-06, T-12-09). `MAX_DICE_COUNT`와 같은
근거 — 굴림 도구 호출 자체는 면수와 무관하게 한 번이지만, 비정상적으로
큰 면수도 입력 실수로 본다."""

_DICE_EXPR = re.compile(r"^(?P<sign>[+-]?)(?P<count>\d+)d(?P<sides>\d+)(?P<flat>[+-]\d+)?$")
"""`NdM` 문법에 앞 부호와 뒤 고정 가감을 붙인 모양만 받는다(예: `"1d6"`,
`"-1d6"`, `"2d8+1"`). 그 밖(`"d6"`·`"1d"`·`"abc"`·`""` 등)은 전부
`InvalidResourceChange`다."""


class InvalidResourceChange(Exception):
    """자원 변화 선언(`ResourceChangeDecl`) 또는 연산(`ResourceOp`)이
    유효하지 않을 때 던진다.

    조용히 통과하면 잘못된 축 이름·못 다루는 동작·주사위식이 그대로
    기록에 남아 재생 시점에야 드러난다 — `InvalidResourceAxis`/
    `InvalidStatEntry`가 세운 "조용히 넘기지 않는다" 규율을 그대로 따른다.
    """

    def __init__(self, reason: str, axis: str | None = None, amount: int | str | None = None) -> None:
        super().__init__(f"자원 변화가 유효하지 않다: {reason} (axis={axis!r}, amount={amount!r})")
        self.reason = reason
        self.axis = axis
        self.amount = amount


@dataclass(frozen=True)
class ResourceChangeDecl:
    """룰북이 적는 자원 변화 선언 하나 — 「축 · 동작 · 양」(D-05).

    `amount`가 `int`면 고정량이고, `str`이면 주사위식이다(`"1d6"`·`"2d8+1"`·
    `"-1d6"` 같은 `NdM` 문법, D-06). 실제 출간작 대부분이 피해를 주사위로
    적는다 — 고정값만 받으면 저장소의 룰북을 원문대로 적을 수 없고 평균값
    근사로 흐른다(이 프로젝트가 금지한 「특정 룰북 근사」). 이 칸은 형식만
    검사한다 — 실제로 굴려서 정수로 바꾸는 것은 `roll_amount`의 몫이다
    (12-01은 문자열을 무조건 거절했다 — 그 거절을 이 형식 검사로 바꾼다).
    """

    axis: str
    operation: ResourceOperation
    amount: int | str

    def __post_init__(self) -> None:
        if not self.axis.strip():
            raise InvalidResourceChange("axis가 비었거나 공백뿐이다", axis=self.axis)
        if isinstance(self.amount, str) and _DICE_EXPR.match(self.amount) is None:
            raise InvalidResourceChange(
                "amount가 주사위식 문법(NdM, 예: '1d6'·'2d8+1'·'-1d6')을 따르지 않는다",
                axis=self.axis,
                amount=self.amount,
            )


@dataclass(frozen=True)
class ResourceOp:
    """실제로 적용된 자원 변화 연산 하나 — 사건 기록에 남는 모양(D-05/D-09).

    `ResourceChangeDecl`이 룰북의 "선언"이라면 이것은 "적용된 사실"이다.
    `rolls`는 주사위식 양이 낸 실제 눈이다 — 고정 정수 양은 빈 튜플이고,
    `roll_amount`가 주사위식을 굴려 만든 값은 굴린 눈 그대로가 채워진다
    (D-06). 실제로 `ResourceChangeDecl`에서 이 필드를 채워 `ResourceOp`를
    만드는 호출부(룰북 결과 목록 → 사건 제출 경로)는 12-04가 잇는다 —
    이 계획은 `roll_amount` 자체와 그 결과 모양만 세운다.
    """

    axis: str
    operation: ResourceOperation
    amount: int
    rolls: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not self.axis.strip():
            raise InvalidResourceChange("axis가 비었거나 공백뿐이다", axis=self.axis)


def roll_amount(roller: DieRoller, amount: int | str) -> tuple[int, tuple[int, ...]]:
    """변화량 하나를 실제 정수로 만든다 — 고정 정수는 그대로, 주사위식은
    굴려서(D-06).

    고정 정수면 `(amount, ())`를 그대로 돌려준다(굴림 도구를 한 번도 안
    부른다). 주사위식(`NdM` 문법)이면 개수만큼 `roller.roll_die(sides)`를
    불러 `(부호 × (눈 합 + 고정 가감), 굴린 눈 튜플)`을 돌려준다.

    **눈은 부호를 붙이지 않은 굴린 값 그대로 돌려준다** — 화면에서
    「1d6 = 4 → 체력 −4」로 검산되어야 한다(D-04). 부호는 결과값에만 붙는다.

    **상한 검사는 굴림 도구를 부르기 전에 한다**(T-12-09) — `MAX_DICE_COUNT`·
    `MAX_DIE_SIDES`를 넘는 주사위식은 `InvalidResourceChange`로 거절하고
    `roller.roll_die`를 단 한 번도 부르지 않는다. 상한을 넘는 굴림 호출은
    계산이 아니라 입력 실수로 본다.
    """
    if isinstance(amount, int):
        return amount, ()

    match = _DICE_EXPR.match(amount)
    if match is None:
        raise InvalidResourceChange(
            "amount가 주사위식 문법(NdM, 예: '1d6'·'2d8+1'·'-1d6')을 따르지 않는다",
            amount=amount,
        )

    sign = -1 if match.group("sign") == "-" else 1
    count = int(match.group("count"))
    sides = int(match.group("sides"))
    flat = int(match.group("flat")) if match.group("flat") else 0

    if count > MAX_DICE_COUNT or sides > MAX_DIE_SIDES:
        raise InvalidResourceChange(
            f"주사위식이 상한을 넘는다(개수 <= {MAX_DICE_COUNT}, 면수 <= {MAX_DIE_SIDES})",
            amount=amount,
        )

    rolls = tuple(roller.roll_die(sides) for _ in range(count))
    return sign * (sum(rolls) + flat), rolls


def apply_resource_op(stat: StatEntry, op: ResourceOp) -> StatEntry:
    """상태값 하나에 연산 하나를 적용해 새 `StatEntry`를 돌려준다.

    `dataclasses.replace`로 만든 결과가 `StatEntry.__post_init__`(형태
    규약 검증)을 다시 지나게 한다 — 잘못된 값이 기록에 영구히 남는 경로를
    구조적으로 막는다(T-12-06). 최대치 자르기는 `max is not None`일 때만
    한다 — 상한이 없다는 뜻이지 0이라는 뜻이 아니다. 0 아래로 내려간 값은
    자르지 않는다 — 그 뜻은 룰북이 정한다(D-08).

    이번 계획이 다루는 `form`은 `numeric`뿐이다. 나머지 다섯 형태는
    `InvalidResourceChange`로 거절한다 — 12-02가 붙인다.
    """
    if stat.name != op.axis:
        raise InvalidResourceChange(
            f"연산의 축 이름({op.axis!r})이 상태값의 축 이름({stat.name!r})과 다르다",
            axis=op.axis,
        )
    if stat.form != "numeric":
        raise InvalidResourceChange(
            f"form {stat.form!r}에는 아직 자원 변화를 적용할 수 없다(numeric만"
            " 다룬다 — 12-02가 나머지 다섯을 붙인다)",
            axis=op.axis,
        )
    if op.operation == "delta":
        assert stat.current is not None  # numeric은 current가 필수다(StatEntry 규약)
        new_current = stat.current + op.amount
        if stat.max is not None and new_current > stat.max:
            new_current = stat.max
        return replace(stat, current=new_current)
    raise InvalidResourceChange(f"알 수 없는 연산: {op.operation!r}", axis=op.axis)


def resolve_character_stats(
    starting: tuple[StatEntry, ...],
    ops: Mapping[str, tuple[ResourceOp, ...]],
) -> tuple[StatEntry, ...]:
    """「시작값 + 축별 연산 이력」을 접어 지금 값을 만든다(RULE-06, D-65).

    시작값 튜플의 선언 순서를 그대로 보존한다. 이력이 없는 축(`ops`에
    없는 이름)은 시작값 그대로 돌려준다 — 「접을 변화가 없다」와 「값이
    0이다」가 섞이지 않는다.
    """
    result: list[StatEntry] = []
    for stat in starting:
        current_stat = stat
        for op in ops.get(stat.name, ()):
            current_stat = apply_resource_op(current_stat, op)
        result.append(current_stat)
    return tuple(result)


@dataclass(frozen=True)
class DepletedAxis:
    """소진된 자원 축 하나 — 이름과 그 축이 가리키는 효과 참조."""

    axis: str
    effect_ref: str


def depleted_axes(stats: tuple[StatEntry, ...]) -> tuple[DepletedAxis, ...]:
    """`current`가 0 이하이고 `depleted_effect_ref`가 있는 축의 목록을
    돌려준다.

    고리를 부르는 데까지가 이 함수의 몫이다 — 그 고리(효과 참조)가 실제로
    무엇을 하는지는 D7(원자 연산 목록)이 다룰 다음 마일스톤이다(D-08).
    """
    result: list[DepletedAxis] = []
    for stat in stats:
        if stat.current is not None and stat.current <= 0 and stat.depleted_effect_ref is not None:
            result.append(DepletedAxis(axis=stat.name, effect_ref=stat.depleted_effect_ref))
    return tuple(result)
