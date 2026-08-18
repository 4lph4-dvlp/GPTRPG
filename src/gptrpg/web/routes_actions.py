"""선언·확인·진행 세 경로 — 브라우저에서 한 턴이 끝까지 돈다.

`POST /sessions/{session_id}/actions/declare`: 문장 하나 -> 무브 후보.
`POST /sessions/{session_id}/actions/confirm`: 확인/거부 -> 판정 -> 서사.
`POST /sessions/{session_id}/proceed`: 굴릴 필요 없는 행동(`tier ==
"no_check"`) -> 판정 없이 서사(D-10 ②갈래, 11-06). `confirm()`의 판정
이후 구간을 거울처럼 따라가되 `ConfirmAction`/`ResolveCheck`를 제출하지
않는다.

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
from dataclasses import replace

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from gptrpg.agents.action_classifier import classify
from gptrpg.agents.config import ConfigNotFound, InvalidAgentConfig, load_config
from gptrpg.agents.context import ItemUseClaim, NO_CHECK_SUMMARY
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.master_gm import narrate
from gptrpg.agents.prompt_assembly import actor_stats
from gptrpg.agents.providers import MissingApiKey, ProviderNotImplemented, UnknownProvider
from gptrpg.agents.providers.base import Provider
from gptrpg.event_log.store import EventStore, SequenceConflict
from gptrpg.rulebooks import UnknownRulebook, get_rulebook
from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID
from gptrpg.rulebooks.moves import get_moves
from gptrpg.rules_core.entities import Entity
from gptrpg.rules_core.resource_change import (
    InvalidResourceChange,
    ResourceChangeDecl,
    ResourceOp,
    resolve_character_stats,
    roll_amount,
)
from gptrpg.rules_core.rulebook import (
    AxisNotOnCharacter,
    GradeBand,
    InvalidOutcomeList,
    OutcomeCategory,
    OutcomeList,
    UnknownDifficultyLevel,
    UnknownGradeName,
    UnknownOutcomeCategory,
    character_axis_names,
    eligible_categories,
    ordered_categories,
    require_axes_on_character,
    require_band,
    require_difficulty,
    validate_outcome_list,
)
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
    AlreadyChanged,
    AlreadyConfirmed,
    AlreadyResolved,
    AppendNarration,
    CommandRejected,
    ConfirmAction,
    DeclareAction,
    ProceedEligible,
    RecordActionClassification,
    RecordAiCall,
    RecordResourceChange,
    RecordSafetyFlag,
    RecordSceneIllustration,
    ResolveCheck,
    VerifyProceedEligibility,
)
from gptrpg.session_actor.actor import SessionActor
from gptrpg.session_actor.live_roller import LiveRoller
from gptrpg.turn.clock_condition import build_clock_judge_context, run_clock_condition_check
from gptrpg.turn.context import CLOCK_SEGMENT_COUNT, build_turn_context
from gptrpg.turn.judgments import build_narration_facts, empty_turn_judgments, gather_turn_judgments
from gptrpg.web.characters_data import get_character, list_characters
from gptrpg.web.cookie_auth import read_identity
from gptrpg.web.media import media_file_path, media_url, scene_relative_path
from gptrpg.session_actor.projection import rebuild_state_from_events

_CHARACTER_NAMES: dict[str, str] = {c.character_id: c.display_name for c in list_characters()}
"""character_id -> display_name, `build_turn_context`의 `character_names`로
그대로 넘긴다 — 최근 대화에서 "플레이어: "만 찍히면 네 명의 발화가 전부
한 사람 것처럼 뭉뚱그려진다(2026-08-04 실전에서 발견, T-05-16급)."""

_NO_CHECK_GRADE_BAND = GradeBand(
    name="__no_check__", counts_as_failure=False, succeeded=True, costs=False
)
"""`proceed()`가 `gather_turn_judgments`에 넘기는 자리표시자(12-06) — 이
경로에는 애초에 판정이 없으므로(D-10 ②갈래, RULE-15) 태울 결과 목록도
없다. `costs=False`이므로 `pick_outcome`이 이 밴드를 받아도 모델을 아예
안 부른다(0회 호출) — `Rulebook.grade_bands`에 실제로 등록된 이름이 아니라
이 파일 안에서만 쓰는 값이다."""

router = APIRouter()


def _current_party_state(store: EventStore, session_id: str) -> tuple[Entity, ...]:
    """세션에 있는 캐릭터 **전원**을 접은 「지금 값」으로 만든 개체 튜플을
    조립한다(12-05, D-17/D-18/RULE-06) — `build_turn_context`의
    `party_state`로 그대로 넘긴다.

    `list_characters()`가 돌려주는 선언 순서 그대로 각 식별자에
    `get_character()`를 부르고, 사건에서 접은 `GameState.
    character_resource_ops`를 `resolve_character_stats`에 넘겨 새 `Entity`를
    만든다. **선언 순서를 다시 정렬하지 않는다**(`list_characters()`가 세운
    관례).

    **`web/routes_characters.py`의 `_current_stats`와 같은 결합 규칙을
    쓴다** — 두 경로가 갈리면 시트와 프롬프트가 서로 다른 값을 보여준다.
    그 함수를 여기서 직접 import하지 않는다 — `routes_characters.py`가
    이미 이 모듈(`MAX_ID_LEN`)을 import하므로, 반대 방향으로 다시 import하면
    순환 import가 생긴다. 그래서 같은 결합 규칙(시작값 + 축별 연산 이력 →
    `resolve_character_stats`)을 이 함수가 독립적으로 반복한다 — 두 자리가
    갈리지 않는다는 것은 이 도크스트링과 `_current_stats`의 도크스트링이
    서로를 지목하는 것으로 못박는다.

    각 파티 구성원의 `entity_id`는 **짧은 캐릭터 식별자**(`"bram"` 등)로
    다시 쓴다 — `characters_data.PLAYER_CHARACTERS`가 쓰는 긴 형태
    (`"player.bram"`)가 아니다. `identity.character_id`도 짧은 형태이고,
    `agents.prompt_assembly.actor_stats`가 `party_state`에서 `entity_id ==
    actor_character_id`로 행위자를 찾으므로 두 값의 식별자 공간이 일치해야
    한다.
    """
    events = store.read_events(session_id)
    state = rebuild_state_from_events(session_id, events)
    party: list[Entity] = []
    for summary in list_characters():
        entity = get_character(summary.character_id)
        if entity is None:
            continue
        ops: dict[str, tuple[ResourceOp, ...]] = {}
        for (op_character_id, axis_name), axis_ops in state.character_resource_ops.items():
            if op_character_id != summary.character_id:
                continue
            ops[axis_name] = axis_ops
        current_stats = resolve_character_stats(entity.stats, ops)
        party.append(replace(entity, entity_id=summary.character_id, stats=current_stats))
    return tuple(party)

MAX_RAW_TEXT_LEN = 2000
"""플레이어가 친 자유 문장의 상한 — 이 자리가 처음으로 신뢰할 수 없는 HTTP
본문이 된다(Phase 3까지는 신뢰되는 명령줄 인자였다). 상한이 없으면 그대로
AI 프롬프트에 흘러 들어간다(T-04-07)."""

MAX_ID_LEN = 64
"""`player_id`/`character_id`/`move`/`stat`/`rulebook_id` 같은 식별자 문자열의
상한 — `DeclareRequest.rulebook_id`·`ConfirmRequest.rulebook_id`도 이 상수를
재사용한다(08-04, QUAL-04). 새 상수를 만들지 않는다 — 이미 같은 성격(식별자
문자열)의 값이 같은 상한을 쓰는 것이 자연스럽다."""

MAX_DIFFICULTY_LEN = 32
"""`ConfirmRequest.difficulty`의 길이 상한(12-01, D-02). `MAX_ID_LEN`(64)
보다 좁게 잡는다 — 난이도 이름은 룰북이 선언한 닫힌 목록에서 고르는
값이라 실제로 훨씬 짧다(예: `"hard"`). `require_difficulty`가 목록에
없는 이름을 어차피 거절하지만, 상한은 그 검증 이전에 요청 본문 크기
자체를 제한한다."""

MAX_PICKED_CATEGORIES = 10
"""`ConfirmResourceChangeRequest.category_ids` 길이 상한(12-06, T-12-30).
`Rulebook.outcome_list.max_picks`가 룰북마다 이미 실제 상한을 두지만
(`ordered_categories`가 그 값을 안 보고도 같은 식별자 중복은 걸러낸다),
요청 본문 자체의 크기를 룰북 조회 이전에 제한하는 것이 이 상수의 목적이다
— 이 저장소가 실제로 선언한 어떤 결과 목록보다도 넉넉하다."""

MAX_DISCRETIONARY_AMOUNT = 20
"""재량 판정 제안(`DiscretionaryProposal.amount`)의 절댓값 상한(RULE-10,
T-12-28). **룰북 규칙이 아니라 입력 실수 방어다** — `resolution_d100.
MAX_BONUS_DICE_MAGNITUDE`(20)와 `resource_change.MAX_DICE_COUNT`(20)가 이미
세운 것과 같은 방어선의 값을 그대로 재사용한다. 이 저장소가 선언한 자원
축의 실제 값 범위(예: 체력 20)를 넘는 재량 제안은 사람이 실수로 눌렀을 때
자원을 통째로 날릴 수 있다 — 「룰북이 정할 일을 플랫폼이 정하는 것
아닌가」라는 반론이 가능한 자리이지만, 이 값이 없으면 확인 화면 한 번의
실수가 캐릭터를 통째로 무력화할 수 있다."""

_NO_SENTENCE = object()
"""narrate()의 첫 조각을 기다릴 때 쓰는 보초값 — `cli/turn_flow.py`의 같은
이름 상수와 같은 이유다(빈 문자열과의 신원 비교로 "아직 하나도 안 나왔다"를
안전하게 구분한다). 이어지는 조각을 꺼낼 때도 이 보초값을 그대로 쓴다 —
`next(narration_iter)`가 `StopIteration`을 던지게 두면 `asyncio.to_thread`가
그 예외를 `Future`로 옮기는 과정에서 `RuntimeError`로 바뀐다(파이썬 asyncio가
`StopIteration`이 `Future`를 타고 넘는 것을 명시적으로 금지한다) — 매번
`next(iter, _NO_SENTENCE)` 형태로 불러 예외 대신 보초값으로 "끝났다"를
알린다."""


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


async def _submit_narration_chunk(
    *,
    actor: SessionActor,
    chunk,  # NarrationChunk — 순환 import를 피하려 타입만 값으로 쓴다(agents는 이 모듈을 모른다)
    chunk_index: int,
    resolve_seq: int,
    narration_texts: list[str],
) -> None:
    """`narrate()`가 낸 `NarrationChunk` 하나를 사건으로 옮긴다(10-01, Task 2 ⑦).

    `chunk.text`는 지금처럼 `AppendNarration`으로 제출한다 — 걸린 조각이면
    `chunk.text`가 이미 `NOTICE_FILTERED`다(`master_gm._judge_sentence`가
    바꿔치기했다). `disposition != "clean"`이면 이어서 `RecordSafetyFlag`를
    같은 `caused_by_seq`로 제출한다. **`disposition == "blocked"`인 조각은
    `narration_texts`에 넣지 않는다** — 그 목록은 배경 시계 조건 검사가
    "이번 턴 서사"로 받는 값이라, 시스템 안내문이 이야기 텍스트로 섞이면
    안 된다.
    """
    await actor.submit(
        AppendNarration(text=chunk.text, chunk_index=chunk_index, caused_by_seq=resolve_seq)
    )
    if chunk.disposition != "clean":
        await actor.submit(
            RecordSafetyFlag(
                source="narration",
                reason=chunk.reason,
                disposition=chunk.disposition,
                matched_len=chunk.matched_len,
                subject_len=chunk.subject_len,
                chunk_index=chunk_index,
                caused_by_seq=resolve_seq,
            )
        )
    if chunk.disposition != "blocked":
        narration_texts.append(chunk.text)


class MoveCandidateView(BaseModel):
    move: str
    stat: str


class DeclareRequest(BaseModel):
    player_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    character_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    raw_text: str = Field(min_length=1, max_length=MAX_RAW_TEXT_LEN)
    rulebook_id: str = Field(default=DUNGEONWORLD_LIKE_ID, max_length=MAX_ID_LEN)


class ItemUseView(BaseModel):
    """분류기가 낸 「이 행동이 소지품 중 무엇을 쓰는가」 판단(RULE-16,
    12-06 Task 3) — `agents.context.ItemUseClaim`을 그대로 옮긴다."""

    kind: str
    item: str | None = None


class RetroDeclarationView(BaseModel):
    """소지품에 없는 것을 쓰겠다고 했을 때(`item_use.kind == "not_held"`)
    이 룰북이 소급 선언을 허용하는지와, 허용하면 그 비용 축·동작(D-16) —
    축과 동작은 룰북이 잠그고 양만 사람이 정한다. `available=False`
    (기본값)면 이 턴에는 소급 선언 여지가 없다(소지품을 쓴다는 판단이
    아예 없었거나, 룰북이 소급 선언을 허용하지 않는다)."""

    available: bool = False
    axis: str | None = None
    operation: str | None = None


class DeclareResponse(BaseModel):
    declare_seq: int
    tier: str
    """`Proposal.tier`(`action_classifier.ProposalTier`)를 그대로 통과시킨
    네 값 중 하나(D-11, 11-05) — `"single"`(후보 하나), `"several"`(후보
    둘 이상), `"no_check"`(모델이 판정 불필요를 명시적으로 표시), `"unclear"`
    (후보도 신호도 없거나, 목록 밖 이름 흡수, 또는 제공자 호출 실패). 이
    타입을 `Literal`로 좁히지 않고 `str`로 남긴 이유: `ProposalTier`가
    바뀌어도 이 파일을 안 고치기 위해서가 아니라, 값 자체가 `Proposal.tier`
    한 곳에서만 정의돼야 한다는 규율을 지키기 위해서다."""
    candidates: list[MoveCandidateView]
    item_use: ItemUseView = ItemUseView(kind="none")
    retro_declaration: RetroDeclarationView = RetroDeclarationView()


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

    **`UnknownMove`는 여기서 더 이상 예외로 나타나지 않는다(SAFE-07, D-12,
    10-05).** `classify()`가 함수 경계에서 이미 흡수했다 — `proposal.tier`가
    `"unclear"`이고 `candidates`가 빈 목록인 응답이 그대로 돌아온다(옛
    값을 11-05가 개명했다 — `DeclareResponse.tier` 도크스트링 참조). 계약
    위반이었다는 사실은 `proposal.unknown_move`에 남고, 아래에서
    `RecordSafetyFlag(source="classifier")`로 운영자 기록에 남긴다 — 새
    응답 칸도 새 상태 코드도 만들지 않는다.
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

        # **파티 전원의 접은 지금 값이 여기서 처음으로 AI 문맥에 들어간다
        # (12-05, D-17/D-18).** 분류기(`classify()`)는 `actor_stats(ctx)`로
        # 파티에서 행위자 한 명만 뽑아 본다 — 남의 상태는 안 받는다(D-17).
        # `build_turn_context`의 `character_stats` 단일 인자가 12-05에서
        # `party_state`/`actor_character_id` 두 인자로 갈렸으므로, 이
        # 호출부도 함께 갱신해야 한다 — 안 그러면 분류기가 이 캐릭터가
        # 아니라 예시 개체(`EXAMPLE_SINGLE_STAT_FOE`)를 보게 된다
        # (`test_prompt_carries_the_acting_character_real_stat_names`가
        # 잡는 회귀).
        ctx = build_turn_context(
            store,
            session_id,
            body.rulebook_id,
            party_state=_current_party_state(store, session_id),
            actor_character_id=identity.character_id,
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
            resource_axes=rulebook.resource_axes,
        )
    except (CommandRejected, UnknownRulebook) as exc:
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
    # T-11-29(11-06 rework) — 분류 결정을 사건에 durable하게 남긴다.
    # `proceed()`의 서버 쪽 안전 검사(`VerifyProceedEligibility`)가 이 표를
    # 서버 재시작 뒤에도 다시 접어 읽는다 — 클라이언트가 보낸 `declare_seq`
    # 하나만 믿고 판정을 건너뛰게 두지 않는다.
    await actor.submit(
        RecordActionClassification(
            no_check=proposal.tier == "no_check",
            caused_by_seq=declare_seq,
        )
    )
    if proposal.unknown_move is not None:
        # SAFE-07/D-12, 10-05 — 계약 위반이었다는 사실을 운영자 기록에
        # 남긴다. 이름 문자열 자체는 사건에 안 들어간다 — 길이 숫자만
        # 남는다(T-10-03, 10-01이 세운 규율).
        await actor.submit(
            RecordSafetyFlag(
                source="classifier",
                reason="unknown_move",
                disposition="blocked",
                subject_len=len(proposal.unknown_move),
                caused_by_seq=declare_seq,
            )
        )

    # 소지품 판단(RULE-16, 12-06 Task 3) — 코드가 다시 대조한다. `kind=
    # "held"`이면 그 문자열이 실제로 슬롯에 있는지 파이썬 `==`로 다시
    # 확인한다(`_prepare_confirm`의 이중 소유권 검사와 같은 신중함).
    # `actor_stats(ctx)`가 분류기가 실제로 본 것과 같은 값이다(`ctx`는
    # `party_state`에서 접은 지금 값을 담고 있다) — `character.stats`
    # (시작값)를 다시 쓰지 않는다.
    item_use = proposal.item_use
    if item_use.kind == "held":
        held_names: set[str] = set()
        for stat in actor_stats(ctx):
            if stat.form == "named_slots":
                held_names.update(v for v in (stat.slot_values or ()) if v is not None)
        if item_use.item not in held_names:
            print(
                "경고: 분류기가 「갖고 있다」고 한 물건이 재확인에서 실제 슬롯에 없다 "
                "— 소급 판단으로 낮춘다",
                file=sys.stderr,
            )
            item_use = ItemUseClaim(item=None, kind="not_held")

    retro_view = RetroDeclarationView()
    if item_use.kind == "not_held" and rulebook.retro_declaration.allowed:
        # RULE-16, D-16 — 축과 동작은 룰북이 잠그고 양만 그때그때
        # 정해진다. 실제 양은 `POST .../confirm-resource-change`의
        # `retro_declaration_amount`가 지나며(12-06 Task 2가 놓은 재량
        # 확인 경로), 새 형식을 만들지 않는다.
        retro_view = RetroDeclarationView(
            available=True,
            axis=rulebook.retro_declaration.cost_axis,
            operation=rulebook.retro_declaration.operation,
        )

    return DeclareResponse(
        declare_seq=declare_seq,
        item_use=ItemUseView(kind=item_use.kind, item=item_use.item),
        retro_declaration=retro_view,
        tier=proposal.tier,
        candidates=[MoveCandidateView(move=c.move, stat=c.stat) for c in proposal.candidates],
    )


class ConfirmRequest(BaseModel):
    """D-02: 바깥(브라우저)에서 판정 계산에 실을 수 있는 자유 숫자 칸이
    없다. `target`/`modifiers`는 더 이상 이 모델에 없다 — 목표값은
    서버가 정한다(`stat_usage`가 `use_as_target`인 룰북은
    `build_stat_check_input`이 돌려준 값을, 아니면 `grading.DEFAULT_TARGET`을
    쓴다). 받는 것은 `difficulty` 하나뿐이고, 그마저도 룰북이 선언한 닫힌
    이름 목록에서만 찾는다(`require_difficulty`) — 목록 밖 이름은 사건을
    남기기 전에 400으로 거절된다. `extra="forbid"`가 오타·조작으로 생긴
    여분 칸(예: 예전 `target`/`modifiers`)을 거절한다.
    """

    model_config = ConfigDict(extra="forbid")

    player_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    move: str = Field(min_length=1, max_length=MAX_ID_LEN)
    stat: str = Field(min_length=1, max_length=MAX_ID_LEN)
    suggestion_move: str = Field(min_length=1, max_length=MAX_ID_LEN)
    suggestion_stat: str = Field(min_length=1, max_length=MAX_ID_LEN)
    confirmed: bool
    declare_seq: int = Field(ge=0)
    rulebook_id: str = Field(default=DUNGEONWORLD_LIKE_ID, max_length=MAX_ID_LEN)
    character_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    difficulty: str | None = Field(default=None, max_length=MAX_DIFFICULTY_LEN)
    """룰북이 선언한 닫힌 이름 목록에서 고른 난이도(D-02, 12-01). `None`이면
    난이도 수정치를 안 싣는다 — 던전월드류처럼 난이도 개념이 없는 룰북은
    이 칸을 안 보낸다."""


class ModifierView(BaseModel):
    type: str
    value: int
    source: str


class ResourceChangeView(BaseModel):
    axis: str
    operation: str
    amount: int
    rolls: list[int] = []
    before: int | None = None
    after: int | None = None


class PendingResourceChangeView(BaseModel):
    """이번 판정으로 「변할 예정」인 자원 변화 하나 — 아직 적용되지 않았다
    (12-06, D-09). `amount_decl`은 룰북 선언 그대로다(`int` 고정값 또는
    `str` 주사위식) — 주사위 양은 아직 안 굴린다(확인 전에 굴리면 「확인
    안 했는데 눈이 소비되는」 일이 생긴다). 실제로 굴린 값·눈은
    `POST .../confirm-resource-change`의 응답(`ResourceChangeView`)에만
    실린다."""

    category_id: str
    axis: str
    operation: str
    amount_decl: int | str
    source: str


class DiscretionaryProposalView(BaseModel):
    """룰북에 결과 목록 선언이 없을 때(RULE-13 empty) 재량 판정이 열려
    있음을 알리는 자리(RULE-10). `axes`는 이 룰북이 선언한 자원 축 이름
    중 재량 제안이 가리킬 수 있는 것들이다 — 축은 룰북이 잠그고, 실제
    제안(축·동작·양)은 `POST .../confirm-resource-change`의
    `discretionary` 칸으로 보낸다. `available=False`(기본값)면 이 턴에는
    재량 판정 여지가 없다는 뜻이다."""

    available: bool = False
    axes: list[str] = []


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
    modifiers: list[ModifierView] = []
    """이 판정에 실제로 실린 수정치 전부 — `check_event.modifiers`를 그대로
    옮긴다(D-04 검산 근거). 능력치·난이도 수정치가 여기 실린 채로 화면에
    닿는다(12-01)."""
    total: int | None = None
    """판정 합계 — `CheckResolved`가 이 값을 따로 저장하지 않으므로(눈+수정치로
    재계산해야 하는데 d100은 십/일의 자리 채택 규칙이 있어 웹 계층에서
    다시 계산하면 `rules_core`의 계산을 중복 구현하게 된다) 이번 계획은
    항상 `None`이다 — 후속 계획이 `CheckResolved`에 칸을 늘리면 채운다."""
    pending_resource_changes: list[PendingResourceChangeView] = []
    """AI가 룰북의 닫힌 결과 목록에서 고른 항목이 가리키는 자원 변화 —
    **아직 사건이 안 쌓였다**(12-06, D-09). 고른 항목의 변화 목록이 비어
    있으면(`NO_CHANGE_CATEGORY_ID`만 골랐거나 목록 자체가 없거나 대가가
    안 붙는 등급) 이 칸은 빈 목록이고, 화면은 확인을 안 띄운다 — 판정마다
    확인 창이 뜨는 것을 이 한 줄이 막는다. 12-01~12-05가 `confirm()` 안에서
    곧바로 적용하던 「탐색적 한 줄기」는 이 계획이 대체했다 — 실제 적용은
    `POST .../confirm-resource-change`로 사람이 확인한 뒤에만 일어난다."""
    discretionary: DiscretionaryProposalView = DiscretionaryProposalView()
    """룰북에 결과 목록이 없어도(RULE-13 empty) 재량 판정으로 자원이 변할
    수 있다는 신호(RULE-10). 결과 목록이 있는 룰북에서는 항상
    `available=False`다."""


def _pending_resource_changes(
    *, rulebook, grade_band, outcome, resolve_seq: int, actor_axes: frozenset[str]
) -> tuple[list[PendingResourceChangeView], DiscretionaryProposalView]:
    """AI가 고른 카테고리(`judgments.outcome`)를 코드가 다시 대조해
    「변할 예정」 목록을 만든다(RULE-13, D-11, T-12-27).

    `ordered_categories`가 룰북 선언 순서로 다시 정렬하며 목록 밖 식별자·
    중복 선택을 다시 검사한다 — `pick_outcome`이 이미 파싱 단계에서 한
    검사를 소비하는 쪽에서 한 번 더 하는 것이다(`_prepare_confirm`의
    이중 소유권 검사와 같은 신중함). 여기서 걸리면(정상 경로라면 절대
    일어나지 않는다 — `gather_turn_judgments`를 감싸는 `try`가 AI 계약
    위반을 이미 흡수했다) 빈 목록으로 조용히 떨어진다 — 이미 굴린
    주사위를 버리지 않는다는 원칙이 여기서도 그대로다.

    RULE-10(재량 판정) — 이 룰북이 결과 목록 자체를 선언하지 않았고
    (`RULE-13 empty`) 이 등급에 대가가 붙으면(`grade_band.costs`), 응답에
    재량 판정 신호를 싣는다. 실제 축·동작·양 제안은 이 함수가 만들지
    않는다 — `outcome_picker`는 결과 목록이 비어 있으면 애초에 모델을
    안 부른다(Task 1의 커밋된 계약, 0회 호출). 사람이 `discretionary.axes`
    (이 룰북이 선언한 축 이름)에서 골라 `confirm-resource-change`의
    `discretionary` 칸으로 직접 제안하면, 그 라우트가 축·형태·동작·상한
    셋을 서버에서 다시 검사한다.
    """
    pending: list[PendingResourceChangeView] = []
    if outcome.category_ids:
        try:
            picked_categories = ordered_categories(rulebook.outcome_list, outcome.category_ids)
        except (UnknownOutcomeCategory, InvalidOutcomeList) as exc:
            print(
                f"경고: outcome_picker가 닫힌 목록과 어긋난 결과를 냈다 (seq {resolve_seq}) — {exc}",
                file=sys.stderr,
            )
            picked_categories = ()
        for category in picked_categories:
            for change in category.changes:
                pending.append(
                    PendingResourceChangeView(
                        category_id=category.category_id,
                        axis=change.axis,
                        operation=change.operation,
                        amount_decl=change.amount,
                        source="outcome_list",
                    )
                )

    discretionary = DiscretionaryProposalView()
    if not pending and not rulebook.outcome_list.categories and grade_band.costs:
        discretionary = DiscretionaryProposalView(
            available=True,
            # 룰북이 선언한 축이 아니라 **이 행위자가 실제로 가진** 축만
            # 제안 대상이다 — 결과 목록 쪽 걸름(`eligible_categories`)과
            # 같은 이유다. 룰북 축을 그대로 내보내면 사람이 나리에게 없는
            # 방어구를 골라 제안할 수 있고, 그 제안은 확인 관문
            # (`require_axes_on_character`)에서 거절되어 막다른 길이 된다.
            axes=[
                axis.name
                for axis in rulebook.resource_axes
                if axis.form != "none" and axis.name in actor_axes
            ],
        )
    return pending, discretionary


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

    # 요청 자체의 유효성(캐릭터·룰북·난이도 이름)은 사건을 하나라도 기록하기
    # 전에 전부 확인한다. 이 검증들은 게임 상태가 아니라 요청 형식에 대한
    # 판단이라 실패해도 사건을 남기지 않아야 한다 — 그렇지 않으면 판정 없는
    # "확인됨" 사건이 로그에 영구히 남아, 이 도구가 보장해야 할 사건 기록의
    # 무결성(RIG-06)이 깨진다. 거부(`confirmed=False`)는 이 검증이 필요 없다.
    # D-02 — 자유 숫자 수정치 구문 검증은 더 이상 없다: `ConfirmRequest`에
    # `modifiers`/`target` 칸 자체가 없다. `difficulty`가 유일한 통로이고,
    # 룰북 선언 대조를 **여기서 미리** 한다 — `ResolveCheck` 제출 시점에
    # `_prepare_resolve_check`가 다시 `require_difficulty`로 확인하지만
    # (방어선 이중화, 저장소 우회 경로까지 막는다), 그 시점은 이미
    # `ConfirmAction`이 기록된 뒤라 여기서 걸러야 사건 개수가 요청 전과
    # 같다는 이 함수의 약속(RIG-06)이 지켜진다.
    character = None
    rulebook = None
    if body.confirmed:
        character = get_character(body.character_id)
        if character is None:
            raise HTTPException(status_code=400, detail="그런 캐릭터가 없다")

        try:
            rulebook = get_rulebook(body.rulebook_id)
        except UnknownRulebook as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if body.difficulty is not None:
            try:
                require_difficulty(rulebook, body.difficulty)
            except UnknownDifficultyLevel as exc:
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
            # ④ 판정 — 서사 호출은 아직 시작하지 않았다. `character_stats`는
            # 서버가 이미 불러 둔 `character.stats`를 그대로 넘긴다 —
            # 액터는 `web.characters_data`를 모르므로(층 계약) 호출부가
            # 값으로 넘긴다. `stat`/`difficulty`가 있으면 액터가 룰북
            # 선언에서 보정치를 조립한다(RULE-02/03, D-01/D-02).
            resolve_seq = await actor.submit(
                ResolveCheck(
                    move=body.move,
                    # D-02 — 바깥에서 자유 수정치를 안 받는다. 능력치
                    # 수정치(`stat`)와 난이도 수정치(`difficulty`)를
                    # `_prepare_resolve_check`가 룰북 선언에서 조립해
                    # 이 빈 튜플 앞뒤에 붙인다.
                    modifiers=(),
                    rulebook_id=body.rulebook_id,
                    caused_by_seq=confirm_seq,
                    person_id=identity.browser_id,
                    character_id=identity.character_id,
                    stat=body.stat,
                    character_stats=character.stats,
                    difficulty=body.difficulty,
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

    # 이 등급의 밴드(D-13/D-14) — `costs`가 결과 목록을 태울지 정한다.
    # `check_event.grade`는 `_prepare_resolve_check`가 이미 룰북 선언에서
    # 뽑은 이름이므로 여기서 `UnknownGradeName`이 나는 것은 룰북 데이터
    # 자체가 등록 뒤에 바뀐 경우뿐이다 — 그래도 조용히 넘기지 않는다.
    try:
        grade_band = require_band(rulebook.grade_bands, check_event.grade)
    except UnknownGradeName as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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
        party_state=_current_party_state(store, session_id),
        actor_character_id=identity.character_id,
        character_names=_CHARACTER_NAMES,
    )

    # 상황판단·장면 신규 대상 판단·시계 신호 관문·결과 선택(12-06)을
    # narrate() 호출 **전**에 병렬로 부른다(09-RESEARCH.md Pitfall 3이
    # 지목한 정확한 구간, ARCH-04). `choices`를 재사용하고 `load_config`를
    # 다시 부르지 않는다 — `situation_judge`/`scene_entity_judge`/
    # `clock_judge`/`outcome_picker`가 설정 파일에 없어도 `ROLE_FALLBACKS`가
    # 이미 다른 역할의 선택을 물려줬다. 이 구간 전체를 `try`로 감싸 실패 시
    # stderr 한 줄만 남기고 빈 판단으로 계속 간다 — 판단 실패가 확인
    # 요청을 막지 않는다(D-05, ARCH-05). `pick_outcome`이 던지는
    # `UnknownOutcomeCategoryFromAI`(T-12-27, AI 계약 위반)도 이 `try`가
    # 흡수한다 — 이미 굴린 주사위(`ResolveCheck`)를 버리지 않는다는 원칙이
    # 판단의 실패 사유를 가리지 않는다. **제공자 구성(`provider_resolver`
    # 호출) 자체도 이 `try` 안에 있다(CR-01 리뷰 발견)** — `master_gm`
    # 제공자 구성과 달리 여기 네 역할은 구성 실패가 판단 *호출* 실패와
    # 똑같은 방식으로 처리돼야 한다. `choices[...]` 사전 조회는 예외를
    # 던지지 않는다(위 ROLE_FALLBACKS 설명)므로 `try` 밖에 남긴다 —
    # `RecordAiCall`이 성공/실패 어느 쪽에서도 `*.model`/`*.provider`를
    # 읽어야 하기 때문이다.
    situation_judge_choice = choices["situation_judge"]
    entity_judge_choice = choices["scene_entity_judge"]
    clock_judge_choice = choices["clock_judge"]
    outcome_judge_choice = choices["outcome_picker"]
    try:
        situation_provider: Provider = request.app.state.provider_resolver(
            "situation_judge", choices, os.environ
        )
        entity_provider: Provider = request.app.state.provider_resolver(
            "scene_entity_judge", choices, os.environ
        )
        clock_provider: Provider = request.app.state.provider_resolver(
            "clock_judge", choices, os.environ
        )
        outcome_provider: Provider = request.app.state.provider_resolver(
            "outcome_picker", choices, os.environ
        )
        judgments = await gather_turn_judgments(
            situation_provider=situation_provider,
            situation_model=situation_judge_choice.model,
            entity_provider=entity_provider,
            entity_model=entity_judge_choice.model,
            clock_provider=clock_provider,
            clock_model=clock_judge_choice.model,
            outcome_provider=outcome_provider,
            outcome_model=outcome_judge_choice.model,
            ctx=ctx,
            check_summary=check_summary,
            rulebook_display_name=rulebook.display_name,
            # 이 **행위자에게 실제로 적용될 수 있는** 항목만 AI에게 보인다.
            # 룰북이 선언한 축과 캐릭터가 실린 축은 다르다(D-49로 확정된 두
            # 캐릭터가 실제로 다르다 — 브람은 방어구를 갖고 나리는 안 갖는다).
            # 이 걸름이 없으면 AI가 「나리의 방어구를 깎는다」를 고르고, 룰북
            # 대조는 통과하고, 사건까지 기록된 뒤 `resolve_character_stats`가
            # 그 연산을 조용히 버린다 — 화면엔 「변했다」가 뜨는데 아무 일도
            # 안 일어난다(2026-08-18 플레이테스트 관측).
            outcome_list=OutcomeList(
                categories=eligible_categories(rulebook.outcome_list, actor_stats(ctx)),
                max_picks=rulebook.outcome_list.max_picks,
            ),
            grade_band=grade_band,
            resource_axes=rulebook.resource_axes,
        )
    except Exception as exc:  # noqa: BLE001 - D-05, 판단(및 그 제공자 구성) 실패가 확인 요청을 막지 않는다
        print(
            f"경고: 상황판단/장면 신규 대상/시계 신호/결과 선택 판단이 실패했다 (seq {resolve_seq}) — {exc}",
            file=sys.stderr,
        )
        judgments = empty_turn_judgments()
        # 제공자 구성이 실패했을 수 있으므로 아래 배경 시계 조건 검사 등록에서
        # 이 변수를 참조하기 전에 안전한 값으로 되돌린다 — `judgments.clock.should_check`는
        # `empty_turn_judgments()`에서 항상 False이므로 실제로 쓰이지는 않지만,
        # unbound 변수를 남겨 두지 않는다(CR-01).
        clock_provider = None

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
    await actor.submit(
        RecordAiCall(
            agent_role="outcome_picker",
            model=outcome_judge_choice.model,
            provider=outcome_judge_choice.provider,
            prompt_tokens=judgments.outcome.ai.prompt_tokens,
            completion_tokens=judgments.outcome.ai.completion_tokens,
            cached_prompt_tokens=judgments.outcome.ai.cached_prompt_tokens,
            latency_ms=judgments.outcome.ai.elapsed_ms,
            caused_by_seq=confirm_seq,
        )
    )

    pending_resource_changes, discretionary = _pending_resource_changes(
        rulebook=rulebook,
        grade_band=grade_band,
        outcome=judgments.outcome,
        resolve_seq=resolve_seq,
        actor_axes=character_axis_names(actor_stats(ctx)),
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
            resource_axes=rulebook.resource_axes,
        )
        first_sentence = await asyncio.to_thread(next, narration_iter, _NO_SENTENCE)
    except Exception as exc:  # noqa: BLE001 - 서사 스트림 생성/첫 조각 실패만 여기서 잡는다(G-03-3)
        narration_error = exc
        first_sentence = _NO_SENTENCE

    if first_sentence is not _NO_SENTENCE:
        await _submit_narration_chunk(  # 액터/저장소 결함은 여기서 그대로 터진다(WR-01)
            actor=actor,
            chunk=first_sentence,
            chunk_index=chunk_index,
            resolve_seq=resolve_seq,
            narration_texts=narration_texts,
        )
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
            await _submit_narration_chunk(  # 액터/저장소 결함은 여기서 그대로 터진다(WR-01)
                actor=actor,
                chunk=sentence,
                chunk_index=chunk_index,
                resolve_seq=resolve_seq,
                narration_texts=narration_texts,
            )
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
            modifiers=[
                ModifierView(type=m.type, value=m.value, source=m.source)
                for m in check_event.modifiers
            ],
            pending_resource_changes=pending_resource_changes,
            discretionary=discretionary,
        )

    # 시계 조건 검사 배경 등록 — 관문 신호가 참일 때만 건다(ARCH-03/D-01).
    # 깊은 판단용 제공자 호출은 신호가 거짓이면 아예 일어나지 않는다 — 값싼
    # 관문이 값비싼 판단을 거른다는 DP-01의 구조가 여기서 그대로 지켜진다.
    # `clock_provider is not None`도 함께 확인한다(CR-01) — 위 제공자 구성이
    # 실패했으면 `judgments.clock.should_check`가 항상 False이므로 이 조건은
    # 방어적 이중 확인이지만, `clock_provider`가 unbound인 채로 아래에서
    # 참조되는 경로를 코드로도 남겨 두지 않는다.
    if judgments.clock.should_check and clock_provider is not None:
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
        modifiers=[
            ModifierView(type=m.type, value=m.value, source=m.source)
            for m in check_event.modifiers
        ],
        pending_resource_changes=pending_resource_changes,
        discretionary=discretionary,
    )


class DiscretionaryProposal(BaseModel):
    """재량 판정 제안 하나 — 축은 룰북이 선언한 이름 중에서, 동작은 플랫폼
    여덟 개 중 하나, 양은 정수(RULE-10). 서버가 이 라우트 안에서 다시
    검사한다(ⓐ 축이 이 룰북에 있는가 ⓑ 축의 form과 동작이 맞는가 ⓒ 양이
    `MAX_DISCRETIONARY_AMOUNT` 안인가) — 사람이 확인을 눌렀다고 해서 보낸
    값을 그대로 믿지 않는다."""

    model_config = ConfigDict(extra="forbid")

    axis: str = Field(min_length=1, max_length=MAX_ID_LEN)
    operation: str = Field(min_length=1, max_length=32)
    amount: int = Field(ge=-MAX_DISCRETIONARY_AMOUNT, le=MAX_DISCRETIONARY_AMOUNT)


class ConfirmResourceChangeRequest(BaseModel):
    """숫자가 실제로 변할 때만 뜨는 확인 관문의 요청(12-06, D-09/D-10).

    **요청은 어느 항목을 골랐는지(식별자)만 말한다.** 변화량 숫자는 이
    본문 어디에도 없다 — 적용되는 값은 서버가 룰북 선언에서 다시 만든다
    (D-02와 같은 근거, T-12-26). `category_ids`는 `ConfirmResponse.
    pending_resource_changes`에 실렸던 카테고리 식별자를 그대로 되돌려
    보내는 것이 정상 사용이지만, 서버는 그 목록을 다시 신뢰하지 않고
    `ordered_categories`로 다시 대조한다(T-12-27). `extra="forbid"`가
    오타·조작으로 생긴 여분 칸을 거절한다(`ConfirmRequest`와 같은 관례).
    """

    model_config = ConfigDict(extra="forbid")

    character_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    caused_by_seq: int = Field(ge=0)
    """이 자원 변화를 일으킨 원인 사건 순번 — 보통 그 판정의 `resolve_seq`다.
    Phase 8 멱등성 창(`GameState.resource_change_by_cause`)이 이 값으로
    재시도를 단락시킨다(같은 값으로 두 번 오면 두 번째는 첫 번째 사건을
    재사용한다, T-12-03)."""
    category_ids: list[str] = Field(default_factory=list, max_length=MAX_PICKED_CATEGORIES)
    confirmed: bool
    rulebook_id: str = Field(default=DUNGEONWORLD_LIKE_ID, max_length=MAX_ID_LEN)
    discretionary: DiscretionaryProposal | None = None
    """룰북에 결과 목록이 없을 때만(`ConfirmResponse.discretionary.available`)
    뜻이 있다 — `category_ids`와 이 칸은 서로 배타적이지 않지만(같은 요청
    안에서 함께 적용될 수 있다), 정상 사용에서는 한쪽만 채워진다."""
    retro_declaration_amount: int | None = Field(
        default=None, ge=-MAX_DISCRETIONARY_AMOUNT, le=MAX_DISCRETIONARY_AMOUNT
    )
    """소지품에 없는 것을 쓰겠다고 했을 때의 소급 선언 양(RULE-16, D-16) —
    `DeclareResponse.retro_declaration.available`이 참일 때만 뜻이 있다.
    축·동작은 이 칸에 없다 — 룰북이 이미 잠갔다(`Rulebook.
    retro_declaration.cost_axis`/`.operation`), 양만 사람이 정한다. 같은
    입력 실수 방어 상한(`MAX_DISCRETIONARY_AMOUNT`)을 재사용한다 — 새
    상한을 만들지 않는다."""


class ConfirmResourceChangeResponse(BaseModel):
    applied: bool
    resource_changes: list[ResourceChangeView] = []


@router.post(
    "/sessions/{session_id}/actions/confirm-resource-change",
    response_model=ConfirmResourceChangeResponse,
)
async def confirm_resource_change(
    session_id: str, request: Request, body: ConfirmResourceChangeRequest
) -> ConfirmResourceChangeResponse:
    """숫자가 실제로 변할 때만 뜨는 확인 관문 — 그 캐릭터를 잡은 사람만
    누를 수 있고, 확인해야만 자원이 깎인다(12-06, D-09/D-10).

    **맨 앞이 신원 대조다(TRUST-02, D-10)** — `confirm()`의 그 자리와
    글자 그대로 같은 모양이다. 새 권한 개념을 만들지 않는다.

    거부(`confirmed=False`)면 검증 없이 즉시 끝난다 — 사건이 하나도
    안 쌓인다. 확인이면 ⓐ `category_ids`를 `ordered_categories`로 룰북
    선언 순서와 다시 대조하고(목록 밖 식별자·중복 선택은 400) ⓑ
    `discretionary`가 있으면 `validate_outcome_list`(등록 시점 검증 함수를
    재사용)로 축·형태·동작을 다시 검사한다. 두 출처를 합쳐도 적용할 변화가
    하나도 없으면(예: `category_ids`가 빈 목록이고 `discretionary`도 없음)
    400이다.

    **변화를 서버가 다시 만든다.** 요청 본문의 숫자는 어디에도 쓰이지
    않는다 — 골라진 `ResourceChangeDecl`을 `roll_amount`(`LiveRoller`)로
    실제 양·눈으로 바꾼 뒤에야 `RecordResourceChange`를 제출한다. 제출은
    `confirm()`이 이미 세운 삼중 `try/except`(`AlreadyChanged` → 재사용
    · `CommandRejected` → 400 · `SequenceConflict` → 409) 모양을 그대로
    쓴다 — 재시도가 두 번 깎지 않는다.
    """
    identity = read_identity(request, session_id)
    if identity is None or identity.character_id != body.character_id:
        print("경고: 신원 검증 실패 — confirm-resource-change 거부", file=sys.stderr)
        raise HTTPException(status_code=403, detail="캐릭터를 다시 선택해 주세요")

    if not body.confirmed:
        return ConfirmResourceChangeResponse(applied=False)

    if len(body.category_ids) != len(set(body.category_ids)):
        raise HTTPException(status_code=400, detail="같은 결과 카테고리를 두 번 보냈다")

    try:
        rulebook = get_rulebook(body.rulebook_id)
    except UnknownRulebook as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    decls: list[ResourceChangeDecl] = []
    source = "outcome_list"
    if body.category_ids:
        try:
            picked_categories = ordered_categories(rulebook.outcome_list, body.category_ids)
        except (UnknownOutcomeCategory, InvalidOutcomeList) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        for category in picked_categories:
            decls.extend(category.changes)

    if body.discretionary is not None:
        source = "discretionary_ruling"
        discretionary_decl = ResourceChangeDecl(
            axis=body.discretionary.axis,
            operation=body.discretionary.operation,
            amount=body.discretionary.amount,
        )
        try:
            # `validate_outcome_list`(등록 시점 검증 함수)를 재사용해 이
            # 제안 하나짜리 임시 결과 목록을 검사한다 — 축 존재·`form !=
            # "none"`·form-operation 대응 세 검증을 새로 안 만든다. 그 함수가
            # 접근하는 `_FORM_ALLOWED_OPERATIONS`는 `rulebook.py`의 비공개
            # 표라서 이 파일이 직접 참조하지 않는다.
            validate_outcome_list(
                OutcomeList(
                    categories=(
                        OutcomeCategory(
                            category_id="_discretionary_ruling", changes=(discretionary_decl,)
                        ),
                    )
                ),
                rulebook,
            )
        except InvalidOutcomeList as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        decls.append(discretionary_decl)

    if body.retro_declaration_amount is not None:
        # RULE-16, D-16 — 축과 동작은 룰북이 이미 잠갔다(`retro_declaration
        # .cost_axis`/`.operation`). 양만 이 요청이 정한다. 룰북이 소급
        # 선언을 허용하지 않으면(`allowed=False`) 이 칸을 채워 봐야 소용
        # 없다 — 목록 밖 카테고리와 같은 무게로 거절한다.
        if not rulebook.retro_declaration.allowed:
            raise HTTPException(status_code=400, detail="이 룰북은 소급 선언을 허용하지 않는다")
        source = "retro_declaration"
        assert rulebook.retro_declaration.cost_axis is not None  # RetroDeclarationDecl 규약
        assert rulebook.retro_declaration.operation is not None
        decls.append(
            ResourceChangeDecl(
                axis=rulebook.retro_declaration.cost_axis,
                operation=rulebook.retro_declaration.operation,
                amount=body.retro_declaration_amount,
            )
        )

    if not decls:
        raise HTTPException(status_code=400, detail="적용할 자원 변화가 없다")

    # 마지막 관문 — 이 캐릭터가 **실제로 가진** 축인지 확인한다. 위 세
    # 갈래(결과 목록·재량 판정·소급 선언)는 전부 **룰북**과만 대조했다.
    # 룰북이 선언한 축과 캐릭터가 실린 축은 다르다(D-49). 여기서 막지 않으면
    # 그 사건이 기록된 뒤 `resolve_character_stats`가 조용히 버려서, 화면엔
    # 「변했다」가 뜨는데 실제로는 아무 일도 안 일어난다 — 잘못된 기록이
    # 영구히 남는다(2026-08-18 플레이테스트 관측).
    actor_entity = get_character(identity.character_id)
    if actor_entity is None:
        raise HTTPException(status_code=404, detail="캐릭터를 찾을 수 없다")
    try:
        require_axes_on_character(decls, actor_entity.stats)
    except AxisNotOnCharacter as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    store = request.app.state.store
    registry = request.app.state.registry
    actor = registry.get_or_create(session_id)

    roller = LiveRoller()
    ops = tuple(
        ResourceOp(axis=decl.axis, operation=decl.operation, amount=rolled_amount, rolls=rolls)
        for decl in decls
        for rolled_amount, rolls in (roll_amount(roller, decl.amount),)
    )

    # 쓰기 전 시연 적용 — 이 연산들을 **실제로 접어 본다**. 여기서 터지는
    # 것이 사건이 기록된 뒤에 터지면 그 세션은 영구히 복구 불가가 된다:
    # 시트 조립(`_current_party_state`)이 세션의 캐릭터 **전원**을 한 번에
    # 접으므로, 한 사람의 잘못된 기록 하나가 그 세션의 모든 요청을 500으로
    # 만든다. 기록을 손대는 것 말고는 되돌릴 방법이 없다.
    #
    # 위의 검증들이 못 잡는 조합이 실재한다(2026-08-18 코드 리뷰 CR-01):
    # 재량 판정·소급 선언의 `amount`는 요청 모델에서 `int`로 못박혀 있는데,
    # `named_slots`(예: Cairn의 `Inventory` — 소급 선언이 유일하게 물려 있는
    # 축)와 `tag_list`는 **문자열** 양이 필요하다. 축 이름·형태·동작 세
    # 검사(`validate_outcome_list`)는 전부 통과하고 양의 타입만 어긋난다.
    #
    # 개별 검사를 새로 만들지 않고 `apply_resource_op` 자체를 재사용한다 —
    # 「적용해서 되는가」가 곧 「기록해도 되는가」이므로 두 판정이 갈릴 수
    # 없다. 시작값으로 접어도 형태·동작·양 타입 검증은 동일하다(그 셋은
    # 현재 값과 무관하다).
    try:
        resolve_character_stats(
            actor_entity.stats, {op.axis: (op,) for op in ops}
        )
    except InvalidResourceChange as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        await actor.submit(
            RecordResourceChange(
                character_id=identity.character_id,
                changes=ops,
                source=source,
                caused_by_seq=body.caused_by_seq,
            )
        )
    except AlreadyChanged as exc:
        # 재시도 — 이미 기록된 변화를 다시 깎지 않는다. 응답은 방금 다시
        # 굴린(그러나 안 쓴) 값이 아니라 **실제로 기록된** 사건을 되읽어
        # 채운다 — 그렇지 않으면 두 번째 요청의 응답이 첫 번째 요청이 실제로
        # 적용한 값과 다른 숫자를 보여준다.
        resource_event = store.read_events(session_id, from_seq=exc.resource_seq)[0]
        return ConfirmResourceChangeResponse(
            applied=True,
            resource_changes=[
                ResourceChangeView(
                    axis=change.axis,
                    operation=change.operation,
                    amount=change.amount,
                    rolls=change.rolls,
                )
                for change in resource_event.changes
            ],
        )
    except CommandRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SequenceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return ConfirmResourceChangeResponse(
        applied=True,
        resource_changes=[
            ResourceChangeView(axis=op.axis, operation=op.operation, amount=op.amount, rolls=list(op.rolls))
            for op in ops
        ],
    )


class ProceedRequest(BaseModel):
    player_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    declare_seq: int = Field(ge=0)
    rulebook_id: str = Field(default=DUNGEONWORLD_LIKE_ID, max_length=MAX_ID_LEN)
    character_id: str = Field(min_length=1, max_length=MAX_ID_LEN)


class ProceedResponse(BaseModel):
    proceeded: bool
    narration_chunk_count: int = 0
    narration_failed: bool = False
    """서사 생성만 실패했다는 표시다 — `ConfirmResponse.narration_failed`와
    같은 뜻·같은 기본값이다(TRUST-06, D-08). 판정이 애초에 없는 경로라
    `rolls`/`grade`/`target` 칸 자체가 없다."""


@router.post("/sessions/{session_id}/proceed", response_model=ProceedResponse)
async def proceed(
    session_id: str,
    request: Request,
    body: ProceedRequest,
    background: BackgroundTasks,
) -> ProceedResponse:
    """굴릴 필요가 없다고 분류된 행동(`tier == "no_check"`)을 판정 없이
    서술로 잇는다(D-10 ②갈래, RULE-15, 11-06).

    `confirm()`의 **판정 이후 구간을 거울처럼 따라간다** — 다른 점은 딱
    둘이다: `ConfirmAction`/`ResolveCheck`를 제출하지 않고, `check_summary`
    자리에 판정 결과 요약 대신 `agents.context.NO_CHECK_SUMMARY` 고정
    문장을 쓴다. 이 턴의 사건 기록은 「선언 + 서사」모양으로 남는다 — 확인·
    판정 사건이 없다(결정 1, PLAN.md). 서사·시계 판단이 가리키는 원인
    사건(`caused_by_seq`)은 `body.declare_seq`다 — 이 경로에 확인·판정
    사건이 없으므로 그보다 앞서 이미 기록된 선언 사건을 가리킨다.

    **신원 대조가 맨 앞이다(TRUST-02, D-04).** `confirm()`과 같은 이유·
    같은 형식이다.

    **신원 대조만으로는 부족하다(T-11-29, 11-06 rework).** 「내가 이
    캐릭터의 주인인가」는 위 신원 대조가 보지만, 「이 `declare_seq`가
    실제로 이 캐릭터가 낸 선언인가」·「이 선언이 실제로 `no_check`로
    분류됐는가」는 별개의 질문이다 — 라우트 계층만으로는 둘 다 클라이언트가
    보낸 값을 그대로 믿게 된다(판정을 요구했던 행동을 판정 없이 진행하는
    구멍). `VerifyProceedEligibility`가 액터의 사건-접은 상태
    (`declare_owners`/`declare_no_check`)로 둘 다 다시 확인한다 —
    `_prepare_confirm`의 소유권 검사와 같은 이유·같은 서버-재시작 내구성.
    """
    identity = read_identity(request, session_id)
    if identity is None or identity.character_id != body.character_id:
        print("경고: 신원 검증 실패 — proceed 거부", file=sys.stderr)
        raise HTTPException(status_code=403, detail="캐릭터를 다시 선택해 주세요")

    store = request.app.state.store
    registry = request.app.state.registry
    actor = registry.get_or_create(session_id)

    try:
        await actor.submit(
            VerifyProceedEligibility(
                declare_seq=body.declare_seq,
                character_id=identity.character_id,
            )
        )
    except ProceedEligible:
        pass  # 검증 통과 — 사건은 안 남는다(위 도크스트링 참조), 그대로 진행한다.
    except CommandRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SequenceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    character = get_character(body.character_id)
    if character is None:
        raise HTTPException(status_code=400, detail="그런 캐릭터가 없다")

    try:
        rulebook = get_rulebook(body.rulebook_id)
    except UnknownRulebook as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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

    # `confirm()`과 같은 자리·같은 모양으로 파티의 「접은 지금 값」을
    # 넘긴다(12-05, D-17/D-18) — **웹 안에서도 호출부가 둘이라는 것이 이
    # 함정이다.** 하나만 고치면 「굴린 턴은 파티를 보고 안 굴린 턴은 못
    # 보는」 어긋남이 생긴다.
    ctx = build_turn_context(
        store,
        session_id,
        body.rulebook_id,
        party_state=_current_party_state(store, session_id),
        actor_character_id=identity.character_id,
        character_names=_CHARACTER_NAMES,
    )

    # 상황판단·장면 신규 대상 판단·시계 신호 관문을 narrate() 호출 **전**에
    # 병렬로 부른다 — `confirm()`과 같은 구조·같은 이유(09-RESEARCH.md
    # Pitfall 3, ARCH-04). 실패해도 확인/진행 요청을 막지 않는다(D-05,
    # ARCH-05) — `confirm()`과 완전히 같은 방어.
    situation_judge_choice = choices["situation_judge"]
    entity_judge_choice = choices["scene_entity_judge"]
    clock_judge_choice = choices["clock_judge"]
    outcome_judge_choice = choices["outcome_picker"]
    try:
        situation_provider: Provider = request.app.state.provider_resolver(
            "situation_judge", choices, os.environ
        )
        entity_provider: Provider = request.app.state.provider_resolver(
            "scene_entity_judge", choices, os.environ
        )
        clock_provider: Provider = request.app.state.provider_resolver(
            "clock_judge", choices, os.environ
        )
        outcome_provider: Provider = request.app.state.provider_resolver(
            "outcome_picker", choices, os.environ
        )
        judgments = await gather_turn_judgments(
            situation_provider=situation_provider,
            situation_model=situation_judge_choice.model,
            entity_provider=entity_provider,
            entity_model=entity_judge_choice.model,
            clock_provider=clock_provider,
            clock_model=clock_judge_choice.model,
            outcome_provider=outcome_provider,
            outcome_model=outcome_judge_choice.model,
            ctx=ctx,
            check_summary=NO_CHECK_SUMMARY,
            rulebook_display_name=rulebook.display_name,
            # 판정 자체가 없는 경로다(D-10 ②갈래) — 결과 목록도 재량 판정도
            # 성립하지 않는다. `_NO_CHECK_GRADE_BAND.costs=False`가
            # `pick_outcome`의 조기 반환을 걸어 모델을 아예 안 부른다.
            outcome_list=OutcomeList(categories=()),
            grade_band=_NO_CHECK_GRADE_BAND,
            resource_axes=rulebook.resource_axes,
        )
    except Exception as exc:  # noqa: BLE001 - D-05, 판단(및 그 제공자 구성) 실패가 진행 요청을 막지 않는다
        print(
            f"경고: 상황판단/장면 신규 대상/시계 신호/결과 선택 판단이 실패했다 (declare_seq {body.declare_seq}) — {exc}",
            file=sys.stderr,
        )
        judgments = empty_turn_judgments()
        clock_provider = None

    # 새 에이전트 호출 셋의 기록 — 성공·실패 어느 쪽에서도 항상 제출한다
    # (MEAS-02, `confirm()`과 같은 규율). caused_by_seq는 `body.declare_seq`다
    # — 이 경로에는 confirm_seq/resolve_seq가 없다.
    await actor.submit(
        RecordAiCall(
            agent_role="situation_judge",
            model=situation_judge_choice.model,
            provider=situation_judge_choice.provider,
            prompt_tokens=judgments.situation.ai.prompt_tokens,
            completion_tokens=judgments.situation.ai.completion_tokens,
            cached_prompt_tokens=judgments.situation.ai.cached_prompt_tokens,
            latency_ms=judgments.situation.ai.elapsed_ms,
            caused_by_seq=body.declare_seq,
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
            caused_by_seq=body.declare_seq,
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
            caused_by_seq=body.declare_seq,
        )
    )
    await actor.submit(
        RecordAiCall(
            agent_role="outcome_picker",
            model=outcome_judge_choice.model,
            provider=outcome_judge_choice.provider,
            prompt_tokens=judgments.outcome.ai.prompt_tokens,
            completion_tokens=judgments.outcome.ai.completion_tokens,
            cached_prompt_tokens=judgments.outcome.ai.cached_prompt_tokens,
            latency_ms=judgments.outcome.ai.elapsed_ms,
            caused_by_seq=body.declare_seq,
        )
    )

    facts = build_narration_facts(ctx=ctx, check_summary=NO_CHECK_SUMMARY, judgments=judgments)

    # 서사 — `confirm()`의 ⑤ 구간과 한 글자도 다르지 않다(예외 포착 범위·
    # 되감지 않음·narration_failed 규약 전부 동일). caused_by_seq만
    # `body.declare_seq`로 다르다.
    narration_start = time.monotonic()
    narration_error: Exception | None = None
    chunk_index = 0
    narration_texts: list[str] = []
    try:
        narration_iter = narrate(
            provider=gm_provider,
            model=gm_choice.model,
            facts=facts,
            rulebook_display_name=rulebook.display_name,
            resource_axes=rulebook.resource_axes,
        )
        first_sentence = await asyncio.to_thread(next, narration_iter, _NO_SENTENCE)
    except Exception as exc:  # noqa: BLE001 - 서사 스트림 생성/첫 조각 실패만 여기서 잡는다(G-03-3)
        narration_error = exc
        first_sentence = _NO_SENTENCE

    if first_sentence is not _NO_SENTENCE:
        await _submit_narration_chunk(  # 액터/저장소 결함은 여기서 그대로 터진다(WR-01)
            actor=actor,
            chunk=first_sentence,
            chunk_index=chunk_index,
            resolve_seq=body.declare_seq,
            narration_texts=narration_texts,
        )
        chunk_index += 1
        while True:
            try:
                sentence = await asyncio.to_thread(next, narration_iter, _NO_SENTENCE)
            except Exception as exc:  # noqa: BLE001 - 서사 스트림 이어받기 실패만 여기서 잡는다(G-03-3)
                narration_error = exc
                break
            if sentence is _NO_SENTENCE:
                break
            await _submit_narration_chunk(  # 액터/저장소 결함은 여기서 그대로 터진다(WR-01)
                actor=actor,
                chunk=sentence,
                chunk_index=chunk_index,
                resolve_seq=body.declare_seq,
                narration_texts=narration_texts,
            )
            chunk_index += 1

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
            caused_by_seq=body.declare_seq,
        )
    )

    if narration_error is not None or not gm_result.ok:
        # D-08/TRUST-06과 같은 이유 — 이 경로는 애초에 판정이 없으므로
        # 버릴 굴림 결과 자체가 없다. 200을 돌려주고 narration_failed로
        # 실패를 알린다.
        return ProceedResponse(
            proceeded=True,
            narration_chunk_count=chunk_index,
            narration_failed=True,
        )

    # 시계 조건 검사 배경 등록 — `confirm()`과 같은 자리·같은 조건
    # (ARCH-03/D-01). caused_by_seq는 `body.declare_seq`다.
    if judgments.clock.should_check and clock_provider is not None:
        background.add_task(
            run_clock_condition_check,
            actor=actor,
            provider=clock_provider,
            model=clock_judge_choice.model,
            judge_ctx=build_clock_judge_context(ctx, NO_CHECK_SUMMARY),
            rulebook_display_name=rulebook.display_name,
            narration_text="\n".join(narration_texts),
            resolve_seq=body.declare_seq,
            clock_id=ctx.clock_state.clock_id,
            clock_segment_count=CLOCK_SEGMENT_COUNT,
        )

    return ProceedResponse(
        proceeded=True,
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
