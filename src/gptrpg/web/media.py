"""그림 파일이 디스크에서 어디에 있고 브라우저에서 어떤 주소를 갖는지 —
그 대응을 정하는 한 자리.

`app.py`(정적 마운트), `routes_characters.py`(초상화 주소),
`routes_actions.py`(장면 삽화 저장)가 모두 이 모듈을 본다. 세 자리가 각자
경로 문자열을 지어내면 마운트 지점과 응답에 실리는 주소가 어긋나고, 그
어긋남은 "로컬에서는 되는데 화면에 그림만 안 나온다"로 나타난다.

**경로 조각에 신뢰할 수 없는 입력을 쓰지 않는다.** `session_id`는
`app.validate_session_id`가 `[A-Za-z0-9_-]{1,64}`로 이미 걸러 둔 값이라
상위 경로(`..`, `/`)를 만들 수 없고, `seq`는 정수다. 이 두 값 말고는 파일
이름에 들어가지 않는다 — 특히 **모델이 만든 글자는 경로에 절대 넣지 않는다**
(프롬프트·서사 문장이 파일 이름이 되면 그 자리가 곧 임의 경로 쓰기가 된다).
"""

from pathlib import Path
from typing import Final

MEDIA_URL_PREFIX: Final = "/media"
"""정적 마운트 지점. `app.py`가 `/`(프론트엔드 포괄 경로)보다 **먼저** 걸어야
한다 — 포괄 경로가 먼저 걸리면 이 주소가 프론트엔드 index.html에 삼켜진다."""

SCENE_DIR_NAME: Final = "scenes"


def scene_relative_path(session_id: str, seq: int) -> str:
    """장면 삽화의 미디어 디렉터리 기준 상대 경로.

    세션별 폴더로 나눈다 — 두 세션(EXP-03)의 그림이 한 폴더에 섞이면 1세션
    기록만 따로 보관하거나 지우는 일이 어려워진다.
    """
    return f"{SCENE_DIR_NAME}/{session_id}/{seq:06d}.png"


def media_url(relative_path: str) -> str:
    """미디어 상대 경로를 브라우저가 쓸 주소로 바꾼다."""
    return f"{MEDIA_URL_PREFIX}/{relative_path}"


def media_file_path(media_dir: Path, relative_path: str) -> Path:
    """미디어 상대 경로를 실제 파일 경로로 바꾸고, 부모 폴더를 만들어 둔다."""
    path = media_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
