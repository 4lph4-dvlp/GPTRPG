"""OpenAI 제공자 어댑터. 이 파일 안에서만 `openai` SDK를 import한다.

환경 변수를 이 파일 안에서 직접 읽지 않는다 — API 키를 읽는 자리는
`agents/providers/__init__.py`의 등록소 한 곳뿐이다. 예외는 삼키지 않는다.

**프롬프트 캐싱 참고:** OpenAI 계열 chat-completions 표면에는 Anthropic의
`cache_control` 같은 명시적 캐시 분기점 API가 없다 — 1024 토큰 이상인
프롬프트에 자동으로 걸리고, 안정적인 접두 순서(`prompt_assembly.py`가 이미
강제하는 영구→세션→턴 순서)가 코드로 붙일 수 있는 유일한 지렛대다.

**그래서 캐시 적중 여부를 실측으로 확인해야 한다.** `cache_control`이 이
변환에서 버려지므로, 캐싱이 실제로 걸렸는지는 코드를 읽어서는 알 수 없고
제공자가 보고하는 `usage.prompt_tokens_details.cached_tokens`로만 알 수
있다. `_cached_prompt_tokens`가 그 값을 꺼내며, 그 칸을 주지 않는 백엔드
(OpenAI 호환을 자칭하는 게이트웨이 상당수가 여기 해당한다)에서는 0이
남는다 — 0은 「캐시 적중 없음」과 「보고하지 않음」을 구분하지 않으므로,
Phase 6은 0을 **원가 상한선(캐시 0% 가정)**으로 읽어야 한다.

**NIM·OpenRouter가 이 클래스를 위임 대상으로 쓰는 이유:** 둘 다 OpenAI 호환
REST 표면이므로 별도 SDK를 설치하지 않고 `base_url`만 바꿔 이 클래스를
그대로 감싼다(`nim_provider.py`, `openrouter_provider.py` 참조).
"""

import time
from collections.abc import Iterator

from openai import OpenAI

from gptrpg.agents.envelope import AgentResult


def _to_openai_messages(system: list[dict], messages: list[dict]) -> list[dict]:
    """`system` 블록 목록(Anthropic 스타일)을 OpenAI chat 메시지 형식으로 접는다.

    `cache_control` 칸은 이 변환에서 버려진다 — OpenAI 호환 표면에는 대응하는
    API가 없다(위 모듈 도크스트링 참조).
    """
    system_text = "\n\n".join(block["text"] for block in system)
    openai_messages: list[dict] = []
    if system_text:
        openai_messages.append({"role": "system", "content": system_text})
    openai_messages.extend(messages)
    return openai_messages


def _cached_prompt_tokens(usage: object) -> int:
    """`usage.prompt_tokens_details.cached_tokens`를 꺼낸다. 없으면 0.

    `getattr` 사슬로 꺼내는 이유: 이 클래스는 진짜 OpenAI뿐 아니라 NIM·
    OpenRouter 같은 OpenAI 호환 게이트웨이의 위임 대상으로도 쓰인다
    (`nim_provider.py`, `openrouter_provider.py`). 그 백엔드들은 `usage`에
    `prompt_tokens_details`를 아예 안 붙이거나 `None`으로 준다 — 있는 곳에서만
    읽고 없으면 0으로 떨어지는 것이 어댑터 다섯 개를 한 코드로 덮는 유일한
    방법이다. 예외를 던지지 않는다: 캐시 보고 여부는 원가 계측의 정밀도
    문제일 뿐이고, 그것 때문에 실제 플레이 턴이 죽으면 안 된다.
    """
    details = getattr(usage, "prompt_tokens_details", None)
    if details is None:
        return 0
    return getattr(details, "cached_tokens", 0) or 0


class OpenAIProvider:
    """`openai.OpenAI` 클라이언트를 얇게 감싼다.

    생성자가 선택적 `base_url`·`default_headers`를 받는 것은 NIM·OpenRouter가
    이 클래스를 그대로 위임해 쓸 수 있게 하기 위해서다.
    """

    name = "openai"

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str | None = None,
        default_headers: dict[str, str] | None = None,
    ) -> None:
        # max_retries=0: SDK 자체 재시도를 끈다. 재시도 정책의 유일한 출처는
        # `invoke.py`의 `call_with_one_retry`(D-28, "정확히 한 번, 지연 없이")여야
        # 한다 — SDK 기본값(max_retries=2, 지수 백오프)을 그대로 두면 앱 계층
        # 재시도가 실행되기도 전에 백오프 지연을 낀 내부 재시도가 최대 2번 더
        # 숨어서 발생해 지연 시간 상한이 깨진다. NIM·OpenRouter도 이 클래스를
        # 위임 대상으로 쓰므로 이 한 곳에서 고치면 셋 다 적용된다.
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers=default_headers,
            max_retries=0,
        )
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return sorted(model.id for model in self._client.models.list())

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
        response = self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=_to_openai_messages(system, messages),
            timeout=timeout_s,
            stream=False,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        text = response.choices[0].message.content or ""
        result = AgentResult(
            ok=True,
            value=text,
            elapsed_ms=elapsed_ms,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            cached_prompt_tokens=_cached_prompt_tokens(response.usage),
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
        prompt_tokens = 0
        completion_tokens = 0
        cached_prompt_tokens = 0
        full_text_parts: list[str] = []
        response = self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=_to_openai_messages(system, messages),
            timeout=timeout_s,
            stream=True,
            stream_options={"include_usage": True},
        )
        for chunk in response:
            if chunk.choices:
                delta = chunk.choices[0].delta.content
                if delta:
                    full_text_parts.append(delta)
                    yield delta
            usage = getattr(chunk, "usage", None)
            if usage is not None:
                prompt_tokens = usage.prompt_tokens
                completion_tokens = usage.completion_tokens
                cached_prompt_tokens = _cached_prompt_tokens(usage)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        self._last_result = AgentResult(
            ok=True,
            value="".join(full_text_parts),
            elapsed_ms=elapsed_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cached_prompt_tokens=cached_prompt_tokens,
        )

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("complete() 또는 stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result
