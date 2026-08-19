"""목록·시트·선택·조회 네 경로. **시트 주소에는 쓰기 처리기가 하나도 없다.**

처리기는 전부 `async def`다 — 저장소를 만지지 않는 경로라도
`routes_events.py`와 관례를 섞지 않는다. 모든 경로는 `gptrpg.web.app`이
라우터를 거는 시점에 `dependencies=[Depends(validate_session_id)]`로 건
`validate_session_id`를 거친다(이 모듈이 `app.py`를 다시 import하면 순환
import가 생기므로, 여기서는 그 함수를 모른다).

`Entity`/`StatEntry`는 pydantic `BaseModel`이 아니라 표준 `dataclass`라
`GameEvent`처럼 응답 모델로 그대로 못 쓴다 — `dataclasses.asdict`로 사전을
만들어 `StatEntryView`/`CharacterSheetView`에 넣는다. 칸 이름은 한 글자도
다르게 짓지 않는다(`entity_id`/`display_name`/`rulebook_id`/`stats`,
`name`/`current`/`max`/`depleted_effect_ref`) — 이름이 갈리면 화면과 규칙
코어가 같은 것을 다른 말로 부르게 된다.

**신뢰 모델(D-01, TRUST-01):** 서버에 세션 저장소나 토큰 발급기를 두지
않는다 — 상태는 서명된 쿠키 자체에 있다. `gptrpg_character` 쿠키는 서버
비밀 열쇠 하나로 HMAC 서명되어(`gptrpg.web.cookie_auth`), 한 글자라도
변조되면 검증에서 떨어져 「고른 적 없음」이 된다. 「같은 방 네 명이 링크
하나를 나눠 가진 것」(D-42)이라는 물리적 신뢰 전제는 그대로이지만, 이제는
그 안에서도 남의 캐릭터를 사칭하는 쿠키를 손으로 써 넣을 수 없다. 계정·결제는
이 마일스톤의 범위 밖이다. 쿠키에 `Secure` 속성을 걸지 않는 것은 M0 실험
한정 판단이다: 이 실험은 같은 방에서 HTTPS 없이 돌 가능성이 높고, 켜면
쿠키가 아예 저장되지 않는다. 공개 인터넷에 이 코드를 올릴 때는 반드시 그
속성을 켜야 한다(`set_cookie`의 `secure` 인자). **이 판단은 M0 실험
한정이다 — M1의 실제 계정 체계로 그대로 가져가면 안 된다.**
"""

import sys
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from gptrpg.event_log.store import SequenceConflict
from gptrpg.rules_core.entities import Entity, StatEntry
from gptrpg.rules_core.reducer import GameState
from gptrpg.rules_core.resource_change import ResourceOp, resolve_character_stats
from gptrpg.rules_core.rulebook import Rulebook
from gptrpg.rulebooks import get_rulebook
from gptrpg.session_actor.actor import AlreadyOccupied, CommandRejected, OccupyCharacter
from gptrpg.session_actor.projection import rebuild_state_from_events
from gptrpg.web.cookie_auth import (
    COOKIE_NAME,
    new_browser_id,
    read_identity,
    sign_cookie,
    verify_cookie,
)
from gptrpg.web.media import MEDIA_URL_PREFIX
from gptrpg.web.portraits import portrait_relative_path
from gptrpg.web.routes_actions import MAX_ID_LEN

router = APIRouter()

COOKIE_MAX_AGE_S = 60 * 60 * 24 * 14
"""14일 — 실험이 1주 간격 두 세션(EXP-03)이라 그 사이를 여유 있게 덮어야
한다."""


class StatEntryView(BaseModel):
    """`StatEntry`의 여덟 칸 그대로 — 칸 이름을 한 글자도 다르게 짓지 않는다.

    `form == "none"`인 축은 이 모델 자체가 아니라 **응답 조립 단계**
    (`_visible_stats`)에서 걸러진다 — 프론트엔드가 조건부로 숨기는 방식이면
    응답 JSON 문자열에 축 이름이 그대로 실려 나가 「완전히 사라진다」가
    문자 그대로 깨진다(RULE-12 성공 기준 2, 11-RESEARCH.md Pitfall 2)."""

    name: str
    form: str
    current: int | None = None
    max: int | None = None
    depleted_effect_ref: str | None = None
    slot_values: list[str | None] | None = None
    tags: list[str] | None = None
    none_kind: str | None = None


class CharacterSheetView(BaseModel):
    """`Entity`의 네 칸 그대로 — 칸 이름을 한 글자도 다르게 짓지 않는다.

    `stats`는 `entity.stats` 전체가 아니라 `_visible_stats`가 「안 쓴다」로
    선언된 축을 제외한 결과다 — 그 제외는 이 뷰가 만들어지기 **전**에
    서버 쪽에서 끝난다."""

    entity_id: str
    display_name: str
    rulebook_id: str
    stats: list[StatEntryView]


