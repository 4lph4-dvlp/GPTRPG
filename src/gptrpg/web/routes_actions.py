"""선언·확인 두 경로 — 브라우저에서 한 턴이 끝까지 돈다.

`POST /sessions/{session_id}/actions/declare`: 문장 하나 -> 무브 후보.
`POST /sessions/{session_id}/actions/confirm`: 확인/거부 -> 판정 -> 서사.

처리기는 전부 `async def`다(`routes_events.py`와 같은 이유 — `EventStore`의
sqlite3 연결이 만든 스레드에 묶여 있다). **막는 AI 호출(`classify`, 서사
조각 꺼내기)만 `asyncio.to_thread`로 작업 스레드에 내보낸다** — 그 안에서
`actor.submit(...)`을 부르지 않는다. 액터·저장소 접근은 예외 없이 이벤트
루프 스레드에 남는다(T-04-06).

`session_id` 검증은 `gptrpg.web.app`이 라우터를 거는 시점에
`dependencies=[Depends(validate_session_id)]`로 건다(이 모듈이 `app.py`를
다시 import하면 순환 import가 생긴다 — `routes_events.py`/`routes_characters.py`와
같은 관례).

**장면 삽화(`GPTRPG_IMAGERY=1`)는 응답을 보낸 **뒤에** 배경에서 만든다.** 그림
한 장이 2~4초이므로 응답 안에서 기다리면 확인 버튼의 체감 지연이 그만큼
늘어난다(D-33이 정한 목표는 확인 -> 서사 첫 글자 2초다). 배경으로 돌리면
브라우저가 이미 1.5초마다 폴링하고 있으므로 그림은 준비되는 대로 다음 폴링에
실려 들어간다 — 새 전송 경로를 만들지 않는다. 그림 생성 자체는 다시
`asyncio.to_thread`로 나가고, 사건 제출은 이벤트 루프로 돌아와서 한다(위와
같은 sqlite3 스레드 제약).
"""

import asyncio
import os
import sys
import time
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field

from gptrpg.agents.action_classifier import UnknownMove, classify
from gptrpg.agents.config import ConfigNotFound, InvalidAgentConfig, load_config
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.master_gm import narrate
from gptrpg.agents.providers import MissingApiKey, ProviderNotImplemented, UnknownProvider
from gptrpg.agents.providers.base import Provider
from gptrpg.event_log.store import SequenceConflict
from gptrpg.rulebooks import UnknownRulebook, get_rulebook
from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID
from gptrpg.rulebooks.moves import get_moves
from gptrpg.rules_core.grading import DEFAULT_TARGET
from gptrpg.rules_core.resolution import Modifier
from gptrpg.imagery import (
    ImageryConfig,
    RenderedImage,
    Renderer,
    RendererUnavailable,
    scene_prompt,
    seed_for,
)
from gptrpg.imagery.scene_prompt import WELL_SCENARIO_SETTING
from gptrpg.session_actor.actor import (
    AlreadyConfirmed,
    AlreadyResolved,
    AppendNarration,
    CommandRejected,
    ConfirmAction,
    DeclareAction,
    RecordAiCall,
    RecordSceneIllustration,
    ResolveCheck,
)
from gptrpg.session_actor.actor import SessionActor
from gptrpg.turn.clock_condition import build_clock_judge_context, run_clock_condition_check
from gptrpg.turn.context import CLOCK_SEGMENT_COUNT, build_turn_context
from gptrpg.turn.judgments import build_narration_facts, empty_turn_judgments, gather_turn_judgments
from gptrpg.web.characters_data import get_character, list_characters
from gptrpg.web.cookie_auth import read_identity
from gptrpg.web.media import media_file_path, media_url, scene_relative_path

_CHARACTER_NAMES: dict[str, str] = {c.character_id: c.display_name for c in list_characters()}
"""character_id -> display_name, `build_turn_context`의 `character_names`로
그대로 넘긴다 — 최근 대화에서 "플레이어: "만 찍히면 네 명의 발화가 전부
한 사람 것처럼 뭉뚱그려진다(2026-08-04 실전에서 발견, T-05-16급)."""

router = APIRouter()

MAX_RAW_TEXT_LEN = 2000
"""플레이어가 친 자유 문장의 상한 — 이 자리가 처음으로 신뢰할 수 없는 HTTP
본문이 된다(Phase 3까지는 신뢰되는 명령줄 인자였다). 상한이 없으면 그대로
AI 프롬프트에 흘러 들어간다(T-04-07)."""

