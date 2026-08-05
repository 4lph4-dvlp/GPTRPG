"""FastAPI 앱 조립: 저장소·레지스트리를 한 번만 만들고, 폴링 라우터를 걸고,
`static_dir`가 있으면 마지막에 정적 파일을 마운트한다.

`web`은 `cli`와 co-equal 층이다(.importlinter contract:2) — 서로 import하지
않는다. `session_id` 경로 조각은 이 파일이 신뢰할 수 없는 입력을 처음 받는
자리이고, 이후 계획(04-02·04-03)에서 이 값이 그대로 집계 파일 이름이 되므로
`validate_session_id`가 상위 경로 조각을 차단하는 것이 T-04-05의 유일한
차단 지점이다.

`validate_session_id`는 `events_router`를 거는 지점에서 `dependencies=`로
걸린다(모듈 import가 아니라 router 등록 시점에 연결) — `routes_events.py`가
이 모듈을 다시 import하면 `app.py` → `routes_events.py` → `app.py` 순환
import가 생기므로, 검증 함수는 여기 있고 라우터 쪽은 이 함수를 몰라도
되게 한다.
"""

import asyncio
import os
import re
import sys
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from gptrpg.agents.config import DEFAULT_CONFIG_PATH, resolve_provider
from gptrpg.agents.providers.base import Provider
from gptrpg.event_log.store import EventStore
from gptrpg.imagery import (
    ImageryConfig,
    Renderer,
    RendererUnavailable,
    SdxlTurboRenderer,
    imagery_config_from_env,
)
from gptrpg.session_actor.actor import SessionRegistry
from gptrpg.web.media import MEDIA_URL_PREFIX
from gptrpg.web.routes_actions import router as actions_router
from gptrpg.web.routes_characters import router as characters_router
from gptrpg.web.routes_events import router as events_router

DEFAULT_DB_ENV = "GPTRPG_DB"

SAFE_SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def validate_session_id(session_id: str) -> str:
    """`session_id` 경로 조각이 `[A-Za-z0-9_-]{1,64}`를 벗어나면 400으로 거절한다.

    이 값은 04-02/04-03에서 집계 파일 이름(`.gptrpg/reports/{session_id}.json`)이
    되므로, 상위 경로를 가리키는 조각(`..`, `/`)이 통과하면 임의 경로 쓰기가
    된다 — T-04-05.
    """
    if not SAFE_SESSION_ID.match(session_id):
        raise HTTPException(
            status_code=400,
            detail="세션 식별자가 허용된 글자 범위를 벗어났다",
        )
    return session_id