def _visible_stats(stats: tuple[StatEntry, ...], rulebook: Rulebook) -> tuple[StatEntry, ...]:
    """`stats`에서 「안 쓴다」로 선언된 축을 제외하고 순서 그대로
    돌려준다(RULE-12 성공 기준 2).

    두 신호를 둘 다 확인한다 — 룰북이 그 이름의 축을 `form="none"`으로
    선언했는지, 그리고 그 상태값 자신의 `StatEntry.form`이 `"none"`인지.
    (등록 시점의 `validate_entity_axes`가 이미 둘이 어긋나면 등록 자체를
    거부하므로 정상 등록된 개체라면 두 신호는 항상 일치하지만, 이 함수는
    그 전제에 기대지 않고 독립적으로 둘 다 본다.) `stats`를 훑는 순서를
    그대로 유지한다 — 「선언 순서를 다시 정렬하지 않는다」 관례와 같은
    이유다.

    **`stats`는 시작값(`entity.stats`)이 아니라 `_current_stats`가 접어
    만든 지금 값이다(RULE-06, D-65, 12-01)** — 마지막 단계는 여전히
    이 "안 쓴다" 필터라는 것은 안 바뀐다.

    **이 제외는 서버 쪽 책임이다.** 프론트엔드가 조건부 렌더링으로 같은
    축을 숨기는 방식으로 구현하면, 이 함수를 거치지 않은 원본 데이터가
    이미 응답 JSON 문자열에 축 이름을 실어 보낸 뒤라 「완전히 사라진다」가
    깨진다(11-RESEARCH.md Pitfall 2).
    """
    axes_by_name = {axis.name: axis for axis in rulebook.resource_axes}
    visible: list[StatEntry] = []
    for stat in stats:
        if stat.form == "none":
            continue
        axis = axes_by_name.get(stat.name)
        if axis is not None and axis.form == "none":
            continue
        visible.append(stat)
    return tuple(visible)


def _current_stats(character_id: str, entity: Entity, state: GameState) -> tuple[StatEntry, ...]:
    """entity.stats(시작값)와 `GameState.character_resource_ops`에서 이
    `character_id`에 해당하는 축별 이력을 뽑아 `resolve_character_stats`에
    넘겨 지금 값을 만든다(RULE-06, D-65).

    `state.character_resource_ops`의 키는 `(character_id, axis)`이고, 이
    `character_id`는 항상 짧은 식별자("bram" 등)다 — `entity.entity_id`
    ("player.bram")가 아니다. 세션 상태 계층 전체(`GameState.declare_owners`
    등)가 이 형식을 쓴다 — `RecordResourceChange`도 `identity.character_id`
    (짧은 식별자)를 그대로 싣는다.
    """
    ops: dict[str, tuple[ResourceOp, ...]] = {}
    for (op_character_id, axis_name), axis_ops in state.character_resource_ops.items():
        if op_character_id != character_id:
            continue
        ops[axis_name] = axis_ops
    return resolve_character_stats(entity.stats, ops)


class CharacterSummaryView(BaseModel):
    """입장 화면용 한 줄 요약(12.1-05부터 이 세션에서 만들어진 캐릭터 기준).

    `portrait_url`은 요약에만 있고 시트(`CharacterSheetView`)에는 없다. 시트는
    `Entity`의 네 칸을 그대로 옮기는 그릇이고(D-20이 확정한 네 칸), 초상화는
    룰북이 정하는 것이 아니라 이 실험 화면이 붙인 그림이다 — `archetype`을
    `Entity`에 넣지 않은 것과 같은 이유로 시트에도 넣지 않는다. `archetype`은
    `character_created` 사건의 `one_line_intro`에서 온다(CHAR-03) — GM이
    정리하며 자동으로 만든 한 줄 소개가 그대로 이 요약 자리에 들어간다.
    """

    character_id: str
    display_name: str
    archetype: str
    portrait_url: str | None = None
    """초상화가 실제로 파일로 있을 때만 채워진다. 없으면 `None`이고, 화면은
    그 경우 이름·소개만 그린다 — 초상화를 아직 안 뽑았다고 입장 화면이
    깨지지 않아야 한다(그림은 있으면 좋은 것이다)."""


class SelectCharacterRequest(BaseModel):
    character_id: str = Field(min_length=1, max_length=MAX_ID_LEN)


class SelectCharacterResponse(BaseModel):
    selected: bool
    character_id: str


class MyCharacterResponse(BaseModel):
    selected: bool
    character_id: str | None = None


