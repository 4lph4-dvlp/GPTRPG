"""캐릭터 초상화 — 세션 **전에** 미리 뽑아 두는 정적 그림.

매 턴 삽화와 갈라 두는 이유가 셋이다.

1. **런타임 비용이 0이다.** 세션 중에는 이미 만들어진 PNG를 정적 파일로
   내려보낼 뿐이라, 진행 중에 GPU를 쓰지 않는다.
2. **사람이 보고 다시 뽑을 수 있다.** 캐릭터 얼굴은 넷뿐이고 세션 내내
   보이므로, 마음에 들지 않으면 `--force`로 씨앗을 바꿔 다시 만들면 된다.
   매 턴 삽화에는 그럴 기회가 없다.
3. **선·호두는 세션 당일 교체된다**(D-49). 그날 캐릭터를 새로 만들고 나서
   이 명령을 한 번 더 돌리는 것이 절차에 들어간다 — 그래서 이 파일이
   실험 절차 문서(README A절)에 걸릴 수 있는 독립된 명령이어야 했다.

이 모듈이 `web`에 있는 이유: 겉모습 문장은 캐릭터 선언 옆에 있어야 하고
(`characters_data.py`가 바로 옆이다), `cli`는 `web`을 import할 수 없다
(contract:2 — 두 층은 co-equal이다). 그래서 진입점이 `gptrpg` 명령의
하위 명령이 아니라 `python -m gptrpg.web.portraits`다.
"""

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from gptrpg.imagery import (
    ImageryConfig,
    Renderer,
    RendererUnavailable,
    SdxlTurboRenderer,
    imagery_config_from_env,
    portrait_prompt,
    seed_for,
)
from gptrpg.imagery.styles import PORTRAIT_STYLE
from gptrpg.web.characters_data import PLAYER_CHARACTERS

PORTRAIT_DIR_NAME: Final = "portraits"
"""미디어 디렉터리 아래 초상화가 모이는 하위 폴더 이름."""

CHARACTER_APPEARANCES: Final[dict[str, str]] = {
    "bram": (
        "a weathered wandering swordsman, worn leather armor over a travel coat, "
        "plain longsword at the shoulder, scarred jaw, steady unflinching gaze, "
        "East Asian features, middle-aged"
    ),
    "nari": (
        "a lithe hooded scout, dark cloth wrappings, shortbow slung across the back, "
        "lockpicks on a belt cord, watchful narrow eyes half in shadow, "
        "East Asian features, young adult"
    ),
    "seon": (
        "a quiet young scholar, ink-stained layered robes, a bound book of old songs "
        "held against the chest, thoughtful faraway expression, "
        "East Asian features, slight build"
    ),
    "hodu": (
        "a quick-smiling wanderer in a patched travel coat, loose scarf, "
        "easy confident posture mid-sentence, bright open face, "
        "East Asian features, young adult"
    ),
}
"""캐릭터별 겉모습 — **영어로 쓴다.** SDXL의 CLIP 텍스트 인코더가 한국어를
사실상 읽지 못하므로, `CHARACTER_ARCHETYPES`의 한국어 한 줄 소개를 그대로
넘기면 프롬프트가 무시된다. 두 사전은 목적이 다르다: 한쪽은 사람이 읽는
화면 캡션이고, 이쪽은 모델에게 먹이는 그림 지시다.

**`PLAYER_CHARACTERS`와 열쇠가 같아야 한다** — 캐릭터를 추가하고 이 사전을
잊으면 그 캐릭터만 초상화 없이 남는다. `tests/test_web_portraits.py`가 두
사전의 열쇠 집합이 같은지 고정한다.

선·호두 항목은 자리표시자 성격이다(D-49) — 세션 당일 실제로 만들어진
캐릭터에 맞춰 이 문장을 고치고 `--force`로 다시 뽑는다."""


