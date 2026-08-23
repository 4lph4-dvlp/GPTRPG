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
(CHAR-02) — 제품에 남아 있던 유일한 정적 캐릭터 상수 모듈은 12.1-05가
지웠다(브람·나리·선·호두 넷은 이제 `tests/fixtures/characters.py`에서
시험 재료로만 산다). 이 라우터는 애초에 그 모듈을 import한 적이 없다.

**`complete` 경로가 지키는 순서** (`routes_characters.select_character`의
「점유 제출이 쿠키 굽기보다 먼저」 규율을 그대로 옮긴다): ① 신원을 먼저
대조한다(이미 쿠키가 있으면 그 캐릭터와 요청의 캐릭터가 달라야 403 — 첫
캐릭터를 만드는 브라우저는 아직 쿠키가 없으므로 이 검사를 그대로
통과한다, `select_character`가 첫 선택에서 쿠키 없이도 통과하는 것과 같은
결) ② `CreateCharacter` 제출 ③ 그 직후 같은 요청 안에서 `OccupyCharacter`
제출(`AlreadyOccupied`는 성공으로 통과 — 본인 재접속, D-05) ④ 마지막에
쿠키를 굽는다. 순서가 뒤집히면 완성은 됐는데 점유가 없는 반쪽 상태가
남는다.