@router.get(
    "/sessions/{session_id}/characters",
    response_model=list[CharacterSummaryView],
)
async def get_characters(session_id: str, request: Request) -> list[CharacterSummaryView]:
    """입장 화면용 캐릭터 목록 — **이 세션에서 실제로 만들어진 캐릭터만**
    돌려준다(CHAR-02, D-12). 아무도 안 만들었으면 빈 목록이다(CHAR-02 empty)
    — 완성된 캐릭터를 즉시 집어드는 정적 목록은 제품 코드 어디에도 없다.

    순서는 `GameState.created_characters`(사건에서 접은 「이 세션에서 만들어진
    캐릭터」)의 삽입 순서 그대로다 — 파이썬 딕셔너리는 삽입 순서를 보존하고,
    같은 캐릭터의 `character_created`가 재제출돼도(GM 정리가 `one_line_intro`
    만 갱신, Phase 12.1-04) 기존 키 갱신은 자리를 옮기지 않으므로 「먼저
    완성한 순서」가 그대로 유지된다.

    `archetype`은 `Entity`가 아니라 `character_created` 사건의
    `one_line_intro`에서 직접 온다 — `Entity`에 그 칸을 두지 않는다(CHAR-04).
    `GameState`도 이 값을 따로 담지 않으므로(파생 칸을 늘리지 않는다) 사건을
    한 번 더 훑어 캐릭터별 마지막 값을 뽑는다 — `created_characters`가 같은
    방식(딕셔너리 갱신 = 나중 값이 이긴다)으로 마지막 stats를 담는 것과 같은
    규칙이다.

    초상화 파일이 있는 캐릭터에만 `portrait_url`을 채운다 — 파일 존재를 여기서
    한 번 확인하고, 없으면 `None`으로 둔다. 화면이 404 나는 `<img>`를 그리게
    두지 않기 위해서다(12.1-05부터 동적 캐릭터는 애초에 초상화 파일이 없다 —
    `web/portraits.py` 모듈 도크스트링의 알려진 한계 참조).
    """
    media_dir = request.app.state.imagery_config.media_dir
    store = request.app.state.store
    events = store.read_events(session_id)
    state = rebuild_state_from_events(session_id, events)
    intros: dict[str, str] = {}
    for event in events:
        if event.event_type == "character_created":
            intros[event.character_id] = event.one_line_intro
    return [
        CharacterSummaryView(
            character_id=character_id,
            display_name=entity.display_name,
            archetype=intros.get(character_id, entity.display_name),
            portrait_url=_portrait_url_if_present(media_dir, character_id),
        )
        for character_id, entity in state.created_characters.items()
    ]


def _portrait_url_if_present(media_dir: Path, character_id: str) -> str | None:
    relative = portrait_relative_path(character_id)
    if not (media_dir / relative).is_file():
        return None
    return f"{MEDIA_URL_PREFIX}/{relative}"


@router.get(
    "/sessions/{session_id}/characters/{character_id}",
    response_model=CharacterSheetView,
)
async def get_character_sheet(
    session_id: str, character_id: str, request: Request
) -> CharacterSheetView:
    """캐릭터 시트를 읽기 전용으로 돌려준다(RIG-05).

    이 주소에는 `GET` 처리기 하나만 등록되어 있다 — `PUT`/`PATCH`/`DELETE`/
    `POST`를 보내면 FastAPI가 등록되지 않은 메서드로 판단해 405를 돌려준다.
    「쓰기 경로가 없다」가 이렇게 시험으로 증명 가능한 사실이 된다.

    **응답이 돌려주는 값은 시작값이 아니라 지금 값이다(RULE-06, D-65,
    12-01).** `request.app.state.store`에서 이 세션의 사건을 읽고
    `rebuild_state_from_events`로 상태를 접은 뒤, `_current_stats`(시작값 +
    접은 자원 변화) → `_visible_stats`(「안 쓴다」 축 제외) 순서로 통과시킨다
    — 순서가 뒤집히면 `_visible_stats`가 이미 걸러낸 축의 변화 이력이
    `_current_stats`에서 다시 살아날 여지가 생긴다. 이 경로에는 여전히
    쓰기 처리기가 하나도 없다 — 사건은 다른 라우트가 쓰고, 이 라우트는
    그 사건을 다시 접어 읽기만 한다.

    **12.1-05부터 시작값의 출처는 `GameState.created_characters`다** —
    `character_created` 사건이 기록한 `Entity`(만들기 완료 산출물)가
    시작값이고, 만들어지지 않은 `character_id`는 404다(CHAR-02 empty와
    같은 「없다」와 「조회 실패」 구분).
    """
    store = request.app.state.store
    events = store.read_events(session_id)
    state = rebuild_state_from_events(session_id, events)
    entity = state.created_characters.get(character_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="그런 캐릭터가 없다")
    rulebook = get_rulebook(entity.rulebook_id)
    current_stats = _current_stats(character_id, entity, state)
    return CharacterSheetView(
        entity_id=entity.entity_id,
        display_name=entity.display_name,
        rulebook_id=entity.rulebook_id,
        stats=[StatEntryView(**asdict(stat)) for stat in _visible_stats(current_stats, rulebook)],
    )


