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
("알 수 없는 판정 방식")로 눈에 보이게 멈추고, 사건 기록에는 아무것도 안
쌓인다 — 이 상태는
`tests/test_session_actor.py#test_rulebook_with_no_registered_resolver_is_rejected_not_silently_substituted`
로 고정되어 있다."""

StatUsage = Literal["add_to_dice_total", "use_as_target"]
"""능력치가 판정 계산에 쓰이는 방식 — 판정 **방식** 이름(`TWO_D6`/
`D100_ROLL_UNDER`/`D20_ROLL_UNDER`)과 같은 성격이다: 플랫폼 능력의 이름이지
룰북 어휘가 아니다(D-01).

- `add_to_dice_total`: 능력치 값이 굴림 합계에 더해지는 수정치가 된다(2d6
  등급식이 쓰는 방식 — "STR이 높으면 판정 합계가 커진다").
- `use_as_target`: 능력치 값 자체가 판정의 비교 기준값(target)이 된다(d100
  롤언더가 쓰는 방식 — "기술값 이하가 나와야 성공").
"""


@dataclass(frozen=True)
class StatModifierBand:
    """능력치 원값 → 보정치로 바꾸는 구간표 하나(D-01의 둘째 층).

    `GradeBand.margin_at_least`/`margin_at_most`와 같은 구간 모양이다 —
    `value_at_least`가 이상, `value_at_most`가 이하, 둘 다 `None`이면 그
    구간은 무제한이다. 능력치 원값을 그대로 수정치로 쓰지 않고 구간표로
    바꾸는 룰북을 위한 선언이다(예: "능력치 12~13이면 +1"). 지금 저장소의
    세 룰북은 아무도 이 구간표를 쓰지 않는다 — 능력치 값을 그대로
    `add_to_dice_total`/`use_as_target`에 쓴다.
    """

    value_at_least: int | None
    value_at_most: int | None
    modifier: int


@dataclass(frozen=True)
class GradeBand:
    """룰북이 선언하는 등급 밴드 하나 — 이름과 그 이름이 적용되는 조건.

    `name`이 "이름 목록" 쪽을, `margin_at_least`/`margin_at_most`가 "수치 구간"
    쪽을 담당한다. `requires_doubles`가 `None`이면 두 눈이 같은지는 무관하다.

    **세 칸이 각자 독립이다(D-13/D-14, RULE-14).** 이름 하나에서 세 사실을
    전부 읽을 수 있지만, 그 셋은 서로에게서 자동으로 뽑히지 않는다:

    | 칸 | 뜻 |
    |---|---|
    | `succeeded` | 이 등급이 시도한 일을 이루었는가 |
    | `costs` | 이 등급에 대가가 붙는가(결과 목록을 태우는가) |
    | `counts_as_failure` | 위협 시계가 도는 입력으로 세는가 |

    **왜 자동으로 뽑지 않는가:** 「성공했는데도 상황은 나빠진다」를 쓰는
    룰북(PbtA류의 부분 성공, 예: `weak_hit` — `succeeded=True, costs=True,
    counts_as_failure=False`)을 담을 수 있어야 하고, 이 저장소 코드는 이미
    `counts_as_failure`를 나머지 판단(성공 여부)과 독립적으로 선언에서 읽고
    있다(D-14). 그래서 `succeeded=True`이면서 `counts_as_failure=True`인
    조합도(성공했지만 그 성공이 위협 시계를 돌리는 룰북) 등록을 거부하지
    않는다 — 셋 다 필수 칸이고 기본값이 없다("모르는 것을 조용히 기본값으로
    넘기지 않는다"는 `StatEntry.form`과 같은 저장소 규율).

    **`succeeded`/`costs`는 사건에 기록하지 않는다** — `counts_as_failure`와
    다르다. `counts_as_failure`는 `rules_core`의 리듀서가 필요로 해서
    `CheckResolved` 사건에 실린다(리듀서는 룰북을 모르므로 사건에 실려
    오지 않으면 실패를 셀 수 없다). `succeeded`/`costs`를 읽는 자리
    (`session_actor`/`web` — 결과 목록을 태울지 정하는 자리)는 이미
    `rulebook_id`를 알고 있어 `require_band`로 선언에서 직접 읽을 수
    있으므로, 이번에는 사건 칸을 늘리지 않는다(`EVENT_SCHEMA_VERSION`을
    또 올리지 않는다). **나중에 접기(fold) 자체가 이 두 값을 필요로 하게
    되면 그때가 판을 올릴 시점이다.**
    """

    name: str
    counts_as_failure: bool
    succeeded: bool
    costs: bool
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
    stat_usage: StatUsage | None = None
    """이 축이 판정 계산에 능력치로 쓰이는 방식(D-01). `None`이면 이
    축은 판정에 안 쓰인다 — `resolution.build_stat_check_input`이
    `StatNotUsableInChecks`로 거절한다."""
    stat_modifier_bands: tuple[StatModifierBand, ...] | None = None
    """능력치 원값 → 보정치 구간표(D-01 둘째 층). `stat_usage`가 `None`이면
    이 칸도 채울 수 없다 — 판정에 안 쓰는 축의 구간표는 뜻이 없다."""

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
        if self.stat_modifier_bands is not None and self.stat_usage is None:
            raise InvalidStatUsage(
                "stat_modifier_bands가 있으면 stat_usage가 필수다", name=self.name
            )
        if self.form == "none" and self.stat_usage is not None:
            raise InvalidStatUsage(
                "form이 none인 축에는 stat_usage를 채울 수 없다 — 판정에 안 쓰는"
                " 축이 동시에 판정 쓰임을 선언할 수 없다",
                name=self.name,
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
class DifficultyLevelDecl:
    """룰북이 선언하는 난이도 이름 하나 — 바깥(브라우저·CLI)이 판정에 실을
    수 있는 닫힌 이름 목록의 항목이다(D-02).

    `modifier_type`/`value`는 `resolution.Modifier`의 같은 이름 칸과 짝이
    맞는다 — `require_difficulty`가 이름으로 이 선언을 찾으면, 호출부가
    그 값으로 `Modifier(type=modifier_type, value=value, source=f"difficulty:{name}")`를
    만든다. 이름이 이겨서 값이 나오는 구조는 `GradeBand.name`/`require_band`와
    같은 "이름 목록 vs 수치" 분업이다.
    """

    name: str
    modifier_type: str
    value: int


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
    difficulty_levels: tuple[DifficultyLevelDecl, ...] = ()
    """이 룰북이 판정에 받아들이는 닫힌 난이도 이름 목록(D-02). 기본값
    빈 튜플이 「이 룰북에는 그 개념이 없다」다 — 던전월드류·Cairn처럼 난이도
    개념이 없는 룰북은 이 칸을 채우지 않는다."""

    def __post_init__(self) -> None:
        names = [axis.name for axis in self.resource_axes]
        if len(names) != len(set(names)):
            raise InvalidResourceAxis(
                "같은 이름의 자원 축이 룰북 안에 두 번 이상 선언됐다 — 이름이 겹치면"
                " 어느 선언이 이기는지 정해지지 않는다"
            )
        difficulty_names = [level.name for level in self.difficulty_levels]
        if len(difficulty_names) != len(set(difficulty_names)):
            raise InvalidDifficultyLevels(
                "같은 이름의 난이도가 룰북 안에 두 번 이상 선언됐다 — 이름이 겹치면"
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


class InvalidStatUsage(Exception):
    """`ResourceAxisDecl.stat_usage`/`stat_modifier_bands`의 조합이 D-01이
    정한 모양을 어겼을 때 던진다.

    조용히 통과하면 판정에 안 쓰기로 한 축이 구간표를 갖거나, 구간표만 있고
    쓰임 방식이 없는 어긋난 선언이 등록되어 판정 계산 시점에야 드러난다 —
    `InvalidResourceAxis`가 세운 "조용히 넘기지 않는다" 규율을 그대로 따른다.
    """

    def __init__(self, reason: str, name: str | None = None) -> None:
        super().__init__(f"능력치 쓰임 선언이 유효하지 않다: {reason} (name={name!r})")
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


class InvalidDifficultyLevels(Exception):
    """`Rulebook.difficulty_levels` 선언 자체가 유효하지 않을 때 던진다
    (예: 같은 이름이 두 번 이상 선언됨) — `InvalidResourceAxis`가 자원 축
    이름 중복에 던지는 것과 같은 이유·같은 "조용히 넘기지 않는다" 규율이다.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(f"난이도 선언이 유효하지 않다: {reason}")
        self.reason = reason


class UnknownDifficultyLevel(Exception):
    """룰북 선언에 없는 난이도 이름으로 `require_difficulty`를 불렀을 때
    던진다(D-02) — `UnknownGradeName`과 같은 이유: 오타난·조작된 난이도
    이름이 조용히 기록에 남는 경로를 막는다. 바깥(브라우저·CLI)이 판정에
    실을 수 있는 것은 이 함수가 찾아낼 수 있는 이름뿐이다."""

    def __init__(self, difficulty_name: str) -> None:
        super().__init__(f"룰북 선언에 없는 난이도 이름: {difficulty_name!r}")
        self.difficulty_name = difficulty_name


def require_difficulty(rulebook: "Rulebook", name: str) -> DifficultyLevelDecl:
    """이름으로 난이도 선언을 찾는다. 없으면 `UnknownDifficultyLevel`.

    `require_band`와 같은 모양이다 — 바깥에서 받는 것은 이름뿐이고, 그
    이름이 실제로 가리키는 수정치 값은 이 함수를 거쳐야만 나온다(D-02:
    자유 숫자가 판정 계산에 들어갈 통로를 닫는다).
    """
    for level in rulebook.difficulty_levels:
        if level.name == name:
            return level
    raise UnknownDifficultyLevel(name)


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
