"""OpenRouter 제공자 어댑터 — `OpenAIProvider`를 기본 주소만 바꿔 위임한다.

OpenRouter도 NIM과 마찬가지로 OpenAI 호환 REST 표면이다(RESEARCH.md Standard
Stack) — 저장소 없는 비공식 OpenRouter PyPI 패키지는 설치하지 않는다
(RESEARCH.md Package Legitimacy Audit, "SLOP-adjacent"로 배제됨). 이 파일은
`openai` SDK를 직접 import하지 않는다 — `OpenAIProvider` 하나만 안다.

**귀속 헤더 방어적 결정 (RESEARCH.md Open Question 1, 미해결로 남았던 항목):**
OpenRouter 문서는 `HTTP-Referer`·`X-Title` 헤더를 "권장"으로 적을 뿐 모델
목록 조회 자체에 필수인지는 조사 단계에서 확인하지 못했다. 넣어서 손해 볼
것이 없으므로 생성 시점에 기본 헤더로 항상 붙인다 — 이 조사 단계 미해결
질문에 대한 방어적 선택이다. 값은 이 도구를 가리키는 고정 문자열이고
호출마다 달라지지 않는다(프롬프트 캐시 접두 안정성과는 무관 — 이 헤더는
`system` 프롬프트 안이 아니라 HTTP 요청 헤더다).

**실측 사고 기록 (G-03-1, 03-UAT.md 1번 시험, 2026-08-02):** `X-Title` 값에
한글 문자열("GPTRPG M0 실험 도구")을 넣었더니 실제 키로 `agents select`를
돌리는 순간 `UnicodeEncodeError`로 다섯 제공자 중 이 하나가 통째로 죽었다
— 아래 「왜 ASCII여야 하는지」 문단 참조. `tests/test_providers.py`의
`_FakeOpenAIClient`는 `openai.OpenAI` 생성자만 가로채고 그 안의 httpx
인코딩 단계는 타지 않으므로, 이 시험 이중체는 이 실패를 재현하지 못한다
— 자동 시험 307개가 전부 통과해도 이 사고가 실제 키 재실행 전까지 드러나지
않았던 이유다. "시험이 통과하니 헤더는 안전하다"로 읽으면 안 된다.

**미검증 항목 (IN-02 리뷰 발견):** `OpenAIProvider.stream()`이 항상 보내는
`stream_options={"include_usage": True}`가 OpenRouter의 OpenAI 호환 표면에서
실제로 동작하는지는 라이브로 확인된 바 없다(`nim_provider.py` 도크스트링은
NIM 백엔드에 대해 이를 명시적으로 검증했다고 적어 두었지만, OpenRouter는
그런 확인이 없다). 실패 모양이 조용하다는 점이 문제다 — 옵션 자체를 거부하면
`narrate()`의 넓은 `except Exception`이 다른 실패와 똑같이 잡아 재시도/실패
처리하지만, 옵션을 조용히 무시만 하는 경우라면 최종 `AgentResult`의
`prompt_tokens`/`completion_tokens`가 0으로 남고 그게 `ok=True`인 채로
`RecordAiCall`에 그대로 기록된다 — 실패 봉투의 "0토큰" 관례(`ok=False`)와
겉모양은 같지만 `ok=True`에 붙는다는 점이 다르다. OpenRouter의 토큰/비용
숫자를 신뢰하기 전에 라이브 스모크 테스트가 필요하다.
"""

from collections.abc import Iterator

from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.providers.openai_provider import OpenAIProvider

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
"""OpenRouter 공식 문서(openrouter.ai/docs)가 명시하는 OpenAI 호환 엔드포인트."""

_ATTRIBUTION_HEADERS = {
    "HTTP-Referer": "https://github.com/gptrpg-m0/gptrpg",
    "X-Title": "GPTRPG M0 Experiment Tool",
}
"""이 도구를 가리키는 고정 문자열 — 호출마다 달라지지 않는다.

**왜 ASCII여야 하는가:** HTTP 헤더 값은 ASCII만 허용된다. 이 사전은 요청
하나가 아니라 `openai.OpenAI` 클라이언트 생성 시점에 `default_headers`로
박혀 이 제공자로 나가는 **모든** 요청(모델 목록·분류·서사 전부)에 붙는다
— 여기에 비-ASCII 한 글자가 들어가면 그 요청 전부가 `UnicodeEncodeError`로
죽는다. 사용자에게 보일 한글 이름이 필요하면 이 헤더가 아니라 화면 출력
쪽에 둬야 한다."""


class OpenRouterProvider:
    """`OpenAIProvider`에 OpenRouter의 `base_url`과 귀속 헤더를 붙여 위임한다.

    이 클래스는 상태를 자기가 갖지 않고 전부 `self._delegate`에 둔다 — 그러므로
    바깥에서 이 객체에 상태를 **직접 속성으로 꽂으면 조용히 사라진다**(예:
    `provider._last_result = ...`). 상태를 남기려면 반드시 `note_result()` 같은
    메서드를 통해야 한다. 03-UAT.md G-03-3이 정확히 이 실수였다 — 다음에 이
    파일을 읽는 사람이 같은 실수를 하지 않게 여기 남긴다.
    """

    name = "openrouter"

    def __init__(self, api_key: str) -> None:
        self._delegate = OpenAIProvider(
            api_key, base_url=OPENROUTER_BASE_URL, default_headers=_ATTRIBUTION_HEADERS
        )

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
