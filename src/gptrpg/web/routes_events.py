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

from gptrpg.event_log.schema import CreationHostClaimed, GameEvent
from gptrpg.rulebooks import UnknownRulebook, get_rulebook
from gptrpg.rules_core.reducer import GameState
from gptrpg.rules_core.rulebook import Rulebook
from gptrpg.session_actor.actor import AUTO_ADVANCE_FAILURE_THRESHOLD
from gptrpg.session_actor.projection import rebuild_state_from_events
from gptrpg.turn.context import CLOCK_SEGMENT_COUNT
from gptrpg.web import creation_state
from gptrpg.web.check_views import CheckCalculationView, calculation_view_for

router = APIRouter()


class CreationCharacterView(BaseModel):
    """완성된 캐릭터 하나(D-04) — 목록으로 만들기 진행 상태를 그린다.

    `consented`/`required_steps_filled`는 서버가 이미 하는 판단을 그대로
    옮긴 것이지 화면이 다시 계산하는 값이 아니다(D-04, Phase 12.2가 세운
    규율).
    """

    character_id: str
    display_name: str
    consented: bool
    required_steps_filled: bool


class CreationReopenedStepView(BaseModel):
    """지금 다시 열려 있는 항목 하나(D-11 부분 재진행). 자기 것만 고르는
    일은 화면이 `character_id`로 한다 — 이 목록 자체는 세션 전체를 담는다."""

    character_id: str
    step_id: str


class CreationStepValueView(BaseModel):
    """만들기 항목 하나가 접힌 뒤의 값(`CreationStepFold`의 화면용 얇은
    거울) — 같은 키로 다시 오면 나중 값이 이긴다는 규칙은 서버(리듀서)만
    적용한다(D-09 경계, Phase 12.2가 고친 사고를 반복하지 않는다).

    **`browser_id`를 싣지 않는다(T-12.3-05)** — `CreationStepFold`에는
    있지만 화면이 쓸 일이 없고, 실으면 남의 식별자가 세션의 네 탭 전부에
    뿌려진다.
    """

    character_id: str
    step_id: str
    kind: str
    text_value: str | None
    picked: list[str] | None
    axis_values: list[tuple[str, int]] | None
    """(축 이름, 값) 짝의 목록 — pydantic이 튜플을 JSON 배열로 그대로
    직렬화한다(`[[axis_name, value], ...]`). 새 응답 모델을 하나 더
    늘리지 않는다."""
    rolls: list[int] | None
    seq: int