@router.post(
    "/sessions/{session_id}/select-character",
    response_model=SelectCharacterResponse,
)
async def select_character(
    session_id: str,
    body: SelectCharacterRequest,
    request: Request,
    response: Response,
) -> SelectCharacterResponse:
    """캐릭터 선택을 서명 쿠키에 남긴다(D-01/D-42/D-43). 알려진 캐릭터가
    아니면 400, 이미 다른 브라우저가 점유한 캐릭터면 409(D-05).

    이미 유효한 쿠키를 들고 온 브라우저는 그 안의 `browser_id`를 그대로
    재사용한다 — 재접속이 새 사람이 되면 「본인 재접속은 그대로 통과한다」
    (D-05)가 성립하지 않는다. 유효한 쿠키가 없거나 다른 세션 것이면 새
    `browser_id`를 발급한다.

    **점유 제출이 쿠키 굽기보다 먼저다** — `declare()`가 `actor.submit`을
    먼저 부르고 그 다음에 진행하는 것과 같은 결이다. 순서가 뒤집히면
    점유에 실패한 브라우저가 쿠키를 들고 나가, 다음 요청에서 신원은
    통과하는데 점유는 없는 반쪽 상태가 된다.

    **새 쿠키를 받는 유일한 문이 이 경로다.** `declare`/`confirm` 쪽 D-14는
    따로 손대지 않는다 — 옛 세션의 브라우저는 서명 쿠키가 없고(그때는
    서명 자체가 없었다) 08-01이 declare/confirm에 유효 쿠키를 요구하게
    만들었으므로 이미 403으로 막힌다. 이 경로만 옛 세션에 대해 닫으면
    된다(D-14, T-08-11).

    **12.1-05부터 「알려진 캐릭터」는 이 세션에서 만들어진 캐릭터다** —
    `GameState.created_characters`에 없는 `character_id`는 400이다. 완성된
    캐릭터를 미리 보여주고 고르게 하는 목록은 어디에도 없다(CHAR-02).
    """
    store = request.app.state.store
    state = rebuild_state_from_events(session_id, store.read_events(session_id))
    if body.character_id not in state.created_characters:
        raise HTTPException(status_code=400, detail="그런 캐릭터가 없다")

    identity = read_identity(request, session_id)
    browser_id = identity.browser_id if identity is not None else new_browser_id()

    actor = request.app.state.registry.get_or_create(session_id)
    try:
        await actor.submit(
            OccupyCharacter(character_id=body.character_id, browser_id=browser_id)
        )
    except AlreadyOccupied:
        pass  # 본인 재접속 — 성공으로 진행한다(D-05).
    except CommandRejected as exc:
        # 거부는 서버 기록에만 한 줄 남긴다(D-04) — 이 줄에도 browser_id를
        # 넣지 않는다(QUAL-05).
        print("경고: 캐릭터 점유 거부 — select-character", file=sys.stderr)
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
    return SelectCharacterResponse(selected=True, character_id=body.character_id)


@router.get(
    "/sessions/{session_id}/my-character",
    response_model=MyCharacterResponse,
)
async def my_character(session_id: str, request: Request) -> MyCharacterResponse:
    """쿠키에 남은 선택을 읽는다. 서명이 깨졌거나 다른 세션 것이거나 모르는
    캐릭터는 전부 조용히 `selected: false`로 떨어진다 — 파싱·검증 실패를
    예외로 터뜨리지 않는다. 위조되었거나 낡은 쿠키를 가진 브라우저가 화면을
    못 여는 것이 더 나쁘다.

    **12.1-05부터 「모르는 캐릭터」는 이 세션의 `GameState.created_characters`
    에 없는 캐릭터다.**
    """
    raw = request.cookies.get(COOKIE_NAME)
    if raw is None:
        return MyCharacterResponse(selected=False, character_id=None)
    payload = verify_cookie(raw, secret=request.app.state.cookie_secret)
    if payload is None:
        return MyCharacterResponse(selected=False, character_id=None)
    if payload.get("session_id") != session_id:
        return MyCharacterResponse(selected=False, character_id=None)
    character_id = payload.get("character_id")
    if not isinstance(character_id, str):
        return MyCharacterResponse(selected=False, character_id=None)
    store = request.app.state.store
    state = rebuild_state_from_events(session_id, store.read_events(session_id))
    if character_id not in state.created_characters:
        return MyCharacterResponse(selected=False, character_id=None)
    return MyCharacterResponse(selected=True, character_id=character_id)
