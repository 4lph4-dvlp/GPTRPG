"""턴 문맥(`TurnContext`) 조립 — 명령줄과 웹이 함께 쓰는 단일 출처.

`gptrpg.cli | gptrpg.web` 바로 아래, `gptrpg.agents` 바로 위에 있는 층이다
(`.importlinter` contract:2). `agents`(TurnContext)와 `event_log`/
`session_actor`(저장소·프로젝션)를 전부 내려다볼 수 있으면서, `cli`와
`web` 양쪽이 이 층을 내려다볼 수 있는 유일한 자리다 — `TurnContext` 조립은
저장소를 읽어야 하므로 `agents` 안으로는 내려갈 수 없다(`agents`는
`event_log`/`session_actor`를 import할 수 없다는 계약, contract:3).
"""

from gptrpg.agents.context import ClockState, RECENT_TURNS_LIMIT, TurnContext
from gptrpg.event_log.store import EventStore
from gptrpg.rules_core.entities import StatEntry
from gptrpg.rulebooks.dungeonworld_like import EXAMPLE_SINGLE_STAT_FOE
from gptrpg.rulebooks.threat_clocks import M0_THREAT_CLOCK, THREAT_CAST, THREAT_CLOCK_SEGMENT_COUNT
from gptrpg.session_actor.projection import rebuild_state_from_events

CLOCK_SEGMENT_COUNT = THREAT_CLOCK_SEGMENT_COUNT
"""이제는 자리표시자가 아니다 — 값의 출처는 `rulebooks.threat_clocks.
THREAT_CLOCK_SEGMENT_COUNT`다. 이 값 하나가 프롬프트에 들어가는 시계 분모와
웹 화면 머리띠 분모(`web/routes_events.py`) 양쪽에 동시에 반영된다.

세 자리(`cli/turn_flow.py`, `web/routes_events.py`, 이전 자기 자신)에
흩어져 있던 같은 값이 이 한 자리로 모였다 — 층 계약이 없던 04-01 시점에는
`web`이 `cli`를 import할 수 없어 값을 다시 선언하는 것이 유일한 방법이었지만,
이제 `gptrpg.turn`이 둘 다가 내려다볼 수 있는 자리이므로 중복이 필요 없다."""