**12.1-05 이후:** `GET /my-character`·`GET /characters/{id}`
(`routes_characters.py`)도 이제 이 계획이 만드는 세션 스코프 캐릭터
(`GameState.created_characters`)를 본다 — 정적 목록으로 갈라져 있던 네
소비처(목록·시트·선택·판정 컨텍스트·초상화)가 전부 같은 출처를 보게
됐다(D-12). 이 라우터는 여전히 사건 기록(`GET /events`에 남는
`character_occupied`)과 쿠키로 「자동 점유가 실제로 일어났다」를 증명한다.
"""

import asyncio
import os
import sys
import time

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from gptrpg.agents.config import ConfigNotFound, InvalidAgentConfig, load_config
from gptrpg.agents.context import PARTY_MEMBER_LIMIT
from gptrpg.agents.creation_gm import (
    CreationGmContractViolation,
    CreationGmFollowUp,
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
    CreationStepDecl,
    CreationStepKind,
    EntityAxisMismatch,
    InvalidCreationStep,
    InvalidResourceAxis,
    PartySizeRange,
    Rulebook,
)
from gptrpg.rulebooks import UnknownRulebook, get_rulebook
from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID
from gptrpg.session_actor.actor import (
    AlreadyGmSpoken,
    AlreadyOccupied,
    ClaimCreationHost,
    CommandRejected,
    CompleteCreationStep,
    CreateCharacter,
    FixPartySize,
    LockPartyRoster,
    OccupyCharacter,
    RecordConsent,
    RecordGmSpoke,
    RecordInterjection,
    ReopenCreationStep,
    RosterAlreadyLocked,
)
from gptrpg.web import creation_state
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


# ---------------------------------------------------------------------------
# 룰북 만들기 항목 선언 조회 (D-05) — 진행 상태를 섞지 않는 순수 GET
# ---------------------------------------------------------------------------


class CreationStepView(BaseModel):
    """`CreationStepDecl`을 얇게 감싼 응답 모델 — 선언의 모든 칸을 그대로
    옮긴다(D-05). 칸을 골라 내리지 않는다 — 화면이 어떤 `kind`의 입력칸을
    그리려면 그 `kind`가 쓰는 칸이 전부 필요하다."""

    step_id: str
    kind: CreationStepKind
    label: str
    required: bool
    provides_display_name: bool
    axis_names: tuple[str, ...]
    options: tuple[str, ...] | None
    pick_count: int | None
    fixed_values: tuple[int, ...] | None
    point_budget: int | None
    per_target_max: int | None
    dice_expr: str | None
    derive_base_axis: str | None
    derive_multiplier: int | None
    derive_offset: int | None
    depends_on: tuple[str, ...]
    default_from: str | None


def _creation_step_view(decl: CreationStepDecl) -> CreationStepView:
    return CreationStepView(
        step_id=decl.step_id,
        kind=decl.kind,
        label=decl.label,
        required=decl.required,
        provides_display_name=decl.provides_display_name,
        axis_names=decl.axis_names,
        options=decl.options,
        pick_count=decl.pick_count,
        fixed_values=decl.fixed_values,
        point_budget=decl.point_budget,
        per_target_max=decl.per_target_max,
        dice_expr=decl.dice_expr,
        derive_base_axis=decl.derive_base_axis,
        derive_multiplier=decl.derive_multiplier,
        derive_offset=decl.derive_offset,
        depends_on=decl.depends_on,
        default_from=decl.default_from,
    )


class PartySizeRangeView(BaseModel):
    """`PartySizeRange`를 그대로 옮기는 얇은 응답 모델(G-12.3-2) — 최소는
    필수, 최대는 상한이 없을 수 있다(`None`)."""

    min_player_characters: int
    max_player_characters: int | None


class CreationDeclarationView(BaseModel):
    """`GET /creation/steps`의 응답 봉투(G-12.3-2) — 룰북이 **선언**한 것
    전부를 담는다: 항목 목록과 인원 범위. 둘 다 세션 중에 안 바뀌는 룰북
    콘텐츠라 같은 자리에서 나온다(D-05가 이 경로를 그렇게 정의했다).
    `party_size_range`는 `None`일 수 있다(룰북이 아직 인원 범위를 선언하지
    않은 경우) — 등록 검사(`validate_registered_rulebooks`)가 등록된
    룰북에 대해서는 이를 막지만, 이 타입은 여전히 열려 있다."""

    steps: list[CreationStepView]
    party_size_range: PartySizeRangeView | None


def _party_size_range_view(range_: PartySizeRange | None) -> PartySizeRangeView | None:
    if range_ is None:
        return None
    return PartySizeRangeView(
        min_player_characters=range_.min_player_characters,
        max_player_characters=range_.max_player_characters,
    )


@router.get("/sessions/{session_id}/creation/steps", response_model=CreationDeclarationView)
async def get_creation_declaration(
    session_id: str,
    rulebook_id: str = Query(default=DUNGEONWORLD_LIKE_ID, max_length=MAX_ID_LEN),
) -> CreationDeclarationView:
    """룰북이 **선언**한 것 전부를 그대로 내려준다(D-05) — 항목 목록과
    인원 범위 둘 다. 항목 목록이 세션 중에 안 바뀌는 것과 똑같이 인원
    범위도 룰북 **콘텐츠**이지 진행 상태가 아니므로 같은 자리에서
    나온다.

    **왜 폴링(`GET /events`)이 아닌가(G-12.3-2)** — 인원 확정 **전에는**
    `GameState.creation_rulebook_id`가 아직 `None`이다(세션의 룰북이
    이 확정과 **함께** 정해진다). 그래서 폴링은 어느 룰북의 범위를
    실어야 할지 알 방법이 구조적으로 없다. 인원 범위는 확정 **전에**
    필요한 값이므로, 확정 전에도 답할 수 있는 이 경로에서 나와야 한다.

    **`party_size_range`가 `None`으로 올 수 있다** — 룰북이 아직 선언을
    안 했을 때다. 등록 검사(`validate_registered_rulebooks`)가 등록된
    룰북에 대해서는 이를 막지만, 이 응답의 타입은 여전히 열려 있다.

    **이 목록은 세션 중에 안 바뀐다** — 1.5초마다 도는 폴링(`GET /events`,
    D-04)에 실으면 안 바뀌는 것을 네 명에게 계속 나르고, AI를 거치는 안내
    응답(`/creation/announce`)에 실으면 AI가 안 돌 때(503) 입력칸을 그릴
    근거조차 없어진다. 그래서 전용 GET 하나로 뗀다.

    `session_id`는 이 경로가 실제로 쓰지 않는다 — 이 경로가 세션 스코프
    라우터(`creation_router`) 아래 있어 URL 모양이 나머지 열 경로와
    같기 때문이다. `get_rulebook`이 순수 조회이고 `GameState`를 읽지
    않으므로 세션이 존재하든 말든 응답은 같다.

    **진행 상태를 섞지 않는다(D-05 경계)** — 이 응답에는 어느 캐릭터가
    무엇을 채웠는지가 들어가지 않는다. 그 값은 폴링(D-04, `GameStateView.
    creation_step_values`)에 있다.

    `rulebook_id` 기본값은 다른 만들기 경로와 같은 `DUNGEONWORLD_LIKE_ID`.
    모르는 `rulebook_id`면 400 + 그 예외 문자열을 `detail`로.
    """
    try:
        rulebook = get_rulebook(rulebook_id)
    except UnknownRulebook as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CreationDeclarationView(
        steps=[_creation_step_view(step) for step in rulebook.creation_steps],
        party_size_range=_party_size_range_view(rulebook.party_size_range),
    )


# ---------------------------------------------------------------------------
# 방장 잡기·승계 (D-11) — 「살아 있다」를 아는 신호로 폴링을 쓸 수 없다
# (폴링은 쿠키 없는 참가자를 식별 못 하는 GET이고 browser_id를 안 싣는다).
# 이 경로 자체가 참가자 브라우저가 주기적으로 자기를 알리는 전용 신호다.
# 배경에서 혼자 도는 장치는 만들지 않는다(D-12 경계) — 서버는 이 요청이
# 올 때만 판정한다.
# ---------------------------------------------------------------------------


class ClaimHostRequest(BaseModel):
    browser_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    character_id: str = Field(default="", max_length=MAX_ID_LEN)
    """이 브라우저가 만들고 있는 캐릭터(D-06 갈래 ①, Phase 12.3-06) —
    비어 있으면 재실 신호만이고 「지금 이 방에 와 있는 사람」에 안 더해진다.
    기본값을 빈 문자열로 둔 이유는 옆 `FixPartySizeRequest.browser_id`와
    같다(화면 없는 호출부·시험·스크립트를 막지 않는다). **다만 그 관대한
    기본값이 곧 1차 검증이 찾은 결함(`fixPartySize`가 이 칸을 빠뜨린 것)의
    모양이었다** — 화면이 이 칸을 실제로 싣는지는
    `frontend/src/api/creationBody.test.ts`가 지킨다."""


class CreationHostResponse(BaseModel):
    you_are_host: bool
    host_claimed: bool
    changed: bool


@router.post("/sessions/{session_id}/creation/host", response_model=CreationHostResponse)
async def claim_creation_host(
    session_id: str, body: ClaimHostRequest, request: Request
) -> CreationHostResponse:
    """방장을 잡거나(이 세션에 가장 먼저 들어온 사람) 승계한다(방장이
    조용해지면, D-11).

    **이 호출 자체가 재실 신호다** — 매번 `mark_browser_seen`을 먼저
    찍는다(순서가 중요하다: 이 요청을 보낸 브라우저 자신은 절대 유휴로
    보이면 안 된다).

    승계 판정: 지금 방장이 `body.browser_id`와 다르면, 그 방장을
    `creation_state.browser_last_seen`으로 조회한다. **`None`이면
    (재시작 직후) 지금 본 것으로만 기록하고 사건을 안 낸다** — 그래야
    재시작 직후 멀쩡한 방장이 애먼 승계를 당하지 않는다(T-12.3-13).
    `HOST_IDLE_S`를 넘겼으면 승계를 제출한다.

    **경쟁에서 진 브라우저에게 오류를 보여줄 이유가 없다** — `CommandRejected`
    /`RosterAlreadyLocked`/`SequenceConflict`를 409로 올리지 않고 삼킨 뒤
    지금 상태로 200을 돌려준다. 응답의 `you_are_host`가 이미 그 사실을
    말한다.

    **`creation_host_browser_id` 값 자체를 응답에 싣지 않는다**(T-12.3-05)
    — 부른 사람에게 「너인가 아닌가」만 답한다.
    """
    creation_state.mark_browser_seen(session_id, body.browser_id)
    if body.character_id:
        creation_state.mark_character_present(session_id, body.character_id)
    actor = request.app.state.registry.get_or_create(session_id)
    changed = False

    if actor.state.party_roster is None:
        current = actor.state.creation_host_browser_id
        try:
            if current is None:
                await actor.submit(
                    ClaimCreationHost(browser_id=body.browser_id, previous_browser_id=None)
                )
                changed = True
            elif current != body.browser_id:
                last_seen = creation_state.browser_last_seen(session_id, current)
                if last_seen is None:
                    creation_state.mark_browser_seen(session_id, current)
                elif time.monotonic() - last_seen > creation_state.HOST_IDLE_S:
                    await actor.submit(
                        ClaimCreationHost(
                            browser_id=body.browser_id, previous_browser_id=current
                        )
                    )
                    changed = True
        except (CommandRejected, SequenceConflict):
            pass

    state = actor.state
    return CreationHostResponse(
        you_are_host=state.creation_host_browser_id == body.browser_id,
        host_claimed=state.creation_host_browser_id is not None,
        changed=changed,
    )


class FixPartySizeRequest(BaseModel):
    player_character_count: int = Field(ge=1)
    rulebook_id: str = Field(default=DUNGEONWORLD_LIKE_ID, max_length=MAX_ID_LEN)
    browser_id: str = Field(default="", max_length=MAX_ID_LEN)
    """방장 관문(T-12.3-11, D-11) 대조용 — 방장이 아직 없으면(아무도
    `/creation/host`를 안 불렀으면) 값과 무관하게 통과한다(기본값을 빈
    문자열로 둔 이유 — 화면이 없는 호출부(시험·스크립트)를 막지
    않는다)."""


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

    **방장 관문(T-12.3-11, D-11)** — 방장이 이미 정해졌으면 그 방장만
    인원을 정할 수 있다(403). 아직 아무도 방장을 안 잡았으면 통과시킨다
    — 그때는 아직 아무도 특권을 갖지 않았으므로 뺏을 것도 없다.
    """
    if body.player_character_count > PARTY_MEMBER_LIMIT:
        raise HTTPException(
            status_code=400,
            detail=f"인원은 {PARTY_MEMBER_LIMIT}명을 넘을 수 없다(안전 상한)",
        )
    actor = request.app.state.registry.get_or_create(session_id)
    host = actor.state.creation_host_browser_id
    if host is not None and host != body.browser_id:
        raise HTTPException(status_code=403, detail="방장만 인원을 정할 수 있어요")
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
    유일한 값이다. **이 값(제출되는 각 항목의 `browser_id`) 자체의 완전한
    위조 방지는 여전히 12.1-03/04(GM이 진행하는 다회 대화, 차례 관리)
    범위다** — 이 트레이서는 한 줄기를 뚫는 것이 목적이라 그 방어를 아직
    완성하지 않는다. (하이재킹 항목이 닫은 것은 이 값이 아니라 그
    **완성 시점의 연속성**이다 — 아래 `complete_creation` 도크스트링
    참조.)

    **CR-01 (12.1-REVIEW.md) 검토 결과 — 여기는 고치지 않는다.** 이
    경로가 다루는 `character_id`는 완성되기 전(`created_characters`에
    없는 동안)에는 정의상 쿠키가 없을 수밖에 없다 — `identity is None`을
    거절하면 정상적인 첫 제출 자체가 막힌다. `/creation/consent`(항상
    이미 완성된 캐릭터만 다룬다)와 `/creation/interject`(완성된 캐릭터
    사칭만 좁게 막는다)와는 상황이 다르다 — **뒤에서 이 검사를 `is None
    or ...`로 "고치지" 말 것.**
    """
    identity = read_identity(request, session_id)
    if identity is not None and identity.character_id != body.character_id:
        print("경고: 신원 검증 실패 — creation/step 거부(쿠키 불일치)", file=sys.stderr)
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

    **CR-01 (12.1-REVIEW.md) 검토 결과 — 여기는 고치지 않는다.** 이
    경로는 쿠키를 **처음으로 발급하는** 자리다(아래 `response.set_cookie`
    참조) — 첫 완성 요청은 정의상 쿠키가 없는 상태에서 온다. `identity is
    None`을 거절하면 첫 완성 자체가 막힌다.

    **하이재킹 항목(12.1-REVIEW.md CR-01 "추가로" 절, 사용자 승인 뒤
    별도 패스로 닫힘) — `_prepare_create_character`가 브라우저 연속성을
    대조한다.** 이 라우트가 쿠키만으로는 완성 전 신원을 대지 못하는
    빈틈을, `session_actor.actor.SessionActor._prepare_create_character`가
    닫는다 — 그 캐릭터의 `creation_step_completed` 사건들이 실제로
    기록한 `browser_id`와 `command.browser_id`가 다르면(=항목을 낸 적
    없는 브라우저가 완성을 시도하면) `CommandRejected`로 409가 난다.
    이 라우트는 그 예외를 그대로 흡수해 아래 `except CommandRejected`가
    409로 옮긴다 — 이 라우트 자신이 추가로 대조할 것은 없다.
    """
    identity = read_identity(request, session_id)
    if identity is not None and identity.character_id != body.character_id:
        print("경고: 신원 검증 실패 — creation/complete 거부(쿠키 불일치)", file=sys.stderr)
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

    **CR-01 (12.1-REVIEW.md) — 쿠키가 없는 요청은 "이미 완성된 캐릭터"
    행세를 할 수 없다.** `/creation/step`과 달리 이 경로가 다루는
    `speaker_character_id`는 두 가지 상태 다 정당하게 올 수 있다 —
    ①아직 한창 자기소개를 만드는 중이라 쿠키가 없는 사람이 자기 이름으로
    끼어드는 경우(정당, 예: 시험
    `test_interjection_is_recorded_with_speaker_and_mentioned`)와
    ②쿠키를 아예 안 보내면서 이미 완성되어 쿠키를 갖고 있어야 할 남의
    `speaker_character_id`를 자칭하는 경우(위조)다. 그래서 다섯 자리 중
    유일하게 이 자리만 "완성 여부"로 갈라 좁게 막는다 — `identity`가
    `None`이어도, 자칭하는 `speaker_character_id`가 `state.created_characters`에
    이미 있으면(=완성돼 쿠키를 받았어야 할 사람이면) 거절한다. 아직
    만드는 중인 사람(①)은 그대로 통과한다 — 그 값의 완전한 위조 방지는
    `/creation/step`과 같은 이유로 이번 패스의 범위 밖이다(12.1-REVIEW.md
    CR-01 "추가로" 항목 참조).
    """
    identity = read_identity(request, session_id)
    actor = request.app.state.registry.get_or_create(session_id)
    if identity is not None and identity.character_id != body.speaker_character_id:
        print("경고: 신원 검증 실패 — creation/interject 거부(쿠키 불일치)", file=sys.stderr)
        raise HTTPException(status_code=403, detail="캐릭터를 다시 선택해 주세요")
    if identity is None and body.speaker_character_id in actor.state.created_characters:
        print(
            "경고: 신원 검증 실패 — creation/interject 거부(쿠키 없음, 완성된 캐릭터 사칭)",
            file=sys.stderr,
        )
        raise HTTPException(status_code=403, detail="캐릭터를 다시 선택해 주세요")

    if len(body.mentioned_character_ids) > PARTY_MEMBER_LIMIT:
        raise HTTPException(
            status_code=400,
            detail=f"언급 대상은 {PARTY_MEMBER_LIMIT}명을 넘을 수 없다(안전 상한)",
        )

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


def _transcript_for(state: GameState, character_ids: tuple[str, ...]) -> tuple[str, ...]:
    """참가자들이 지금까지 낸 자유 서술 값을 대화록 모양으로 편다.

    `creation_step_values`에서 `text_value`가 있는 항목만 뽑는다 — 숫자
    배치·주사위 굴림 결과는 서사가 아니므로 대화록에 안 싣는다. 플레이어가
    쓴 원문이므로 `fence_player_text()`를 지난다(SAFE-03) — 새 방어 로직을
    발명하지 않는다.
    """
    numbered: list[tuple[int, str]] = []
    for (character_id, _step_id), fold in state.creation_step_values.items():
        if character_id not in character_ids:
            continue
        if fold.text_value:
            numbered.append((fold.seq, f"{character_id}: {fence_player_text(fold.text_value)}"))
    # 사람이 그냥 한 말도 대화록에 싣는다(G-12.3-13) — 이게 없으면 GM의
    # 되물음에 말로 답할 방법이 없다. 항목 값과 섞어 **순번 순서**로 편다:
    # 되물음에 대한 답은 질문 뒤에 오므로 순서가 뜻을 가진다.
    for interjection in state.creation_interjections:
        if interjection.speaker_character_id not in character_ids:
            continue
        numbered.append(
            (
                interjection.seq,
                f"{interjection.speaker_character_id}: {fence_player_text(interjection.text)}",
            )
        )
    return tuple(line for _seq, line in sorted(numbered, key=lambda pair: pair[0]))


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


def _gm_dedupe_key(
    kind: str,
    state: GameState,
    character_id: str | None = None,
    candidates: tuple[str, ...] | None = None,
) -> str:
    """「그 시점」을 나타내는 문자열(D-02/D-12) — GM 호출의 입력이 바뀌면
    새 값이 된다. `state.creation_gm_said`에 이미 이 키가 있으면 서버가
    AI를 다시 부르지 않고 기록된 `say`를 그대로 돌려준다.

    네 갈래를 지금 전부 적는다 — 이 계획(12.3-01)은 `announce`만 쓰지만,
    12.3-02가 나머지 셋을 붙일 때 이 규칙을 다시 발명하지 않게 한다.
    """
    if kind == "announce":
        # 세션당 한 번이다 — 인원 확정 뒤 몇 번을 부르든 안내 내용은
        # 같은 룰북 선언에서 나오므로 입력이 바뀌지 않는다.
        return "announce"
    if kind == "nominate":
        # 이 키는 그 호출이 **실제로 쓴** 후보 목록에서 나와야 한다
        # (T-12.3-20, 정확성 문제이지 선택이 아니다, Phase 12.3-06) — 키를
        # 후보 목록과 따로 재계산하면, 첫 사람이 완성돼 사건 기반 목록이
        # 다시 비는 순간 두 번째 지목이 첫 번째 지목과 같은 키로 뭉쳐 지난
        # 지목이 그대로 재사용되고, 이미 완성된 사람을 다시 지목한 꼴이
        # 되어 같은 교착이 되돌아온다. `candidates`가 안 주어지면(다른
        # 호출부·시험 호환) 옛 계산으로 떨어진다.
        cands = candidates if candidates is not None else creation_state.unfinished_candidates(state)
        return "nominate:" + "|".join(cands)
    if kind == "follow_up":
        # 그 사람이 값을 하나 더 내면(만들기 항목이 늘면) 새 되묻기가
        # 가능해진다. 값이 하나도 없으면 0.
        max_seq = 0
        for (fold_character_id, _step_id), fold in state.creation_step_values.items():
            if fold_character_id == character_id:
                max_seq = max(max_seq, fold.seq)
        # 그 사람이 **말을 하나 더 해도** 새 되묻기가 가능해진다
        # (G-12.3-13) — 안 그러면 답을 적어도 키가 그대로라 GM이 같은
        # 질문만 되돌려줘서, 되물음에 답할 길이 구조적으로 막힌다.
        for interjection in state.creation_interjections:
            if interjection.speaker_character_id == character_id:
                max_seq = max(max_seq, interjection.seq)
        return f"follow_up:{character_id}:{max_seq}"
    if kind == "wrap_up":
        # 동의 관문에서 「아니요」로 항목이 다시 채워지면 값이 바뀌어
        # GM이 다시 정리한다(D-11).
        max_seq = max((fold.seq for fold in state.creation_step_values.values()), default=0)
        return "wrap_up:" + str(max_seq)
    raise ValueError(f"모르는 GM 말 갈래: {kind!r}")


class AnnounceCreationRequest(BaseModel):
    rulebook_id: str = Field(default=DUNGEONWORLD_LIKE_ID, max_length=MAX_ID_LEN)


class AnnounceCreationResponse(BaseModel):
    message: str
    seq: int


@router.post("/sessions/{session_id}/creation/announce", response_model=AnnounceCreationResponse)
async def announce_creation(
    session_id: str, body: AnnounceCreationRequest, request: Request
) -> AnnounceCreationResponse:
    """GM이 룰북이 선언한 필수 항목을 자연스러운 문장으로 안내한다(D-03).

    특정 룰북의 항목 이름은 이 경로 어디에도 하드코딩되어 있지 않다 —
    `rulebook.creation_steps` 선언에서 그대로 나온다(CHAR-01). GM 호출이
    실패해도 `announce_requirements`가 내부에서 폴백 문구로 떨어지므로
    이 경로는 500을 내지 않는다(ARCH-05).

    **D-02/D-12 — 사건에 남고, 서버가 한 번만 낸다.** `_gm_dedupe_key`로
    「이미 말했나」를 AI를 부르기 **전에** 본다 — 이미 기록에 있으면
    제공자 해석조차 하지 않는다(제공자 설정이 없어도 화면이 지난 안내를
    볼 수 있어야 한다).
    """
    actor = request.app.state.registry.get_or_create(session_id)
    if actor.state.party_roster is not None:
        raise HTTPException(status_code=409, detail="파티 명단이 이미 잠겼다")

    try:
        rulebook = get_rulebook(body.rulebook_id)
    except UnknownRulebook as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    key = _gm_dedupe_key("announce", actor.state)
    already_said = actor.state.creation_gm_said.get(key)
    if already_said is not None:
        return AnnounceCreationResponse(message=already_said.say, seq=already_said.seq)

    try:
        provider, model = _resolve_creation_gm_provider(request)
    except _AGENT_RESOLUTION_ERRORS as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    message = await asyncio.to_thread(announce_requirements, rulebook, provider, model)
    try:
        seq = await actor.submit(
            RecordGmSpoke(kind="announce", say=message, target_character_id=None, dedupe_key=key)
        )
    except AlreadyGmSpoken as exc:
        # CR-04: 겹친 두 요청이 둘 다 위 `already_said is None`을 보고
        # 여기까지 왔다 — 액터 큐 안의 단락이 두 번째를 잡았으니 첫 번째가
        # 이미 기록한 값을 그대로 재사용한다(AI는 여전히 두 번 불렸을 수
        # 있지만, 기록·최종 상태는 하나로 수렴한다).
        return AnnounceCreationResponse(message=exc.prior.say, seq=exc.prior.seq)
    except RosterAlreadyLocked as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except CommandRejected as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SequenceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return AnnounceCreationResponse(message=message, seq=seq)


class NominateSpeakerRequest(BaseModel):
    rulebook_id: str = Field(default=DUNGEONWORLD_LIKE_ID, max_length=MAX_ID_LEN)


class NominateSpeakerResponse(BaseModel):
    character_id: str
    say: str
    seq: int


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

    **D-02/D-12 — announce와 정확히 같은 모양으로 사건에 남고, 서버가
    한 번만 낸다.** `_gm_dedupe_key`로 「이미 지목했나」를 AI를 부르기
    **전에** 본다 — 후보 목록이 바뀌지 않는 한(누군가 완성되지 않는 한)
    같은 지목을 두 번 안 낸다.
    """
    actor = request.app.state.registry.get_or_create(session_id)
    state = actor.state
    if state.party_roster is not None:
        raise HTTPException(status_code=409, detail="파티 명단이 이미 잠겼다")
    if state.party_size_fixed is None:
        raise HTTPException(status_code=409, detail="인원이 아직 확정되지 않아 차례가 없다")

    # D-06 갈래 ① (Phase 12.3-06) — 사건에서 나온 후보(절대 안 잘림)에
    # 재실 신호만 있는 사람(아직 항목을 안 낸 사람)을 뒤에 더한다. 그래야
    # 완전히 새 세션에서도 첫 지목이 일어난다 — `unfinished_candidates`
    # 하나만 쓰면 아무도 이미 항목을 낸 적이 없어 후보가 영원히 빈다.
    candidates = creation_state.present_candidates(state, session_id)
    if not candidates:
        raise HTTPException(status_code=409, detail="아직 자기소개를 안 끝낸 사람이 없다")

    key = _gm_dedupe_key("nominate", state, candidates=candidates)
    # 이 세션에서 마지막으로 판정된 흘려보냄을 표시로 이어 붙인다 —
    # 「지금 흘려보낸 상태인가」가 아니라 「이 세션에서 마지막으로
    # 흘려보내진 것이 무엇인가」이고, 회복으로 판정이 풀려도 **뒤로 안
    # 돌아간다**(12.3-10). 이미 항목 값을 낸 사람이 흘려보내지면 후보
    # 목록 자체는 안 바뀌므로(그 사람이 앞줄에 그대로 있다), 이 표시가
    # 없으면 서버가 옛 지목을 그대로 되돌려 줘 새 지목 사건이 영원히 안
    # 생긴다(12.3-09, 4차 검증 `missing` ③). 표시가 뒤로 돌아가면(옛
    # 12.3-09 구현) 회복 뒤 이 키가 흘려보내지기 전과 같아져, 리듀서가
    # 영구 보관한 옛 지목 기록이 회복 뒤에도 다시 되돌아온다(5차 검증
    # §CR-01, `12.3-REVIEW.md` CR-01).
    key = key + creation_state.forfeited_nomination_mark(state, session_id)
    already_said = state.creation_gm_said.get(key)
    if already_said is not None and already_said.target_character_id is not None:
        return NominateSpeakerResponse(
            character_id=already_said.target_character_id,
            say=already_said.say,
            seq=already_said.seq,
        )

    transcript = _transcript_for(state, candidates)

    try:
        provider, model = _resolve_creation_gm_provider(request)
    except _AGENT_RESOLUTION_ERRORS as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        nomination = await asyncio.to_thread(
            nominate_speaker, candidates, transcript, provider, model
        )
        character_id, say = nomination.character_id, nomination.say
    except CreationGmContractViolation as exc:
        print(f"경고: creation_gm 지목이 계약을 어겼다 — {exc}", file=sys.stderr)
        character_id = candidates[0]
        say = f"{character_id} 님, 이야기를 들려주시겠어요?"

    try:
        seq = await actor.submit(
            RecordGmSpoke(
                kind="nominate", say=say, target_character_id=character_id, dedupe_key=key
            )
        )
    except AlreadyGmSpoken as exc:
        # CR-04: announce와 같은 이유 — 겹친 두 요청의 두 번째를 큐 안의
        # 단락이 잡았다. `already_said.target_character_id`가 있어야만
        # 재사용하는 위 조회와 같은 불변식을 지킨다(target_character_id는
        # nominate가 항상 채우므로 여기서는 항상 있다).
        prior_target = exc.prior.target_character_id
        if prior_target is not None:
            return NominateSpeakerResponse(
                character_id=prior_target, say=exc.prior.say, seq=exc.prior.seq
            )
        raise HTTPException(status_code=409, detail="이미 기록된 GM 말을 재사용할 수 없다") from exc
    except RosterAlreadyLocked as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except CommandRejected as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SequenceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return NominateSpeakerResponse(character_id=character_id, say=say, seq=seq)


