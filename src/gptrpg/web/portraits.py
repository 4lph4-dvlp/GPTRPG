"""캐릭터 초상화 — 세션 **전에** 손으로 미리 뽑아 두는 정적 그림.

매 턴 삽화와 갈라 두는 이유가 둘이다.

1. **런타임 비용이 0이다.** 세션 중에는 이미 만들어진 PNG를 정적 파일로
   내려보낼 뿐이라, 진행 중에 GPU를 쓰지 않는다.
2. **사람이 보고 다시 뽑을 수 있다.** 마음에 들지 않으면 `--force`로
   씨앗을 바꿔 다시 만들면 된다. 매 턴 삽화에는 그럴 기회가 없다.

이 모듈이 `web`에 있는 이유: `cli`는 `web`을 import할 수 없다(contract:2 —
두 층은 co-equal이다). 그래서 진입점이 `gptrpg` 명령의 하위 명령이 아니라
`python -m gptrpg.web.portraits`다.

**알려진 한계(12.1-05부터, D-12) — 동적으로 만들어진 캐릭터에 초상화가
없다.** 12.1(캐릭터 만들기)이 캐릭터를 세션 중 대화로 동적으로 만들게
하면서, `CHARACTER_APPEARANCES`(아래)가 그리는 대상(브람·나리·선·호두)은
더 이상 제품에 존재하지 않는 캐릭터가 됐다 — 그 넷은 이제
`tests/fixtures/characters.py`에 시험 재료로만 산다. 동적 캐릭터의
초상화를 뽑으려면 「자유 서술(한국어) → 영어 초상화 프롬프트」 변환이라는
새 AI 경로가 필요한데, 그 경로는 아직 없다(12.1-RESEARCH.md가 새로 발견한
구멍 — `12.1-CONTEXT.md` 어디에도 이 요구가 없다). **이번 계획(12.1-05)은
`PLAYER_CHARACTERS`와의 결합만 끊고 그 변환은 만들지 않는다** — 화면은
초상화가 없는 캐릭터를 이미 견딘다(`routes_characters._portrait_url_if_present`
가 파일이 없으면 `None`을 돌려주고, 목록 조회는 그대로 성공한다).

**이 모듈을 지우지 않는 이유:** `CHARACTER_APPEARANCES`의 영어 프롬프트
문장과 렌더러 배선(`generate_portraits`/`SdxlTurboRenderer`)은 다음
단계가 재사용할 자산이다 — 「자유 서술 → 초상화 문구」 변환이 생기면
그 변환의 출력을 여기 `generate_portraits`에 그대로 넘기면 된다. 지금
당장은 `CHARACTER_APPEARANCES`가 옛 정적 넷의 영어 문장만 담은 채로
남는다(수동으로 `--only`를 넘겨 그 넷의 초상화를 다시 뽑는 용도로는
여전히 동작한다).
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

**시험 재료(`tests/fixtures/characters.py`의 `PLAYER_CHARACTERS`)와 열쇠가
같다** — `tests/test_imagery.py`가 두 집합의 열쇠가 같은지 고정한다. 이
넷은 제품 코드가 아니라 시험 재료이므로(D-12), 이 값이 유지되는 것은
「이 파일을 지우지 않고 남긴다」는 위 모듈 도크스트링의 판단을 지지하는
근거일 뿐 — 제품이 이 넷 중 하나를 사용자에게 보여준다는 뜻이 아니다.

선·호두 항목은 자리표시자 성격이다(D-49, 시험 재료 한정) — 실제로 손으로
다시 뽑아야 한다면 `--only`로 대상을 지정하고 `--force`로 다시 뽑는다."""


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
        help=(
            "이 캐릭터만 만든다(반복 가능). 기본은 CHARACTER_APPEARANCES에 겉모습이"
            f" 있는 전부: {', '.join(CHARACTER_APPEARANCES)}"
        ),
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
    character_ids = args.only or list(CHARACTER_APPEARANCES)
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
