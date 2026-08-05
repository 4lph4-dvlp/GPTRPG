"""그림체 프리셋 — 던전물 넷 + 초상화용 하나.

**SDXL Turbo 는 CFG(guidance_scale)를 쓰지 않는 distill 모델이라 네거티브
프롬프트가 동작하지 않는다.** 그래서 그림체를 "이건 넣지 마라"로 통제할
수단이 없고, 원하는 화풍을 전부 포지티브 프롬프트에 녹여야 한다. 아래
템플릿이 그 일을 한다 — `{subject}` 자리에 `scene_prompt.py`가 조립한
장면/인물 묘사가 들어간다.

이름이 곧 사건에 남는 값(`SceneIllustrated.style`)이므로 **이미 기록된 이름은
바꾸지 않는다.** 새 화풍은 새 이름으로 추가한다 — 옛 사건의 `style` 값이
사전에서 사라지면 그 사건이 어떤 그림체로 그려졌는지 되짚을 수 없다.
"""

from typing import Final

DEFAULT_STYLE: Final = "dungeon"
"""매 턴 삽화의 기본 그림체. 실험 세션에서 실제로 쓰이는 값이다."""

PORTRAIT_STYLE: Final = "portrait"
"""캐릭터 초상화 전용 — 상반신 구도를 고정해야 시트에서 얼굴이 잘리지 않는다."""

STYLES: Final[dict[str, str]] = {
    "dungeon": (
        "dark fantasy dungeon art, {subject}, torchlit wet stone, "
        "painterly, dramatic chiaroscuro, muted earthy tones, detailed"
    ),
    "dungeon-ink": (
        "grimdark ink illustration, {subject}, heavy black linework, "
        "cross-hatching, sepia and crimson, high contrast, parchment"
    ),
    "dungeon-oil": (
        "classic D&D oil painting, {subject}, vintage 1980s fantasy cover, "
        "visible oil brushwork, warm torchlight, canvas texture"
    ),
    "dungeon-pixel": (
        "16-bit pixel art, {subject}, retro roguelike dungeon, "
        "limited dark palette, dithering, crisp pixels, black outlines"
    ),
    PORTRAIT_STYLE: (
        "dark fantasy portrait, {subject}, head and shoulders, centered, "
        "painterly, torchlit rim light, plain dark background"
    ),
}
"""**길이가 품질의 일부다 — CLIP은 77토큰에서 자른다.**

SDXL의 텍스트 인코더는 77토큰을 넘는 입력의 **뒤쪽을 조용히 버린다**(경고
한 줄만 남는다). 프리셋이 프롬프트 뒤쪽에 오므로, 템플릿이 길면 그림체 지시가
바로 그 잘리는 자리에 놓인다 — 실제로 처음 쓴 판은 43토큰짜리 프리셋이라
장면 조합 5,600개 중 2,617개에서 꼬리("deep shadows, highly detailed, fantasy
RPG illustration")가 잘려 나갔다. 화면에는 아무 오류도 보이지 않고 그림만
어중간해진다.

그래서 각 프리셋은 30토큰 안쪽으로 쓴다. 형용사를 늘리고 싶으면 다른 것을
줄인다 — `tests/test_imagery.py`의 프롬프트 길이 상한 시험이 이 예산을 지킨다."""

STYLE_NAMES: Final = tuple(STYLES)


def apply_style(style: str, subject: str) -> str:
    """프리셋에 묘사를 끼워 최종 프롬프트를 만든다. 모르는 이름이면 `KeyError`.

    모르는 이름을 조용히 기본값으로 바꾸지 않는다 — 잘못된 그림체 이름이
    설정에 들어갔을 때 그림이 다른 화풍으로 조용히 나오는 것보다, 부르는
    자리에서 걸러 사람이 알아채는 편이 낫다. 설정에서 오는 값을 무르게
    받아야 하는 자리는 `unknown_style_fallback`을 쓴다.
    """
    return STYLES[style].format(subject=subject)


def unknown_style_fallback(style: str) -> str:
    """설정에서 온 그림체 이름을 검사해, 모르는 이름이면 기본값으로 되돌린다.

    설정 오타 하나로 서버가 매 턴 예외를 내는 것을 막는 자리다 — 그림은
    있으면 좋은 것이고 없어도 게임은 굴러가야 한다(`web`의 삽화 경로 전체가
    같은 원칙으로 쓰여 있다).
    """
    return style if style in STYLES else DEFAULT_STYLE
