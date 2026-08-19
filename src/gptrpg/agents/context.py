"""매 턴 에이전트에게 넘기는 것을 역할별로 못박는다.

ROADMAP 성공조건 4, 설계 문서 §3.8이 세운 규율 — AI가 저장소 전체를 훑는
경로를 만들지 않기 위해, 에이전트가 받는 문맥은 이 파일이 선언하는 값
객체뿐이다. `gptrpg.event_log`나 `gptrpg.session_actor`를 참조할 수단 자체가
없다(`.importlinter` contract:3).

12-05부터 `TurnContext`/`NarrationFacts`가 담는 캐릭터 상태는 행위자 한 명이
아니라 **파티 전원**이다(D-17/D-18) — 세션1(2026-08-04)이 무너진 지점이
"AI가 네 명을 한 사람으로 인식했다"였고, 그 사고의 원인이 이 값 객체가
행위자 한 명의 상태값만 담을 자리를 갖고 있던 것이었다. 아래
`TurnContext`/`NarrationFacts` 도크스트링이 이 전환의 근거를 자세히 적는다.
"""

from dataclasses import dataclass, fields
from typing import Literal

from gptrpg.rules_core.entities import Entity, StatEntry

RECENT_TURNS_LIMIT = 10
"""매 턴 넣는 최근 대화의 최대 개수 (D-31)."""

NO_CHECK_SUMMARY = "이번 행동은 판정 없이 진행됐다."
"""판정 없이 진행한 턴에서 `check_summary` 자리에 넣는 플랫폼 고정 문장(11-06,
D-10 ②갈래).

판정이 없었으므로 판정 결과 요약(등급·목표값)이 없다 — 이 자리에 플레이어가
친 원문을 요약해 넣으면 SAFE-03이 세운 원문 울타리(`fence_player_text`)를
우회하는 경로가 생긴다(원문이 `check_summary`를 통해 울타리 없이 진행자
프롬프트로 흘러 들어간다). 그래서 룰북 어휘도 플레이어 원문도 담지 않는
플랫폼 고정 문장 하나를 쓴다. `web/routes_actions.py`의 `proceed()`와
`cli/turn_flow.py`의 `no_check` 갈래가 이 상수를 그대로 넘긴다."""


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


class ContextCapExceeded(Exception):
    """역할별 문맥 값 객체 중 하나가 스스로 정한 상한을 넘겼을 때 던진다(D-66/ARCH-06).

    `TooMuchContext`(위, `TurnContext.recent_turns` 전용)와 달리 이 예외는
    여러 역할별 값 객체가 공유한다 — 어느 칸이 몇 개로 몇을 넘겼는지 세
    속성에 그대로 남긴다.
    """

    def __init__(self, field_name: str, length: int, limit: int) -> None:
        super().__init__(f"{field_name} 길이가 {length}로 상한({limit})을 넘었다")
        self.field_name = field_name
        self.length = length
        self.limit = limit


PARTY_MEMBER_LIMIT = 8
"""`TurnContext.party_state`/`NarrationFacts.party_state`에 들어갈 수 있는
파티 구성원의 최대 개수(D-18, ARCH-06, 12-05) — `RECENT_TURNS_LIMIT`·
`NEW_ENTITY_LIMIT`과 같은 성격의 절대 안전 밸브다.

**인원의 출처가 아니다.** 12.1(캐릭터 만들기)부터 인원은 상수가 아니라
층으로 쌓인 데이터다(D-01) — `Rulebook.party_size_range`
(`rules_core/rulebook.py`)가 룰북·시나리오가 권장하는 범위를 선언하고,
방을 여는 사람이 그 범위 안에서 실제 인원을 확정한다
(`rules_core/rulebook.py`의 `validate_party_size`가 그 확정을 룰북 범위와
대조해 12.1-02가 이미 검사를 붙였다). 이 상수는 그 위에 얹힌 절대 상한일
뿐이다 — **어떤 룰북도 이 상한을 넘을 수 없고**, 넘으면 인원 확정 시점에
거절된다.

**요약하려는 장치가 아니다** — D-18이 "파티 전원의 축이 요약 없이 같은
모양으로 들어간다"를 못박았다. 이 상한은 파티 인원이 비정상적으로 커져
프롬프트가 폭주하는 것(T-12-23)만 막는다 — 정상 파티 크기에서는 절대
걸리지 않도록 넉넉하게 잡았다."""


