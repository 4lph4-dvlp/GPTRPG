"""자원 변화 「축 · 동작 · 양」 — 순수 함수. 무작위·시간·파일·네트워크를 쓰지
않는다(`.importlinter` contract:1). 무작위는 `DieRoller`를 통해서만 받는다
— `rules_core` 안에서 `random`/`secrets`를 직접 import하는 자리는 없다
(`roll_amount`가 그 유일한 통로다, D-06).

D-05가 확정한 형식이다: 판정 결과가 자원을 얼마나 바꾸는지는 항상 이 세
칸짜리 항목의 목록으로 적힌다. `ResourceOperation`이 여덟 값으로 자란
뒤에도(12-02, RULE-09) 「축 · 동작 · 양」 세 칸짜리 모양 자체는 안
바뀐다 — 동작 이름이 늘어난 것이 유일한 변화다. **여섯 표현 형태마다
「변한다」의 뜻이 다르므로** `apply_resource_op`은 `stat.form`으로 먼저
갈라 각 형태가 허용하는 동작만 받는다(형태 × 동작 대응표는
`ResourceOperation` 도크스트링).
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Literal

from gptrpg.rules_core.dice import DieRoller
from gptrpg.rules_core.entities import StatEntry

ResourceOperation = Literal[
    "delta", "advance", "fill", "clear", "add_tag", "remove_tag", "step_down", "deplete"
]
"""변화량이 표현하는 원자 연산의 이름 — 여덟 값(12-02, RULE-09). 어느
룰북의 낱말도 아니다 — `ResourceAxisForm`(entities.py)이 이미 세운 것과
같은 플랫폼 어휘 원칙이다.

**형태 × 동작 대응표(허용된 조합 밖은 전부 `InvalidResourceChange`):**

| `form`        | 허용 동작                | `amount`의 뜻                          |
|---------------|---------------------------|------------------------------------------|
| `numeric`     | `delta`                   | 더하고 뺄 정수(양/음, 주사위식 가능)     |
| `clock`       | `advance`                 | 나아갈 칸 수(정수, 음수면 물러난다)      |
| `named_slots` | `fill`                    | 채울 문자열(빈 슬롯이 없으면 거절)       |
| `named_slots` | `clear`                   | 비울 문자열(완전 일치, 없으면 거절)      |
| `tag_list`    | `add_tag`                 | 붙일 태그 문자열(중복이면 그대로 둔다)   |
| `tag_list`    | `remove_tag`               | 뗄 태그 문자열(완전 일치, 없으면 거절)   |
| `usage_die`   | `step_down`                | 내려갈 목표 면수(정수, 절대값)          |
| `usage_die`   | `deplete`                  | 쓰지 않는다(면수를 0으로 고정)          |
| `none`        | (없음)                     | 어떤 동작도 못 받는다                    |

동작 이름만 늘리면 이후의 다른 효과(상태를 붙인다·이동시킨다 같은)가
같은 「축 · 동작 · 양」 세 칸 위에 그대로 자란다(D-05/RULE-09) — 룰북
데이터·사건 기록·이 모듈의 폴딩 함수 세 곳이 동시에 새 이름을 알게 되는
것이 유일한 변화다."""

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

    `amount`가 `int | str`인 이유는 형태마다 뜻이 다르기 때문이다
    (`ResourceOperation` 도크스트링의 대응표) — `numeric`/`clock`/
    `usage_die`는 정수(가감·주사위식 결과·목표 면수), `named_slots`/
    `tag_list`는 문자열(채울/비울 값, 붙일/뗄 태그)이다. `apply_resource_op`이
    `stat.form`으로 갈라 어느 쪽이 맞는지 검사한다 — 어긋나면
    `InvalidResourceChange`다.
    """

    axis: str
    operation: ResourceOperation
    amount: int | str
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