MAX_ID_LEN = 64
"""`player_id`/`character_id`/`move`/`stat`/`rulebook_id` 같은 식별자 문자열의
상한 — `DeclareRequest.rulebook_id`·`ConfirmRequest.rulebook_id`도 이 상수를
재사용한다(08-04, QUAL-04). 새 상수를 만들지 않는다 — 이미 같은 성격(식별자
문자열)의 값이 같은 상한을 쓰는 것이 자연스럽다."""

MIN_TARGET = -200
MAX_TARGET = 200
"""`ConfirmRequest.target`의 범위(08-04, QUAL-04). d100 롤언더 룰북(OpenQuest)의
기술값은 0~100이고 난이도 수정치(`OPENQUEST_DIFFICULTY`)가 겹으로 붙어도
±50 단위라 이 범위를 넉넉히 덮는다. 2d6 등급식(dungeonworld_like)의 목표값은
`DEFAULT_TARGET=10` 근방의 한 자리~두 자리 수다. 상한을 「일단 크게」 잡아
사실상 없는 것으로 만들지 않는다 — 신뢰할 수 없는 본문이 판정 결과 사건
(`CheckResolved.target`)의 크기를 정하지 못하게 막는 것이 이 범위의 목적이다."""

MAX_MODIFIERS_COUNT = 20
"""`ConfirmRequest.modifiers` 목록의 항목 수 상한(08-04, QUAL-04, T-08-19).
룰북 수정치가 판정 하나에 이보다 많이 붙을 자연스러운 이유가 없다 — 상한이
없으면 그대로 `CheckResolved.modifiers`의 크기를 요청자가 정하게 된다."""

MAX_MODIFIER_LEN = 128
"""`ConfirmRequest.modifiers`의 항목 문자열 하나(`"유형:값:출처"` 형식)의
길이 상한(08-04, QUAL-04). `_parse_modifier`가 쪼개는 세 조각(유형·값·출처
설명)을 넉넉히 담으면서도 `MAX_RAW_TEXT_LEN`처럼 크게 잡지 않는다."""

_NO_SENTENCE = object()
"""narrate()의 첫 조각을 기다릴 때 쓰는 보초값 — `cli/turn_flow.py`의 같은
이름 상수와 같은 이유다(빈 문자열과의 신원 비교로 "아직 하나도 안 나왔다"를
안전하게 구분한다). 이어지는 조각을 꺼낼 때도 이 보초값을 그대로 쓴다 —
`next(narration_iter)`가 `StopIteration`을 던지게 두면 `asyncio.to_thread`가
그 예외를 `Future`로 옮기는 과정에서 `RuntimeError`로 바뀐다(파이썬 asyncio가
`StopIteration`이 `Future`를 타고 넘는 것을 명시적으로 금지한다) — 매번
`next(iter, _NO_SENTENCE)` 형태로 불러 예외 대신 보초값으로 "끝났다"를
알린다."""


def _parse_modifier(raw: str) -> Modifier:
    """'유형:값:출처' 형태의 수정치 문자열 하나를 `Modifier`로 바꾼다.

    `cli/turn_flow.py`의 `_parse_modifier`와 같은 형식이다 — 이 계획이 만드는
    04-06의 화면은 이 칸을 비워 보낼 계획이라(수정치 입력 화면은 만들지
    않는다, UI-SPEC) 실제 실험 세션에서는 쓰이지 않지만, 룰북 수정치를
    확인 요청에 직접 실어 보내는 경로 자체는 열어 둔다.
    """
    parts = raw.split(":", 2)
    if len(parts) != 3:
        raise ValueError(f"modifier 형식은 '유형:값:출처'여야 한다: {raw!r}")
    mod_type, raw_value, source = parts
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"modifier 값은 정수여야 한다: {raw!r}") from exc
    return Modifier(type=mod_type, value=value, source=source)


def _last_result_or_failure_envelope(provider: Provider, *, elapsed_ms: int) -> AgentResult:
    """`provider.last_result()`를 시도하고, 예외가 나면 실패 껍데기를 만들어 돌려준다.

    `cli/turn_flow.py`의 같은 이름 도우미와 같은 이유다 — 제공자가
    `note_result()`/`last_result()` 규약을 어겨도(G-03-3) 이 처리기가 raw
    traceback으로 죽지 않게 한다.
    """
    try:
        return provider.last_result()
    except Exception:  # noqa: BLE001 - 제공자가 규약을 어겨도 처리기는 죽지 않아야 한다
        return AgentResult(
            ok=False,
            value=None,
            elapsed_ms=elapsed_ms,
            prompt_tokens=0,
            completion_tokens=0,
            cached_prompt_tokens=0,
        )


