"""Google Gemini 제공자 어댑터. 이 파일 안에서만 `google.genai` SDK를 import한다.

환경 변수를 이 파일 안에서 직접 읽지 않는다 — API 키를 읽는 자리는
`agents/providers/__init__.py`의 등록소 한 곳뿐이다. 예외는 삼키지 않는다.

**프롬프트 캐싱 참고:** Gemini 계열의 암묵 캐싱(implicit caching)은 기본으로
켜져 있고 안정적인 접두(`prompt_assembly.py`가 강제하는 영구→세션→턴 순서)에
같은 규율로 적중한다(RESEARCH.md Architecture Patterns §2). `caches.create`로
명시 캐시를 만드는 왕복은 이번 단계에 넣지 않는다 — 암묵 캐싱이 코드 없이
같은 규율로 작동하고, 명시 캐시는 별도 왕복(생성 API 호출)이 필요해 이
단계의 범위를 넘는다.

`google.genai`의 정확한 서명은 구현 전에 `python -c "import google.genai as g;
help(g.Client)"`로 확인했다(RESEARCH.md 요구사항) — `client.models.list()`,
`client.models.generate_content(...)`, `client.models.generate_content_stream(...)`
가 실제 서명이다. 시스템 프롬프트는 `types.GenerateContentConfig(system_instruction=...)`
로 넘긴다(별도 system 메시지 role이 아니다).
"""

import time
from collections.abc import Iterator

from google import genai
from google.genai import types

from gptrpg.agents.envelope import AgentResult


def _system_text(system: list[dict]) -> str:
    return "\n\n".join(block["text"] for block in system)


def _cached_prompt_tokens(usage: object) -> int:
    """`usage_metadata.cached_content_token_count`를 꺼낸다. 없으면 0.

    Gemini의 암묵 캐싱은 켜고 끄는 API가 없어(위 모듈 도크스트링) **적중
    여부를 코드로는 알 수 없고 이 칸으로만 알 수 있다.** 그래서 이 값이
    이 어댑터에서 캐싱 실측의 유일한 창구다. Gemini는 이 몫을
    `prompt_token_count`에 **포함해서** 보고하므로 `prompt_tokens`를 따로
    보정하지 않는다 — `AgentResult`의 불변식(캐시 몫은 입력 몫의 부분집합)이
    이 어댑터에서는 그대로 성립한다(Anthropic은 그렇지 않아
    `anthropic_provider._input_token_counts`가 따로 더한다).

    `getattr`로 꺼내는 이유는 형제 어댑터와 같다 — 칸이 없어도 플레이 턴이
    죽지 않아야 한다.
    """
    if usage is None:
        return 0
    return getattr(usage, "cached_content_token_count", 0) or 0


def _to_gemini_contents(messages: list[dict]) -> list[str]:
    """`messages`(OpenAI 스타일 role/content 짝)를 Gemini `contents`로 접는다.

    이 코드베이스의 프롬프트 조립은 항상 사용자 메시지 하나뿐이다
    (`prompt_assembly.py`의 `build_classifier_prompt`/`build_gm_prompt` 참조) —
    role 분기 없이 텍스트만 이어 붙인다.
    """
    return [message["content"] for message in messages]


class GeminiProvider:
    """`google.genai.Client`를 얇게 감싼다."""

    name = "gemini"

    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return sorted(model.name for model in self._client.models.list() if model.name)

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
        config = types.GenerateContentConfig(
            system_instruction=_system_text(system) or None,
            max_output_tokens=max_tokens,
            http_options=types.HttpOptions(timeout=int(timeout_s * 1000)),
        )
        response = self._client.models.generate_content(
            model=model, contents=_to_gemini_contents(messages), config=config
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        usage = response.usage_metadata
        result = AgentResult(
            ok=True,
            value=response.text or "",
            elapsed_ms=elapsed_ms,
            prompt_tokens=(usage.prompt_token_count or 0) if usage else 0,
            completion_tokens=(usage.candidates_token_count or 0) if usage else 0,
            cached_prompt_tokens=_cached_prompt_tokens(usage),
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
        config = types.GenerateContentConfig(
            system_instruction=_system_text(system) or None,
            max_output_tokens=max_tokens,
            http_options=types.HttpOptions(timeout=int(timeout_s * 1000)),
        )
        prompt_tokens = 0
        completion_tokens = 0
        cached_prompt_tokens = 0
        full_text_parts: list[str] = []
        for chunk in self._client.models.generate_content_stream(
            model=model, contents=_to_gemini_contents(messages), config=config
        ):
            if chunk.text:
                full_text_parts.append(chunk.text)
                yield chunk.text
            usage = chunk.usage_metadata
            if usage is not None:
                prompt_tokens = usage.prompt_token_count or 0
                completion_tokens = usage.candidates_token_count or 0
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
