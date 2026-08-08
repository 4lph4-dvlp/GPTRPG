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
    """매 턴 에이전트에게 넘기는 것 딱 네 가지 — 그 이상도 이하도 아니다.

    09-02부터는 `action_classifier`와 `situation_judge` 둘만 이 값 객체를
    받는다 — 이 둘이 시나리오 원문(시계 상태 포함)까지 필요한 유일한 역할이다.
    서술(`master_gm.narrate`)은 더 이상 `TurnContext`를 받지 않는다(D-06) —
    좁아진 `NarrationFacts`(아래)를 받는다.
    """

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


class ContextCapExceeded(Exception):
    """역할별 문맥 값 객체 중 하나가 스스로 정한 상한을 넘겼을 때 던진다(D-66/ARCH-06).

    `TooMuchContext`(위, `TurnContext` 전용)와 달리 이 예외는 새로 생기는
    역할별 값 객체들이 공유한다 — 어느 칸이 몇 개로 몇을 넘겼는지 세 속성에
    그대로 남긴다.
    """

    def __init__(self, field_name: str, length: int, limit: int) -> None:
        super().__init__(f"{field_name} 길이가 {length}로 상한({limit})을 넘었다")
        self.field_name = field_name
        self.length = length
        self.limit = limit


CLOCK_JUDGE_RECENT_TURNS_LIMIT = 4
"""시계 판단이 받는 최근 대화 상한(ARCH-06 "각자 상한"의 첫 조각). 조건 검사는
"방금 무슨 일이 있었나"만 보면 되므로 서술용 `RECENT_TURNS_LIMIT`(10)보다
좁다 — 시계 판단은 다음 칸 조건이 이번 턴 판정으로 충족됐는지만 보고,
그 앞의 맥락 전체가 필요한 서술과는 다른 급의 문맥이다."""


@dataclass(frozen=True)
class ClockJudgeContext:
    """`clock_judge` 역할(judge_clock_signal/judge_clock_condition)이 받는 문맥 — 딱 네 칸.

    **정체·원하는 것·파국 문장을 담는 칸이 아예 없다** — 조건 검사는 "다음
    칸에 적힌 일이 일어났는가"만 판단하면 되고, 시나리오 원문 전체는 필요
    없다. 이 값 객체의 칸을 넷으로 좁힌 것 자체가 그 필요 없음을 타입
    차원에서 막는다(ARCH-02와 같은 원리 — 필요 이상을 애초에 못 받게
    설계한다).
    """

    clock_position: str
    """예 `"2/4"` — 현재 칸/전체 칸 수를 한 줄로 표시."""
    next_segment_description: str
    """다음 칸의 자연어 설명. 없으면 빈 문자열."""
    recent_turns: tuple[str, ...]
    check_summary: str
    """이번 턴 판정 결과 요약 한 줄 — "방금 무슨 일이 있었나"의 핵심."""

    def __post_init__(self) -> None:
        if len(self.recent_turns) > CLOCK_JUDGE_RECENT_TURNS_LIMIT:
            raise ContextCapExceeded(
                "recent_turns", len(self.recent_turns), CLOCK_JUDGE_RECENT_TURNS_LIMIT
            )


SITUATION_FACTS_LIMIT = 5
"""상황판단(`situation_judge`)이 서술에 넘길 수 있는 사실 문장 개수 상한
(ARCH-02, ARCH-06 "각자 상한"의 두 번째 조각).

상한이 없으면 상황판단이 시나리오 원문을 통째로 "사실"이라 부르며 옮겨
담는 우회로가 열린다 — ARCH-02가 막으려는 것이 정확히 그 경로다. 자르는
책임은 `situation_judge.judge_situation`에 있다(모델이 이 개수보다 많이
돌려줘도 앞에서부터 잘라 넘긴다) — 아래 `NarrationFacts`는 그래도 넘치면
예외를 던지는 마지막 방어선이다.
"""


@dataclass(frozen=True)
class NarrationFacts:
    """서술(`master_gm.narrate`)이 받는 것 전부 — 위협 시계 상태를 담는 칸이 없다.

    **왜 시계 상태 칸이 아예 없는가(ARCH-02, 잠금 요구사항):** 서술 담당은
    진행자 지시문·규칙·시나리오 원문(정체·원하는 것·파국 문장·칸 설명)을
    받지 않는다. 지금 이 칸에서 무슨 일이 벌어지는가는 상황판단이
    `scene_summary` 한두 문장으로 좁혀 준 것만 받는다. 이 칸을 나중에
    추가하는 것은 곧 ARCH-02 위반이다 — "그 칸은 안 쓰기로 한다"는 관례가
    아니라, 애초에 그 칸이 타입에 없다는 것으로 막는다.

    (09-03이 여기에 `new_entities` 칸을 하나 더한다 — 그 칸도 시나리오
    원문이 아니라 이번 턴 장면에 새로 등장한 대상 목록일 뿐이다.)
    """

    check_summary: str
    scene_summary: str
    facts: tuple[str, ...]
    scene_entities: tuple[Entity, ...]
    character_state: tuple[StatEntry, ...]
    recent_turns: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.facts) > SITUATION_FACTS_LIMIT:
            raise ContextCapExceeded("facts", len(self.facts), SITUATION_FACTS_LIMIT)
        if len(self.recent_turns) > RECENT_TURNS_LIMIT:
            raise ContextCapExceeded(
                "recent_turns", len(self.recent_turns), RECENT_TURNS_LIMIT
            )