class MoveCandidateView(BaseModel):
    move: str
    stat: str


class DeclareRequest(BaseModel):
    player_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    character_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    raw_text: str = Field(min_length=1, max_length=MAX_RAW_TEXT_LEN)
    rulebook_id: str = Field(default=DUNGEONWORLD_LIKE_ID, max_length=MAX_ID_LEN)


class DeclareResponse(BaseModel):
    declare_seq: int
    tier: str
    candidates: list[MoveCandidateView]


@router.post("/sessions/{session_id}/actions/declare", response_model=DeclareResponse)
async def declare(session_id: str, request: Request, body: DeclareRequest) -> DeclareResponse:
    """문장 하나를 받아 선언을 먼저 기록한 뒤 무브 후보를 돌려준다.

    **선언이 분류보다 먼저 기록된다** — 플레이어가 실제로 친 문장이
    다듬어지지 않고 그대로 기록되는 것이 정답 데이터(MEAS-04)이므로, 분류가
    실패하든 말든 `action_declared` 사건은 이미 남아 있다.

    **신원 대조가 맨 앞이다(TRUST-02, D-04).** 쿠키가 없거나 쿠키의
    캐릭터가 요청 본문의 캐릭터와 다르면 `actor.submit`을 부르기 전에 403을
    던진다 — 이 검증은 게임 상태가 아니라 요청 형식에 대한 판단이므로
    사건을 하나도 남기지 않는다(281~285줄이 적어 둔 관례).
    """
    identity = read_identity(request, session_id)
    if identity is None or identity.character_id != body.character_id:
        print("경고: 신원 검증 실패 — declare 거부", file=sys.stderr)
        raise HTTPException(status_code=403, detail="캐릭터를 다시 선택해 주세요")

    store = request.app.state.store
    registry = request.app.state.registry
    actor = registry.get_or_create(session_id)

    try:
        declare_seq = await actor.submit(
            DeclareAction(
                player_id=body.player_id,
                raw_text=body.raw_text,
                character_id=identity.character_id,
            )
        )

        character = get_character(body.character_id)
        if character is None:
            raise HTTPException(status_code=400, detail="그런 캐릭터가 없다")

        # **행동한 사람의 실제 캐릭터 상태값이 여기서 처음으로 AI 문맥에 들어간다.**
        ctx = build_turn_context(
            store,
            session_id,
            body.rulebook_id,
            character_stats=character.stats,
            character_names=_CHARACTER_NAMES,
        )

        rulebook = get_rulebook(body.rulebook_id)
        moves = get_moves(body.rulebook_id)

        choices = load_config(request.app.state.agent_config_path)
        classifier_choice = choices["action_classifier"]
        provider: Provider = request.app.state.provider_resolver(
            "action_classifier", choices, os.environ
        )

        # **막는 AI 호출이 이벤트 루프 밖 작업 스레드로 나간다** — 여기서
        # 직접 부르면 2~15초 동안 uvicorn의 단일 이벤트 루프가 멈춰 나머지
        # 세 브라우저의 폴링까지 전부 정지한다(T-04-06).
        proposal = await asyncio.to_thread(
            classify,
            provider=provider,
            model=classifier_choice.model,
            ctx=ctx,
            raw_text=body.raw_text,
            moves=moves,
            rulebook_display_name=rulebook.display_name,
        )
    except (UnknownMove, CommandRejected, UnknownRulebook) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SequenceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (
        ConfigNotFound,
        InvalidAgentConfig,
        UnknownProvider,
        MissingApiKey,
        ProviderNotImplemented,
    ) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # 저장소·액터 호출은 절대 작업 스레드로 내보내지 않는다 — 이벤트
    # 루프에서 그대로 `await`한다(`EventStore`의 sqlite3 연결이 만든
    # 스레드에 묶여 있다).
    await actor.submit(
        RecordAiCall(
            agent_role="action_classifier",
            model=classifier_choice.model,
            provider=classifier_choice.provider,
            prompt_tokens=proposal.ai.prompt_tokens,
            completion_tokens=proposal.ai.completion_tokens,
            cached_prompt_tokens=proposal.ai.cached_prompt_tokens,
            latency_ms=proposal.ai.elapsed_ms,
            caused_by_seq=declare_seq,
        )
    )

    return DeclareResponse(
        declare_seq=declare_seq,
        tier=proposal.tier,
        candidates=[MoveCandidateView(move=c.move, stat=c.stat) for c in proposal.candidates],
    )


