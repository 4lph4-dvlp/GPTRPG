"""d100 롤언더 판정 계산 — 순수 함수. 무작위는 PercentileRoller를 통해서만 얻는다.

`resolution.py`의 `Modifier`/`CheckOutcome`/`UnsupportedModifier`를 다시
정의하지 않고 그대로 import해서 재사용한다 — 두 판정 방식이 같은 판정 요청·
판정 결과 모양 위에서 돈다는 것의 실물 증거다.

수정치 네 유형은 계산 파이프라인에서 서로 다른 시점에 적용된다(02-RESEARCH.md
Pattern 2) — `_flat_total`을 복사해 유형만 늘리는 접근으로는 만들 수 없다:

- 굴리기 전  : `TARGET_SHIFT` — 비교 기준값(target)에 가산. 굴림 자체는 안 바뀐다
- 굴림 자체  : `BONUS_DICE`   — 십의 자리를 몇 번 굴려서 어느 쪽을 채택할지를 바꾼다
- 굴린 뒤    : `FLAT`(resolution.py 재사용) — 합계에 가산
- 판정이 끝난 후: `PUSH` — 이 함수에서는 아무 효과가 없다. 표식으로만 남아
  `push_d100`이 나중에 읽는다(조용한 건너뛰기가 아니라 명시된 의미다)
"""

from collections.abc import Sequence

from gptrpg.rules_core.dice import PercentileRoller
from gptrpg.rules_core.resolution import FLAT, CheckOutcome, Modifier, UnsupportedModifier
from gptrpg.rules_core.rulebook import GradeBand, grade_for_margin

TARGET_SHIFT = "target_shift"
"""목표값 변경 수정치 유형. value는 skill(비교 기준값)에 가산할 정수다.
굴림 절차 자체는 안 바뀐다 — OpenQuest 난이도가 이 유형으로 표현된다."""

BONUS_DICE = "bonus_dice"
"""주사위 추가·제거 수정치 유형. value가 양수면 보너스 다이스 개수, 음수면
페널티 다이스 개수다. 십의 자리를 굴리는 횟수와 채택 규칙 자체를 바꾼다 —
합계에 더할 숫자가 아니다."""

PUSH = "push"
"""재굴림(푸시 롤) 허용 표식. resolve_d100의 계산에는 아무 효과가 없다 —
push_d100이 previous.modifiers에서 이 표식의 존재 여부만 읽는다."""

_KNOWN_MODIFIER_TYPES = frozenset({FLAT, TARGET_SHIFT, BONUS_DICE, PUSH})

MAX_BONUS_DICE_MAGNITUDE = 20
"""BONUS_DICE 합의 절대값 상한(T-02-06). 이보다 크면 굴림 도구 호출 횟수가
비정상적으로 커지므로 계산이 아니라 입력 실수로 보고 거부한다. 로컬 CLI라
실제 위험은 낮지만 M1의 룰북 업로드가 이 자리를 신뢰 경계로 바꾼다."""


def percentile_value(tens: int, units: int) -> int:
    """십의 자리·일의 자리 눈 두 개를 백분위 값 하나로 합친다.

    `tens * 10 + units`가 0이면(둘 다 0) 100으로 읽는다 — 0이 아니다.
    """
    total = tens * 10 + units
    return 100 if total == 0 else total


def _flat_total(values: Sequence[int]) -> int:
    return sum(values)


class PushNotPermitted(Exception):
    """룰북이 PUSH를 허용하지 않은 판정에 `push_d100`을 호출했을 때 던진다.

    `UnsupportedModifier`와 같은 형태를 따른다 — 무엇이 왜 거부됐는지
    메시지에 담고 관련 값을 속성으로 노출한다. 룰북이 허용하지 않은
    재굴림이 조용히 일어나는 경로를 막는다.
    """

    def __init__(self, move: str) -> None:
        super().__init__(
            f"move {move!r}의 앞선 판정에 PUSH 수정치가 없어 재굴림이 허용되지 않는다"
        )
        self.move = move


