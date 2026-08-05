"""그림 생성 층 — 로컬 SDXL Turbo 로 장면 삽화와 캐릭터 초상화를 만든다.

**이 층은 `agents`와 같은 자리에 있다**(.importlinter contract:2). `agents`가
글자를 만드는 외부 모델 호출이라면 이 층은 그림을 만드는 로컬 모델 호출이고,
둘 다 같은 성질을 공유한다 — 느리고, 실패할 수 있고, **사건을 쓸 수단이
없어야 한다.** `agents`와 똑같이 `event_log`·`session_actor`를 import하지
않으므로(contract:4) 그림이 게임 상태를 건드릴 통로가 구조적으로 없다.
그림을 사건으로 남기는 유일한 통로는 `web`이 반환값을 받아 명령으로
조립하는 것뿐이다.

**프롬프트에 AI를 쓰지 않는다.** 서사 문장은 한국어인데 SDXL의 CLIP 텍스트
인코더는 한국어를 사실상 읽지 못한다. 번역을 위해 언어 모델을 한 번 더
부르면 그 호출이 `ai_invoked`로 남아 H5(원가)와 MEAS-02(지연) 측정에
그림 기능의 비용이 섞여 든다 — 실험이 재려는 것은 진행자 AI의 원가다.
그래서 프롬프트는 **이미 영어인 구조화된 값**(`move_id`·등급 이름·시계
칸 번호)에서 결정적으로 조립한다(`scene_prompt.py`). AI 호출이 늘지 않고,
같은 판정에서 같은 프롬프트가 나오며, 시험이 문자열을 그대로 검증할 수 있다.
"""

from gptrpg.imagery.config import ImageryConfig, imagery_config_from_env
from gptrpg.imagery.renderer import (
    RenderedImage,
    Renderer,
    RendererUnavailable,
    SdxlTurboRenderer,
    seed_for,
)
from gptrpg.imagery.scene_prompt import portrait_prompt, scene_prompt
from gptrpg.imagery.styles import DEFAULT_STYLE, STYLE_NAMES, unknown_style_fallback

__all__ = [
    "DEFAULT_STYLE",
    "STYLE_NAMES",
    "ImageryConfig",
    "RenderedImage",
    "Renderer",
    "RendererUnavailable",
    "SdxlTurboRenderer",
    "imagery_config_from_env",
    "portrait_prompt",
    "scene_prompt",
    "seed_for",
    "unknown_style_fallback",
]
