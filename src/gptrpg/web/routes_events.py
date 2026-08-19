"""폴링 엔드포인트: `GET /sessions/{session_id}/events?from_seq=N`.

접기 로직을 여기서 다시 짜지 않는다 — 상태 숫자를 만드는 곳은
`session_actor.projection.rebuild_state` 하나뿐이다. 사건 목록도
`event_log.store.EventStore.read_events`가 돌려주는 `GameEvent`를 그대로
응답 모델로 쓴다 — 두 번째 전송용 스키마를 손으로 만들지 않는다.

**파생값은 사건과 나란한 다른 칸에 싣는다(Phase 12.2, RESEARCH §6).**
`check_calculations`가 이 규약의 첫 사례다 — 판정의 눈이 어떻게 합계가
되는지는 사건에 없는 파생값(D-08/D-09)이라 사건 객체 자체를 바꾸지
않고, `seq`로 사건과 짝지어지는 **병렬 목록**으로 싣는다. `events` 목록의
사건 객체는 이 처리기에서 여전히 한 글자도 안 바뀐다 — 위 문단의 원래
원칙은 그대로다.

처리기는 반드시 `async def`다. FastAPI는 동기 `def` 처리기를 워커
스레드에서 돌리는데, `EventStore`의 sqlite3 연결은 만든 스레드에 묶여 있어
(`check_same_thread` 기본값) 다른 스레드에서 만지면 `ProgrammingError`가 난다.
저장소를 만지는 처리기는 전부 이벤트 루프 스레드(= lifespan이 연결을 연
스레드)에 남아 있어야 한다.

`session_id` 문자열 검증(`validate_session_id`)은 이 모듈이 아니라
`gptrpg.web.app`이 라우터를 거는 시점에 `dependencies=`로 건다 — 이 모듈이
`app.py`를 다시 import하면 순환 import가 생긴다.
"""

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from gptrpg.event_log.schema import GameEvent
from gptrpg.session_actor.actor import AUTO_ADVANCE_FAILURE_THRESHOLD
from gptrpg.session_actor.projection import rebuild_state_from_events
from gptrpg.turn.context import CLOCK_SEGMENT_COUNT
from gptrpg.web.check_views import CheckCalculationView, calculation_view_for

router = APIRouter()


class GameStateView(BaseModel):
    """`GameState`의 칸 그대로 + 화면이 분모로 쓸 `clock_segment_count`/`auto_advance_threshold`.

    `auto_advance_threshold`는 `session_actor.actor.AUTO_ADVANCE_FAILURE_THRESHOLD`를
    import해서 채운다 — 문턱값이 화면에 하드코딩되면 표시된 "/3"과 실제로
    시계를 돌리는 규칙이 어긋날 수 있다. 값이 한 자리(액터)에만 있어야
    이 어긋남이 구조적으로 불가능하다.
    """

    session_id: str
    last_seq: int
    turn_count: int
    check_count: int
    failure_count: int
    fails_since_clock: int
    clock_segment: int
    clock_advances: int
    narration_count: int
    ai_calls: int
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    cached_prompt_tokens: int
    last_grade: str | None
    clock_segment_count: int
    auto_advance_threshold: int


class PollResponse(BaseModel):
    events: list[GameEvent]
    state: GameStateView
    check_calculations: list[CheckCalculationView] = []
    """`events`와 나란한 파생값 목록(Phase 12.2) — 사건 객체 자체는 안
    바뀐다. 각 항목의 `seq`가 그 순번의 `check_resolved` 사건을 가리킨다.
    판 10 미만 기록이거나 등록 안 된 룰북이면 그 판정에는 항목이 없다."""


@router.get("/sessions/{session_id}/events", response_model=PollResponse)
async def poll_events(
    session_id: str,
    request: Request,
    from_seq: int = Query(0, ge=0),
) -> PollResponse:
    """`from_seq` 이상인 사건(경계 포함)과, 리듀서가 접어 만든 현재 상태를 함께 돌려준다.

    사건이 하나도 없는 세션도 200과 빈 목록 + 초기 상태를 돌려준다 (404 아님) —
    `EventStore.read_events`/`rebuild_state_from_events` 둘 다 세션 존재 여부를
    검사하지 않고 빈 결과·초기 상태를 그대로 내어주는 동작을 그대로 물려받는다.

    **저장소를 한 번만 읽는다.** 상태는 언제나 사건 전체를 접어 만들어야
    하므로(D-08, 중간 저장 없음) 전체를 읽되, 응답에 실을 목록은 그 결과를
    잘라서 쓴다. 예전에는 `read_events(from_seq)`로 한 번, `rebuild_state`가
    내부에서 또 한 번 — 브라우저 넷이 1.5초마다 폴링하는 동안 요청마다 사건
    전체를 두 번 파싱했다. 자르는 것이 다시 읽는 것보다 언제나 싸다.

    두 값이 한 번의 읽기에서 나오므로 목록과 상태가 서로 다른 시점을 가리킬
    수 없다 — 예전에도 이 처리기 안에 `await`가 없어서 사실상 원자적이었지만,
    이제는 읽기가 하나뿐이라 그 성질이 코드 모양에서 바로 드러난다.
    """
    store = request.app.state.store
    all_events = store.read_events(session_id)
    game_state = rebuild_state_from_events(session_id, all_events)
    events = [event for event in all_events if event.seq >= from_seq]
    check_calculations = [
        view
        for event in events
        if event.event_type == "check_resolved"
        and (view := calculation_view_for(event)) is not None
    ]
    state_view = GameStateView(
        session_id=game_state.session_id,
        last_seq=game_state.last_seq,
        turn_count=game_state.turn_count,
        check_count=game_state.check_count,
        failure_count=game_state.failure_count,
        fails_since_clock=game_state.fails_since_clock,
        clock_segment=game_state.clock_segment,
        clock_advances=game_state.clock_advances,
        narration_count=game_state.narration_count,
        ai_calls=game_state.ai_calls,
        total_tokens=game_state.total_tokens,
        prompt_tokens=game_state.prompt_tokens,
        completion_tokens=game_state.completion_tokens,
        cached_prompt_tokens=game_state.cached_prompt_tokens,
        last_grade=game_state.last_grade,
        clock_segment_count=CLOCK_SEGMENT_COUNT,
        auto_advance_threshold=AUTO_ADVANCE_FAILURE_THRESHOLD,
    )
    return PollResponse(events=events, state=state_view, check_calculations=check_calculations)
