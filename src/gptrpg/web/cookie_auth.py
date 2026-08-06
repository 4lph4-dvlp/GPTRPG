"""HMAC 서명 쿠키(D-01) + 두 처리기가 함께 쓰는 신원 조회.

서버 비밀 열쇠 하나로 `gptrpg_character` 쿠키에 서명하고, 한 글자라도
변조되면 검증에서 떨어진다. 서버는 상태를 들지 않는다 — 쿠키 자체가
서명된 진실이다.

**이 모듈의 어떤 예외·로그 문구에도 쿠키 값·비밀 열쇠·서명을 넣지 않는다**
(QUAL-05). 애초에 이 모듈은 예외를 던지지 않고 `None`을 돌려주는 것이
실패 모드다 — `routes_characters.my_character()`가 이미 "조용히
`selected:false`로 떨어진다"는 관례를 갖고 있고(옛 형식 쿠키를 예외로
터뜨리지 않는다), 이 모듈이 그 관례를 이어받는다.

`CookieIdentity`/`read_identity`가 여기 있는 이유는 순환 import를 피하기
위해서다 — `routes_characters.py`는 `MAX_ID_LEN` 재사용을 위해
`routes_actions.py`를 import하고(QUAL-04), `routes_actions.py`는 신원 조회를
위해 이 모듈을 import한다. 신원 조회 함수를 `routes_characters.py`에 두면
두 라우트 모듈이 서로를 import하는 순환이 생긴다 — 이 모듈(`cookie_auth.py`)은
어느 라우트 모듈도 import하지 않으므로 순환이 생기지 않는다.
"""

import base64
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from pathlib import Path

from fastapi import Request

_DIGESTMOD = "sha256"

COOKIE_NAME = "gptrpg_character"

COOKIE_SECRET_FILENAME = "cookie_secret"
"""`.gptrpg/` 디렉터리 안에 두는 비밀 열쇠 파일 이름 — `.gptrpg/events.db`
(`app.py`의 기본값)와 같은 자리다. `.gitignore:7`의 `.gptrpg/`가 이미 이
디렉터리 전체를 덮으므로 새 gitignore 항목이 필요 없다."""


def load_or_create_secret(
    path: Path, *, env_var: str = "GPTRPG_COOKIE_SECRET", environ: dict = os.environ
) -> bytes:
    """환경변수가 있으면 그것을 우선한다(D-02). 없으면 파일에서 읽거나 새로 만든다.

    새로 만든 열쇠는 파일에 저장해 다음 실행에서 재사용된다 — 서버를 껐다
    켜도 아무도 쫓겨나지 않는다(D-02). 밖에서 준 열쇠(`GPTRPG_COOKIE_SECRET`)가
    있으면 파일을 아예 만들지 않고 그 값을 그대로 쓴다.
    """
    if env_var in environ:
        return environ[env_var].encode("utf-8")
    if path.is_file():
        return path.read_bytes()
    secret = secrets.token_bytes(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(secret)
    return secret


def new_browser_id() -> str:
    """브라우저(사람) 식별자를 새로 만든다 — 고른 캐릭터와 분리된 신원(D-03)."""
    return secrets.token_urlsafe(16)


def sign_cookie(payload: dict, *, secret: bytes) -> str:
    """페이로드를 서명한다. 반환값은 `base64url(payload).hex(hmac)` 형태의
    단일 문자열이다 — 점 하나로 나뉜 두 조각이라 `json.loads`로 그대로
    읽히지 않는다(TRUST-01)."""
    body = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).rstrip(b"=")
    signature = hmac.new(secret, body, digestmod=_DIGESTMOD).hexdigest()
    return f"{body.decode('ascii')}.{signature}"


def verify_cookie(raw: str, *, secret: bytes) -> dict | None:
    """서명이 안 맞거나 형식이 깨지면 조용히 `None`을 돌려준다.

    서명 검증이 실패했을 때 서명 없는 본문을 믿는 경로로 조용히 떨어지지
    않는다 — 검증 실패는 언제나 「고른 적 없음」이다. `hmac.compare_digest`만
    쓴다 — 타이밍 공격에 노출되는 평범한 `==` 비교는 쓰지 않는다.
    """
    try:
        body, signature = raw.rsplit(".", 1)
        expected = hmac.new(secret, body.encode("ascii"), digestmod=_DIGESTMOD).hexdigest()
    except (ValueError, UnicodeEncodeError):
        return None
    if not hmac.compare_digest(expected, signature):
        return None
    try:
        padded = body + "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


@dataclass(frozen=True)
class CookieIdentity:
    """서명 쿠키에서 검증되어 나온 신원 두 칸 — 브라우저 식별자와 고른 캐릭터(D-03)."""

    browser_id: str
    character_id: str


def read_identity(request: Request, session_id: str) -> CookieIdentity | None:
    """요청의 서명 쿠키를 검증해 `CookieIdentity`를 돌려준다.

    쿠키가 없거나, 서명이 깨졌거나, 다른 세션 것이거나, 칸이 모자라면
    조용히 `None`을 돌려준다 — 예외를 던지지 않는다. 이 함수가 이 프로젝트의
    유일한 신원 검증 경로다(`routes_characters.my_character`와
    `routes_actions.declare`/`confirm`이 전부 이 함수를 거친다) — 검증 경로가
    두 벌이면 한쪽만 고쳐질 수 있다.
    """
    raw = request.cookies.get(COOKIE_NAME)
    if raw is None:
        return None
    payload = verify_cookie(raw, secret=request.app.state.cookie_secret)
    if payload is None:
        return None
    if payload.get("session_id") != session_id:
        return None
    browser_id = payload.get("browser_id")
    character_id = payload.get("character_id")
    if not isinstance(browser_id, str) or not isinstance(character_id, str):
        return None
    return CookieIdentity(browser_id=browser_id, character_id=character_id)
