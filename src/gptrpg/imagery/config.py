"""그림 기능 설정 — 환경 변수에서 읽고, 기본값은 「꺼짐」이다.

**기본값이 꺼짐인 이유:** 이 기능은 매 턴 로컬 GPU를 2~4초 점유하고 모델
가중치로 메모리 약 7GB를 문다. 실험 세션에서 재려는 것은 진행자 AI의
재미(H1)와 원가(H5)이므로, 그림이 그 측정에 끼어들지 않는 상태가 기본이어야
한다. 켜는 것은 명시적인 선택이다.

환경 변수를 직접 읽지 않고 `Mapping`을 받는 이유는 `agents.config`와 같다 —
시험이 실제 환경을 건드리지 않고 설정을 갈아 끼울 수 있어야 한다.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from gptrpg.imagery.styles import DEFAULT_STYLE, unknown_style_fallback

ENABLE_ENV: Final = "GPTRPG_IMAGERY"
DIR_ENV: Final = "GPTRPG_IMAGERY_DIR"
STYLE_ENV: Final = "GPTRPG_IMAGERY_STYLE"
STEPS_ENV: Final = "GPTRPG_IMAGERY_STEPS"
SIZE_ENV: Final = "GPTRPG_IMAGERY_SIZE"
MODEL_ENV: Final = "GPTRPG_IMAGERY_MODEL"

DEFAULT_MEDIA_DIR: Final = Path(".gptrpg/media")
DEFAULT_MODEL: Final = "stabilityai/sdxl-turbo"
DEFAULT_STEPS: Final = 4
DEFAULT_SIZE: Final = 512

TRUE_VALUES: Final = frozenset({"1", "true", "yes", "on"})

MAX_STEPS: Final = 12
"""Turbo 의 정상 범위는 1~4다. 그 위는 느려지기만 하고 좋아지지 않으므로
설정 실수를 막는 상한만 둔다."""


@dataclass(frozen=True)
class ImageryConfig:
    """그림 기능의 전체 설정. 만들어진 뒤에는 바뀌지 않는다."""

    enabled: bool
    media_dir: Path
    style: str
    steps: int
    size: int
    model: str


def imagery_config_from_env(env: Mapping[str, str]) -> ImageryConfig:
    """환경 변수 사전에서 설정을 읽는다. **어떤 값이 틀려도 예외를 던지지 않는다.**

    숫자 칸에 숫자가 아닌 값이, 그림체 칸에 모르는 이름이 들어오면 기본값으로
    돌아간다 — 설정 오타 하나로 서버가 뜨지 않는 것보다, 기본값으로 돌면서
    게임이 굴러가는 편이 실험 당일에 낫다. 켜짐/꺼짐만은 오타가 곧 「꺼짐」이라
    조용히 켜지는 일이 없다.
    """
    return ImageryConfig(
        enabled=env.get(ENABLE_ENV, "").strip().lower() in TRUE_VALUES,
        media_dir=Path(env.get(DIR_ENV) or DEFAULT_MEDIA_DIR),
        style=unknown_style_fallback(env.get(STYLE_ENV) or DEFAULT_STYLE),
        steps=_positive_int(env.get(STEPS_ENV), DEFAULT_STEPS, MAX_STEPS),
        size=_positive_int(env.get(SIZE_ENV), DEFAULT_SIZE, 2048),
        model=env.get(MODEL_ENV) or DEFAULT_MODEL,
    )


def _positive_int(raw: str | None, default: int, maximum: int) -> int:
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if value < 1 or value > maximum:
        return default
    return value
