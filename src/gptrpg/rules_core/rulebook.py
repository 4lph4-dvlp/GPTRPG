"""룰북이 선언할 수 있는 것들의 **모양**만 정의한다. 실제 선언 내용은 규칙
코어 밖(`gptrpg/rulebooks/`)에 있다.

**margin 규약(핵심):** margin은 "성공 여유분"이다. 굴려서 넘기는 방식(2d6 등)은
`총합 - 목표값`, 굴려서 밑도는 방식(d100 롤언더 등)은 `목표값 - 총합`으로
계산한다. 두 방향 모두 `margin >= 0`이 성공이 되므로, 룰북은 판정 방향을
몰라도 같은 수치 구간 어휘로 등급을 선언할 수 있다.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from gptrpg.rules_core.entities import Entity, NoneKind, ResourceAxisForm

TWO_D6 = "2d6"
"""판정 **방식** 이름 — 플랫폼이 제공하는 계산 능력의 이름이지 룰북 어휘가 아니다."""

D100_ROLL_UNDER = "d100_roll_under"
"""판정 **방식** 이름 — 위와 동일한 성격."""

D20_ROLL_UNDER = "d20_roll_under"
"""판정 **방식** 이름 — 위 둘과 동일한 성격(d20을 굴려 능력치 이하면 통과).

**11-04 시점에는 이 이름을 아는 계산기가 없다** — `session_actor.actor._RESOLVERS`에
`D20_ROLL_UNDER` 항목이 없다(D-14 시험 순수성을 위해 Task 0에서 `declare-only`로
결정됨, 11-04-PLAN.md). 이 방식을 선언한 룰북으로 실제 판정을 시도하면 조용히
다른 계산기로 대체되지 않고 `session_actor.actor.CommandRejected`
("알 수 없는 판정 방식")로 눈에 보이게 멈춘다 — 이 상태는
`tests/test_session_actor.py`의 회귀 시험으로 고정되어 있다."""


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


CheckTriggerMode = Literal["declared_list", "no_dice", "gm_discretion"]
"""판정 트리거 목록이 비어 있는 경우가 두 갈래로 갈린다는 것을 룰북이 명시적으로
골라야 한다(D-12) — 세 값은 **플랫폼 능력의 이름이지 룰북 어휘가 아니다**(위
`TWO_D6`/`D100_ROLL_UNDER`/`D20_ROLL_UNDER`와 같은 성격, 본 모듈 상단 도크스트링의
규율).

- `declared_list`: 룰북이 무브/판정 트리거 목록을 실제로 적어 뒀고, 분류기는 그
  목록에서 고른다. 이 값이면 목록이 비어 있으면 안 된다.
- `no_dice`: 이 게임은 아예 주사위를 굴리지 않는다. 목록이 비어 있는 것이 정상이고,
  그 빈 목록은 "다이스 없음"이라는 뜻이다.
- `gm_discretion`: 굴리긴 하지만 **언제 굴릴지를 고정 목록이 아니라 그 자리에서
  진행자가 정한다**(Cairn류). 목록이 비어 있는 것이 정상이고, 그 빈 목록은
  "재량으로 정한다"는 뜻이다 — `no_dice`와 같은 빈 목록이지만 의미가 다르다.
