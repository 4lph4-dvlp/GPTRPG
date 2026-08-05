"""매 턴 에이전트에게 넘기는 것을 네 가지로 못박는다.

ROADMAP 성공조건 4, 설계 문서 §3.8이 정한 것 그대로다 — 장면에 등장한 대상 /
내 캐릭터 상태 / 위협 시계 상태 / 최근 대화 열 턴, 그 이상도 이하도 아니다.
AI가 저장소 전체를 훑는 경로를 만들지 않기 위해, 에이전트가 받는 문맥은 이
파일이 선언하는 값 객체뿐이다 — `gptrpg.event_log`나 `gptrpg.session_actor`를
참조할 수단 자체가 없다(`.importlinter` contract:3).
"""

from dataclasses import dataclass, fields

from gptrpg.rules_core.entities import Entity, StatEntry

RECENT_TURNS_LIMIT = 10
"""매 턴 넣는 최근 대화의 최대 개수 (D-31)."""


class TooMuchContext(Exception):
    """`recent_turns`가 `RECENT_TURNS_LIMIT`을 넘겼을 때 던진다.

    조용히 잘라내면 "열 턴 고정"이 깨진 것을 아무도 모른다 — 호출부가 저장소
    사건을 텍스트로 뽑을 때 직접 잘라서 넘겨야 한다.
    """

    def __init__(self, length: int) -> None:
        super().__init__(
            f"recent_turns 길이가 {length}로 RECENT_TURNS_LIMIT({RECENT_TURNS_LIMIT})을 넘었다"
        )
        self.length = length


@dataclass(frozen=True)
class ClockState:
    """위협 시계 상태 한 조각 — 몇 번째 칸인지와 전체 칸 수, 그리고 이야기 내용.

    시나리오 내용 다섯 칸(`threat_name` 이하)은 전부 기본값이 있다 —
    캐릭터·판정 시험처럼 시나리오 내용과 무관한 기존 호출부가 `clock_id`/
    `segment_index`/`segment_count`만 넘겨도 그대로 동작해야 하기 때문이다.
    """

    clock_id: str
    segment_index: int
    segment_count: int
    threat_name: str = ""
    threat_identity: str = ""
    threat_wants: str = ""
    segment_descriptions: tuple[str, ...] = ()
    catastrophe_text: str = ""


@dataclass(frozen=True)
class TurnContext:
    """매 턴 에이전트에게 넘기는 것 딱 네 가지 — 그 이상도 이하도 아니다."""

    scene_entities: tuple[Entity, ...]
    character_state: tuple[StatEntry, ...]
    clock_state: ClockState
    recent_turns: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.recent_turns) > RECENT_TURNS_LIMIT:
            raise TooMuchContext(len(self.recent_turns))


# 칸이 정확히 넷임을 코드로도 고정한다 — `entities.py`의 `ENTITY_FIELD_NAMES`
# 관례를 그대로 따른다.
TURN_CONTEXT_FIELD_NAMES = frozenset(f.name for f in fields(TurnContext))
