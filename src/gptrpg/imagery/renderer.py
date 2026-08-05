"""로컬 SDXL Turbo 렌더러 — 모델을 한 번만 올리고, 호출을 직렬화한다.

세 가지가 이 파일의 전부다.

1. **torch/diffusers 를 모듈 맨 위에서 import 하지 않는다.** 두 꾸러미는
   합쳐 2.5GB가 넘고 기본 설치에 들어 있지 않다(`pyproject.toml`의 선택
   의존성 `imagery`). 맨 위에서 import하면 그림 기능을 쓰지 않는 사람과
   399개 시험 전체가 그 무게를 지게 된다. 실제 import는 `_load()` 안에서만
   일어나고, 없으면 `RendererUnavailable`로 바뀐다.
2. **호출을 락으로 직렬화한다.** MPS 파이프라인을 여러 스레드에서 동시에
   부르면 결과가 깨지거나 메모리가 터진다. 플레이어 넷이 동시에 확인
   버튼을 누를 수 있으므로(D-10이 발언권 락을 폐기했다) 동시 호출은
   가정이 아니라 예정된 일이다.
3. **씨앗을 사건 번호에서 만든다.** `seed_for(session_id, seq)`가 결정적이라
   같은 판정은 언제나 같은 그림이 된다 — 사건 기록만 있으면 그림을 다시
   만들 수 있다(D-08 재구성 정신).

이 파일은 사건을 쓰지 않고 파일도 쓰지 않는다. PNG 바이트를 돌려주는 데서
끝나고, 어디에 저장할지는 부르는 층(`web`)이 정한다.
"""

import io
import threading
import time
import warnings
import zlib
from dataclasses import dataclass
from typing import Protocol

from gptrpg.imagery.config import ImageryConfig


class RendererUnavailable(RuntimeError):
    """그림을 만들 수 없다 — 꾸러미가 없거나 모델을 올리지 못했다.

    부르는 쪽은 이 예외를 「이번 턴에 그림이 없다」로 다루고 턴 자체는 그대로
    끝내야 한다. 그림 실패가 게임 진행을 막아서는 안 된다.
    """


@dataclass(frozen=True)
class RenderedImage:
    """그림 하나와 그것을 만든 조건 전부. 사건에 남길 값이 여기서 나온다."""

    png: bytes
    prompt: str
    style: str
    seed: int
    steps: int
    size: int
    latency_ms: int


class Renderer(Protocol):
    """그림 만드는 것의 최소 계약.

    `web`은 이 형태만 알면 되므로, 시험은 torch 없이 도는 대역을 끼워 넣을 수
    있다(`agents`의 `provider_resolver` 주입 이음매와 같은 방식).
    """

    def render(self, prompt: str, *, style: str, seed: int) -> RenderedImage:
        """프롬프트 하나를 PNG 바이트로. 실패하면 `RendererUnavailable`."""
        ...


def seed_for(scope: str, index: int) -> int:
    """이름표와 번호에서 32비트 씨앗을 결정적으로 만든다.

    장면 삽화는 `seed_for(session_id, seq)`로 부른다 — 같은 판정이 언제나 같은
    그림이 되므로 사건 기록만 있으면 그림을 다시 만들 수 있다(D-08 재구성
    정신). 초상화는 `seed_for(f"portrait:{character_id}", 0)`처럼 부른다.

    `random`을 쓰지 않는다. CRC32는 암호학적 성질이 필요 없는 이 용도에
    충분하고, 파이썬 판이 달라도 값이 같다 — `hash()`는 문자열에 대해
    실행마다 값이 달라지므로(PYTHONHASHSEED) 재현에 쓸 수 없다.
    """
    return zlib.crc32(f"{scope}:{index}".encode())


class SdxlTurboRenderer:
    """SDXL Turbo 파이프라인 하나를 물고 있는 렌더러.

    `warm_up()`을 부르지 않으면 첫 `render()`가 모델을 올린다(로컬 캐시가
    있어도 6~7초, 없으면 6.9GB 내려받기). 서버 기동 때 미리 부르는 쪽이
    첫 턴을 기다리게 하지 않는다.
    """

    def __init__(self, config: ImageryConfig) -> None:
        self._config = config
        self._pipe = None
        self._lock = threading.Lock()

    def warm_up(self) -> None:
        """모델을 미리 올린다. 실패하면 `RendererUnavailable`."""
        with self._lock:
            self._load()

    def render(self, prompt: str, *, style: str, seed: int) -> RenderedImage:
        """그림 하나. **락 안에서 돈다** — 동시 호출은 줄을 선다."""
        started = time.monotonic()
        with self._lock:
            pipe = self._load()
            image = self._infer(pipe, prompt, seed)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return RenderedImage(
            png=buffer.getvalue(),
            prompt=prompt,
            style=style,
            seed=seed,
            steps=self._config.steps,
            size=self._config.size,
            latency_ms=int((time.monotonic() - started) * 1000),
        )

    def _infer(self, pipe, prompt: str, seed: int):
        import torch

        # 파이프라인 내부의 VAE upcast 경고가 매 턴 서버 로그를 덮는다. 전역
        # 필터를 걸지 않고 이 호출만 감싼다 — 이 층이 남의 경고 설정을
        # 영구히 바꾸지 않는다.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            result = pipe(
                prompt=prompt,
                num_inference_steps=self._config.steps,
                # Turbo 는 CFG 없이 distill 된 모델이다 — 0이 아니면 결과가 망가진다.
                guidance_scale=0.0,
                height=self._config.size,
                width=self._config.size,
                # 씨앗 생성기는 CPU에 둔다. MPS 생성기는 같은 씨앗에서 기기·판에
                # 따라 다른 잡음을 내므로, 재현이 기기에 묶이지 않게 한다.
                generator=torch.Generator(device="cpu").manual_seed(seed),
            )
        return result.images[0]

    def _load(self):
        """파이프라인을 만들거나 이미 만든 것을 돌려준다. **락 안에서만 부른다.**"""
        if self._pipe is not None:
            return self._pipe
        try:
            import torch
            from diffusers import AutoPipelineForText2Image
        except ImportError as exc:
            raise RendererUnavailable(
                "그림 꾸러미가 없다 — `uv sync --extra imagery`로 torch/diffusers를 설치한다"
            ) from exc

        if torch.backends.mps.is_available():
            device, dtype = "mps", torch.float16
        elif torch.cuda.is_available():
            device, dtype = "cuda", torch.float16
        else:
            # CPU에는 fp16 커널이 없다. 돌기는 하지만 한 장에 분 단위다.
            device, dtype = "cpu", torch.float32

        kwargs = {"torch_dtype": dtype}
        if dtype is torch.float16:
            kwargs["variant"] = "fp16"
        try:
            pipe = AutoPipelineForText2Image.from_pretrained(self._config.model, **kwargs)
            pipe.to(device)
        except Exception as exc:  # noqa: BLE001 - 내려받기·가중치·기기 실패를 한 종류로 다룬다
            raise RendererUnavailable(f"모델을 올리지 못했다: {exc}") from exc
        pipe.set_progress_bar_config(disable=True)
        self._pipe = pipe
        return pipe
