"""캐릭터 만들기 네 경로 — 인원 확정 · 항목 값 확정 · 완성 · 명단 잠금
(D-03~D-09, Phase 12.1).

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

import sys

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from gptrpg.event_log.store import SequenceConflict
from gptrpg.rules_core.rulebook import EntityAxisMismatch, InvalidCreationStep, InvalidResourceAxis
from gptrpg.rulebooks import UnknownRulebook
from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID
from gptrpg.session_actor.actor import (
    AlreadyOccupied,
    CommandRejected,
    CompleteCreationStep,
    CreateCharacter,
    FixPartySize,
    LockPartyRoster,
    OccupyCharacter,
    RosterAlreadyLocked,
)
from gptrpg.web.cookie_auth import COOKIE_NAME, read_identity, sign_cookie
from gptrpg.web.routes_actions import MAX_ID_LEN, MAX_RAW_TEXT_LEN

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
    """방을 여는 사람이 이 세션의 인원을 확정한다(D-01). 재확정은 없다."""
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
