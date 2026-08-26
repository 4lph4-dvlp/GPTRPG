"""턴 문맥(`TurnContext`) 조립 — 명령줄과 웹이 함께 쓰는 단일 출처.

`gptrpg.cli | gptrpg.web` 바로 아래, `gptrpg.agents` 바로 위에 있는 층이다
(`.importlinter` contract:2). `agents`(TurnContext)와 `event_log`/
`session_actor`(저장소·프로젝션)를 전부 내려다볼 수 있으면서, `cli`와
`web` 양쪽이 이 층을 내려다볼 수 있는 유일한 자리다 — `TurnContext` 조립은
저장소를 읽어야 하므로 `agents` 안으로는 내려갈 수 없다(`agents`는
`event_log`/`session_actor`를 import할 수 없다는 계약, contract:3).
"""

from gptrpg.agents.context import ClockState, RECENT_TURNS_LIMIT, TurnContext
from gptrpg.agents.prompt_assembly import fence_player_text
from gptrpg.event_log.store import EventStore
from gptrpg.rules_core.entities import Entity
from gptrpg.rules_core.scenario import ScenarioDecl
from gptrpg.rulebooks import threat_clocks
from gptrpg.rulebooks.dungeonworld_like import EXAMPLE_SINGLE_STAT_FOE
from gptrpg.session_actor.projection import rebuild_state_from_events

# `threat_clocks`를 모듈 자체로 import하고 아래에서 `threat_clocks.*`로만
# 참조한다(개별 이름을 따로 import하지 않는다) — `scenario`가 안 주어졌을
# 때만 쓰는 기본값 갈래(`build_turn_context` 본문) 딱 한 자리에서만
# `threat_clocks.THREAT_CAST`가 등장하게 하기 위해서다(13-03 Task 2
# acceptance criteria — 하드코딩 대입 자리가 그 한 곳에만 남았음을 grep으로
# 고정한다).

CLOCK_SEGMENT_COUNT = threat_clocks.THREAT_CLOCK_SEGMENT_COUNT
"""이제는 자리표시자가 아니다 — 값의 출처는 `rulebooks.threat_clocks.
THREAT_CLOCK_SEGMENT_COUNT`다. 이 값 하나가 프롬프트에 들어가는 시계 분모와
웹 화면 머리띠 분모(`web/routes_events.py`) 양쪽에 동시에 반영된다.

세 자리(`cli/turn_flow.py`, `web/routes_events.py`, 이전 자기 자신)에
흩어져 있던 같은 값이 이 한 자리로 모였다 — 층 계약이 없던 04-01 시점에는
`web`이 `cli`를 import할 수 없어 값을 다시 선언하는 것이 유일한 방법이었지만,
이제 `gptrpg.turn`이 둘 다가 내려다볼 수 있는 자리이므로 중복이 필요 없다.

**13-03(D-18)이 판단한 것: 이 값은 이번 계획에서 시나리오별로 만들지
않는다.** 지금 이 값 하나가 프롬프트 분모와 화면 머리띠 분모 양쪽에
동시에 반영되고, 웹 라우트 두 자리(`routes_events.py`, `routes_actions.py`)
가 이 상수를 직접 import한다 — 시나리오별로 가르려면 그 두 자리도 함께
옮겨야 하고, 그것은 위협 시계 진행 규칙 확장(Phase 15) 소관이다. 대신
`rulebooks.scenarios.validate_registered_scenarios()`가 등록 시점에
「모든 시나리오의 `threat_clock.segment_descriptions` 길이가 이 값과
같아야 한다」를 강제한다 — 칸 수가 다른 시나리오가 조용히 들어와 분모가
어긋나는 일이 구조적으로 막힌다."""


