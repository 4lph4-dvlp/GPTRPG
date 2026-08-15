"""적과 NPC의 숫자를 담는 **그릇**만 정의한다. 그 값이 무슨 뜻인지, 바닥나면
무슨 일이 일어나는지는 룰북이 정한다.

D-20/D-21(ROADMAP 성공조건 4, RIG-08d)을 자료구조로 직접 만족시킨다 — 상태값
하나짜리 적과 열 개짜리 적이 코드 수정 없이 같은 `Entity` 그릇에 들어간다.
이 모듈은 `rules_core` 안이므로 시간·무작위·파일·네트워크를 못 쓴다
(`.importlinter` contract:1).
"""

from dataclasses import dataclass, fields
from typing import Literal

ResourceAxisForm = Literal["numeric", "clock", "named_slots", "tag_list", "usage_die", "none"]
"""자원 축 값이 담기는 여섯 가지 표현 형태 — 룰북의 `ResourceAxisDecl.form`과
`StatEntry.form`이 이 리터럴 하나를 공유한다(D-13). 플랫폼이 아는 것은 이
여섯 형태의 모양뿐이고, "체력"·"소지품" 같은 개념 이름은 모른다(D-06)."""

NoneKind = Literal["discretionary", "absent"]
"""`form == "none"`일 때만 채우는 두 갈래(D-05) — `discretionary`는 "이
개념은 있지만 규칙으로 안 센다", `absent`는 "이 세계에 그 개념 자체가
없다"다. 둘을 하나의 `None`으로 뭉개면 "0"과 "개념 없음"과 "규칙으로 안
셈"이라는 서로 다른 세 가지 사실이 구분되지 않는다."""


class InvalidStatEntry(Exception):
    """상태값 선언 하나가 D-20이 정한 모양을 어겼을 때 던진다.

    조용히 통과하면 잘못된 상한·빈 이름이 이후 모든 소모 계산의 기준이 되고,
    그 기준은 어디서도 복원되지 않는다 (T-02-09, RESEARCH.md Security Domain V5).
    """

    def __init__(self, reason: str, name: str | None = None) -> None:
        super().__init__(f"상태값 선언이 유효하지 않다: {reason} (name={name!r})")
        self.reason = reason
        self.name = name


class InvalidEntity(Exception):
    """엔티티 선언 하나가 D-21이 정한 모양을 어겼을 때 던진다.

    이름이 겹치면 "이름으로 찾기"가 어느 쪽을 돌려줄지 정해지지 않아 계산이
    비결정적이 된다 — 조용히 통과하지 않는다 (T-02-10).
    """

    def __init__(self, reason: str, entity_id: str | None = None) -> None:
        super().__init__(f"엔티티 선언이 유효하지 않다: {reason} (entity_id={entity_id!r})")
        self.reason = reason
        self.entity_id = entity_id


