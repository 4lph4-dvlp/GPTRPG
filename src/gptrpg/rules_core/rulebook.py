"""룰북이 선언할 수 있는 것들의 **모양**만 정의한다. 실제 선언 내용은 규칙
코어 밖(`gptrpg/rulebooks/`)에 있다.

**margin 규약(핵심):** margin은 "성공 여유분"이다. 굴려서 넘기는 방식(2d6 등)은
`총합 - 목표값`, 굴려서 밑도는 방식(d100 롤언더 등)은 `목표값 - 총합`으로
계산한다. 두 방향 모두 `margin >= 0`이 성공이 되므로, 룰북은 판정 방향을
몰라도 같은 수치 구간 어휘로 등급을 선언할 수 있다.
"""

from dataclasses import dataclass

from gptrpg.rules_core.entities import NoneKind, ResourceAxisForm

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
class ResourceAxisDecl:
    """룰북이 선언하는 자원 축 하나 — 이름과 그 값이 담기는 표현 형태.

    `name`이 룰북 어휘("체력" 같은 이름)를 담당하고, `form`은 플랫폼이
    아는 여섯 종 표현 형태(`ResourceAxisForm`)를 담당한다 —
    `GradeBand.name`/`margin_at_least` 쌍과 같은 "이름 목록 vs 수치·형태
    구간" 분업이다.

    **강제 범위(D-06):** 플랫폼이 강제하는 것은 「룰북이 이 목록 필드를
    실제로 적었는가」까지다(`Rulebook.resource_axes`가 기본값 없는 필수
    필드라는 것으로 이미 강제된다, D-02). 「체력·소지품·스트레스·진행
    원을 각각 다뤘는가」는 강제하지 않는다 — `rules_core`가 그 네 이름을
    알게 되는 순간 그것이 이 저장소가 금지하는 특정 룰북 편향이 된다.
    """

    name: str
    form: ResourceAxisForm
    none_kind: NoneKind | None = None
    slot_count: int | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidResourceAxis("name이 비었거나 공백뿐이다", name=self.name)
        if self.form == "none":
            if self.none_kind is None:
                raise InvalidResourceAxis(
                    "form이 none이면 none_kind가 필수다", name=self.name
                )
        elif self.none_kind is not None:
            raise InvalidResourceAxis(
                "form이 none이 아니면 none_kind를 채울 수 없다", name=self.name
            )
        if self.form == "named_slots":
            if self.slot_count is None or self.slot_count < 1:
                raise InvalidResourceAxis(
                    "form이 named_slots면 slot_count가 1 이상이어야 한다", name=self.name
                )
        elif self.slot_count is not None:
            raise InvalidResourceAxis(
                "form이 named_slots가 아니면 slot_count를 채울 수 없다", name=self.name
            )


@dataclass(frozen=True)
class Rulebook:
    """룰북 하나의 선언 전체 — 어떤 판정 방식을 쓰고 어떤 등급 밴드/자원
    축을 갖는가."""

    rulebook_id: str
    display_name: str
    resolution_method: str
    grade_bands: tuple[GradeBand, ...]
    resource_axes: tuple[ResourceAxisDecl, ...]

    def __post_init__(self) -> None:
        names = [axis.name for axis in self.resource_axes]
        if len(names) != len(set(names)):
            raise InvalidResourceAxis(
                "같은 이름의 자원 축이 룰북 안에 두 번 이상 선언됐다 — 이름이 겹치면"
                " 어느 선언이 이기는지 정해지지 않는다"
            )


class InvalidResourceAxis(Exception):
    """자원 축 선언 하나(`ResourceAxisDecl`) 또는 룰북의 자원 축 목록
    (`Rulebook.resource_axes`)이 유효하지 않을 때 던진다.

    조용히 통과하면 룰북이 선언한 목록과 실제로 개체가 갖는 값의 형태가
    어긋난 채로 등록되고, 그 어긋남은 화면·판정 코드에 닿기 전까지 어디서도
    드러나지 않는다 — `NoMatchingGradeBand`/`UnknownGradeName`이 세운 "조용히
    넘기지 않는다" 규율을 그대로 따른다.
    """

    def __init__(self, reason: str, name: str | None = None) -> None:
        super().__init__(f"자원 축 선언이 유효하지 않다: {reason} (name={name!r})")
        self.reason = reason
        self.name = name


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
