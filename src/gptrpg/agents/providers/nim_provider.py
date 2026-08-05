"""Nvidia NIM 제공자 어댑터 — `OpenAIProvider`를 기본 주소만 바꿔 위임한다.

NIM은 자체 SDK가 없다 — NVIDIA 공식 문서(build.nvidia.com) 자체가 `openai`
클라이언트에 `base_url`만 바꿔 쓰라고 안내한다(RESEARCH.md Standard Stack).
이 파일은 `openai` SDK를 직접 import하지 않는다 — `OpenAIProvider` 하나만
안다. 환경 변수는 여기서 직접 읽지 않는다 — 등록소(`agents/providers/__init__.py`)
한 곳에서만 읽는다.

**03-02가 03-01의 앞당김을 이 계획의 설계대로 정리한 부분(reconciliation):**
03-01은 `ANTHROPIC_API_KEY` 없이 `NVIDIA_API_KEY`만 가진 사용자를 위해 이
어댑터를 최소 범위로 앞당기면서(deviation, 03-01-SUMMARY.md 참조),
`OpenAIProvider`가 아직 없었으므로 OpenAI chat-completions 호출 로직을 이
파일 안에 직접 복제해 넣었다. 03-02(이 계획)가 `OpenAIProvider`를 새로
만들었으므로, 이 파일을 03-02의 원래 설계("OpenAIProvider를 기본 주소만
바꿔 만들어 위임한다")대로 다시 짰다 — 복제된 로직을 지우고 위임으로
바꿨다. 동작은 03-01이 NIM으로 라이브 검증한 것과 동일하다(같은 엔드포인트,
같은 `openai` 클라이언트 호출 모양) — 이번 재작성은 중복 제거일 뿐 행동
변경이 아니다.

`list_models()`의 실제 응답 모양과 `stream_options={"include_usage": True}`가
NIM 백엔드에서 그대로 받아들여지는지는 03-01의 Task 3 라이브 검증(스트리밍
`stream()` 경로로 실제 확인됨)으로 이미 확인됐다.
"""

from collections.abc import Iterator

from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.providers.openai_provider import OpenAIProvider

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
"""NVIDIA 공식 문서(build.nvidia.com)가 명시하는 OpenAI 호환 엔드포인트."""


class NimProvider:
    """`OpenAIProvider`에 NIM의 `base_url`만 바꿔 그대로 위임한다.

    이 클래스는 상태를 자기가 갖지 않고 전부 `self._delegate`에 둔다 — 그러므로
    바깥에서 이 객체에 상태를 **직접 속성으로 꽂으면 조용히 사라진다**(예:
    `provider._last_result = ...`). 상태를 남기려면 반드시 `note_result()` 같은
    메서드를 통해야 한다. 03-UAT.md G-03-3이 정확히 이 실수였다 — 다음에 이
    파일을 읽는 사람이 같은 실수를 하지 않게 여기 남긴다.
    """

    name = "nim"

    def __init__(self, api_key: str) -> None:
        self._delegate = OpenAIProvider(api_key, base_url=NIM_BASE_URL)

    def list_models(self) -> list[str]:
        return self._delegate.list_models()

    def complete(
        self,
        *,
        model: str,
        system: list[dict],
        messages: list[dict],
        max_tokens: int,
        timeout_s: float,
    ) -> AgentResult:
        return self._delegate.complete(
            model=model, system=system, messages=messages, max_tokens=max_tokens, timeout_s=timeout_s
        )

    def stream(
        self,
        *,
        model: str,
        system: list[dict],
        messages: list[dict],
        max_tokens: int,
        timeout_s: float,
    ) -> Iterator[str]:
        yield from self._delegate.stream(
            model=model, system=system, messages=messages, max_tokens=max_tokens, timeout_s=timeout_s
        )

    def last_result(self) -> AgentResult:
        return self._delegate.last_result()

    def note_result(self, result: AgentResult) -> None:
        self._delegate.note_result(result)
