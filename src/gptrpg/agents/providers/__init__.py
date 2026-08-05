"""제공자 이름을 일급 개념으로 만드는 등록소.

환경 변수에서 API 키를 읽는 자리는 이 모듈 하나뿐이다 — 어댑터 파일들은
직접 `os.environ`을 읽지 않는다. 키 값 자체는 어떤 예외 메시지에도 넣지
않는다.
"""

from collections.abc import Callable, Mapping

from gptrpg.agents.providers.anthropic_provider import AnthropicProvider
from gptrpg.agents.providers.base import Provider
from gptrpg.agents.providers.gemini_provider import GeminiProvider
from gptrpg.agents.providers.nim_provider import NimProvider
from gptrpg.agents.providers.openai_provider import OpenAIProvider
from gptrpg.agents.providers.openrouter_provider import OpenRouterProvider

PROVIDER_ENV_VARS: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "nim": "NVIDIA_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}
"""다섯 제공자 이름 -> 환경 변수 이름 (D-31)."""

PROVIDER_FACTORIES: dict[str, Callable[[str], Provider]] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "nim": NimProvider,
    "openrouter": OpenRouterProvider,
    "gemini": GeminiProvider,
}
"""다섯 제공자 전부 등록됨(D-31) — 03-01이 트레이서 검증용으로 `anthropic`·
`nim` 둘만 앞당겨 등록했던 것을, 이 계획이 나머지 셋(`openai`·`openrouter`·
`gemini`)을 더해 다섯으로 채웠다. 열쇠 집합이 `PROVIDER_ENV_VARS`와 정확히
같다."""


class UnknownProvider(Exception):
    """`PROVIDER_ENV_VARS`에 없는 이름으로 조회했을 때 던진다."""

    def __init__(self, name: str) -> None:
        super().__init__(f"등록되지 않은 제공자: {name!r}")
        self.name = name


class MissingApiKey(Exception):
    """이름은 알지만 대응하는 환경 변수 값이 비어 있을 때 던진다."""

    def __init__(self, name: str, env_var: str) -> None:
        super().__init__(f"{name!r} 제공자의 API 키({env_var})가 설정되어 있지 않다")
        self.name = name
        self.env_var = env_var


class ProviderNotImplemented(Exception):
    """이름과 키는 있지만 아직 어댑터가 등록되지 않았을 때 던진다.

    지금은 `PROVIDER_FACTORIES`가 다섯 자리를 전부 채웠으므로 정상 흐름에서
    이 갈래에 도달하지 않는다 — 그래도 갈래 자체는 지우지 않는다. 여섯 번째
    제공자를 `PROVIDER_ENV_VARS`에 먼저 등록하고 어댑터는 나중에 붙이는 두
    단계 배포를 할 때 다시 쓰인다.
    """

    def __init__(self, name: str) -> None:
        super().__init__(f"{name!r} 제공자의 어댑터가 아직 구현되지 않았다")
        self.name = name


def available_providers(env: Mapping[str, str]) -> list[str]:
    """값이 비어 있지 않은 API 키를 가진 제공자 이름만 정렬해 돌려준다 (D-31)."""
    return sorted(name for name, env_var in PROVIDER_ENV_VARS.items() if env.get(env_var))


def get_provider(name: str, env: Mapping[str, str]) -> Provider:
    """제공자 이름으로 실제 어댑터를 만든다.

    이름이 없으면 `UnknownProvider`, 키가 없으면 `MissingApiKey`, 어댑터가
    아직 등록되지 않았으면 `ProviderNotImplemented` — 셋 다 조용히 다른
    제공자로 대체하지 않는다(`get_rulebook`/`UnknownRulebook`이 세운 규율과
    같은 이유).
    """
    env_var = PROVIDER_ENV_VARS.get(name)
    if env_var is None:
        raise UnknownProvider(name)
    api_key = env.get(env_var)
    if not api_key:
        raise MissingApiKey(name, env_var)
    factory = PROVIDER_FACTORIES.get(name)
    if factory is None:
        raise ProviderNotImplemented(name)
    return factory(api_key)