class GameStateView(BaseModel):
    """`GameState`의 칸 그대로 + 화면이 분모로 쓸 `clock_segment_count`/`auto_advance_threshold`.

    `auto_advance_threshold`는 `session_actor.actor.AUTO_ADVANCE_FAILURE_THRESHOLD`를
    import해서 채운다 — 문턱값이 화면에 하드코딩되면 표시된 "/3"과 실제로
    시계를 돌리는 규칙이 어긋날 수 있다. 값이 한 자리(액터)에만 있어야
    이 어긋남이 구조적으로 불가능하다.

    **만들기 칸(D-04, Phase 12.3)도 같은 규율을 따른다 — 값이 한 자리
    (서버)에만 있어야 어긋남이 구조적으로 불가능하다.** 계산은
    `creation_state.py`(서버 두 라우터가 공유)와 `GameState`에서 그대로
    가져온다. 화면은 이 칸들을 읽기만 하고 다시 접지 않는다.

    **방장이 누구인지는 이 응답에 없다(T-12.3-05).** `creation_host_claimed`
    는 여부(불리언)만 담는다 — 「내가 방장인가」는 부른 사람에게만 답하는
    전용 경로(`POST /creation/host`)가 답한다. 뒤에 오는 계획이 편의로
    `creation_host_browser_id`를 여기 싣지 않도록 이유를 남긴다: 방장의
    식별자가 새면 그 값을 그대로 넣어 승계를 가로챌 수 있다.
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

    party_size_fixed: int | None
    """방장이 확정한 이 세션의 인원(D-01) — `None`은 아직 확정 전."""
    creation_rulebook_id: str | None
    """인원 확정과 함께 정해지는 이 세션의 룰북(D-01). `None`이면 만들기가
    아직 시작되지 않은 세션이다."""
    party_roster: list[str] | None
    """잠긴 명단(D-08) — `None`과 빈 목록의 뜻이 다르다는 `GameState` 규약을
    그대로 옮긴다. `None`은 「아직 안 잠겼다」, 빈 목록은 이 저장소 규칙상
    일어나지 않지만 `GameState.party_roster`의 타입을 그대로 반영한다."""
    creation_unfinished_character_ids: list[str]
    """항목을 하나라도 냈지만 아직 완성되지 않은 사람의 닫힌 목록
    (`creation_state.unfinished_candidates` 그대로)."""
    creation_current_speaker_id: str | None
    """GM이 가장 최근에 지목한 사람 — 그 사람이 이미 완성됐으면 차례가
    끝난 것이므로 `None`이다.

    **해제 조건이 하나 더 있다(Phase 12.3-08, T-12.3-22).** 그 사람이
    자기 차례를 흘려보낸 것으로 판정돼도(`creation_state.forfeited_nominee`)
    이 값은 `None`이다 — 그래서 이 값은 이제 사건 기록만의 함수가
    아니라 시계(재실 신호·항목 제출 시각)에도 의존한다."""
    creation_characters: list[CreationCharacterView]
    """완성된 캐릭터 목록 — 이름·동의 여부·룰북 최소선 충족 여부."""
    creation_reopened_step_ids: list[CreationReopenedStepView]
    """지금 다시 열려 있는 항목들(D-11)."""
    creation_step_values: list[CreationStepValueView]
    """접힌 뒤의 항목 값 전부(D-09) — 확정한 항목이 목록으로 보이고 각
    항목 옆에 고치기가 있으려면(D-09) 화면이 이 목록을 읽어야 한다. 접는
    일(같은 키가 다시 오면 나중 것이 이긴다)은 서버만 한다."""
    creation_host_claimed: bool
    """이 세션의 방장이 잡혔는지 **여부만**(D-11) — `creation_host_browser_id`
    값 자체는 절대 싣지 않는다(T-12.3-05). 다른 브라우저의 식별자가 네 탭
    전부에 뿌려지면 그 값을 사칭해 남의 항목을 제출할 수 있게 된다. 「내가
    방장인가」는 부른 사람에게만 답하는 전용 경로(12.3-03)가 답한다."""


def _creation_character_views(
    game_state: GameState, rulebook: Rulebook | None
) -> list[CreationCharacterView]:
    """완성된 캐릭터마다 이름·동의·룰북 최소선 충족 여부를 묶는다.

    `rulebook`이 `None`이면(룰북을 못 찾았거나 아직 안 정해졌으면)
    `required_steps_filled`를 `False`로 둔다 — 폴링을 절대 500으로
    만들지 않는다(T-12.3-09).
    """
    views: list[CreationCharacterView] = []
    for character_id, entity in game_state.created_characters.items():
        filled = (
            creation_state.required_steps_filled(game_state, rulebook, character_id)
            if rulebook is not None
            else False
        )
        views.append(
            CreationCharacterView(
                character_id=character_id,
                display_name=entity.display_name,
                consented=game_state.creation_consents.get(character_id, False),
                required_steps_filled=filled,
            )
        )
    return views


def _creation_current_speaker_id(game_state: GameState) -> str | None:
    """가장 최근 `nominate` 지목의 대상 — 이미 완성됐으면(D-04,
    `creation_state.latest_nomination`) 또는 자기 차례를 흘려보낸
    것으로 판정됐으면(Phase 12.3-08, `creation_state.forfeited_nominee`)
    `None`이다. 판단 본문은 `creation_state`에만 있다 — 여기서는 위임만
    한다."""
    nomination = creation_state.latest_nomination(game_state)
    if nomination is None:
        return None
    nominee, _seq = nomination
    if creation_state.forfeited_nominee(game_state, game_state.session_id) == nominee:
        return None
    return nominee


def _creation_step_value_views(game_state: GameState) -> list[CreationStepValueView]:
    """`GameState.creation_step_values`를 화면용 얇은 거울로 옮긴다 —
    `browser_id`는 뺀다(T-12.3-05)."""
    return [
        CreationStepValueView(
            character_id=character_id,
            step_id=step_id,
            kind=fold.kind,
            text_value=fold.text_value,
            picked=list(fold.picked) if fold.picked is not None else None,
            axis_values=list(fold.axis_values) if fold.axis_values is not None else None,
            rolls=list(fold.rolls) if fold.rolls is not None else None,
            seq=fold.seq,
        )
        for (character_id, step_id), fold in game_state.creation_step_values.items()
    ]


def _redact_host_claimed(event: GameEvent) -> GameEvent:
    """`creation_host_claimed`의 `browser_id`/`previous_browser_id`를
    폴링 `events` 목록에서 가린다(T-12.3-05, 12.3-REVIEW.md CR-03).

    `GameStateView`(`state` 칸)는 이미 여부만 싣도록 지켜졌지만, 같은
    보호가 `events` 목록에는 없었다 — 이 사건은 `visibility: "public"`
    기본값을 쓰므로(공개 필터링 없음) 폴링하는 모든 브라우저가 지금
    방장의 `browser_id`를 평문으로 읽을 수 있었다(`CreationScreen.tsx`가
    자기 것과 비교하려고 이미 이 값을 읽고 있었다는 사실이 유출을
    스스로 증명한다). 읽은 값을 `/creation/party-size`의 `body.browser_id`
    관문(`routes_creation.py::fix_party_size`, 단순 문자열 비교)에 그대로
    실으면 방장이 아닌 브라우저가 방장 전용 조작을 통과했다 — 이 리듀서는
    그 유출 경로 자체를 닫는다. `previous_browser_id`도 같은 이유로
    가린다(옛 방장의 식별자도 남의 것이다).

    **저장소(`EventStore`)에 실제로 적힌 기록은 손대지 않는다** — 이
    함수는 응답으로 나가는 사본만 가공한다. 서버 쪽 재구성(`apply_event`)
    은 언제나 저장소의 원본을 읽으므로 리듀서 상태는 이 redaction의
    영향을 받지 않는다.

    `CreationScreen.tsx`는 이 값을 더 이상 쓰지 않는다(12.3-REVIEW-FIX,
    CR-02/CR-03 동시 수정) — 「방금 내가 승계받았나」는 `POST
    /creation/host` 응답(`you_are_host`/`changed`)과 폴링이 이미 내려주는
    `state.creation_host_claimed`만으로 판단한다.
    """
    if isinstance(event, CreationHostClaimed):
        return event.model_copy(update={"browser_id": "", "previous_browser_id": None})
    return event


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
    # 상태 재구성(위 줄)은 저장소의 원본 사건을 그대로 쓴다 — redaction은
    # 응답에 실을 목록에만 적용한다(T-12.3-05, CR-03).
    events = [_redact_host_claimed(event) for event in all_events if event.seq >= from_seq]
    check_calculations = [
        view
        for event in events
        if event.event_type == "check_resolved"
        and (view := calculation_view_for(event)) is not None
    ]

    # 룰북을 못 찾거나 아직 안 정해졌으면 만들기 최소선 계산을 False로
    # 두고 넘어간다 — 폴링이 절대 500을 내지 않아야 한다(T-12.3-09,
    # ARCH-05와 같은 층의 규율). 세션 전체가 이 응답 하나에 걸려 있다.
    rulebook = None
    if game_state.creation_rulebook_id is not None:
        try:
            rulebook = get_rulebook(game_state.creation_rulebook_id)
        except UnknownRulebook:
            rulebook = None

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
        party_size_fixed=game_state.party_size_fixed,
        creation_rulebook_id=game_state.creation_rulebook_id,
        party_roster=(
            list(game_state.party_roster) if game_state.party_roster is not None else None
        ),
        creation_unfinished_character_ids=list(
            creation_state.unfinished_candidates(game_state)
        ),
        creation_current_speaker_id=_creation_current_speaker_id(game_state),
        creation_characters=_creation_character_views(game_state, rulebook),
        creation_reopened_step_ids=[
            CreationReopenedStepView(character_id=character_id, step_id=step_id)
            for character_id, step_id in game_state.reopened_creation_steps
        ],
        creation_step_values=_creation_step_value_views(game_state),
        creation_host_claimed=game_state.creation_host_browser_id is not None,
    )
    return PollResponse(events=events, state=state_view, check_calculations=check_calculations)
