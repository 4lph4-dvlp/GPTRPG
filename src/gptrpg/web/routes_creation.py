"""캐릭터 만들기 일곱 경로 — 인원 확정 · 항목 값 확정 · 완성 · 명단 잠금
· 안내 · 지목 · 되묻기(D-03~D-09, Phase 12.1).

**뒤 셋(`announce`/`nominate`/`follow-up`, 12.1-03)이 자기소개 진행 경로다.**
값 확정(`step`/`complete`/`lock-roster`)과 달리 이 셋은 `creation_gm`
역할을 부른다 — 하지만 「지금 몇 단계인지 · 누가 아직 안 끝났는지 · 룰북
최소선이 채워졌는지」는 여전히 이 라우터가 `GameState`에서 직접 계산한다
(대화의 상태 기계는 코드가 돌린다, 12.1-03-PLAN.md § 결정한 열린 지점 ①).
AI가 하는 것은 안내 산문 · 닫힌 후보 목록에서 다음 차례 고르기 · 되물을지
판단뿐이고, 반환값에 값을 정하는 통로가 없다(D14).

이 라우터는 미리 만들어진 캐릭터 목록을 돌려주는 경로를 만들지 않는다
(CHAR-02) — `web.characters_data`를 import하지 않는다. 정적 넷(브람·나리·
선·호두)과 **나란히 존재하는** 새 경로다(12.1-05가 그 정적 넷을 지운다).

**`complete` 경로가 지키는 순서** (`routes_characters.select_character`의
「점유 제출이 쿠키 굽기보다 먼저」 규율을 그대로 옮긴다): ① 신원을 먼저
대조한다(이미 쿠키가 있으면 그 캐릭터와 요청의 캐릭터가 달라야 403 — 첫
캐릭터를 만드는 브라우저는 아직 쿠키가 없으므로 이 검사를 그대로
통과한다, `select_character`가 첫 선택에서 쿠키 없이도 통과하는 것과 같은
결) ② `CreateCharacter` 제출 ③ 그 직후 같은 요청 안에서 `OccupyCharacter`
제출(`AlreadyOccupied`는 성공으로 통과 — 본인 재접속, D-05) ④ 마지막에
쿠키를 굽는다. 순서가 뒤집히면 완성은 됐는데 점유가 없는 반쪽 상태가
남는다.

**알려진 범위 경계:** `GET /my-character`·`GET /characters/{id}`
(`routes_characters.py`)는 여전히 `web.characters_data`의 정적 목록만
읽는다 — 이 계획이 만드는 세션 스코프 캐릭터(`GameState.created_characters`)
는 그 두 경로에서 아직 보이지 않는다. 12.1-05가 그 세 호출부를 한꺼번에
세션 기준으로 옮긴다(D-12). 이 계획은 사건 기록(`GET /events`에 남는
`character_occupied`)과 쿠키로 「자동 점유가 실제로 일어났다」를 증명한다.
"""

import asyncio
import os
import sys

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from gptrpg.agents.config import ConfigNotFound, InvalidAgentConfig, load_config
from gptrpg.agents.context import PARTY_MEMBER_LIMIT
from gptrpg.agents.creation_gm import (
    CreationGmContractViolation,
    CreationGmWrapUp,
    announce_requirements,
    judge_hooks,
    nominate_speaker,
    wrap_up,
)
from gptrpg.agents.prompt_assembly import fence_player_text
from gptrpg.agents.providers import MissingApiKey, ProviderNotImplemented, UnknownProvider
from gptrpg.agents.providers.base import Provider
from gptrpg.event_log.store import SequenceConflict
from gptrpg.rules_core.reducer import GameState
from gptrpg.rules_core.rulebook import (
    EntityAxisMismatch,
    InvalidCreationStep,
    InvalidResourceAxis,
    Rulebook,
)
from gptrpg.rulebooks import UnknownRulebook, get_rulebook
from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID
from gptrpg.session_actor.actor import (
    AlreadyOccupied,
    CommandRejected,
    CompleteCreationStep,
    CreateCharacter,
    FixPartySize,
    LockPartyRoster,
    OccupyCharacter,
    RecordConsent,
    RecordInterjection,
    ReopenCreationStep,
    RosterAlreadyLocked,
)
from gptrpg.web.cookie_auth import COOKIE_NAME, read_identity, sign_cookie
from gptrpg.web.routes_actions import MAX_ID_LEN, MAX_RAW_TEXT_LEN