def build_turn_context(
    store: EventStore,
    session_id: str,
    rulebook_id: str,
    *,
    scenario: ScenarioDecl | None = None,
    party_state: tuple[Entity, ...] | None = None,
    actor_character_id: str | None = None,
    character_names: dict[str, str] | None = None,
) -> TurnContext:
    """`TurnContext` 다섯 칸을 채운다 — 명령줄·웹 두 호출부가 공유하는 단일 출처.

    시계 상태는 `rebuild_state`가 돌려주는 `GameState.clock_segment`에서
    「몇 번째 칸인가」를, 시나리오의 위협 시계 선언에서 이야기 내용(이름·
    정체·원하는 것·칸 설명·파국)을 채운다. 최근 턴은 저장소에서 읽은
    사건 중 선언·서사 텍스트만 뽑아 마지막 `RECENT_TURNS_LIMIT`개로
    잘라서, 장면 대상은 시나리오 캐스트 전체로 채운다(D-48 — 국면별로
    걸러내는 로직은 두지 않는다, 매 턴 캐스트 전체가 그대로 들어간다).

    **`scenario`가 주어지면(13-03, D-18) 시계 내용·장면 대상 둘 다 그
    `ScenarioDecl`의 것으로 채운다** — `scenario.cast`가 장면 대상, 등록
    시점 검사(`validate_registered_scenarios`)가 이미 `threat_clock`이
    `None`이 아님을 보장했으므로 그대로 위협 시계 내용의 출처가 된다.
    `scenario`를 생략하면(기존 CLI 경로, 그리고 이 계획이 아직 안 고친
    웹 호출부 — `scenario`를 실제로 넘기기 시작하는 것은 Task 3과
    13-04다) 지금까지처럼 `rulebooks.threat_clocks`의 시나리오 캐스트
    상수·위협 시계 내용 상수를 그대로 쓴다 — **이 함수 하나만으로는
    실행 중 동작이 안 바뀐다**(회귀 위험이 0이다).

    **파티 상태는 `party_state`가 주어지면 그것으로, 아니면 예시 개체
    하나짜리 파티(`EXAMPLE_SINGLE_STAT_FOE`)로 채운다(12-05, D-17/D-18).**
    이전에는 행위자 한 명의 상태값(`character_stats`)만 받는 자리였다 —
    이제는 파티 전원의 상태, 그중 한 명이 행위자라는 것이 일차 개념이다
    (`agents.context.TurnContext` 도크스트링). 두 인자를 모두 생략하면
    (기존 CLI 경로) 예시 개체 하나짜리 파티와 그 개체의 식별자가 기본값으로
    들어간다 — 캐릭터를 아직 고르지 않은 명령줄 경로가 쓰는 자리라
    시나리오 캐스트와 무관하게 남아 있다(기존 동작 그대로 유지). **웹
    경로는 세션에 있는 파티 구성원 전원의 「접은 지금 값」을 여기로
    넘긴다** — 시작값이 아니라 사건을 접어 만든 지금 값이다(RULE-06과
    같은 경로).

    **각 줄에 화자를 밝힌다.** 예전에는 플레이어 원문과 진행자 서사를
    "플레이어: "/"진행자: " 구분 없이 그냥 한 줄씩 이어 붙였다 — 03-04 Task 3
    라이브 검증에서 이게 실제로 문제를 냈다. 화자 표시가 없는 문장 뭉치를
    받은 모델이 그걸 "다음에 일어날 일을 서술하라"는 문맥이 아니라 "이
    사용자 입력 뭉치를 분석/요약하라"는 별개의 과제로 오인해, 서사 대신
    "The user seems to be trying multiple actions..." 같은 메타 분석과 원문
    되풀이를 내놨다. 화자 표시를 붙이면 이 텍스트 뭉치가 지금까지의
    대화록이라는 게 형태로 드러나므로, `build_gm_prompt`가 이어서 붙이는
    "분석하지 말고 서사만 써라" 지시문과 함께 이 오작동을 막는다.

    **플레이어가 친 원문에는 울타리를 친다(SAFE-05, D-10, 10-04).**
    `action_declared` 사건의 `raw_text`를 `agents.prompt_assembly.
    fence_player_text`로 감싼 뒤 "화자: " 줄을 만든다 — 이번 턴에만이 아니라
    **이후 모든 턴에 「최근 대화」로 재주입되는 과거 발화까지** 감싼다. 이번
    문장만 감싸면 한 번 통과한 적대적 문장이 울타리 밖에서 세션 내내 반복
    주입돼 방어가 한 턴짜리로 끝난다(D-10). `narration_appended`(「진행자: 」)
    줄은 **울타리로 감싸지 않는다** — AI가 쓴 서사까지 감싸는 것은 D-10이
    명시적으로 뺀 범위다(프롬프트 캐싱 순서를 다시 재약해야 하는 비용이
    얻는 것보다 크다). `gptrpg.turn`이 `gptrpg.agents`를 import하는 것은 층
    계약상 허용된다(`.importlinter` contract:2, `turn`이 `agents` 위 층) —
    `turn/judgments.py`가 이미 같은 방향으로 import하고 있다.

    **`character_names`가 없으면 전부 "플레이어: "다 — 네 명이 함께 쓰는
    세션에서 실전 발견된 문제(2026-08-04).** CLI 경로처럼 캐릭터 이름
    사전이 없는 호출부는 예전 그대로 "플레이어: "만 쓴다(회귀 없음,
    tests/test_turn_tracer.py). 웹 경로처럼 `character_names`
    (character_id -> display_name)를 넘기면, 지나간 `action_declared`
    사건 각각을 실제로 그 사건을 낸 캐릭터 이름으로 표시한다 — 넷이
    한 세션에서 번갈아 행동해도 모델이 "지금까지 전부 한 사람이 한 말"로
    뭉뚱그리지 않는다. 이 층(`gptrpg.turn`)은 `gptrpg.web`의 캐릭터 데이터를
    import하지 않는다(층 계약 — 웹이 turn을 내려다보지, 그 반대가 아니다) —
    그래서 이름 사전은 호출부가 만들어서 넘긴다.

    **시계 정보는 「지금 몇 번째 칸인가」까지만 넣는다.** `clock_advances`
    (그동안 몇 번 돌았나)도 `fails_since_clock`(실패가 몇 번 쌓였나)도
    `TurnContext`에 넣지 않는다 — 둘 다 「AI가 봐주고 있는가」를 사후에
    재는 관측 지표이고, AI가 그 지표를 보면 지표를 만족시키는 쪽으로
    서사와 제안을 바꿔서 계측 자체가 무의미해진다. 시나리오의 위협 시계
    선언이 담는 값들은 서사 내용(이름·정체·원하는 것·칸 설명·파국)이지
    관측 지표가 아니다 — 이 경계 밖의 값이다.
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
            texts.append(f"{speaker}: {fence_player_text(event.raw_text)}")
        elif event.event_type == "narration_appended":
            texts.append(f"진행자: {event.text}")
    recent_turns = tuple(texts[-RECENT_TURNS_LIMIT:])

    if scenario is not None:
        # 등록 시점 검사(`validate_registered_scenarios`)가 이미
        # `threat_clock is not None`을 보장했다(D-18) — 여기서 다시
        # 검사하지 않는다.
        clock_content = scenario.threat_clock
        assert clock_content is not None, (
            "등록된 시나리오는 threat_clock을 선언한다(D-18,"
            " validate_registered_scenarios가 이미 보장)"
        )
        scene_entities = scenario.cast
    else:
        clock_content = threat_clocks.M0_THREAT_CLOCK
        scene_entities = threat_clocks.THREAT_CAST

    clock_state = ClockState(
        clock_id="threat",
        segment_index=state.clock_segment,
        segment_count=CLOCK_SEGMENT_COUNT,
        threat_name=clock_content.name,
        threat_identity=clock_content.identity,
        threat_wants=clock_content.wants,
        segment_descriptions=clock_content.segment_descriptions,
        catastrophe_text=clock_content.catastrophe,
    )

    if party_state is not None:
        resolved_party_state = party_state
        resolved_actor_character_id = actor_character_id
    else:
        resolved_party_state = (EXAMPLE_SINGLE_STAT_FOE,)
        resolved_actor_character_id = EXAMPLE_SINGLE_STAT_FOE.entity_id

    return TurnContext(
        scene_entities=scene_entities,
        party_state=resolved_party_state,
        actor_character_id=resolved_actor_character_id,
        clock_state=clock_state,
        recent_turns=recent_turns,
    )