@dataclass(frozen=True)
class StatEntry:
    """적/NPC/플레이어의 자원 축 값 하나를 담는 그릇 — 여덟 칸, 여섯 표현
    형태(`form`, D-13).

    D-20이 잠근 것은 "숫자 하나짜리 상태값 그릇의 모양"이었다. 그 잠금을
    뒤집는 것이 아니라, 이 그릇이 담는 **범위**를 능력치·체력 같은 수치
    축 하나에서 이름 붙은 자원 축 전체(칸·슬롯·태그·사용주사위·없음)로
    다시 그린 것이다(D-03) — D17·D31이 D-64·D-66에서 적용 범위를 다시
    그린 것과 같은 패턴. `form`은 기본값이 없다 — "모르는 것을 조용히
    기본값으로 넘기지 않는다"는 이 저장소의 규율(`UnknownEventType` 등)을
    그대로 따른다.

    "체력"이라는 개념은 `name`에 담긴 문자열이지 코드의 칸이 아니다.
    `depleted_effect_ref`는 참조 문자열일 뿐이고 플랫폼은 그 내용을 해석하지
    않는다(효과의 실제 연산은 D7, M1 범위).
    """

    name: str
    form: ResourceAxisForm
    current: int | None = None
    max: int | None = None
    depleted_effect_ref: str | None = None
    slot_values: tuple[str | None, ...] | None = None
    tags: tuple[str, ...] | None = None
    none_kind: NoneKind | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidStatEntry("name이 비었거나 공백뿐이다", name=self.name)
        if self.max is not None and self.max < 0:
            raise InvalidStatEntry("max가 음수다", name=self.name)
        # current는 음수를 거부하지 않는다 — 0 아래로 깎인 값의 뜻은
        # 룰북이 정한다(D32). 0인 current(예: 마법점 0인 언데드)도 정상이다.
        if self.depleted_effect_ref is not None and not self.depleted_effect_ref.strip():
            raise InvalidStatEntry("depleted_effect_ref가 빈 문자열이다", name=self.name)
        self._validate_form_payload()

    def _validate_form_payload(self) -> None:
        """`form`이 선언한 형태와 실제로 채워진 칸이 어긋나면 즉시 멈춘다
        (Pitfall 1) — 두 형태가 동시에 채워진 값이 화면·판정 코드에서
        `None` 역참조를 일으키는 경로를 구조적으로 막는다(T-11-01)."""
        form = self.form
        if form == "numeric":
            if self.current is None:
                raise InvalidStatEntry("numeric은 current가 필수다", name=self.name)
            if self.slot_values is not None or self.tags is not None or self.none_kind is not None:
                raise InvalidStatEntry(
                    "numeric에는 slot_values/tags/none_kind를 채울 수 없다", name=self.name
                )
        elif form == "clock":
            if self.current is None or self.max is None:
                raise InvalidStatEntry("clock은 current와 max가 둘 다 필수다", name=self.name)
            if not (0 <= self.current <= self.max):
                raise InvalidStatEntry(
                    "clock의 current는 0 이상 max 이하여야 한다", name=self.name
                )
            if self.slot_values is not None or self.tags is not None or self.none_kind is not None:
                raise InvalidStatEntry(
                    "clock에는 slot_values/tags/none_kind를 채울 수 없다", name=self.name
                )
        elif form == "named_slots":
            if self.slot_values is None or len(self.slot_values) < 1:
                raise InvalidStatEntry(
                    "named_slots는 slot_values가 필수이고 길이가 1 이상이어야 한다",
                    name=self.name,
                )
            if (
                self.current is not None
                or self.max is not None
                or self.tags is not None
                or self.none_kind is not None
            ):
                raise InvalidStatEntry(
                    "named_slots에는 current/max/tags/none_kind를 채울 수 없다", name=self.name
                )
        elif form == "tag_list":
            if self.tags is None:
                raise InvalidStatEntry("tag_list는 tags가 필수다(빈 튜플은 허용)", name=self.name)
            if (
                self.current is not None
                or self.max is not None
                or self.slot_values is not None
                or self.none_kind is not None
            ):
                raise InvalidStatEntry(
                    "tag_list에는 current/max/slot_values/none_kind를 채울 수 없다",
                    name=self.name,
                )
        elif form == "usage_die":
            if self.current is None:
                raise InvalidStatEntry("usage_die는 current가 필수다(0은 소진)", name=self.name)
            if self.slot_values is not None or self.tags is not None or self.none_kind is not None:
                raise InvalidStatEntry(
                    "usage_die에는 slot_values/tags/none_kind를 채울 수 없다", name=self.name
                )
        elif form == "none":
            if self.none_kind is None:
                raise InvalidStatEntry("none은 none_kind가 필수다", name=self.name)
            if (
                self.current is not None
                or self.max is not None
                or self.depleted_effect_ref is not None
                or self.slot_values is not None
                or self.tags is not None
            ):
                raise InvalidStatEntry(
                    "none에는 current/max/depleted_effect_ref/slot_values/tags를"
                    " 채울 수 없다",
                    name=self.name,
                )
        else:
            raise InvalidStatEntry(f"알 수 없는 form: {form!r}", name=self.name)


@dataclass(frozen=True)
class Entity:
    """적/NPC 하나 — 상태값 개수에 코드가 상한을 두지 않는다 (D-21).

    `stats`는 `list`가 아니라 `tuple`이다 — `CheckOutcome.modifiers`가 세운
    "규칙 코어 안의 순서 있는 불변 묶음은 튜플" 관례를 따른다. 튜플 길이에는
    어떤 검사도 두지 않는다 — 상태값 하나짜리 적과 열 개짜리 적이 같은
    클래스로 만들어진다.
    """

    entity_id: str
    display_name: str
    rulebook_id: str
    stats: tuple[StatEntry, ...] = ()

    def __post_init__(self) -> None:
        if not self.entity_id.strip():
            raise InvalidEntity("entity_id가 비었다", entity_id=self.entity_id)
        if not self.display_name.strip():
            raise InvalidEntity("display_name이 비었다", entity_id=self.entity_id)
        if not self.rulebook_id.strip():
            raise InvalidEntity("rulebook_id가 비었다", entity_id=self.entity_id)
        names = [stat.name for stat in self.stats]
        if len(names) != len(set(names)):
            raise InvalidEntity(
                "한 엔티티 안에 같은 이름의 상태값이 둘 이상이다", entity_id=self.entity_id
            )


# StatEntry는 정확히 이 여덟, Entity는 정확히 이 넷임을 코드로도 고정한다
# — 나중에 누가 필드를 추가/삭제하면 이 상수와 어긋나 즉시 드러난다는 것을
# 테스트가 확인한다(D-03이 StatEntry를 네 칸에서 여덟 칸으로 재고정했다).
STAT_ENTRY_FIELD_NAMES = frozenset(f.name for f in fields(StatEntry))
ENTITY_FIELD_NAMES = frozenset(f.name for f in fields(Entity))
