"""자원 변화 「축 · 동작 · 양」 — 순수 함수. 무작위·시간·파일·네트워크를 쓰지
않는다(`.importlinter` contract:1).

D-05가 확정한 형식이다: 판정 결과가 자원을 얼마나 바꾸는지는 항상 이 세
칸짜리 항목의 목록으로 적힌다. `ResourceOperation`은 이번 계획에서
`"delta"` 하나뿐이다 — **동작 이름만 늘리면** 「상태를 붙인다」·「이동시킨다」
같은 나머지 원자 연산이 이 형식 위에 그대로 자란다(RULE-09, 로드맵 성공
기준 8). 12-02가 `roll_amount`(주사위식 양)와 나머지 동작 이름들을 이
모듈에 더한다.
"""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Literal

from gptrpg.rules_core.entities import StatEntry

ResourceOperation = Literal["delta"]
"""변화량이 표현하는 원자 연산의 이름 — 이번 계획은 `"delta"`(더하고 뺀다)
하나뿐이다. 12-02가 나머지 일곱을 더한다. 동작 이름이 늘어도 「축 · 동작 ·
양」 세 칸짜리 모양 자체는 안 바뀐다(D-05) — 룰북 데이터·사건 기록·이
모듈의 폴딩 함수 세 곳이 동시에 새 이름을 알게 되는 것이 유일한 변화다."""


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

    `amount`가 `int`면 고정량이고, `str`이면 12-02가 붙일 주사위식이다.
    이번 계획은 `str`을 `InvalidResourceChange`로 거절한다 — 주사위식
    해석기는 12-02가 만든다.
    """

    axis: str
    operation: ResourceOperation
    amount: int | str

    def __post_init__(self) -> None:
        if not self.axis.strip():
            raise InvalidResourceChange("axis가 비었거나 공백뿐이다", axis=self.axis)
        if isinstance(self.amount, str):
            raise InvalidResourceChange(
                "amount가 문자열(주사위식)이다 — 이번 계획은 정수 고정량만"
                " 다룬다(12-02가 주사위식 해석을 붙인다)",
                axis=self.axis,
                amount=self.amount,
            )


@dataclass(frozen=True)
class ResourceOp:
    """실제로 적용된 자원 변화 연산 하나 — 사건 기록에 남는 모양(D-05/D-09).

    `ResourceChangeDecl`이 룰북의 "선언"이라면 이것은 "적용된 사실"이다.
    `rolls`는 주사위식 양이 낸 실제 눈이다(이번 계획은 고정량만 다루므로
    항상 빈 튜플) — 12-02가 채운다.
    """

    axis: str
    operation: ResourceOperation
    amount: int
    rolls: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not self.axis.strip():
            raise InvalidResourceChange("axis가 비었거나 공백뿐이다", axis=self.axis)


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