class CreationFollowUpRequest(BaseModel):
    character_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    rulebook_id: str = Field(default=DUNGEONWORLD_LIKE_ID, max_length=MAX_ID_LEN)


class CreationFollowUpResponse(BaseModel):
    needs_more: bool
    question: str | None
    required_steps_filled: bool
    seq: int | None = None
    """되물을 것이 있을 때만 채워진다(D-02 ④) — GM이 아무 말도 안 했으면
    사건을 남기지 않으므로 짝지어질 `seq`가 없다."""


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

    **D-02/D-12 — 되물을 것이 있을 때만 사건에 남는다.** `needs_more=True`면
    announce/nominate와 같은 모양으로 `creation_gm_spoke` 사건에 남고 서버가
    한 번만 낸다. `needs_more=False`(GM이 아무 말도 안 함)면 **사건을 남기지
    않는다** — 대화 줄기에 남길 말이 없고, `RecordGmSpoke`도 빈 `say`를
    거절한다. 이 경우 중복 방지가 굳이 필요하지 않다 — 값이 바뀌지 않는 한
    다시 눌러도 같은 판정이 나오므로 비용은 AI를 한 번 더 부르는 것뿐이다
    (D-14 「갈고리를 놓치지 않는다」는 사람이 「더 말하기」를 고를 때 지켜진다).

    `required_steps_filled`는 GM 재량(위층)과 별개로 코드가 `GameState`
    에서 직접 계산한 룰북 최소선 충족 여부다(D-05 아래층). GM 호출이
    계약을 어기면(`CreationGmContractViolation`) 되묻지 않는 것으로
    폴백하고 500을 내지 않는다(ARCH-05).

    **CR-01 (12.1-REVIEW.md) 검토 결과 — 여기는 고치지 않는다.** 이
    경로는 ①`GameState`를 바꾸는 사건을 하나도 만들지 않고(`actor.submit`
    호출이 없다 — GM이 되물을지만 판단해 응답으로 돌려줄 뿐이다) ②완성
    전(쿠키가 없는) 참가자가 정당하게 부를 수 있다(`/creation/step`과
    같은 문서화된 범위, 위 문단이 스스로 그렇게 적었다 — 실제로 시험
    `test_the_whole_creation_flow_passes_for_two_people_in_order`의 ⑤
    되묻기가 hero-1이 아직 완성되기 **전에** 쿠키 없이 불린다). 상태를
    바꾸지 않으므로 쿠키 없는 요청이 통과해도 남길 수 있는 부수효과가
    없다 — `/creation/consent`·`/creation/interject`(둘 다 사건을
    남기거나 명단 잠금에 영향을 준다)와 위험 등급이 다르다.
    """
    identity = read_identity(request, session_id)
    if identity is not None and identity.character_id != body.character_id:
        print("경고: 신원 검증 실패 — creation/follow-up 거부(쿠키 불일치)", file=sys.stderr)
        raise HTTPException(status_code=403, detail="캐릭터를 다시 선택해 주세요")

    actor = request.app.state.registry.get_or_create(session_id)
    state = actor.state
    if state.party_roster is not None:
        raise HTTPException(status_code=409, detail="파티 명단이 이미 잠겼다")

    try:
        rulebook = get_rulebook(body.rulebook_id)
    except UnknownRulebook as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    required_steps_filled = creation_state.required_steps_filled(
        state, rulebook, body.character_id
    )

    key = _gm_dedupe_key("follow_up", state, body.character_id)
    already_said = state.creation_gm_said.get(key)
    if already_said is not None:
        needs_more = bool(already_said.say.strip())
        return CreationFollowUpResponse(
            needs_more=needs_more,
            question=already_said.say if needs_more else None,
            required_steps_filled=required_steps_filled,
            seq=already_said.seq,
        )

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
        follow_up = CreationGmFollowUp(needs_more=False, question=None)

    if not follow_up.needs_more:
        # 되물을 것이 없으면 GM이 아무 말도 안 한 것이다(D-02 ④) — 대화
        # 줄기에 남길 말이 없으므로 사건을 남기지 않는다(RecordGmSpoke는
        # 빈 say를 거절하기도 한다). 중복 방지도 필요 없다 — 값이 안
        # 바뀐 동안 다시 눌러도 같은 판정(needs_more=False)이 나오므로
        # 비용은 AI를 한 번 더 부르는 것뿐이다.
        return CreationFollowUpResponse(
            needs_more=False, question=None, required_steps_filled=required_steps_filled, seq=None
        )

    try:
        seq = await actor.submit(
            RecordGmSpoke(
                kind="follow_up",
                say=follow_up.question,
                target_character_id=body.character_id,
                dedupe_key=key,
            )
        )
    except AlreadyGmSpoken as exc:
        # CR-04: announce와 같은 이유. `already_said.say`가 채워져 있으므로
        # (RecordGmSpoke가 빈 say를 거절한다) needs_more는 항상 True다.
        return CreationFollowUpResponse(
            needs_more=True,
            question=exc.prior.say,
            required_steps_filled=required_steps_filled,
            seq=exc.prior.seq,
        )
    except RosterAlreadyLocked as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except CommandRejected as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SequenceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return CreationFollowUpResponse(
        needs_more=True,
        question=follow_up.question,
        required_steps_filled=required_steps_filled,
        seq=seq,
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
    seq: int


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
    아니라 `creation_state.unfinished_candidates`다** — 12.1-CONTEXT.md D-08이 「명단과
    출석은 다르다」를 명시한다(정원이 안 차도 진행한다, D22). 룰북 권장
    범위 안에서 방을 열었어도 실제 참가자가 그보다 적을 수 있다 — 그
    경우에도 「시작한 사람 전원이 끝났는가」만 보면 된다. 아직 아무도
    안 만들었으면(참가자가 하나도 없으면) 정리할 것이 없으므로 이것도
    409다.

    **D-02/D-12 — announce/nominate와 정확히 같은 모양으로 사건에 남고,
    서버가 한 번만 낸다.** 완성된 캐릭터 집합이 바뀌지 않는 한(동의
    관문에서 「아니요」로 항목이 다시 채워지지 않는 한) 같은 정리를 두 번
    안 낸다 — 이미 말했으면 `CreateCharacter` 재제출도 건너뛴다(정리
    내용이 안 바뀌었으므로 다시 쓸 값도 없다).
    """
    actor = request.app.state.registry.get_or_create(session_id)
    state = actor.state
    if state.party_roster is not None:
        raise HTTPException(status_code=409, detail="파티 명단이 이미 잠겼다")
    if not state.created_characters:
        raise HTTPException(status_code=409, detail="아직 완성된 캐릭터가 없다")
    if creation_state.unfinished_candidates(state):
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

    key = _gm_dedupe_key("wrap_up", state)
    already_said = state.creation_gm_said.get(key)
    if already_said is not None:
        # 완성된 집합이 바뀌지 않았으면 정리 내용도 안 바뀌었다 — 각
        # 캐릭터의 한 줄 소개는 `fallback_intros`와 같은 계산으로 다시
        # 조립한다(제공자를 다시 부르지 않는다, D-12). `CreateCharacter`
        # 재제출도 건너뛴다 — 첫 호출에서 이미 같은 값으로 기록됐다.
        return WrapUpCreationResponse(
            say=already_said.say,
            intros=[
                CharacterIntroBody(character_id=character_id, intro=intro)
                for character_id, intro in fallback_intros
            ],
            seq=already_said.seq,
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

    try:
        seq = await actor.submit(
            RecordGmSpoke(kind="wrap_up", say=result.say, target_character_id=None, dedupe_key=key)
        )
    except AlreadyGmSpoken as exc:
        # CR-04: announce와 같은 이유. `intros`는 위 `already_said` 이른
        # 반환과 같은 방식으로 `fallback_intros`에서 다시 조립한다 —
        # 제공자를 다시 부르지 않는다(D-12).
        return WrapUpCreationResponse(
            say=exc.prior.say,
            intros=[
                CharacterIntroBody(character_id=character_id, intro=intro)
                for character_id, intro in fallback_intros
            ],
            seq=exc.prior.seq,
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
        seq=seq,
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

    **CR-01 (12.1-REVIEW.md) — 쿠키가 아예 없는 요청도 거절한다.**
    `_process_consent`(`session_actor/actor.py`)는 `character_id`가
    `state.created_characters`에 있어야만 통과시킨다 — 즉 이 경로가
    다루는 캐릭터는 **항상 이미 완성되어 있고, 완성된 순간
    `/creation/complete`가 이미 쿠키를 구웠다**(`complete_creation`
    참조). 따라서 이 경로에는 `/creation/step`처럼 "완성 전이라 쿠키가
    아직 없을 수 있다"는 정당한 경우가 **존재하지 않는다** — 쿠키가
    없으면 그것은 항상 신원을 아예 대지 않고 남의 동의·재오픈을
    위조하려는 시도다. 그래서 다른 다섯 자리 중 이 자리만
    `routes_actions.py`(`declare`/`confirm` 등)가 이미 쓰는 `is None or`
    패턴을 그대로 쓴다(예전에는 `is not None and`라서 쿠키를 안 보내면
    이 대조 전체가 통과됐다).
    """
    identity = read_identity(request, session_id)
    if identity is None or identity.character_id != body.character_id:
        _reason = "쿠키 없음" if identity is None else "쿠키 불일치"
        print(f"경고: 신원 검증 실패 — creation/consent 거부({_reason})", file=sys.stderr)
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
