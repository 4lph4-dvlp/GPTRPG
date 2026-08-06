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

from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from gptrpg.web.characters_data import get_character, list_characters
from gptrpg.web.cookie_auth import COOKIE_NAME, new_browser_id, sign_cookie, verify_cookie
from gptrpg.web.media import MEDIA_URL_PREFIX
from gptrpg.web.portraits import portrait_relative_path
from gptrpg.web.routes_actions import MAX_ID_LEN

router = APIRouter()

COOKIE_MAX_AGE_S = 60 * 60 * 24 * 14
"""14일 — 실험이 1주 간격 두 세션(EXP-03)이라 그 사이를 여유 있게 덮어야
한다."""


class StatEntryView(BaseModel):
    """`StatEntry`의 네 칸 그대로 — 칸 이름을 한 글자도 다르게 짓지 않는다."""

    name: str
    current: int
    max: int | None = None
    depleted_effect_ref: str | None = None


class CharacterSheetView(BaseModel):
    """`Entity`의 네 칸 그대로 — 칸 이름을 한 글자도 다르게 짓지 않는다."""

    entity_id: str
    display_name: str
    rulebook_id: str
    stats: list[StatEntryView]


class CharacterSummaryView(BaseModel):
    """입장 화면용 한 줄 요약 — `characters_data.CharacterSummary`를 옮긴 것.

    `portrait_url`은 요약에만 있고 시트(`CharacterSheetView`)에는 없다. 시트는
    `Entity`의 네 칸을 그대로 옮기는 그릇이고(D-20이 확정한 네 칸), 초상화는
    룰북이 정하는 것이 아니라 이 실험 화면이 붙인 그림이다 — `archetype`을
    `Entity`에 넣지 않은 것과 같은 이유로 시트에도 넣지 않는다.
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
    """입장 화면용 캐릭터 목록. `list_characters()`의 선언 순서를 그대로 옮긴다.

    초상화 파일이 있는 캐릭터에만 `portrait_url`을 채운다 — 파일 존재를 여기서
    한 번 확인하고, 없으면 `None`으로 둔다. 화면이 404 나는 `<img>`를 그리게
    두지 않기 위해서다.
    """
    media_dir = request.app.state.imagery_config.media_dir
    return [
        CharacterSummaryView(
            character_id=summary.character_id,
            display_name=summary.display_name,
            archetype=summary.archetype,
            portrait_url=_portrait_url_if_present(media_dir, summary.character_id),
        )
        for summary in list_characters()
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
async def get_character_sheet(session_id: str, character_id: str) -> CharacterSheetView:
    """캐릭터 시트를 읽기 전용으로 돌려준다(RIG-05).

    이 주소에는 `GET` 처리기 하나만 등록되어 있다 — `PUT`/`PATCH`/`DELETE`/
    `POST`를 보내면 FastAPI가 등록되지 않은 메서드로 판단해 405를 돌려준다.
    「쓰기 경로가 없다」가 이렇게 시험으로 증명 가능한 사실이 된다.
    """
    entity = get_character(character_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="그런 캐릭터가 없다")
    return CharacterSheetView(**asdict(entity))


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
    아니면 400.

    이미 유효한 쿠키를 들고 온 브라우저는 그 안의 `browser_id`를 그대로
    재사용한다 — 재접속이 새 사람이 되면 「본인 재접속은 그대로 통과한다」
    (D-05)가 성립하지 않는다. 유효한 쿠키가 없거나 다른 세션 것이면 새
    `browser_id`를 발급한다.
    """
    entity = get_character(body.character_id)
    if entity is None:
        raise HTTPException(status_code=400, detail="그런 캐릭터가 없다")

    secret = request.app.state.cookie_secret
    browser_id: str | None = None
    raw = request.cookies.get(COOKIE_NAME)
    if raw is not None:
        existing = verify_cookie(raw, secret=secret)
        if existing is not None and existing.get("session_id") == session_id:
            candidate = existing.get("browser_id")
            if isinstance(candidate, str):
                browser_id = candidate
    if browser_id is None:
        browser_id = new_browser_id()

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
    if not isinstance(character_id, str) or get_character(character_id) is None:
        return MyCharacterResponse(selected=False, character_id=None)
    return MyCharacterResponse(selected=True, character_id=character_id)