def resolve_d100(
    roller: PercentileRoller,
    move: str,
    modifiers: Sequence[Modifier],
    skill: int,
    bands: tuple[GradeBand, ...],
) -> CheckOutcome:
    """굴림 도구로 백분위 눈을 굴리고, 룰북이 선언한 등급 밴드로 등급까지 산출한다.

    수정치 목록을 한 번 훑어 네 유형(FLAT/TARGET_SHIFT/BONUS_DICE/PUSH)으로
    분류한다. 어느 것도 아니면 그 자리에서 `UnsupportedModifier`를 던진다.

    계산 순서(굴리기 전 -> 굴림 자체 -> 굴린 뒤):
    1. 굴리기 전: `target = skill + (TARGET_SHIFT 값들의 합)`. PUSH는 여기서
       아무 효과가 없다 — push_d100이 이 표식을 나중에 읽는다.
    2. 굴림 자체: `dice_delta = BONUS_DICE 값들의 합`(절대값이
       `MAX_BONUS_DICE_MAGNITUDE`를 넘으면 `UnsupportedModifier`). 십의
       자리를 `1 + abs(dice_delta)`번 굴린다. `dice_delta > 0`이면 굴린
       것 중 가장 작은 값을(보너스 — 밑돌아야 유리하므로 작을수록 좋다),
       `< 0`이면 가장 큰 값을(페널티), `0`이면 유일한 값을 채택한다. 일의
       자리는 한 번만 굴린다.
    3. 굴린 뒤: `total = percentile_value(채택된 십의 자리, 일의 자리) +
       (FLAT 값들의 합)`.

    등급: `is_doubles = (채택된 십의 자리 == 일의 자리)`,
    `margin = target - total`, `grade_for_margin(margin, is_doubles, bands)`.

    `CheckOutcome.rolls`는 굴린 십의 자리 전부(버려진 것도 포함) + 일의
    자리 순서로 담는다 — 채택 규칙이 나중에 검증 가능해야 하고(D-16), 재생이
    같은 눈을 같은 순서로 소비해야 한다.

    보너스/페널티 다이스 계산 규칙은 OpenQuest SRD가 아니라 크툴루 계열
    장르 공통 관행에서 왔다 — OpenQuest 원문에는 이 메커닉이 없다.
    `[CITED: call-of-cthulhu-nachtstadt-berlin.fandom.com/wiki/Bonus_Dice_and_Penalty_Dice]`
    """
    flat_values: list[int] = []
    target_shift_values: list[int] = []
    bonus_dice_values: list[int] = []
    for modifier in modifiers:
        if modifier.type == FLAT:
            flat_values.append(modifier.value)
        elif modifier.type == TARGET_SHIFT:
            target_shift_values.append(modifier.value)
        elif modifier.type == BONUS_DICE:
            bonus_dice_values.append(modifier.value)
        elif modifier.type == PUSH:
            continue
        else:
            raise UnsupportedModifier(modifier.type, modifier.source, resolver="resolve_d100")

    target = skill + _flat_total(target_shift_values)

    dice_delta = _flat_total(bonus_dice_values)
    if abs(dice_delta) > MAX_BONUS_DICE_MAGNITUDE:
        raise UnsupportedModifier(
            BONUS_DICE, "combined bonus_dice sum", resolver="resolve_d100"
        )
    extra = abs(dice_delta)
    tens_rolls = tuple(roller.roll_tens() for _ in range(1 + extra))
    units = roller.roll_units()
    if dice_delta > 0:
        chosen_tens = min(tens_rolls)
    elif dice_delta < 0:
        chosen_tens = max(tens_rolls)
    else:
        chosen_tens = tens_rolls[0]

    total = percentile_value(chosen_tens, units) + _flat_total(flat_values)
    is_doubles = chosen_tens == units
    margin = target - total
    band = grade_for_margin(margin, is_doubles, bands)

    return CheckOutcome(
        move=move,
        rolls=tens_rolls + (units,),
        modifiers=tuple(modifiers),
        total=total,
        target=target,
        grade=band.name,
    )


def push_d100(
    roller: PercentileRoller, previous: CheckOutcome, bands: tuple[GradeBand, ...]
) -> CheckOutcome:
    """앞선 d100 판정 결과에 재굴림(푸시 롤)을 이어 붙인다.

    앞선 눈을 지우지 않는다 — 굴림 도구를 새로 불러 십의 자리 하나·일의
    자리 하나를 얻고, `rolls`는 앞선 눈 뒤에 새 눈을 이어 붙인 것으로
    만든다. `total`과 `grade`는 새로 굴린 눈만으로 다시 계산한다.
    `modifiers`와 `target`은 앞선 판정의 것을 그대로 물려받는다
    (`reroll_2d6`과 같은 불변식, D-23).

    `previous.modifiers`에 PUSH 유형이 하나도 없으면 `PushNotPermitted`를
    던진다 — 룰북이 허용하지 않은 재굴림이 조용히 일어나지 않는다.

    푸시에서는 보너스/페널티 다이스를 다시 적용하지 않는다 — 새 굴림은
    십의 자리 하나·일의 자리 하나뿐이다(`reroll_2d6`이 수정치 중 FLAT만
    다시 적용하는 것과 같은 선택). FLAT 수정치는 새 총합에 그대로 다시
    적용된다.
    """
    if not any(modifier.type == PUSH for modifier in previous.modifiers):
        raise PushNotPermitted(previous.move)

    new_tens = roller.roll_tens()
    new_units = roller.roll_units()
    flat_values = [m.value for m in previous.modifiers if m.type == FLAT]
    total = percentile_value(new_tens, new_units) + _flat_total(flat_values)
    is_doubles = new_tens == new_units
    margin = previous.target - total
    band = grade_for_margin(margin, is_doubles, bands)

    return CheckOutcome(
        move=previous.move,
        rolls=previous.rolls + (new_tens, new_units),
        modifiers=previous.modifiers,
        total=total,
        target=previous.target,
        grade=band.name,
    )