"""


@dataclass(frozen=True)
class Rulebook:
    """룰북 하나의 선언 전체 — 어떤 판정 방식을 쓰고 어떤 등급 밴드/자원
    축을 갖는가."""

    rulebook_id: str
    display_name: str
    resolution_method: str
    grade_bands: tuple[GradeBand, ...]
    resource_axes: tuple[ResourceAxisDecl, ...]
    check_trigger_mode: CheckTriggerMode

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


class ShadowedGradeBand(Exception):
    """어떤 `(margin, is_doubles)` 조합에서도 한 번도 승자가 되지 못하는
    등급 밴드가 있을 때 던진다 — 앞선 밴드들에 완전히 가려져 선언 순서상
    영영 선택될 수 없는 밴드다(D-15 ①).

    조용히 등록되면 그 등급 이름은 게임이 끝날 때까지 판정 결과로 단 한 번도
    나오지 않는데도, 룰북 작성자는 그 사실을 등록 시점에 알 방법이 없다 —
    `NoMatchingGradeBand`가 "구멍"을 런타임에 잡는 것과 대칭으로, 이 예외는
    "가려짐"을 등록 시점에 잡는다.
    """

    def __init__(self, band_name: str) -> None:
        super().__init__(f"등급 밴드 {band_name!r}가 앞선 밴드들에 완전히 가려져 있다")
        self.band_name = band_name


class UncoveredOutcomeGap(Exception):
    """어떤 `(margin, is_doubles)` 조합도 어느 밴드에도 안 맞는 구멍이
    있을 때 던진다(D-15 ②).

    조용히 등록되면 그 조합이 실제 판정에서 나올 때 `grade_for_margin`이
    `NoMatchingGradeBand`를 던져 진행 중이던 턴을 죽인다 — 이 예외는 그
    실패를 게임 도중이 아니라 룰북 등록 시점으로 앞당긴다.
    """

    def __init__(self, margin: int, is_doubles: bool) -> None:
        super().__init__(
            f"margin={margin}, is_doubles={is_doubles} 조합에 맞는 등급 밴드가 없다"
        )
        self.margin = margin
        self.is_doubles = is_doubles


def _band_matches(band: GradeBand, margin: int, is_doubles: bool) -> bool:
    """밴드 하나가 이 `(margin, is_doubles)` 조합의 제약을 전부 만족하는가.

    `grade_for_margin`과 `validate_grade_bands`가 이 헬퍼 하나를 공유한다 —
    두 곳이 서로 다른 판정 규칙을 쓰면 등록에서 통과한 룰북이 런타임에
    `NoMatchingGradeBand`를 던지는 어긋남이 생긴다.
    """
    if band.margin_at_least is not None and margin < band.margin_at_least:
        return False
    if band.margin_at_most is not None and margin > band.margin_at_most:
        return False
    if band.requires_doubles is not None and is_doubles != band.requires_doubles:
        return False
    return True


def grade_for_margin(margin: int, is_doubles: bool, bands: tuple[GradeBand, ...]) -> GradeBand:
    """선언 순서대로 훑어 제약을 전부 만족하는 첫 밴드를 돌려준다.

    `margin_at_least`는 이상, `margin_at_most`는 이하, `requires_doubles`가
    `None`이면 무관하게 통과한다. 어느 밴드도 안 맞으면 `NoMatchingGradeBand`를
    던진다 — 조용히 `None`을 돌려주지 않는다.
    """
    for band in bands:
        if _band_matches(band, margin, is_doubles):
            return band
    raise NoMatchingGradeBand(margin, is_doubles)


def validate_grade_bands(bands: tuple[GradeBand, ...]) -> None:
    """등급 밴드 선언에 「가려짐」이나 「구멍」이 있으면 등록 시점에
    거부한다(D-15, QUAL-03).

    **단순 겹침은 판정 대상이 아니다.** 두 밴드의 구간이 겹치는지 자체는
    아무 데서도 묻지 않는다 — `grade_for_margin`이 선언 순서대로 첫 매치를
    돌려주는 방식으로 겹침을 정상적으로 해소하기 때문이다. 이 저장소의 두
    룰북(던전월드류의 `strong_hit`/`weak_hit`, OpenQuest의 `critical`/`success`)이
    실제로 겹치게 선언돼 있다 — "겹치면 거부"를 글자 그대로 구현하면 이
    저장소 자신의 룰북 둘을 등록 거부하게 된다. 그래서 이 함수가 묻는 것은
    "겹치는가"가 아니라 "선언 순서대로 훑었을 때 한 번이라도 승자가 되어
    본 적이 있는가"뿐이다.

    **알고리즘.** `is_doubles`가 참/거짓인 두 세계로 나눈다. 각 세계 안에서,
    그 세계에 참여하는(`requires_doubles`가 `None`이거나 그 세계와 같은)
    밴드들의 경계(`margin_at_least`, `margin_at_most + 1`)로 정수선을 유한
    개의 원자 구간으로 쪼갠다. 각 원자 구간의 대표 margin 값 하나마다
    `grade_for_margin`과 정확히 같은 「선언 순서 첫 매치」 규칙(`_band_matches`)
    으로 승자를 가린다. 두 세계 × 모든 구간을 통틀어 한 번도 승자가 아닌
    밴드가 있으면 `ShadowedGradeBand`, 승자가 하나도 없는 구간이 있으면
    `UncoveredOutcomeGap`.
    """
    matched_indices: set[int] = set()
    for is_doubles in (True, False):
        participating = [
            band
            for band in bands
            if band.requires_doubles is None or band.requires_doubles == is_doubles
        ]
        breakpoints: set[int] = set()
        for band in participating:
            if band.margin_at_least is not None:
                breakpoints.add(band.margin_at_least)
            if band.margin_at_most is not None:
                breakpoints.add(band.margin_at_most + 1)
        if breakpoints:
            representative_margins: set[int] = set()
            for point in breakpoints:
                representative_margins.add(point)
                representative_margins.add(point - 1)
        else:
            # 참여 밴드 전부가 margin에 아무 제약이 없다(정수선 전체를
            # 덮거나, 참여 밴드가 아예 없다) — 대표점 하나면 충분하다.
            representative_margins = {0}

        for margin in sorted(representative_margins):
            winner_index: int | None = None
            for index, band in enumerate(bands):
                if _band_matches(band, margin, is_doubles):
                    winner_index = index
                    break
            if winner_index is None:
                raise UncoveredOutcomeGap(margin=margin, is_doubles=is_doubles)
            matched_indices.add(winner_index)

    for index, band in enumerate(bands):
        if index not in matched_indices:
            raise ShadowedGradeBand(band_name=band.name)


def require_band(bands: tuple[GradeBand, ...], grade_name: str) -> GradeBand:
    """이름으로 밴드를 찾는다. 없으면 `UnknownGradeName`."""
    for band in bands:
        if band.name == grade_name:
            return band
    raise UnknownGradeName(grade_name)


class EntityAxisMismatch(Exception):
    """개체가 가진 상태값 이름·형태, 또는 무브가 가리키는 능력치 이름이
    그 룰북이 선언한 자원 축과 어긋날 때 던진다(D-01).

    조용히 통과하면 룰북이 모르는 이름의 상태값이나 존재하지 않는 축을
    가리키는 무브가 등록되고, 그 어긋남은 화면·분류기 프롬프트에 닿기
    전까지 어디서도 드러나지 않는다.
    """

    def __init__(
        self,
        reason: str,
        entity_id: str | None = None,
        axis_name: str | None = None,
    ) -> None:
        super().__init__(
            f"자원 축이 룰북 선언과 어긋난다: {reason}"
            f" (entity_id={entity_id!r}, axis_name={axis_name!r})"
        )
        self.reason = reason
        self.entity_id = entity_id
        self.axis_name = axis_name


def validate_entity_axes(entity: Entity, rulebook: Rulebook) -> None:
    """개체가 가진 각 상태값이 그 개체 룰북이 선언한 자원 축 안에 있는지
    검사한다(D-01) — 「이 세계에 존재하는 축」(룰북)과 「이 개체가 가진
    축」(개체)의 분리를 검사로 성립시킨다.

    이름 비교는 파이썬 `==` 완전 일치다 — 유니코드 정규화·대소문자 접기·
    앞뒤 공백 제거를 하지 않는다. 일치하는 축을 찾으면 `StatEntry.form`이
    그 `ResourceAxisDecl.form`과 같은지도 검사한다. 룰북이 선언한 축 중
    개체가 안 가진 것은 위반이 아니다(D-04) — 방향은 개체 → 룰북 한쪽뿐이다.

    **강제 범위(D-06):** 이 함수는 「개체가 든 이름이 룰북이 적은 이름
    목록 안에 있는가」만 묻는다. 「체력」·「소지품」·「스트레스」·「진행
    원」 같은 룰북 어휘 이름을 이 함수의 상수나 조건문으로 쓰지 않는다 —
    그것이 이 저장소가 금지하는 특정 룰북 편향이다.
    """
    axes_by_name = {axis.name: axis for axis in rulebook.resource_axes}
    for stat in entity.stats:
        axis = axes_by_name.get(stat.name)
        if axis is None:
            raise EntityAxisMismatch(
                f"룰북 {rulebook.rulebook_id!r}에 선언되지 않은 축 이름 {stat.name!r}",
                entity_id=entity.entity_id,
                axis_name=stat.name,
            )
        if stat.form != axis.form:
            raise EntityAxisMismatch(
                f"축 {stat.name!r}의 선언된 form({axis.form!r})과 엔티티의"
                f" form({stat.form!r})이 다르다",
                entity_id=entity.entity_id,
                axis_name=stat.name,
            )


def validate_move_stats(default_stats: Iterable[str | None], rulebook: Rulebook) -> None:
    """룰북 무브의 `default_stat` 문자열들이 그 룰북의 `resource_axes`
    이름 목록 안에 있는지 검사한다.

    `MoveDecl`은 `gptrpg.rulebooks.moves`에 있어 `rules_core`가 그 타입을
    import할 수 없다(`.importlinter` contract 2, `rulebooks`는
    `rules_core`보다 아래 층이다) — 그래서 이 함수는 `MoveDecl` 타입이
    아니라 문자열 이터러블만 받는다. 층 경계를 넘지 않기 위한 의도적
    선택이다.

    **`None`은 검사에서 건너뛴다** — "이 무브는 접근 방식에 따라 어느
    능력치든 쓸 수 있다"는 룰북 원문의 의도적 설계다(던전월드 "Defy
    Danger"가 그 예. `.planning/todos/completed/2026-08-15-move-default-stat-optional.md`).
    구멍 검사 자체는 유지한다 — 실제로 채워진 문자열은 계속 축 목록과
    대조하고, 축에 없는 이름을 조용히 통과시키지 않는다.
    """
    axis_names = {axis.name for axis in rulebook.resource_axes}
    for default_stat in default_stats:
        if default_stat is None:
            continue
        if default_stat not in axis_names:
            raise EntityAxisMismatch(
                f"MoveDecl.default_stat {default_stat!r}가 룰북"
                f" {rulebook.rulebook_id!r}의 자원 축 목록에 없다",
                axis_name=default_stat,
            )


class InvalidTriggerMode(Exception):
    """`Rulebook.check_trigger_mode`와 그 룰북의 무브 목록 길이가 어긋날 때
    던진다(D-12).

    빈 목록은 미완성이 아니라 정상값이지만, 어느 종류의 정상인가(주사위를
    아예 안 굴리는가, 굴리되 그 자리에서 정하는가)는 룰북이 반드시 말해야
    한다 — 조용히 통과하면 목록을 채우다 만 룰북과 원래 목록이 없는 룰북이
    구분되지 않는다(T-11-14).
    """

    def __init__(self, reason: str, rulebook_id: str | None = None) -> None:
        super().__init__(
            f"check_trigger_mode가 무브 목록과 어긋난다: {reason} (rulebook_id={rulebook_id!r})"
        )
        self.reason = reason
        self.rulebook_id = rulebook_id


def validate_trigger_mode(mode: CheckTriggerMode, move_count: int) -> None:
    """빈 목록은 미완성이 아니라 정상값이고, 어느 종류의 정상인지를 룰북이
    말해야 한다(D-12) — `declared_list`인데 목록이 비었거나, `no_dice`/
    `gm_discretion`인데 목록이 차 있으면 `InvalidTriggerMode`.
    """
    if mode == "declared_list" and move_count == 0:
        raise InvalidTriggerMode(
            "declared_list인데 무브 목록이 비어 있다 — 목록을 채우거나"
            " no_dice/gm_discretion으로 바꿔야 한다"
        )
    if mode in ("no_dice", "gm_discretion") and move_count > 0:
        raise InvalidTriggerMode(
            f"{mode!r}인데 무브 목록이 채워져 있다 — 목록이 있다면 declared_list여야 한다"
        )