class ConfirmRequest(BaseModel):
    player_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    move: str = Field(min_length=1, max_length=MAX_ID_LEN)
    stat: str = Field(min_length=1, max_length=MAX_ID_LEN)
    suggestion_move: str = Field(min_length=1, max_length=MAX_ID_LEN)
    suggestion_stat: str = Field(min_length=1, max_length=MAX_ID_LEN)
    confirmed: bool
    declare_seq: int = Field(ge=0)
    target: int = Field(default=DEFAULT_TARGET, ge=MIN_TARGET, le=MAX_TARGET)
    rulebook_id: str = Field(default=DUNGEONWORLD_LIKE_ID, max_length=MAX_ID_LEN)
    character_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    modifiers: list[Annotated[str, Field(max_length=MAX_MODIFIER_LEN)]] = Field(
        default_factory=list, max_length=MAX_MODIFIERS_COUNT
    )


class ConfirmResponse(BaseModel):
    confirmed: bool
    confirm_seq: int
    resolve_seq: int | None = None
    rolls: list[int] | None = None
    grade: str | None = None
    target: int | None = None
    narration_chunk_count: int = 0
    narration_failed: bool = False
    """서사 생성만 실패했다는 표시다(TRUST-06, D-08) — `rolls`/`grade`/`target`은
    그대로 채워져 있다. 「굴림 실패」(오류 상태 코드, 판정 값 없음)와 구분된다.
    기본값이 있으므로 기존 응답 조립 자리를 전부 고치지 않아도 된다."""