class ActorNotInParty(Exception):
    """행위자 식별자를 파티 목록에서 찾을 수 없을 때 던진다
    (`agents.prompt_assembly.actor_stats`가 던진다).

    조용히 빈 튜플로 넘어가면 "행위자가 없는 정상 상태"와 "행위자를 못
    찾은 이상 상태"가 구분되지 않는다 — `ContextCapExceeded`와 같은 모양으로
    원인을 속성에 남긴다(D-17, T-12-25).
    """

    def __init__(self, actor_character_id: str | None, party_size: int) -> None:
        super().__init__(
            f"actor_character_id({actor_character_id!r})를 party_state(길이 {party_size})에서 "
            "찾을 수 없다"
        )
        self.actor_character_id = actor_character_id
        self.party_size = party_size


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
    """매 턴 `action_classifier`/`situation_judge`에게 넘기는 것 다섯 칸.

    **일차 개념은 「이 세션에 있는 파티의 상태, 그중 한 명이 행위자」다
    (D-17/D-18, 12-05).** 이전에는 `character_state`가 「행동한 캐릭터의
    상태값」 한 명분이었다 — 그 칸에는 파티 전원을 넣을 자리가 없었고,
    이것이 세션1(2026-08-04)에서 "AI가 네 명을 한 사람으로 인식했다"는
    사고의 코드 쪽 원인이었다. `party_state`(전원)를 일차 표현으로 올리고,
    「행위자 한 명의 상태」는 그것에서 **파생되는 값**으로 내렸다
    (`agents.prompt_assembly.actor_stats`가 이 파생을 만든다).

    **왜 행위자 상태값을 따로 저장하지 않는가.** 두 값을 나란히 저장하면
    조용히 어긋날 수 있고, 네 명을 한 사람으로 인식하는 사고가 정확히
    「어긋난 단수 표현이 살아남는」 모양이다. 파생으로 만들면 어긋날 자리가
    구조적으로 사라진다.

    09-02부터는 `action_classifier`와 `situation_judge` 둘만 이 값 객체를
    받는다 — 이 둘이 시나리오 원문(시계 상태 포함)까지 필요한 유일한
    역할이다. 다만 `action_classifier`는 `party_state` 전체가 아니라
    `actor_stats(ctx)`가 뽑은 행위자 한 명만 본다(D-17,
    `agents.prompt_assembly.build_classifier_prompt`). 서술
    (`master_gm.narrate`)은 더 이상 `TurnContext`를 받지 않는다(D-06) —
    좁아진 `NarrationFacts`(아래)를 받는다.
    """

    scene_entities: tuple[Entity, ...]
    party_state: tuple[Entity, ...]
    actor_character_id: str | None
    clock_state: ClockState
    recent_turns: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.recent_turns) > RECENT_TURNS_LIMIT:
            raise TooMuchContext(len(self.recent_turns))
        if len(self.party_state) > PARTY_MEMBER_LIMIT:
            raise ContextCapExceeded("party_state", len(self.party_state), PARTY_MEMBER_LIMIT)