_AGENT_RESOLUTION_ERRORS = (
    ConfigNotFound,
    InvalidAgentConfig,
    UnknownProvider,
    MissingApiKey,
    ProviderNotImplemented,
)
"""`web/routes_actions.py`의 declare()/confirm()이 이미 쓰는 503 처리 대상과
같은 예외 집합이다 — 운영자 설정 문제(제공자 미설정·키 없음)는 「GM 호출
실패」(D-05/ARCH-05 폴백 대상)와 다른 층이므로 여기서 갈라 503으로 낸다.
`CreationGmContractViolation`(AI 계약 위반)과 `call_with_one_retry`가 흡수하는
제공자 호출 실패는 이 목록에 없다 — 그 둘은 라우트별로 폴백 값과 함께 200을
낸다(Task 3 ⑥)."""

router = APIRouter()

COOKIE_MAX_AGE_S = 60 * 60 * 24 * 14
"""`routes_characters.COOKIE_MAX_AGE_S`와 같은 값 — 이 경로도 같은 쿠키를
굽는다(같은 만료 규약을 두 곳에 따로 정하지 않는다)."""


class FixPartySizeRequest(BaseModel):
    player_character_count: int = Field(ge=1)
    rulebook_id: str = Field(default=DUNGEONWORLD_LIKE_ID, max_length=MAX_ID_LEN)


class SeqResponse(BaseModel):
    seq: int


@router.post("/sessions/{session_id}/creation/party-size", response_model=SeqResponse)
async def fix_party_size(
    session_id: str, body: FixPartySizeRequest, request: Request
) -> SeqResponse:
    """방을 여는 사람이 이 세션의 인원을 확정한다(D-01). 재확정은 없다.

    **`PARTY_MEMBER_LIMIT` 절대 안전 밸브(T-12.1-13)를 여기서 검사한다** —
    `session_actor`는 `agents`를 import할 수 없으므로(`.importlinter`
    contract:2) 이 상한 검사는 액터가 아니라 이 호출부의 몫이다. 룰북
    범위 대조(액터, `validate_party_size`)와 이 상한은 서로 다른 층에
    있는 두 관문이다 — 어떤 룰북도 이 상한을 넘을 수 없다.
    """
    if body.player_character_count > PARTY_MEMBER_LIMIT:
        raise HTTPException(
            status_code=400,
            detail=f"인원은 {PARTY_MEMBER_LIMIT}명을 넘을 수 없다(안전 상한)",
        )
    actor = request.app.state.registry.get_or_create(session_id)
    try:
        seq = await actor.submit(
            FixPartySize(
                player_character_count=body.player_character_count,
                rulebook_id=body.rulebook_id,
            )
        )
    except UnknownRulebook as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except CommandRejected as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SequenceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return SeqResponse(seq=seq)


class AxisValueBody(BaseModel):
    axis_name: str = Field(min_length=1, max_length=MAX_ID_LEN)
    value: int


class CompleteCreationStepRequest(BaseModel):
    character_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    browser_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    step_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    rulebook_id: str = Field(default=DUNGEONWORLD_LIKE_ID, max_length=MAX_ID_LEN)
    text_value: str | None = Field(default=None, max_length=MAX_RAW_TEXT_LEN)
    picked: tuple[str, ...] | None = None
    axis_values: list[AxisValueBody] | None = None