@router.post("/sessions/{session_id}/actions/confirm", response_model=ConfirmResponse)
async def confirm(
    session_id: str,
    request: Request,
    body: ConfirmRequest,
    background: BackgroundTasks,
) -> ConfirmResponse:
    """확인/거부를 먼저 기록하고, 확인이면 판정을 서사보다 먼저 제출한 뒤
    문장 조각이 나오는 족족 사건으로 쌓는다.

    **판정을 서사보다 먼저 제출하는 것이 흐름 구조로 보장된다** — 조건
    분기가 아니라 코드 순서다. 지연이 1초든 15초를 넘기든 판정 사건이
    기록에서 서사 사건보다 앞선 순번을 갖는 것이 뒤집힐 수 없다. 판정을
    재사용하는 경로(같은 declare_seq로 재시도)도 이 성질을 유지한다 — 재사용은
    이미 기록된 앞선 순번을 가리키는 것이므로 순서가 뒤집힐 수 없다.

    **신원 대조가 맨 앞이다(TRUST-02, D-04).** declare()와 같은 이유·같은
    형식이다.

    **「굴림 실패」와 「서사 실패」가 응답에서 구분된다(TRUST-06).** 판정
    제출(`ResolveCheck`) 자체가 던지는 예외는 오류 상태 코드로 나가고
    응답에 `rolls`가 없다. 서사만 실패하면 200이고 `rolls`/`grade`/`target`이
    채워진 채 `narration_failed=True`가 함께 온다 — 이미 굴린 주사위 결과를
    버리지 않는다(D-08). 다시 시도를 누르면(같은 declare_seq) 캐시된 판정을
    재사용하고 서사만 다시 쓴다(D-09).
    """
    identity = read_identity(request, session_id)
    if identity is None or identity.character_id != body.character_id:
        print("경고: 신원 검증 실패 — confirm 거부", file=sys.stderr)
        raise HTTPException(status_code=403, detail="캐릭터를 다시 선택해 주세요")

    store = request.app.state.store
    registry = request.app.state.registry
    actor = registry.get_or_create(session_id)

    # 요청 자체의 유효성(캐릭터·룰북·수정자 구문)은 사건을 하나라도 기록하기
    # 전에 전부 확인한다. 이 검증들은 게임 상태가 아니라 요청 형식에 대한
    # 판단이라 실패해도 사건을 남기지 않아야 한다 — 그렇지 않으면 판정 없는
    # "확인됨" 사건이 로그에 영구히 남아, 이 도구가 보장해야 할 사건 기록의
    # 무결성(RIG-06)이 깨진다. 거부(`confirmed=False`)는 이 검증이 필요 없다.
    modifiers: tuple[Modifier, ...] = ()
    character = None
    rulebook = None
    if body.confirmed:
        try:
            modifiers = tuple(_parse_modifier(raw) for raw in body.modifiers)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        character = get_character(body.character_id)
        if character is None:
            raise HTTPException(status_code=400, detail="그런 캐릭터가 없다")

        try:
            rulebook = get_rulebook(body.rulebook_id)
        except UnknownRulebook as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    # D-10/D-11 — 같은 선언에 대한 재확인은 `AlreadyConfirmed`(CommandRejected의
    # 하위 클래스)로 액터가 단락시킨다. **하위 클래스를 먼저 잡는다** — 순서가
    # 뒤집히면 아래 일반 `except CommandRejected`가 먼저 걸려 영원히 안 잡힌다.
    # `prior`가 남으면 이 확인은 이미 기록된 확인·판정을 재사용한다는 뜻이다.
    prior_confirm = None
    try:
        confirm_seq = await actor.submit(
            ConfirmAction(
                player_id=body.player_id,
                move=body.move,
                stat=body.stat,
                system_suggestion={
                    "move": body.suggestion_move,
                    "stat": body.suggestion_stat,
                },
                player_confirmed=body.confirmed,
                caused_by_seq=body.declare_seq,
                character_id=identity.character_id,
            )
        )
    except AlreadyConfirmed as exc:
        prior_confirm = exc.prior
        confirm_seq = prior_confirm.confirm_seq
    except CommandRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SequenceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if not body.confirmed:
        # 되돌리기 전용 화면을 만들지 않는다 — `ConfirmAction` 자체는 이미
        # 제출했으니 「확인 사건은 있지만 판정 사건은 없다」가 곧 「거부됐다」의
        # 기록이다. 거부해도 move/stat 값을 비우지 않는 이유는 명령줄 흐름과
        # 같다(확인 사건에 그 칸이 필요하고, 판정은 여기서 걸러진다).
        return ConfirmResponse(confirmed=False, confirm_seq=confirm_seq)

    if prior_confirm is not None and prior_confirm.resolve_seq is not None:
        # D-09 — 판정을 재사용한다. 주사위는 이미 굴렀으니 `ResolveCheck`를
        # 다시 제출하지 않고 그 순번을 그대로 쓴다 — 아래 346줄대의 기존
        # 되읽기 경로(store.read_events)를 그대로 탄다.
        resolve_seq = prior_confirm.resolve_seq
    else:
        # `prior_confirm`이 있는데 `resolve_seq`가 없으면(확인은 됐는데 판정이
        # 아직 없는 상태 — 그 사이에 서버가 죽었을 수도, 동시에 들어온 다른
        # 확인 요청이 아직 판정을 제출하지 않았을 수도 있다) 평소대로
        # 제출한다. D-11/TEST-02 — 이 "재사용 판단" 자체가 확인↔판정 사이의
        # TOCTOU 창이다(동시에 들어온 두 요청이 둘 다 여기 도달할 수 있다).
        # `AlreadyResolved`가 액터 안에서 그 창을 최종적으로 닫는다 — 하위
        # 클래스이므로 일반 `CommandRejected`보다 먼저 잡는다.
        try:
            # ④ 판정 — 서사 호출은 아직 시작하지 않았다.
            resolve_seq = await actor.submit(
                ResolveCheck(
                    move=body.move,
                    modifiers=modifiers,
                    target=body.target,
                    rulebook_id=body.rulebook_id,
                    caused_by_seq=confirm_seq,
                    person_id=identity.browser_id,
                    character_id=identity.character_id,
                )
            )
        except AlreadyResolved as exc:
            resolve_seq = exc.resolve_seq
        except CommandRejected as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except SequenceConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    check_event = store.read_events(session_id, from_seq=resolve_seq)[0]
    check_summary = f"{body.move} 판정 결과 {check_event.grade} (목표 {check_event.target})"

    try:
        choices = load_config(request.app.state.agent_config_path)
        gm_choice = choices["master_gm"]
        gm_provider: Provider = request.app.state.provider_resolver(
            "master_gm", choices, os.environ
        )
    except (
        ConfigNotFound,
        InvalidAgentConfig,
        UnknownProvider,
        MissingApiKey,
        ProviderNotImplemented,
    ) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    ctx = build_turn_context(
        store,
        session_id,
        body.rulebook_id,
        character_stats=character.stats,
        character_names=_CHARACTER_NAMES,
    )

    # 상황판단·장면 신규 대상 판단·시계 신호 관문을 narrate() 호출 **전**에
    # 병렬로 부른다(09-RESEARCH.md Pitfall 3이 지목한 정확한 구간, ARCH-04).
    # `choices`를 재사용하고 `load_config`를 다시 부르지 않는다 —
    # `situation_judge`/`scene_entity_judge`/`clock_judge`가 설정 파일에
    # 없어도 `ROLE_FALLBACKS`가 이미 다른 역할의 선택을 물려줬다. 이 구간
    # 전체를 `try`로 감싸 실패 시 stderr 한 줄만 남기고 빈 판단으로 계속
    # 간다 — 판단 실패가 확인 요청을 막지 않는다(D-05, ARCH-05).
    situation_judge_choice = choices["situation_judge"]
    situation_provider: Provider = request.app.state.provider_resolver(
        "situation_judge", choices, os.environ
    )
    entity_judge_choice = choices["scene_entity_judge"]
    entity_provider: Provider = request.app.state.provider_resolver(
        "scene_entity_judge", choices, os.environ
    )
    clock_judge_choice = choices["clock_judge"]
    clock_provider: Provider = request.app.state.provider_resolver(
        "clock_judge", choices, os.environ
    )
    try:
        judgments = await gather_turn_judgments(
            situation_provider=situation_provider,
            situation_model=situation_judge_choice.model,
            entity_provider=entity_provider,
            entity_model=entity_judge_choice.model,
            clock_provider=clock_provider,
            clock_model=clock_judge_choice.model,
            ctx=ctx,
            check_summary=check_summary,
            rulebook_display_name=rulebook.display_name,
        )
    except Exception as exc:  # noqa: BLE001 - D-05, 판단 실패가 확인 요청을 막지 않는다
        print(
            f"경고: 상황판단/장면 신규 대상/시계 신호 판단이 실패했다 (seq {resolve_seq}) — {exc}",
            file=sys.stderr,
        )
        judgments = empty_turn_judgments()

    # 새 에이전트 호출 셋의 기록 — 성공·실패 어느 쪽에서도 항상 제출한다
    # (MEAS-02, `master_gm` 호출 기록과 같은 규율). 새 에이전트 호출이 계측에서
    # 빠지지 않는다.
    await actor.submit(
        RecordAiCall(
            agent_role="situation_judge",
            model=situation_judge_choice.model,
            provider=situation_judge_choice.provider,
            prompt_tokens=judgments.situation.ai.prompt_tokens,
            completion_tokens=judgments.situation.ai.completion_tokens,
            cached_prompt_tokens=judgments.situation.ai.cached_prompt_tokens,
            latency_ms=judgments.situation.ai.elapsed_ms,
            caused_by_seq=confirm_seq,
        )
    )
    await actor.submit(
        RecordAiCall(
            agent_role="scene_entity_judge",
            model=entity_judge_choice.model,
            provider=entity_judge_choice.provider,
            prompt_tokens=judgments.entity.ai.prompt_tokens,
            completion_tokens=judgments.entity.ai.completion_tokens,
            cached_prompt_tokens=judgments.entity.ai.cached_prompt_tokens,
            latency_ms=judgments.entity.ai.elapsed_ms,
            caused_by_seq=confirm_seq,
        )
    )
    await actor.submit(
        RecordAiCall(
            agent_role="clock_judge",
            model=clock_judge_choice.model,
            provider=clock_judge_choice.provider,
            prompt_tokens=judgments.clock.ai.prompt_tokens,
            completion_tokens=judgments.clock.ai.completion_tokens,
            cached_prompt_tokens=judgments.clock.ai.cached_prompt_tokens,
            latency_ms=judgments.clock.ai.elapsed_ms,
            caused_by_seq=confirm_seq,
        )
    )

    facts = build_narration_facts(ctx=ctx, check_summary=check_summary, judgments=judgments)

    # ⑤ 서사 — 판정 결과가 이미 기록된 뒤에야 시작한다.
    #
    # 예외 포착은 AI 스트림 자체(narrate() 생성/첫 조각/이후 조각 이어받기)만
    # 감싼다 — `actor.submit(AppendNarration(...))`는 이 밖에 둔다(WR-01과
    # 같은 이유). 이 호출이 던지는 예외는 이벤트 스키마·저장소 I/O 같은
    # 액터/저장소 계층의 결함이지 서사 실패가 아니므로, 아래 `narration_failed`
    # 200 응답으로 뭉뚱그리지 않고 그대로 500으로 올라가게 둔다(TRUST-06 —
    # 「굴림 실패」와 「서사 실패」가 응답에서 구분된다). `Exception`만 잡는다 —
    # `BaseException`은 잡지 않는다. **되감지 않는다** — 이미 나온 문장은 그
    # 자리에서 `AppendNarration`으로 제출한다.
    narration_start = time.monotonic()
    narration_error: Exception | None = None
    chunk_index = 0
    narration_texts: list[str] = []
    """이번 턴에 실제로 나간 서사 조각을 모아 둔다 — 배경 시계 조건 검사가
    서사가 끝난 뒤의 `narration_text`로 이걸 이어 붙여 받는다."""
    try:
        narration_iter = narrate(
            provider=gm_provider,
            model=gm_choice.model,
            facts=facts,
            rulebook_display_name=rulebook.display_name,
        )
        first_sentence = await asyncio.to_thread(next, narration_iter, _NO_SENTENCE)
    except Exception as exc:  # noqa: BLE001 - 서사 스트림 생성/첫 조각 실패만 여기서 잡는다(G-03-3)
        narration_error = exc
        first_sentence = _NO_SENTENCE

    if first_sentence is not _NO_SENTENCE:
        await actor.submit(  # 액터/저장소 결함은 여기서 그대로 터진다(WR-01)
            AppendNarration(
                text=first_sentence, chunk_index=chunk_index, caused_by_seq=resolve_seq
            )
        )
        narration_texts.append(first_sentence)
        chunk_index += 1
        while True:
            try:
                # 보초값을 쓴다 — `StopIteration`을 그대로 던지게 두면
                # `asyncio.to_thread`가 그 예외를 `Future`로 옮기는 과정에서
                # `RuntimeError`로 바뀐다(asyncio가 `StopIteration`이 `Future`를
                # 타고 넘는 것을 명시적으로 금지한다).
                sentence = await asyncio.to_thread(next, narration_iter, _NO_SENTENCE)
            except Exception as exc:  # noqa: BLE001 - 서사 스트림 이어받기 실패만 여기서 잡는다(G-03-3)
                narration_error = exc
                break
            if sentence is _NO_SENTENCE:
                break
            await actor.submit(  # 액터/저장소 결함은 여기서 그대로 터진다(WR-01)
                AppendNarration(text=sentence, chunk_index=chunk_index, caused_by_seq=resolve_seq)
            )
            narration_texts.append(sentence)
            chunk_index += 1

    # ⑥ 두 번째 AI 호출 기록 — 성공·실패 어느 쪽에서도 항상 제출한다. 실패한
    # 호출도 걸린 시간이 남아야 MEAS-02의 두 번째 지점에서 실패한 턴이
    # 통째로 빠지지 않는다.
    elapsed_ms = int((time.monotonic() - narration_start) * 1000)
    gm_result = _last_result_or_failure_envelope(gm_provider, elapsed_ms=elapsed_ms)
    await actor.submit(
        RecordAiCall(
            agent_role="master_gm",
            model=gm_choice.model,
            provider=gm_choice.provider,
            prompt_tokens=gm_result.prompt_tokens,
            completion_tokens=gm_result.completion_tokens,
            cached_prompt_tokens=gm_result.cached_prompt_tokens,
            latency_ms=gm_result.elapsed_ms,
            caused_by_seq=confirm_seq,
        )
    )

    if narration_error is not None or not gm_result.ok:
        # D-08/TRUST-06 — 서사만 실패했다. 이미 기록된 판정 결과를 버리지
        # 않는다: 200을 돌려주고 `rolls`/`grade`/`target`은 되읽은 판정
        # 사건에서 그대로 채운 채 `narration_failed=True`로 실패를 알린다.
        # 액터·저장소 결함(이벤트 스키마·I/O)은 이 분기가 아니라 그 위 호출부에서
        # 그대로 500으로 올라간다(다른 원인이므로 다른 상태 코드, 502 분기가
        # 아니다) — 「굴림 실패」와 「서사 실패」의 구분이 여기서 코드 구조로
        # 남는다.
        return ConfirmResponse(
            confirmed=True,
            confirm_seq=confirm_seq,
            resolve_seq=resolve_seq,
            rolls=list(check_event.rolls),
            grade=check_event.grade,
            target=check_event.target,
            narration_chunk_count=chunk_index,
            narration_failed=True,
        )

    # 시계 조건 검사 배경 등록 — 관문 신호가 참일 때만 건다(ARCH-03/D-01).
    # 깊은 판단용 제공자 호출은 신호가 거짓이면 아예 일어나지 않는다 — 값싼
    # 관문이 값비싼 판단을 거른다는 DP-01의 구조가 여기서 그대로 지켜진다.
    if judgments.clock.should_check:
        background.add_task(
            run_clock_condition_check,
            actor=actor,
            provider=clock_provider,
            model=clock_judge_choice.model,
            judge_ctx=build_clock_judge_context(ctx, check_summary),
            rulebook_display_name=rulebook.display_name,
            narration_text="\n".join(narration_texts),
            resolve_seq=resolve_seq,
            clock_id=ctx.clock_state.clock_id,
            clock_segment_count=CLOCK_SEGMENT_COUNT,
        )

    # ⑦ 장면 삽화 — **성공한 턴에만, 응답을 보낸 뒤에.** 위 서사 실패 분기가
    # 먼저 반환하는 것이 의도다: 서사가 실패한 턴에 그림만 남으면 화면에 서사
    # 없는 삽화가 떠서 무슨 일이 있었는지 더 알기 어려워진다.
    imagery_config: ImageryConfig = request.app.state.imagery_config
    if imagery_config.enabled:
        background.add_task(
            _illustrate_scene,
            actor=actor,
            renderer=request.app.state.renderer,
            config=imagery_config,
            session_id=session_id,
            resolve_seq=resolve_seq,
            move=body.move,
            grade=check_event.grade,
            clock_segment=ctx.clock_state.segment_index,
        )

    return ConfirmResponse(
        confirmed=True,
        confirm_seq=confirm_seq,
        resolve_seq=resolve_seq,
        rolls=list(check_event.rolls),
        grade=check_event.grade,
        target=check_event.target,
        narration_chunk_count=chunk_index,
    )


