"""Anthropic 제공자 어댑터. 이 파일 안에서만 `anthropic` SDK를 import한다.

환경 변수를 이 파일 안에서 직접 읽지 않는다 — API 키를 읽는 자리는
`agents/providers/__init__.py`의 등록소 한 곳뿐이다. 예외는 삼키지 않는다 —
그대로 위로 올린다(재시도 규칙은 03-03이 한 자리에 만든다).
"""

import time
from collections.abc import Iterator

import anthropic

from gptrpg.agents.envelope import AgentResult


def _extract_text(content: list) -> str:
    """응답 콘텐츠 블록들에서 텍스트만 이어 붙인다."""
    return "".join(block.text for block in content if getattr(block, "text", None))


def _input_token_counts(usage: object) -> tuple[int, int]:
    """`(prompt_tokens, cached_prompt_tokens)` 짝을 꺼낸다.

    **Anthropic의 `input_tokens`는 캐시 몫을 포함하지 않는다** — 캐시 쓰기
    (`cache_creation_input_tokens`)와 캐시 읽기(`cache_read_input_tokens`)를
    따로 보고하고 둘 다 `input_tokens` 밖에 있다. 그래서 `input_tokens`를
    그대로 `prompt_tokens`로 쓰면 캐싱이 걸린 호출의 입력 토큰이 실제
    처리량보다 **적게** 집계된다 — 원가를 실제보다 싸게 계산하는 방향의
    오차이므로 H5 판정에 그대로 쓰면 안 된다.

    그래서 셋을 더해 「이번 호출이 처리한 입력 토큰 전체」를 `prompt_tokens`로
    돌려주고, 그중 캐시 적중 몫만 `cached_prompt_tokens`로 돌려준다 — 이러면
    `AgentResult`가 선언한 불변식(캐시 몫은 입력 몫의 부분집합)이 이
    어댑터에서도 성립한다.

    **남는 오차 한 가지를 명시한다.** 캐시 쓰기 토큰은 신규 입력보다 비싸게
    (Anthropic 기준 1.25배) 과금되는데 이 함수는 그것을 신규 입력과 같은
    칸에 넣는다. 즉 캐시를 처음 채우는 호출의 원가는 약간 낮게 잡힌다.
    칸을 하나 더 늘리지 않은 이유는 M0이 재려는 것이 캐싱의 유무가 만드는
    배수(3.7배, D19)이고 그 판단은 이 정밀도로 충분하기 때문이다 — 필요해지면
    `AgentResult`에 칸을 하나 더 붙이는 확장이다.

    `getattr`로 꺼내는 것은 SDK 판이 올라가며 칸이 붙거나 빠져도 플레이 턴이
    죽지 않게 하기 위해서다(`openai_provider._cached_prompt_tokens`와 같은 이유).
    """
    base = getattr(usage, "input_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    return base + cache_write + cache_read, cache_read


class AnthropicProvider:
    """`anthropic.Anthropic` 클라이언트를 얇게 감싼다."""

    name = "anthropic"

    def __init__(self, api_key: str) -> None:
        # max_retries=0: SDK 자체 재시도를 끈다. 재시도 정책의 유일한 출처는
        # `invoke.py`의 `call_with_one_retry`(D-28, "정확히 한 번, 지연 없이")여야
        # 한다 — SDK 기본값(max_retries=2, 지수 백오프)을 그대로 두면 앱 계층
        # 재시도가 실행되기도 전에 백오프 지연을 낀 내부 재시도가 최대 2번 더
        # 숨어서 발생해 지연 시간 상한이 깨진다.
        self._client = anthropic.Anthropic(api_key=api_key, max_retries=0)
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        # client.models.list()는 자동으로 다음 페이지까지 순회한다 — .data를
        # 인덱싱하지 않고 반복자로 그대로 돈다.
        return [model.id for model in self._client.models.list()]

    def complete(
        self,
        *,
        model: str,
        system: list[dict],
        messages: list[dict],
        max_tokens: int,
        timeout_s: float,
    ) -> AgentResult:
        start = time.monotonic()
        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            timeout=timeout_s,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        prompt_tokens, cached_prompt_tokens = _input_token_counts(response.usage)
        result = AgentResult(
            ok=True,
            value=_extract_text(response.content),
            elapsed_ms=elapsed_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=response.usage.output_tokens,
            cached_prompt_tokens=cached_prompt_tokens,
        )
        self._last_result = result
        return result

    def stream(
        self,
        *,
        model: str,
        system: list[dict],
        messages: list[dict],
        max_tokens: int,
        timeout_s: float,
    ) -> Iterator[str]:
        start = time.monotonic()
        with self._client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            timeout=timeout_s,
        ) as stream:
            yield from stream.text_stream
            final = stream.get_final_message()
        elapsed_ms = int((time.monotonic() - start) * 1000)
        prompt_tokens, cached_prompt_tokens = _input_token_counts(final.usage)
        self._last_result = AgentResult(
            ok=True,
            value=_extract_text(final.content),
            elapsed_ms=elapsed_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=final.usage.output_tokens,
            cached_prompt_tokens=cached_prompt_tokens,
        )

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("complete() 또는 stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result