def create_app(
    *,
    db_path: str | Path,
    static_dir: Path | None = None,
    provider_resolver: Callable[[str, Mapping, Mapping], Provider] = resolve_provider,
    agent_config_path: Path = DEFAULT_CONFIG_PATH,
    imagery_config: ImageryConfig | None = None,
    renderer_factory: Callable[[ImageryConfig], Renderer] = SdxlTurboRenderer,
) -> FastAPI:
    """`EventStore`와 `SessionRegistry`를 lifespan 안에서 한 번만 만든다.

    요청마다 새로 만들면 `SessionRegistry.get_or_create`가 주는 「세션당 액터
    하나」(D-09①) 보장이 요청마다 깨진다.

    `provider_resolver`/`agent_config_path`는 시험 주입 이음매다 — 실제
    운영에서는 기본값(`agents.config.resolve_provider`/`DEFAULT_CONFIG_PATH`)이
    그대로 쓰이고, 시험은 이 두 자리를 갈아 끼워 대역 제공자를 넣는다. 이
    이음매가 없으면 `routes_actions.py`의 HTTP 계층 시험이 실제 제공자
    키와 네트워크를 요구하게 된다.

    `imagery_config`/`renderer_factory`가 그림 쪽의 같은 이음매다. 시험은
    torch 없이 도는 대역 렌더러를 끼워 넣으므로, 그림 기능이 있어도 시험
    묶음이 2.5GB 꾸러미를 요구하지 않는다.
    """
    config = imagery_config if imagery_config is not None else imagery_config_from_env(os.environ)
    renderer = renderer_factory(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        store = EventStore(db_path)
        store.initialize()
        app.state.store = store
        app.state.registry = SessionRegistry(store)
        warm_up_task = _start_renderer_warm_up(config, renderer)
        try:
            yield
        finally:
            if warm_up_task is not None:
                warm_up_task.cancel()
            store.close()

    app = FastAPI(lifespan=lifespan)
    app.state.provider_resolver = provider_resolver
    app.state.agent_config_path = agent_config_path
    app.state.imagery_config = config
    app.state.renderer = renderer
    app.include_router(
        events_router,
        prefix="/api",
        dependencies=[Depends(validate_session_id)],
    )
    app.include_router(
        characters_router,
        prefix="/api",
        dependencies=[Depends(validate_session_id)],
    )
    app.include_router(
        actions_router,
        prefix="/api",
        dependencies=[Depends(validate_session_id)],
    )

    # 그림 파일 마운트는 프론트엔드 포괄 경로보다 **먼저** 걸어야 한다 —
    # 순서가 뒤집히면 `/media/...`가 index.html로 삼켜져 그림 자리마다
    # HTML이 내려간다. 그림 기능이 꺼져 있어도 마운트한다: 초상화만 쓰고
    # 매 턴 삽화는 끄는 구성이 유효하기 때문이다(`portraits.py` 참조).
    #
    # **`check_dir=False`가 중요하다.** 기본값(`True`)은 없는 디렉터리에
    # 마운트하면 그 자리에서 예외를 던지므로 미리 `mkdir`을 해야 하는데,
    # 이 모듈 맨 아래 `app = create_app(...)`가 **import 시점에** 돌기 때문에
    # 그 `mkdir`은 곧 「`gptrpg.web.app`을 import하면 디렉터리가 생긴다」가
    # 된다(시험이 저장소에 흔적을 남긴다). 끄고 나면 디렉터리는 실제로 그림을
    # 쓰는 자리에서만 생기고(`media.media_file_path`·`portraits.py`), 아직
    # 없는 동안 이 경로는 404를 돌려준다 — 그림이 없을 때 맞는 답이다.
    # 서버를 띄운 뒤에 초상화를 뽑아도 다시 시작할 필요가 없다는 뜻도 된다.
    app.mount(
        MEDIA_URL_PREFIX,
        StaticFiles(directory=config.media_dir, check_dir=False),
        name="media",
    )

    if static_dir is not None and static_dir.exists():
        # 맨 마지막에 건다 — 정적 파일 포괄 경로가 먼저 걸리면 /api/*를 삼킨다.
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")

    return app


def _start_renderer_warm_up(config: ImageryConfig, renderer: Renderer) -> asyncio.Task | None:
    """그림 기능이 켜져 있으면 모델을 배경에서 미리 올린다.

    기동을 막지 않는다 — 가중치를 올리는 데 6~7초(처음이면 6.9GB 내려받기)가
    걸리므로 여기서 `await`하면 그만큼 서버가 요청을 받지 못한다. 배경으로
    돌려 두면 첫 턴이 끝날 무렵에는 준비가 끝나 있고, 안 끝났더라도 첫
    삽화만 늦어질 뿐이다(삽화는 응답 뒤에 만들어진다).

    실패는 경고 한 줄로 끝낸다. 그림 꾸러미가 없거나 모델을 못 내려받았다고
    게임 서버가 뜨지 않아서는 안 된다.
    """
    if not config.enabled:
        return None
    warm_up = getattr(renderer, "warm_up", None)
    if warm_up is None:
        return None

    async def _warm_up() -> None:
        try:
            await asyncio.to_thread(warm_up)
        except RendererUnavailable as exc:
            print(f"경고: 그림 모델을 올리지 못했다 — 삽화 없이 진행한다: {exc}", file=sys.stderr)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - 배경 준비 실패가 서버를 멈추게 하지 않는다
            print(f"경고: 그림 모델 준비 중 예상 못한 실패 — 삽화 없이 진행한다: {exc}", file=sys.stderr)

    return asyncio.create_task(_warm_up())


app = create_app(
    db_path=os.environ.get(DEFAULT_DB_ENV, ".gptrpg/events.db"),
    static_dir=Path("frontend/dist"),
)
"""uvicorn 진입점: `uv run uvicorn gptrpg.web.app:app --host 0.0.0.0 --port 8000`."""
