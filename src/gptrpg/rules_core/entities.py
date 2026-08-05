"""적과 NPC의 숫자를 담는 **그릇**만 정의한다. 그 값이 무슨 뜻인지, 바닥나면
무슨 일이 일어나는지는 룰북이 정한다.

D-20/D-21(ROADMAP 성공조건 4, RIG-08d)을 자료구조로 직접 만족시킨다 — 상태값
하나짜리 적과 열 개짜리 적이 코드 수정 없이 같은 `Entity` 그릇에 들어간다.
이 모듈은 `rules_core` 안이므로 시간·무작위·파일·네트워크를 못 쓴다
(`.importlinter` contract:1).
"""

from dataclasses import dataclass, fields


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
    """적/NPC 상태값 하나 — D-20이 확정한 네 칸뿐이다. 칸을 더 늘리지 않는다.

    "체력"이라는 개념은 `name`에 담긴 문자열이지 코드의 칸이 아니다.
    `depleted_effect_ref`는 참조 문자열일 뿐이고 플랫폼은 그 내용을 해석하지
    않는다(효과의 실제 연산은 D7, M1 범위).
    """

    name: str
    current: int
    max: int | None = None
    depleted_effect_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidStatEntry("name이 비었거나 공백뿐이다", name=self.name)
        if self.max is not None and self.max < 0:
            raise InvalidStatEntry("max가 음수다", name=self.name)
        # current는 음수를 거부하지 않는다 — 0 아래로 깎인 값의 뜻은
        # 룰북이 정한다(D32). 0인 current(예: 마법점 0인 언데드)도 정상이다.
        if self.depleted_effect_ref is not None and not self.depleted_effect_ref.strip():
            raise InvalidStatEntry("depleted_effect_ref가 빈 문자열이다", name=self.name)


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


# 필드 목록이 정확히 이 넷임을 코드로도 고정한다 — 나중에 누가 필드를
# 추가/삭제하면 이 상수와 어긋나 즉시 드러난다는 것을 테스트가 확인한다.
STAT_ENTRY_FIELD_NAMES = frozenset(f.name for f in fields(StatEntry))
ENTITY_FIELD_NAMES = frozenset(f.name for f in fields(Entity))