@router.post("/sessions/{session_id}/creation/step", response_model=SeqResponse)
async def complete_creation_step(
    session_id: str, body: CompleteCreationStepRequest, request: Request
) -> SeqResponse:
    """만들기 항목 하나(자유 서술 또는 정해진 숫자 배치)의 값을 확정한다
    (D-03/D-07).

    **신원 대조의 범위:** 이미 유효한 쿠키를 든 브라우저가 다른 캐릭터의
    항목을 제출하려 하면 403이다(T-12.1-01). 아직 쿠키가 없는 첫 만들기
    대화 참가자는 이 검사를 그대로 통과한다 — 완성(`/complete`)이 나서야
    쿠키가 구워지므로, 그 전까지는 `body.browser_id`가 이 참가자를 가리키는
    유일한 값이다. 이 값의 완전한 위조 방지는 12.1-03/04(GM이 진행하는
    다회 대화, 차례 관리)가 붙인다 — 이 트레이서는 한 줄기를 뚫는 것이
    목적이라 그 방어를 아직 완성하지 않는다.
    """
    identity = read_identity(request, session_id)
    if identity is not None and identity.character_id != body.character_id:
        print("경고: 신원 검증 실패 — creation/step 거부", file=sys.stderr)
        raise HTTPException(status_code=403, detail="캐릭터를 다시 선택해 주세요")

    actor = request.app.state.registry.get_or_create(session_id)
    axis_values = (
        tuple((item.axis_name, item.value) for item in body.axis_values)
        if body.axis_values is not None
        else None
    )
    try:
        seq = await actor.submit(
            CompleteCreationStep(
                character_id=body.character_id,
                browser_id=body.browser_id,
                step_id=body.step_id,
                rulebook_id=body.rulebook_id,
                text_value=body.text_value,
                picked=body.picked,
                axis_values=axis_values,
            )
        )
    except (UnknownRulebook, InvalidCreationStep) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RosterAlreadyLocked as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except CommandRejected as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SequenceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return SeqResponse(seq=seq)


class CreateCharacterRequest(BaseModel):
    character_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    browser_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    rulebook_id: str = Field(default=DUNGEONWORLD_LIKE_ID, max_length=MAX_ID_LEN)
    one_line_intro: str = Field(min_length=1, max_length=MAX_RAW_TEXT_LEN)


class CreationCompleteResponse(BaseModel):
    character_id: str
    character_seq: int
    occupy_seq: int