# 칸이 정확히 다섯임을 코드로도 고정한다 — `entities.py`의 `ENTITY_FIELD_NAMES`
# 관례를 그대로 따른다. 11-CONTEXT.md D-03: 칸을 늘리게 되면 이 고정 시험을
# 지우지 말고 새 목록으로 다시 고정한다 — 12-05가 넷에서 다섯으로 다시
# 고정했다(character_state 한 칸 -> party_state·actor_character_id 두 칸).
TURN_CONTEXT_FIELD_NAMES = frozenset(f.name for f in fields(TurnContext))


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
    설계한다). 12-05 이후로도 파티 상태 칸을 받지 않는다(D-17) — 이
    값 객체 자체가 그 칸을 갖고 있지 않다.
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

    **12-05부터 `party_state`/`actor_character_id`가 옛 `character_state`를
    대신한다** — `TurnContext`와 같은 이유다(D-17/D-18). 서술은 지금 행동한
    사람 하나가 아니라 파티 전원의 상태를 정직하게 받는다 — 세션1에서
    AI가 네 명을 한 사람으로 인식한 사고의 반대편이다. **요약하지 않는다**
    — 어느 축을 넣을지 플랫폼이 고르지 않는다(D-18, 특정 룰북 편향 금지).

    `new_entities`(09-03)는 시나리오 원문이 아니다 — 이번 턴 장면에 새로
    등장한 대상(인물·사물)의 표시 이름 목록일 뿐이다. `scene_entity_judge`가
    판단한 결과가 여기로 흘러 서술이 그 이름을 자연스럽게 등장시킨다(D-03).
    기본값 없이 명시 인자로 받는다 — 어느 호출부도 이 칸을 "빈 값이니
    생략해도 된다"고 착각하지 않게 한다.
    """

    check_summary: str
    scene_summary: str
    facts: tuple[str, ...]
    scene_entities: tuple[Entity, ...]
    party_state: tuple[Entity, ...]
    actor_character_id: str | None
    recent_turns: tuple[str, ...]
    new_entities: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.facts) > SITUATION_FACTS_LIMIT:
            raise ContextCapExceeded("facts", len(self.facts), SITUATION_FACTS_LIMIT)
        if len(self.recent_turns) > RECENT_TURNS_LIMIT:
            raise ContextCapExceeded(
                "recent_turns", len(self.recent_turns), RECENT_TURNS_LIMIT
            )
        if len(self.new_entities) > NEW_ENTITY_LIMIT:
            raise ContextCapExceeded(
                "new_entities", len(self.new_entities), NEW_ENTITY_LIMIT
            )
        if len(self.party_state) > PARTY_MEMBER_LIMIT:
            raise ContextCapExceeded(
                "party_state", len(self.party_state), PARTY_MEMBER_LIMIT
            )


ENTITY_JUDGE_RECENT_TURNS_LIMIT = 4
"""장면 신규 대상 판단이 받는 최근 대화 상한(ARCH-06 "각자 상한"의 세 번째
조각). 이 판단은 "방금 무슨 일이 있었나"만 보면 새 인물·사물 등장 여부를
가릴 수 있으므로 서술용 `RECENT_TURNS_LIMIT`(10)보다 좁다 — `clock_judge`의
`CLOCK_JUDGE_RECENT_TURNS_LIMIT`과 같은 이유의 좁힘이다."""

NEW_ENTITY_LIMIT = 3
"""한 턴에 서술이 새로 소개할 수 있는 대상(인물·사물) 개수 상한.
`action_classifier.MAX_CANDIDATES = 3`과 같은 이유의 상한이다 — 상한이
없으면 모델이 장면을 통째로 새로 짓는 우회로가 열린다."""


@dataclass(frozen=True)
class EntityJudgeContext:
    """`scene_entity_judge` 역할(judge_new_entity)이 받는 문맥 — 딱 세 칸.

    **시계 상태 칸도 파티 상태 칸도 없다** — "이번 판정 결과가 장면에
    새 인물·사물을 등장시키는가"를 판단하는 데 위협 시계가 몇 칸째인지도
    캐릭터들의 남은 자원도 필요 없다. 이 값 객체가 그 두 칸을 애초에 갖고
    있지 않은 것 자체가 ARCH-06의 "각자 상한"이다 — 필요 이상을 못 받게
    타입으로 막는다(`ClockJudgeContext`와 같은 원리, 12-05 이후로도 그대로다).
    """

    scene_entities: tuple[Entity, ...]
    recent_turns: tuple[str, ...]
    check_summary: str

    def __post_init__(self) -> None:
        if len(self.recent_turns) > ENTITY_JUDGE_RECENT_TURNS_LIMIT:
            raise ContextCapExceeded(
                "recent_turns", len(self.recent_turns), ENTITY_JUDGE_RECENT_TURNS_LIMIT
            )


OUTCOME_PICKER_RECENT_TURNS_LIMIT = 4
"""결과 선택 판단(`outcome_picker`)이 받는 최근 대화 상한(ARCH-06 "각자 상한"의
네 번째 조각, 12-06). 이 판단은 "방금 판정이 어떻게 됐는가"만 보고 룰북의
닫힌 결과 목록에서 카테고리를 고르면 되므로 서술용 `RECENT_TURNS_LIMIT`(10)
보다 좁다 — `CLOCK_JUDGE_RECENT_TURNS_LIMIT`/`ENTITY_JUDGE_RECENT_TURNS_LIMIT`과
같은 이유의 좁힘이다."""


@dataclass(frozen=True)
class OutcomePickerContext:
    """`outcome_picker` 역할(`agents.outcome_picker.pick_outcome`)이 받는
    문맥 — 딱 네 칸(12-06).

    **파티 상태 칸을 두지 않는다** — D-17이 파티 상태를 받는 역할을
    상황판단(`situation_judge`)과 서술(`master_gm`) 둘로 한정했고, 결과
    선택은 그 목록에 없다. 이 값 객체가 그 칸을 애초에 갖고 있지 않은
    것 자체가 ARCH-06의 "각자 상한"이다 — `ClockJudgeContext`/
    `EntityJudgeContext`와 같은 원리, 필요 이상을 타입 차원에서 막는다.
    """

    check_summary: str
    """이번 턴 판정 결과 요약 한 줄 — 등급·목표·합계."""
    actor_stats: tuple[StatEntry, ...]
    """행위자 자신의 상태값. `agents.prompt_assembly.actor_stats(ctx)`가
    `TurnContext.party_state`에서 뽑아 넘긴다 — 남의 상태는 안 들어간다(D-17)."""
    recent_turns: tuple[str, ...]
    category_ids: tuple[str, ...]
    """이번에 고를 수 있는 결과 카테고리 식별자의 닫힌 목록 — 룰북
    `OutcomeList.categories`의 `category_id`만 옮긴 것이다. 서술 문장은
    담지 않는다(`OutcomeCategory`가 애초에 그 칸을 갖고 있지 않다)."""

    def __post_init__(self) -> None:
        if len(self.recent_turns) > OUTCOME_PICKER_RECENT_TURNS_LIMIT:
            raise ContextCapExceeded(
                "recent_turns", len(self.recent_turns), OUTCOME_PICKER_RECENT_TURNS_LIMIT
            )


NO_ITEM_USED = "이 행동은 소지품을 안 쓴다"
"""분류기가 「이번 행동은 소지품을 쓰지 않는다」를 표시하는 특별
항목(RULE-16, 12-06 Task 3) — `action_classifier.NO_CHECK_SIGNAL`과 같은
성격의 예약 문자열이다. 지시문과 파서(`_parse_item_use`)가 이 상수를
공유해 문구가 갈리는 사고를 코드로 막는다."""

ITEM_NOT_IN_INVENTORY = "쓰는데 목록에 없다"
"""분류기가 「이 행동에 물건이 필요한데 소지품 목록에 없다」를 표시하는
특별 항목(RULE-16, D-15) — `kind="not_held"`로 이어져 재량 판정(또는
소급 선언)으로 간다."""


@dataclass(frozen=True)
class ItemUseClaim:
    """분류기가 낸 「이 행동이 소지품 중 무엇을 쓰는가」 판단 하나(RULE-16,
    12-06 Task 3).

    `kind="none"`이면 이 행동은 소지품을 안 쓴다(또는 이 룰북이 소지품을
    규칙으로 안 세어 판단 자체가 성립하지 않는다, D-09 적용 범위) —
    `item`은 그때 `None`이다. `kind="held"`면 `item`이 그 캐릭터의
    채워진 슬롯에서 파이썬 `==` 완전 일치로 고른 문자열이다. `kind=
    "not_held"`면 이 행동에 물건이 필요한데 목록에 없다는 뜻이고, `item`은
    `None`이다(어떤 물건을 원했는지는 담지 않는다 — 재량 판정/소급 선언은
    「무엇을 원했는가」가 아니라 「없다」는 사실만 필요로 한다)."""

    item: str | None
    kind: Literal["none", "held", "not_held"]