def _require_int_amount(op: ResourceOp) -> int:
    """정수 `amount`가 필요한 연산에서 실제로 정수인지 확인한다.

    조용히 형변환하지 않는다 — 문자열이 온 것은 룰북 데이터나 호출부가
    엉뚱한 형태의 값을 실었다는 신호이고, 그것을 삼키면 잘못된 값이
    그대로 기록에 남는다."""
    if not isinstance(op.amount, int):
        raise InvalidResourceChange(
            f"연산 {op.operation!r}은 정수 amount가 필요하다", axis=op.axis, amount=op.amount
        )
    return op.amount


def _require_str_amount(op: ResourceOp) -> str:
    """문자열 `amount`가 필요한 연산(슬롯 채움/비움, 태그 붙임/뗌)에서
    실제로 문자열인지 확인한다. 빈 문자열도 거절한다 — 슬롯·태그 값은
    빈 문자열로 표현하지 않는다(빈 슬롯은 `None`)."""
    if not isinstance(op.amount, str) or not op.amount:
        raise InvalidResourceChange(
            f"연산 {op.operation!r}은 비어 있지 않은 문자열 amount가 필요하다",
            axis=op.axis,
            amount=op.amount,
        )
    return op.amount


def apply_resource_op(stat: StatEntry, op: ResourceOp) -> StatEntry:
    """상태값 하나에 연산 하나를 적용해 새 `StatEntry`를 돌려준다.

    `stat.form`으로 먼저 갈라 각 형태가 허용하는 동작만 받는다 — 허용
    밖 조합(예: `tag_list`에 `delta`)은 `InvalidResourceChange`로 멈춘다.
    「모르는 것을 조용히 기본값으로 넘기지 않는다」는 이 저장소 규율
    (`UnknownEventType`·`InvalidStatEntry`·`UnsupportedModifier`)을 그대로
    따른다. `dataclasses.replace`로 만든 결과가
    `StatEntry.__post_init__`(형태 규약 검증)을 다시 지나게 한다 — 잘못된
    값이 기록에 영구히 남는 경로를 구조적으로 막는다(T-12-06).

    슬롯·태그 문자열 비교는 파이썬 `==` 완전 일치다
    (`validate_entity_axes`가 세운 규약과 같다 — 유니코드 정규화·대소문자
    접기·공백 제거 없음).

    **최대치는 코드가 자르고, 0 아래의 뜻은 룰북이 정한다(QUAL-06/D-08의
    분업).** `numeric`은 `max is not None`일 때만 위쪽을 자르고, `clock`은
    `max`가 항상 필수이므로 위아래를 둘 다 자른다. `numeric`의 아래쪽(0
    미만)은 절대 자르지 않는다 — 0 아래로 내려간 값의 뜻은 룰북이 정한다.
    """
    if stat.name != op.axis:
        raise InvalidResourceChange(
            f"연산의 축 이름({op.axis!r})이 상태값의 축 이름({stat.name!r})과 다르다",
            axis=op.axis,
        )

    if stat.form == "numeric":
        if op.operation != "delta":
            raise InvalidResourceChange(
                f"numeric 축은 delta만 받는다(받은 연산: {op.operation!r})", axis=op.axis
            )
        assert stat.current is not None  # numeric은 current가 필수다(StatEntry 규약)
        new_current = stat.current + _require_int_amount(op)
        if stat.max is not None and new_current > stat.max:
            new_current = stat.max
        return replace(stat, current=new_current)

    if stat.form == "clock":
        if op.operation != "advance":
            raise InvalidResourceChange(
                f"clock 축은 advance만 받는다(받은 연산: {op.operation!r})", axis=op.axis
            )
        assert stat.current is not None and stat.max is not None  # clock 규약(StatEntry)
        new_current = stat.current + _require_int_amount(op)
        new_current = max(0, min(stat.max, new_current))
        return replace(stat, current=new_current)

    if stat.form == "named_slots":
        slot_values = stat.slot_values or ()
        if op.operation == "fill":
            value = _require_str_amount(op)
            if None not in slot_values:
                raise InvalidResourceChange("빈 슬롯이 없다", axis=op.axis, amount=op.amount)
            idx = slot_values.index(None)
            new_slots = slot_values[:idx] + (value,) + slot_values[idx + 1 :]
            return replace(stat, slot_values=new_slots)
        if op.operation == "clear":
            value = _require_str_amount(op)
            if value not in slot_values:
                raise InvalidResourceChange(
                    f"슬롯에 {value!r}가 없다", axis=op.axis, amount=op.amount
                )
            idx = slot_values.index(value)
            new_slots = slot_values[:idx] + (None,) + slot_values[idx + 1 :]
            return replace(stat, slot_values=new_slots)
        raise InvalidResourceChange(
            f"named_slots 축은 fill/clear만 받는다(받은 연산: {op.operation!r})", axis=op.axis
        )

    if stat.form == "tag_list":
        tags = stat.tags or ()
        if op.operation == "add_tag":
            tag = _require_str_amount(op)
            if tag in tags:
                return stat  # 이미 있는 태그를 다시 붙여도 중복으로 안 붙는다
            return replace(stat, tags=tags + (tag,))
        if op.operation == "remove_tag":
            tag = _require_str_amount(op)
            if tag not in tags:
                raise InvalidResourceChange(f"태그 {tag!r}가 없다", axis=op.axis, amount=op.amount)
            return replace(stat, tags=tuple(t for t in tags if t != tag))
        raise InvalidResourceChange(
            f"tag_list 축은 add_tag/remove_tag만 받는다(받은 연산: {op.operation!r})",
            axis=op.axis,
        )

    if stat.form == "usage_die":
        if op.operation == "step_down":
            target_sides = _require_int_amount(op)
            return replace(stat, current=target_sides)
        if op.operation == "deplete":
            return replace(stat, current=0)
        raise InvalidResourceChange(
            f"usage_die 축은 step_down/deplete만 받는다(받은 연산: {op.operation!r})",
            axis=op.axis,
        )

    if stat.form == "none":
        raise InvalidResourceChange("none 형태 축에는 어떤 동작도 적용할 수 없다", axis=op.axis)

    raise InvalidResourceChange(f"알 수 없는 form: {stat.form!r}", axis=op.axis)


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