@router.post("/sessions/{session_id}/creation/complete", response_model=CreationCompleteResponse)
async def complete_creation(
    session_id: str,
    body: CreateCharacterRequest,
    request: Request,
    response: Response,
) -> CreationCompleteResponse:
    """확정된 항목 값으로 캐릭터를 완성하고, 만든 사람이 곧바로 그
    캐릭터를 점유한 채로 쿠키를 받는다(CHAR-05).
    """
    identity = read_identity(request, session_id)
    if identity is not None and identity.character_id != body.character_id:
        print("경고: 신원 검증 실패 — creation/complete 거부", file=sys.stderr)
        raise HTTPException(status_code=403, detail="캐릭터를 다시 선택해 주세요")
    browser_id = identity.browser_id if identity is not None else body.browser_id

    actor = request.app.state.registry.get_or_create(session_id)
    try:
        character_seq = await actor.submit(
            CreateCharacter(
                character_id=body.character_id,
                browser_id=browser_id,
                rulebook_id=body.rulebook_id,
                one_line_intro=body.one_line_intro,
            )
        )
    except UnknownRulebook as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (EntityAxisMismatch, InvalidResourceAxis) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RosterAlreadyLocked as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except CommandRejected as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SequenceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    # 완성 직후 같은 요청 안에서 자동 점유(CHAR-05) — 기존 Phase 8 경로를
    # 그대로 재사용한다. 새 권한 개념을 만들지 않는다.
    try:
        occupy_seq = await actor.submit(
            OccupyCharacter(character_id=body.character_id, browser_id=browser_id)
        )
    except AlreadyOccupied:
        occupy_seq = character_seq  # 본인 재접속 — 새 사건 없음(D-05).
    except CommandRejected as exc:
        print("경고: 캐릭터 점유 거부 — creation/complete", file=sys.stderr)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SequenceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    secret = request.app.state.cookie_secret
    response.set_cookie(
        key=COOKIE_NAME,
        value=sign_cookie(
            {
                "session_id": session_id,
                "browser_id": browser_id,
                "character_id": body.character_id,
            },
            secret=secret,
        ),
        max_age=COOKIE_MAX_AGE_S,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return CreationCompleteResponse(
        character_id=body.character_id,
        character_seq=character_seq,
        occupy_seq=occupy_seq,
    )


class LockPartyRosterRequest(BaseModel):
    character_ids: list[str]


@router.post("/sessions/{session_id}/creation/lock-roster", response_model=SeqResponse)
async def lock_party_roster(
    session_id: str, body: LockPartyRosterRequest, request: Request
) -> SeqResponse:
    """전원 동의 뒤 파티 명단을 잠근다(D-08) — 잠근 뒤에는 되돌릴 수 없다."""
    actor = request.app.state.registry.get_or_create(session_id)
    try:
        seq = await actor.submit(LockPartyRoster(character_ids=tuple(body.character_ids)))
    except RosterAlreadyLocked as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except CommandRejected as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SequenceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return SeqResponse(seq=seq)


# ---------------------------------------------------------------------------
# 되돌리기와 끼어들기 — D-07 경계 · D-09 (Phase 12.1-04)
# ---------------------------------------------------------------------------


class InterjectionRequest(BaseModel):
    speaker_character_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    browser_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    during_character_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    mentioned_character_ids: list[str] = Field(default_factory=list)
    text: str = Field(min_length=1, max_length=MAX_RAW_TEXT_LEN)


@router.post("/sessions/{session_id}/creation/interject", response_model=SeqResponse)
async def record_interjection(
    session_id: str, body: InterjectionRequest, request: Request
) -> SeqResponse:
    """남의 차례에 자유롭게 끼어드는 말을 사건으로 남긴다(D-09).

    **신원 대조가 맨 앞이다** — 이미 쿠키를 든 브라우저가 다른 캐릭터인
    척 끼어들 수 없다. **이 말은 어느 캐릭터의 데이터도 바꾸지 않는다**
    (D-09 결정) — 응답 모델(`SeqResponse`)에 바뀐 값 칸을 두지 않는
    것이 그 표현이다.
    """
    identity = read_identity(request, session_id)
    if identity is not None and identity.character_id != body.speaker_character_id:
        print("경고: 신원 검증 실패 — creation/interject 거부", file=sys.stderr)
        raise HTTPException(status_code=403, detail="캐릭터를 다시 선택해 주세요")

    if len(body.mentioned_character_ids) > PARTY_MEMBER_LIMIT:
        raise HTTPException(
            status_code=400,
            detail=f"언급 대상은 {PARTY_MEMBER_LIMIT}명을 넘을 수 없다(안전 상한)",
        )

    actor = request.app.state.registry.get_or_create(session_id)
    try:
        seq = await actor.submit(
            RecordInterjection(
                speaker_character_id=body.speaker_character_id,
                browser_id=body.browser_id,
                during_character_id=body.during_character_id,
                mentioned_character_ids=tuple(body.mentioned_character_ids),
                text=body.text,
            )
        )
    except RosterAlreadyLocked as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except CommandRejected as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SequenceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return SeqResponse(seq=seq)


# ---------------------------------------------------------------------------
# 자기소개 진행 — 안내 · 지목 · 되묻기 (D-03/D-05/D-06, 12.1-03)
# ---------------------------------------------------------------------------


def _unfinished_candidates(state: GameState) -> tuple[str, ...]:
    """진행 중인데 아직 완성되지 않은 사람의 닫힌 목록.

    **대화의 상태 기계는 코드가 돌린다**(12.1-03-PLAN.md § 결정한 열린
    지점 ①) — 에이전트에게 묻지 않는다. `state.creation_step_values`의
    키에서 `character_id`를 뽑고 `state.created_characters`에 아직 없는
    사람만 남긴다. 순서는 그 사람이 만들기 항목을 처음 제출한 순서를
    보존한다(딕셔너리 삽입 순서 = 사건 순번 오름차순).

    아직 항목을 하나도 제출하지 않은 사람은 이 목록에 못 들어간다 —
    플랫폼이 아는 유일한 참가자 식별 통로가 `CompleteCreationStep`의
    `character_id`이기 때문이다(방을 여는 사람이 정한 인원수와 실제
    참가자 식별자는 다른 정보다).
    """
    seen: list[str] = []
    for character_id, _step_id in state.creation_step_values:
        if character_id not in state.created_characters and character_id not in seen:
            seen.append(character_id)
    return tuple(seen)


def _transcript_for(state: GameState, character_ids: tuple[str, ...]) -> tuple[str, ...]:
    """참가자들이 지금까지 낸 자유 서술 값을 대화록 모양으로 편다.

    `creation_step_values`에서 `text_value`가 있는 항목만 뽑는다 — 숫자
    배치·주사위 굴림 결과는 서사가 아니므로 대화록에 안 싣는다. 플레이어가
    쓴 원문이므로 `fence_player_text()`를 지난다(SAFE-03) — 새 방어 로직을
    발명하지 않는다.
    """
    lines: list[str] = []
    for (character_id, _step_id), fold in state.creation_step_values.items():
        if character_id not in character_ids:
            continue
        if fold.text_value:
            lines.append(f"{character_id}: {fence_player_text(fold.text_value)}")
    return tuple(lines)


def _required_steps_filled(state: GameState, rulebook: Rulebook, character_id: str) -> bool:
    """룰북 최소선(`required=True`)이 채워졌는지 코드가 직접 본다(D-05
    아래층) — GM 재량(위층, `judge_hooks`)과는 다른 층의 판단이다."""
    for step in rulebook.creation_steps:
        if step.required and (character_id, step.step_id) not in state.creation_step_values:
            return False
    return True


def _fallback_intro_for(state: GameState, rulebook: Rulebook, character_id: str) -> str:
    """AI 정리가 두 번 실패했을 때 쓸 기본 한 줄 소개(CHAR-03/D-10).

    `provides_display_name`인 항목의 값(표시 이름)과, 그 항목이 아닌
    첫 `free_text` 항목의 첫 문장을 이어 붙인다. 한 줄 소개가 아예 없는
    상태를 만들지 않는다 — CHAR-03이 "자동으로 만들어진다"를 요구한다.
    """
    entity = state.created_characters.get(character_id)
    display_name = entity.display_name if entity is not None else character_id

    first_sentence = ""
    for step in rulebook.creation_steps:
        if step.kind != "free_text" or step.provides_display_name:
            continue
        fold = state.creation_step_values.get((character_id, step.step_id))
        if fold is not None and fold.text_value:
            first_sentence = fold.text_value.strip().splitlines()[0][:200]
            break

    if first_sentence:
        return f"{display_name} — {first_sentence}"
    return display_name


def _resolve_creation_gm_provider(request: Request) -> tuple[Provider, str]:
    """`creation_gm` 역할의 제공자·모델을 고른다 — 기존 호출부(`declare()`
    등)와 같은 방식이다. 설정에 없으면 `ROLE_FALLBACKS`가 `master_gm`을
    물려준다. 새 선택 경로를 만들지 않는다."""
    choices = load_config(request.app.state.agent_config_path)
    provider: Provider = request.app.state.provider_resolver("creation_gm", choices, os.environ)
    return provider, choices["creation_gm"].model


class AnnounceCreationRequest(BaseModel):
    rulebook_id: str = Field(default=DUNGEONWORLD_LIKE_ID, max_length=MAX_ID_LEN)


class AnnounceCreationResponse(BaseModel):
    message: str


@router.post("/sessions/{session_id}/creation/announce", response_model=AnnounceCreationResponse)
async def announce_creation(
    session_id: str, body: AnnounceCreationRequest, request: Request
) -> AnnounceCreationResponse:
    """GM이 룰북이 선언한 필수 항목을 자연스러운 문장으로 안내한다(D-03).

    특정 룰북의 항목 이름은 이 경로 어디에도 하드코딩되어 있지 않다 —
    `rulebook.creation_steps` 선언에서 그대로 나온다(CHAR-01). GM 호출이
    실패해도 `announce_requirements`가 내부에서 폴백 문구로 떨어지므로
    이 경로는 500을 내지 않는다(ARCH-05).
    """
    actor = request.app.state.registry.get_or_create(session_id)
    if actor.state.party_roster is not None:
        raise HTTPException(status_code=409, detail="파티 명단이 이미 잠겼다")

    try:
        rulebook = get_rulebook(body.rulebook_id)
    except UnknownRulebook as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        provider, model = _resolve_creation_gm_provider(request)
    except _AGENT_RESOLUTION_ERRORS as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    message = await asyncio.to_thread(announce_requirements, rulebook, provider, model)
    return AnnounceCreationResponse(message=message)


class NominateSpeakerRequest(BaseModel):
    rulebook_id: str = Field(default=DUNGEONWORLD_LIKE_ID, max_length=MAX_ID_LEN)


class NominateSpeakerResponse(BaseModel):
    character_id: str
    say: str


@router.post("/sessions/{session_id}/creation/nominate", response_model=NominateSpeakerResponse)
async def nominate_creation_speaker(
    session_id: str, body: NominateSpeakerRequest, request: Request
) -> NominateSpeakerResponse:
    """GM이 아직 자기소개를 안 끝낸 사람 중에서 다음 차례를 지목한다(D-06).

    아직 안 끝난 사람의 닫힌 목록은 `GameState`에서 이 경로가 직접
    계산한다 — 에이전트에게 묻지 않는다. 목록이 비면 409(D-06 empty),
    인원이 아직 확정되지 않았으면 409(차례라는 개념 자체가 인원 확정
    이후에만 성립한다). AI가 후보 목록 밖을 지목하면
    `CreationGmContractViolation`이 나고, 이 경로는 그것을 흡수해 후보
    첫 번째로 폴백하며 500을 내지 않는다(ARCH-05).
    """
    actor = request.app.state.registry.get_or_create(session_id)
    state = actor.state
    if state.party_roster is not None:
        raise HTTPException(status_code=409, detail="파티 명단이 이미 잠겼다")
    if state.party_size_fixed is None:
        raise HTTPException(status_code=409, detail="인원이 아직 확정되지 않아 차례가 없다")

    candidates = _unfinished_candidates(state)
    if not candidates:
        raise HTTPException(status_code=409, detail="아직 자기소개를 안 끝낸 사람이 없다")

    transcript = _transcript_for(state, candidates)

    try:
        provider, model = _resolve_creation_gm_provider(request)
    except _AGENT_RESOLUTION_ERRORS as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        nomination = await asyncio.to_thread(
            nominate_speaker, candidates, transcript, provider, model
        )
    except CreationGmContractViolation as exc:
        print(f"경고: creation_gm 지목이 계약을 어겼다 — {exc}", file=sys.stderr)
        first = candidates[0]
        return NominateSpeakerResponse(
            character_id=first, say=f"{first} 님, 이야기를 들려주시겠어요?"
        )

    return NominateSpeakerResponse(character_id=nomination.character_id, say=nomination.say)


class CreationFollowUpRequest(BaseModel):
    character_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    rulebook_id: str = Field(default=DUNGEONWORLD_LIKE_ID, max_length=MAX_ID_LEN)


class CreationFollowUpResponse(BaseModel):
    needs_more: bool
    question: str | None
    required_steps_filled: bool


@router.post("/sessions/{session_id}/creation/follow-up", response_model=CreationFollowUpResponse)
async def creation_follow_up(
    session_id: str, body: CreationFollowUpRequest, request: Request
) -> CreationFollowUpResponse:
    """GM이 방금 나온 이야기에 더 물을 것이 있는지 판단한다(D-05 위층).

    **신원 대조가 맨 앞이다**(`confirm()`이 이미 쓰는 순서 규율,
    TRUST-02/D-04) — 이미 쿠키를 든 브라우저가 다른 캐릭터로 되묻기를
    제출하려 하면 403(T-12.1-19). 아직 쿠키가 없는 참가자(완성 전)는 이
    검사를 그대로 통과한다 — `/creation/step`이 이미 쓰는 것과 같은 신원
    대조 범위다.

    `required_steps_filled`는 GM 재량(위층)과 별개로 코드가 `GameState`
    에서 직접 계산한 룰북 최소선 충족 여부다(D-05 아래층). GM 호출이
    계약을 어기면(`CreationGmContractViolation`) 되묻지 않는 것으로
    폴백하고 500을 내지 않는다(ARCH-05).
    """
    identity = read_identity(request, session_id)
    if identity is not None and identity.character_id != body.character_id:
        print("경고: 신원 검증 실패 — creation/follow-up 거부", file=sys.stderr)
        raise HTTPException(status_code=403, detail="캐릭터를 다시 선택해 주세요")

    actor = request.app.state.registry.get_or_create(session_id)
    state = actor.state
    if state.party_roster is not None:
        raise HTTPException(status_code=409, detail="파티 명단이 이미 잠겼다")

    try:
        rulebook = get_rulebook(body.rulebook_id)
    except UnknownRulebook as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    required_steps_filled = _required_steps_filled(state, rulebook, body.character_id)
    step_labels = tuple(step.label for step in rulebook.creation_steps)
    transcript = _transcript_for(state, (body.character_id,))

    try:
        provider, model = _resolve_creation_gm_provider(request)
    except _AGENT_RESOLUTION_ERRORS as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        follow_up = await asyncio.to_thread(judge_hooks, step_labels, transcript, provider, model)
    except CreationGmContractViolation as exc:
        print(f"경고: creation_gm 되묻기가 계약을 어겼다 — {exc}", file=sys.stderr)
        return CreationFollowUpResponse(
            needs_more=False, question=None, required_steps_filled=required_steps_filled
        )

    return CreationFollowUpResponse(
        needs_more=follow_up.needs_more,
        question=follow_up.question,
        required_steps_filled=required_steps_filled,
    )


# ---------------------------------------------------------------------------
# GM 정리·한 줄 소개(CHAR-03/D-10) · 동의 관문과 부분 재진행(D-11)
# (Phase 12.1-04)
# ---------------------------------------------------------------------------


class WrapUpCreationRequest(BaseModel):
    rulebook_id: str = Field(default=DUNGEONWORLD_LIKE_ID, max_length=MAX_ID_LEN)


class CharacterIntroBody(BaseModel):
    character_id: str
    intro: str


class WrapUpCreationResponse(BaseModel):
    say: str
    intros: list[CharacterIntroBody]


@router.post("/sessions/{session_id}/creation/wrap-up", response_model=WrapUpCreationResponse)
async def wrap_up_creation(
    session_id: str, body: WrapUpCreationRequest, request: Request
) -> WrapUpCreationResponse:
    """전원 완성 뒤 GM이 정리하고 캐릭터마다 한 줄 소개를 낸다(CHAR-03/D-10).

    아직 전원이 완성되지 않았으면 409. 완성된 캐릭터 전원에 대해
    `CreateCharacter`를 `one_line_intro`와 함께 **다시 제출**해
    `character_created`를 갱신한다(같은 `character_id`로 다시 기록되고
    접을 때 나중 것이 이긴다) — 새 사건 종류를 만들지 않는 방법이 이것이다.
    **별도 입력 장치를 만들지 않는다** — 이 경로가 CHAR-03을 만족하는
    유일한 자리다.

    **「전원 완성」의 판정 기준은 `party_size_fixed`(룰북 권장 인원)가
    아니라 `_unfinished_candidates`다** — 12.1-CONTEXT.md D-08이 「명단과
    출석은 다르다」를 명시한다(정원이 안 차도 진행한다, D22). 룰북 권장
    범위 안에서 방을 열었어도 실제 참가자가 그보다 적을 수 있다 — 그
    경우에도 「시작한 사람 전원이 끝났는가」만 보면 된다. 아직 아무도
    안 만들었으면(참가자가 하나도 없으면) 정리할 것이 없으므로 이것도
    409다.
    """
    actor = request.app.state.registry.get_or_create(session_id)
    state = actor.state
    if state.party_roster is not None:
        raise HTTPException(status_code=409, detail="파티 명단이 이미 잠겼다")
    if not state.created_characters:
        raise HTTPException(status_code=409, detail="아직 완성된 캐릭터가 없다")
    if _unfinished_candidates(state):
        raise HTTPException(status_code=409, detail="아직 자기소개를 안 끝낸 사람이 있다")

    try:
        rulebook = get_rulebook(body.rulebook_id)
    except UnknownRulebook as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    character_ids = tuple(state.created_characters)
    fallback_intros = tuple(
        (character_id, _fallback_intro_for(state, rulebook, character_id))
        for character_id in character_ids
    )
    transcript = _transcript_for(state, character_ids)

    try:
        provider, model = _resolve_creation_gm_provider(request)
    except _AGENT_RESOLUTION_ERRORS as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        result = await asyncio.to_thread(wrap_up, fallback_intros, transcript, provider, model)
    except CreationGmContractViolation as exc:
        print(f"경고: creation_gm 정리가 계약을 어겼다 — {exc}", file=sys.stderr)
        result = CreationGmWrapUp(
            intros=fallback_intros, say="다들 준비되셨나요? 이렇게 게임을 진행할까요?"
        )

    intro_by_id = dict(result.intros)
    for character_id in character_ids:
        entity = state.created_characters[character_id]
        try:
            await actor.submit(
                CreateCharacter(
                    character_id=character_id,
                    browser_id=state.occupied_by.get(character_id, ""),
                    rulebook_id=entity.rulebook_id,
                    one_line_intro=intro_by_id.get(character_id, entity.display_name),
                )
            )
        except RosterAlreadyLocked as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except CommandRejected as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except SequenceConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return WrapUpCreationResponse(
        say=result.say,
        intros=[
            CharacterIntroBody(character_id=character_id, intro=intro)
            for character_id, intro in result.intros
        ],
    )


class ConsentRequest(BaseModel):
    character_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    browser_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    agree: bool
    step_id: str | None = Field(default=None, max_length=MAX_ID_LEN)


class ConsentResponse(BaseModel):
    locked: bool
    party_roster: list[str] | None = None
    reopened_step_id: str | None = None
    message: str | None = None


@router.post("/sessions/{session_id}/creation/consent", response_model=ConsentResponse)
async def record_creation_consent(
    session_id: str, body: ConsentRequest, request: Request
) -> ConsentResponse:
    """동의 표시(D-10)와 「아니요」를 통한 부분 재진행(D-11)을 처리한다.

    **신원 대조가 맨 앞이다** — 남의 캐릭터로 동의를 보낼 수 없다
    (T-12.1-24). `agree=true`면 동의가 집계되고, 전원 동의가 모이면
    같은 요청 안에서 명단이 잠긴다(액터가 내부에서
    `LockPartyRoster`를 재귀 제출한다). `agree=false`면 `step_id`가
    필수이고 그 사람의 그 항목 하나만 다시 열린다 — **앞서 받은 동의는
    전부 무효**가 된다(D-11). 이 경로에 「명단에서 사람을 뺀다」는
    없다 — `ReopenCreationStep`은 항목 하나를 다시 여는 것이지 명단을
    바꾸지 않는다(D-11 경계, D-08).
    """
    identity = read_identity(request, session_id)
    if identity is not None and identity.character_id != body.character_id:
        print("경고: 신원 검증 실패 — creation/consent 거부", file=sys.stderr)
        raise HTTPException(status_code=403, detail="캐릭터를 다시 선택해 주세요")

    actor = request.app.state.registry.get_or_create(session_id)

    if not body.agree:
        if not body.step_id:
            raise HTTPException(
                status_code=400, detail="동의하지 않으면 다시 열 항목(step_id)이 필요하다"
            )
        try:
            await actor.submit(
                ReopenCreationStep(
                    character_id=body.character_id,
                    browser_id=body.browser_id,
                    step_id=body.step_id,
                )
            )
        except RosterAlreadyLocked as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except CommandRejected as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except SequenceConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return ConsentResponse(
            locked=False,
            reopened_step_id=body.step_id,
            message=(
                f"{body.step_id!r} 항목이 다시 열렸다 — 다시 채우고 나면 GM이"
                " 다시 정리해서 다시 묻는다."
            ),
        )

    try:
        await actor.submit(
            RecordConsent(character_id=body.character_id, browser_id=body.browser_id, agree=True)
        )
    except RosterAlreadyLocked as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except CommandRejected as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SequenceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    state = actor.state
    locked = state.party_roster is not None
    return ConsentResponse(
        locked=locked,
        party_roster=list(state.party_roster) if locked else None,
    )