async def _illustrate_scene(
    *,
    actor: SessionActor,
    renderer: Renderer,
    config: ImageryConfig,
    session_id: str,
    resolve_seq: int,
    move: str,
    grade: str,
    clock_segment: int,
) -> None:
    """판정 하나에 딸린 삽화를 만들어 파일로 쓰고 사건으로 남긴다.

    **응답이 나간 뒤에 돈다**(FastAPI `BackgroundTasks`). 그림이 늦어도 턴은
    이미 끝났고, 브라우저는 폴링으로 나중에 집어 간다.

    **어떤 실패도 위로 던지지 않는다.** 이 함수는 응답 뒤에 돌기 때문에 여기서
    던진 예외는 사용자에게 전달될 길이 없고, 대신 요청 처리 자체를 오류로
    기록시켜 로그를 어지럽힌다. 그림은 있으면 좋은 것이므로 경고 한 줄을
    남기고 조용히 끝낸다 — 그림이 없는 턴은 삽화 사건이 없는 턴으로 남는다.
    """
    prompt = scene_prompt(
        move=move,
        grade=grade,
        clock_segment=clock_segment,
        style=config.style,
        setting=WELL_SCENARIO_SETTING,
    )
    relative_path = scene_relative_path(session_id, resolve_seq)
    try:
        # 그림 생성과 파일 쓰기를 한 번에 작업 스레드로 내보낸다 — 둘 다 막는
        # 일이고, 여기서 하면 폴링하던 브라우저 넷이 그 시간 동안 멈춘다.
        image = await asyncio.to_thread(
            _render_and_write,
            renderer=renderer,
            config=config,
            prompt=prompt,
            session_id=session_id,
            resolve_seq=resolve_seq,
            relative_path=relative_path,
        )
    except RendererUnavailable as exc:
        print(f"경고: 삽화를 만들지 못했다 (seq {resolve_seq}) — {exc}", file=sys.stderr)
        return
    except Exception as exc:  # noqa: BLE001 - 배경 작업의 실패가 요청 처리를 오염시키지 않는다
        print(f"경고: 삽화 중 예상 못한 실패 (seq {resolve_seq}) — {exc}", file=sys.stderr)
        return

    try:
        # 사건 제출은 이벤트 루프로 돌아와서 한다(sqlite3 스레드 제약).
        await actor.submit(
            RecordSceneIllustration(
                image_path=media_url(relative_path),
                prompt=image.prompt,
                style=image.style,
                seed=image.seed,
                steps=image.steps,
                size=image.size,
                latency_ms=image.latency_ms,
                caused_by_seq=resolve_seq,
            )
        )
    except Exception as exc:  # noqa: BLE001 - 위와 같은 이유
        print(f"경고: 삽화 사건을 남기지 못했다 (seq {resolve_seq}) — {exc}", file=sys.stderr)


def _render_and_write(
    *,
    renderer: Renderer,
    config: ImageryConfig,
    prompt: str,
    session_id: str,
    resolve_seq: int,
    relative_path: str,
) -> RenderedImage:
    """작업 스레드에서 도는 부분 — 그림을 만들고 파일로 쓴다.

    **여기서 `actor`나 저장소를 만지지 않는다**(모듈 도크스트링의 sqlite3 스레드
    제약). 이 함수가 아는 것은 렌더러와 파일 경로뿐이다.
    """
    image = renderer.render(
        prompt,
        style=config.style,
        seed=seed_for(session_id, resolve_seq),
    )
    media_file_path(config.media_dir, relative_path).write_bytes(image.png)
    return image