def _is_depleted(stat: StatEntry) -> bool:
    """형태마다 「다 썼다」의 뜻이 다르다 — `numeric`은 `current <= 0`,
    `usage_die`는 `current == 0`(0이 소진이라는 것은 entities.py가 이미
    정한 규약), `clock`은 `current >= max`(칸이 다 찼다), `named_slots`는
    빈 슬롯이 0개(전부 찼다)다. `tag_list`/`none`은 소진 개념이 없어
    항상 `False`다."""
    if stat.form == "numeric":
        return stat.current is not None and stat.current <= 0
    if stat.form == "usage_die":
        return stat.current is not None and stat.current == 0
    if stat.form == "clock":
        return stat.current is not None and stat.max is not None and stat.current >= stat.max
    if stat.form == "named_slots":
        slot_values = stat.slot_values or ()
        return len(slot_values) > 0 and all(value is not None for value in slot_values)
    return False


def depleted_axes(stats: tuple[StatEntry, ...]) -> tuple[DepletedAxis, ...]:
    """형태별 「다 썼다」 기준(`_is_depleted`)을 만족하고
    `depleted_effect_ref`가 있는 축의 목록을 돌려준다.

    고리를 부르는 데까지가 이 함수의 몫이다 — 그 고리(효과 참조)가 실제로
    무엇을 하는지는 D7(원자 연산 목록)이 다룰 다음 마일스톤이다(D-08).
    """
    result: list[DepletedAxis] = []
    for stat in stats:
        if stat.depleted_effect_ref is not None and _is_depleted(stat):
            result.append(DepletedAxis(axis=stat.name, effect_ref=stat.depleted_effect_ref))
    return tuple(result)
