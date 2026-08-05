"""룰북이 선언할 수 있는 것들의 **모양**만 정의한다. 실제 선언 내용은 규칙
코어 밖(`gptrpg/rulebooks/`)에 있다.

**margin 규약(핵심):** margin은 "성공 여유분"이다. 굴려서 넘기는 방식(2d6 등)은
`총합 - 목표값`, 굴려서 밑도는 방식(d100 롤언더 등)은 `목표값 - 총합`으로
계산한다. 두 방향 모두 `margin >= 0`이 성공이 되므로, 룰북은 판정 방향을
몰라도 같은 수치 구간 어휘로 등급을 선언할 수 있다.
"""

from dataclasses import dataclass

TWO_D6 = "2d6"
"""판정 **방식** 이름 — 플랫폼이 제공하는 계산 능력의 이름이지 룰북 어휘가 아니다."""

D100_ROLL_UNDER = "d100_roll_under"
"""판정 **방식** 이름 — 위와 동일한 성격."""


@dataclass(frozen=True)
class GradeBand:
    """룰북이 선언하는 등급 밴드 하나 — 이름과 그 이름이 적용되는 조건.

    `name`이 "이름 목록" 쪽을, `margin_at_least`/`margin_at_most`가 "수치 구간"
    쪽을 담당한다. `requires_doubles`가 `None`이면 두 눈이 같은지는 무관하다.
    """

    name: str
    counts_as_failure: bool
    margin_at_least: int | None = None
    margin_at_most: int | None = None
    requires_doubles: bool | None = None


@dataclass(frozen=True)
class Rulebook:
    """룰북 하나의 선언 전체 — 어떤 판정 방식을 쓰고 어떤 등급 밴드를 갖는가."""

    rulebook_id: str
    display_name: str
    resolution_method: str
    grade_bands: tuple[GradeBand, ...]


class NoMatchingGradeBand(Exception):
    """어느 밴드의 제약도 만족하지 않는 margin/doubles 조합이 나왔을 때 던진다.

    조용히 None이나 기본 등급을 돌려주면 틀린 등급이 기록에 남고 이후 어디서도
    복원되지 않는다 — `UnsupportedModifier`/`UnknownEventType`이 세운 규율과
    같은 이유로 예외로 실패시킨다.
    """

    def __init__(self, margin: int, is_doubles: bool) -> None:
        super().__init__(f"margin={margin}, is_doubles={is_doubles}에 맞는 등급 밴드가 없다")
        self.margin = margin
        self.is_doubles = is_doubles


class UnknownGradeName(Exception):
    """룰북 선언에 없는 등급 이름으로 밴드를 찾으려 했을 때 던진다.

    오타난 등급 이름이 조용히 기록에 남는 경로를 막는 방어선이다(T-02-02).
    """

    def __init__(self, grade_name: str) -> None:
        super().__init__(f"룰북 선언에 없는 등급 이름: {grade_name!r}")
        self.grade_name = grade_name


def grade_for_margin(margin: int, is_doubles: bool, bands: tuple[GradeBand, ...]) -> GradeBand:
    """선언 순서대로 훑어 제약을 전부 만족하는 첫 밴드를 돌려준다.

    `margin_at_least`는 이상, `margin_at_most`는 이하, `requires_doubles`가
    `None`이면 무관하게 통과한다. 어느 밴드도 안 맞으면 `NoMatchingGradeBand`를
    던진다 — 조용히 `None`을 돌려주지 않는다.
    """
    for band in bands:
        if band.margin_at_least is not None and margin < band.margin_at_least:
            continue
        if band.margin_at_most is not None and margin > band.margin_at_most:
            continue
        if band.requires_doubles is not None and is_doubles != band.requires_doubles:
            continue
        return band
    raise NoMatchingGradeBand(margin, is_doubles)


def require_band(bands: tuple[GradeBand, ...], grade_name: str) -> GradeBand:
    """이름으로 밴드를 찾는다. 없으면 `UnknownGradeName`."""
    for band in bands:
        if band.name == grade_name:
            return band
    raise UnknownGradeName(grade_name)