def portrait_relative_path(character_id: str) -> str:
    """미디어 디렉터리 기준 상대 경로. URL 경로와 파일 경로가 같은 문자열이다."""
    return f"{PORTRAIT_DIR_NAME}/{character_id}.png"


def portrait_seed(character_id: str) -> int:
    """캐릭터 식별자에서 씨앗을 결정적으로 만든다 — 같은 캐릭터는 같은 얼굴."""
    return seed_for(f"portrait:{character_id}", 0)


def generate_portraits(
    renderer: Renderer,
    *,
    media_dir: Path,
    character_ids: Sequence[str],
    style: str = PORTRAIT_STYLE,
    force: bool = False,
    seed_offset: int = 0,
) -> list[Path]:
    """초상화를 만들어 파일로 쓰고, 쓴 경로를 순서대로 돌려준다.

    이미 있는 파일은 건너뛴다(`force=True`면 덮어쓴다) — 세션 당일 선·호두만
    다시 뽑을 때 브람·나리를 헛되게 다시 만들지 않기 위해서다.

    `seed_offset`은 「같은 캐릭터, 다른 얼굴」을 얻는 손잡이다. 마음에 드는
    얼굴이 나올 때까지 1, 2, 3… 을 넣어 본다.
    """
    out_dir = media_dir / PORTRAIT_DIR_NAME
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for character_id in character_ids:
        path = media_dir / portrait_relative_path(character_id)
        if path.exists() and not force:
            print(f"건너뜀 (이미 있음): {path}", file=sys.stderr)
            continue
        appearance = CHARACTER_APPEARANCES[character_id]
        image = renderer.render(
            portrait_prompt(appearance, style=style),
            style=style,
            seed=portrait_seed(character_id) + seed_offset,
        )
        path.write_bytes(image.png)
        written.append(path)
        print(f"만듦 ({image.latency_ms}ms, seed={image.seed}): {path}", file=sys.stderr)
    return written


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m gptrpg.web.portraits",
        description="캐릭터 초상화를 미리 만들어 미디어 디렉터리에 저장한다",
    )
    parser.add_argument(
        "--only",
        action="append",
        metavar="캐릭터",
        help=f"이 캐릭터만 만든다(반복 가능). 기본은 넷 전부: {', '.join(PLAYER_CHARACTERS)}",
    )
    parser.add_argument("--force", action="store_true", help="이미 있는 파일도 덮어쓴다")
    parser.add_argument(
        "--seed-offset",
        type=int,
        default=0,
        help="같은 캐릭터의 다른 얼굴을 얻는다 (1, 2, 3… 을 넣어 본다)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """`python -m gptrpg.web.portraits`. 그림 꾸러미가 없으면 2로 끝난다."""
    args = _build_parser().parse_args(argv)
    character_ids = args.only or list(PLAYER_CHARACTERS)
    unknown = [cid for cid in character_ids if cid not in CHARACTER_APPEARANCES]
    if unknown:
        print(f"모르는 캐릭터: {', '.join(unknown)}", file=sys.stderr)
        return 1

    config: ImageryConfig = imagery_config_from_env(os.environ)
    # 초상화는 `GPTRPG_IMAGERY` 켜짐 여부와 무관하게 만든다 — 그 플래그는
    # 「세션 중 매 턴 삽화」를 켜는 스위치이고, 초상화는 세션 전에 손으로
    # 돌리는 준비 작업이다. 둘을 한 플래그로 묶으면 삽화를 끄고 초상화만
    # 쓰는(런타임 부담 0인) 구성이 불가능해진다.
    renderer = SdxlTurboRenderer(config)
    try:
        written = generate_portraits(
            renderer,
            media_dir=config.media_dir,
            character_ids=character_ids,
            force=args.force,
            seed_offset=args.seed_offset,
        )
    except RendererUnavailable as exc:
        print(f"그림을 만들 수 없다: {exc}", file=sys.stderr)
        return 2
    print(f"{len(written)}장 만들었다 (미디어 디렉터리: {config.media_dir})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