def build_turn_context(
    store: EventStore,
    session_id: str,
    rulebook_id: str,
    *,
    character_stats: tuple[StatEntry, ...] | None = None,
    character_names: dict[str, str] | None = None,
) -> TurnContext:
    """`TurnContext` 네 칸을 채운다 — 명령줄·웹 두 호출부가 공유하는 단일 출처.

    시계 상태는 `rebuild_state`가 돌려주는 `GameState.clock_segment`에서
    「몇 번째 칸인가」를, `rulebooks.threat_clocks.M0_THREAT_CLOCK`에서
    이야기 내용(이름·정체·원하는 것·칸 설명·파국)을 채운다. 최근 턴은
    저장소에서 읽은 사건 중 선언·서사 텍스트만 뽑아 마지막
    `RECENT_TURNS_LIMIT`개로 잘라서, 장면 대상은 시나리오 캐스트
    `THREAT_CAST` 전체로 채운다(D-48 — 국면별로 걸러내는 로직은 두지
    않는다, 매 턴 캐스트 전체가 그대로 들어간다). 캐릭터 상태는
    `character_stats`가 주어지면 그것으로, 아니면 `EXAMPLE_SINGLE_STAT_FOE.
    stats`로 채운다 — 이 기본값은 캐릭터를 아직 고르지 않은 명령줄 경로가
    쓰는 자리라 시나리오 캐스트와 무관하게 남아 있다. 웹 경로는 행동한
    사람의 실제 캐릭터 상태값을 여기로 넘긴다(RIG-05 연장).

    **각 줄에 화자를 밝힌다.** 예전에는 플레이어 원문과 진행자 서사를
    "플레이어: "/"진행자: " 구분 없이 그냥 한 줄씩 이어 붙였다 — 03-04 Task 3
    라이브 검증에서 이게 실제로 문제를 냈다. 화자 표시가 없는 문장 뭉치를
    받은 모델이 그걸 "다음에 일어날 일을 서술하라"는 문맥이 아니라 "이
    사용자 입력 뭉치를 분석/요약하라"는 별개의 과제로 오인해, 서사 대신
    "The user seems to be trying multiple actions..." 같은 메타 분석과 원문
    되풀이를 내놨다. 화자 표시를 붙이면 이 텍스트 뭉치가 지금까지의
    대화록이라는 게 형태로 드러나므로, `build_gm_prompt`가 이어서 붙이는
    "분석하지 말고 서사만 써라" 지시문과 함께 이 오작동을 막는다.

    **`character_names`가 없으면 전부 "플레이어: "다 — 네 명이 함께 쓰는
    세션에서 실전 발견된 문제(2026-08-04).** CLI 경로처럼 캐릭터 이름
    사전이 없는 호출부는 예전 그대로 "플레이어: "만 쓴다(회귀 없음,
    tests/test_turn_tracer.py). 웹 경로처럼 `character_names`
    (character_id -> display_name)를 넘기면, 지나간 `action_declared`
    사건 각각을 실제로 그 사건을 낸 캐릭터 이름으로 표시한다 — 넷이
    한 세션에서 번갈아 행동해도 모델이 "지금까지 전부 한 사람이 한 말"로
    뭉뚱그리지 않는다. 이 층(`gptrpg.turn`)은 `gptrpg.web.characters_data`를
    import하지 않는다(층 계약 — 웹이 turn을 내려다보지, 그 반대가 아니다) —
    그래서 이름 사전은 호출부가 만들어서 넘긴다.

    **시계 정보는 「지금 몇 번째 칸인가」까지만 넣는다.** `clock_advances`
    (그동안 몇 번 돌았나)도 `fails_since_clock`(실패가 몇 번 쌓였나)도
    `TurnContext`에 넣지 않는다 — 둘 다 「AI가 봐주고 있는가」를 사후에
    재는 관측 지표이고, AI가 그 지표를 보면 지표를 만족시키는 쪽으로
    서사와 제안을 바꿔서 계측 자체가 무의미해진다. 이번에 새로 들어오는
    `M0_THREAT_CLOCK`의 값들은 서사 내용(이름·정체·원하는 것·칸 설명·
    파국)이지 관측 지표가 아니다 — 이 경계 밖의 값이다.
    """
    # 사건을 **한 번만** 읽는다. 예전에는 `rebuild_state(store, ...)`가 한 번,
    # 바로 아래 `read_events`가 또 한 번 — 같은 사건 전체를 두 번 읽고 두 번
    # 파싱했다. 턴 하나가 이 함수를 두 번 부르므로(선언·확인) 행동 하나당
    # 전체 읽기가 네 번이었다.
    events = store.read_events(session_id)
    state = rebuild_state_from_events(session_id, events)
    texts = []
    for event in events:
        if event.event_type == "action_declared":
            speaker = "플레이어"
            if character_names is not None:
                speaker = character_names.get(event.player_id, event.player_id)
            texts.append(f"{speaker}: {event.raw_text}")
        elif event.event_type == "narration_appended":
            texts.append(f"진행자: {event.text}")
    recent_turns = tuple(texts[-RECENT_TURNS_LIMIT:])

    clock_state = ClockState(
        clock_id="threat",
        segment_index=state.clock_segment,
        segment_count=CLOCK_SEGMENT_COUNT,
        threat_name=M0_THREAT_CLOCK.name,
        threat_identity=M0_THREAT_CLOCK.identity,
        threat_wants=M0_THREAT_CLOCK.wants,
        segment_descriptions=M0_THREAT_CLOCK.segment_descriptions,
        catastrophe_text=M0_THREAT_CLOCK.catastrophe,
    )

    scene_entities = THREAT_CAST
    character_state = (
        character_stats if character_stats is not None else EXAMPLE_SINGLE_STAT_FOE.stats
    )

    return TurnContext(
        scene_entities=scene_entities,
        character_state=character_state,
        clock_state=clock_state,
        recent_turns=recent_turns,
    )
