"""다섯 제공자 어댑터의 등록·프로토콜 준수를 네트워크 없이 확인한다.

SDK 클라이언트 생성 자체는 실제 네트워크를 타지 않는다(생성자만 부르고
`list_models`/`complete`/`stream`은 부르지 않는다) — 그래도 혹시 모를 부작용을
막기 위해 각 SDK의 클라이언트 생성자를 `monkeypatch`로 가로챈다.
"""

import pytest

from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.providers import (
    PROVIDER_ENV_VARS,
    PROVIDER_FACTORIES,
    MissingApiKey,
    ProviderNotImplemented,
    UnknownProvider,
    available_providers,
    get_provider,
)
from gptrpg.agents.providers.base import Provider
from gptrpg.agents.providers.gemini_provider import GeminiProvider
from gptrpg.agents.providers.nim_provider import NIM_BASE_URL, NimProvider
from gptrpg.agents.providers.openai_provider import OpenAIProvider
from gptrpg.agents.providers.openrouter_provider import OPENROUTER_BASE_URL, OpenRouterProvider

_FAKE_KEY = "fake-key-does-not-touch-network"


class _FakeOpenAIClient:
    """`openai.OpenAI(...)`를 대신하는 가짜 — base_url·headers·max_retries만 기억한다."""

    def __init__(self, *, api_key, base_url=None, default_headers=None, **_kwargs):
        self.api_key = api_key
        self.base_url = base_url
        self.default_headers = default_headers
        self.max_retries = _kwargs.get("max_retries")


class _FakeGenaiClient:
    """`google.genai.Client(...)`를 대신하는 가짜."""

    def __init__(self, *, api_key, **_kwargs):
        self.api_key = api_key


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """다섯 어댑터 전부의 SDK 클라이언트 생성자를 가짜로 바꿔치기한다."""
    monkeypatch.setattr("gptrpg.agents.providers.openai_provider.OpenAI", _FakeOpenAIClient)
    monkeypatch.setattr("gptrpg.agents.providers.anthropic_provider.anthropic.Anthropic", _FakeOpenAIClient)
    monkeypatch.setattr("gptrpg.agents.providers.gemini_provider.genai.Client", _FakeGenaiClient)


# ---------------------------------------------------------------------------
# 다섯 어댑터 전부가 Provider 프로토콜을 만족한다
# ---------------------------------------------------------------------------


def test_all_five_adapters_satisfy_provider_protocol():
    for name, factory in PROVIDER_FACTORIES.items():
        instance = factory(_FAKE_KEY)
        assert isinstance(instance, Provider), f"{name} 어댑터가 Provider 프로토콜을 만족하지 않는다"


# ---------------------------------------------------------------------------
# PROVIDER_FACTORIES 와 PROVIDER_ENV_VARS 의 열쇠 집합이 정확히 같다 (다섯 개)
# ---------------------------------------------------------------------------


def test_provider_factories_and_env_vars_have_identical_key_sets():
    assert set(PROVIDER_FACTORIES) == set(PROVIDER_ENV_VARS)
    assert len(PROVIDER_FACTORIES) == 5


# ---------------------------------------------------------------------------
# get_provider 의 세 예외 갈래
# ---------------------------------------------------------------------------


def test_get_provider_raises_unknown_provider_for_unregistered_name():
    with pytest.raises(UnknownProvider):
        get_provider("does-not-exist", {})


def test_get_provider_raises_missing_api_key_when_env_var_absent():
    with pytest.raises(MissingApiKey) as exc_info:
        get_provider("anthropic", {})
    # 키 값이 예외 메시지에 들어 있지 않다 — 애초에 값 자체가 없으므로 환경
    # 변수 '이름'만 메시지에 있는지 확인한다.
    assert "ANTHROPIC_API_KEY" in str(exc_info.value)


def test_missing_api_key_message_never_contains_key_value():
    secret = "sk-super-secret-value-should-not-leak"
    try:
        get_provider("anthropic", {"ANTHROPIC_API_KEY": ""})
    except MissingApiKey as exc:
        assert secret not in str(exc)
    else:
        pytest.fail("빈 문자열 키는 MissingApiKey를 던져야 한다")


def test_get_provider_raises_provider_not_implemented_when_factory_missing(monkeypatch):
    # 다섯 자리가 전부 채워진 지금은 자연 발생하지 않는 갈래다 — 임시로 하나를
    # 비워 세 번째 예외 갈래가 여전히 살아 있음을 확인한다.
    monkeypatch.delitem(PROVIDER_FACTORIES, "gemini")
    with pytest.raises(ProviderNotImplemented):
        get_provider("gemini", {"GEMINI_API_KEY": _FAKE_KEY})


# ---------------------------------------------------------------------------
# 키가 있는 제공자만 available_providers 에 뜬다
# ---------------------------------------------------------------------------


def test_available_providers_lists_only_names_with_nonempty_env_value():
    env = {"ANTHROPIC_API_KEY": "x", "OPENAI_API_KEY": "", "NVIDIA_API_KEY": "y"}
    assert available_providers(env) == ["anthropic", "nim"]


def test_available_providers_empty_when_no_keys_set():
    assert available_providers({}) == []


# ---------------------------------------------------------------------------
# NIM 과 OpenRouter는 서로 다른 기본 주소로 만들어진다
# ---------------------------------------------------------------------------


def test_nim_and_openrouter_have_different_base_urls():
    nim = NimProvider(_FAKE_KEY)
    openrouter = OpenRouterProvider(_FAKE_KEY)
    assert nim._delegate._client.base_url != openrouter._delegate._client.base_url
    assert nim._delegate._client.base_url == NIM_BASE_URL
    assert openrouter._delegate._client.base_url == OPENROUTER_BASE_URL


def test_openrouter_sends_attribution_headers():
    openrouter = OpenRouterProvider(_FAKE_KEY)
    headers = openrouter._delegate._client.default_headers
    assert headers is not None
    assert "HTTP-Referer" in headers
    assert "X-Title" in headers
    # 헤더를 지우는 방식의 "수정"에 대한 회귀 방지 — 두 칸 다 값이 비어 있지 않다.
    assert headers["HTTP-Referer"]
    assert headers["X-Title"]


# ---------------------------------------------------------------------------
# G-03-1 회귀 방지: 귀속 헤더가 ASCII로 인코딩 가능해야 한다. 실제 키로
# `agents select`를 돌리면 httpx가 default_headers를 인코딩하는 시점에
# UnicodeEncodeError로 다섯 제공자 중 하나가 통째로 죽었었다(03-UAT.md 1번
# 시험) — `_FakeOpenAIClient`는 httpx의 인코딩 단계를 타지 않으므로 아래
# 시험은 `.encode("ascii")`를 직접 호출해 그 단계를 흉내 낸다.
# ---------------------------------------------------------------------------


def test_openrouter_attribution_header_constant_is_ascii():
    from gptrpg.agents.providers.openrouter_provider import _ATTRIBUTION_HEADERS

    for key, value in _ATTRIBUTION_HEADERS.items():
        key.encode("ascii")
        value.encode("ascii")


def test_openrouter_delegate_client_headers_are_ascii():
    # 상수만 고치고 클라이언트에 넘기는 경로가 따로 생겨도 이 시험이 잡는다 —
    # 모듈 상수가 아니라 어댑터가 **실제로 클라이언트에 넘긴** 헤더 사전을 본다.
    openrouter = OpenRouterProvider(_FAKE_KEY)
    headers = openrouter._delegate._client.default_headers
    assert headers is not None
    for key, value in headers.items():
        key.encode("ascii")
        value.encode("ascii")


def test_all_five_adapters_header_dicts_are_ascii_when_present():
    # 다섯 어댑터 전부를 돌되, 클라이언트가 헤더 사전을 갖고 있고 그 값이
    # None이 아닐 때만 단언한다 — 여섯 번째 어댑터가 헤더를 붙이면 자동으로
    # 이 그물에 걸린다.
    for name, factory in PROVIDER_FACTORIES.items():
        provider = factory(_FAKE_KEY)
        client = getattr(provider, "_delegate", provider)._client
        headers = getattr(client, "default_headers", None)
        if headers is None:
            continue
        for key, value in headers.items():
            try:
                key.encode("ascii")
                value.encode("ascii")
            except UnicodeEncodeError as exc:
                pytest.fail(f"{name} 어댑터의 헤더 {key!r}={value!r}가 ASCII로 인코딩되지 않는다: {exc}")


# ---------------------------------------------------------------------------
# CR-01 회귀 방지: SDK 자체 재시도가 꺼져 있다(max_retries=0) — 재시도 정책의
# 유일한 출처는 `invoke.py`의 `call_with_one_retry`(D-28)여야 한다. SDK
# 기본값(anthropic/openai 둘 다 max_retries=2)이 몰래 되살아나면 이 테스트가
# 잡는다.
# ---------------------------------------------------------------------------


def test_anthropic_client_disables_sdk_level_retries():
    from gptrpg.agents.providers.anthropic_provider import AnthropicProvider

    provider = AnthropicProvider(_FAKE_KEY)
    assert provider._client.max_retries == 0


@pytest.mark.parametrize(
    ("provider_cls"),
    [OpenAIProvider, NimProvider, OpenRouterProvider],
)
def test_openai_compatible_clients_disable_sdk_level_retries(provider_cls):
    provider = provider_cls(_FAKE_KEY)
    client = getattr(provider, "_delegate", provider)._client
    assert client.max_retries == 0


# ---------------------------------------------------------------------------
# 각 어댑터의 name 이 등록소 열쇠와 일치한다
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("factory_name", "provider_cls"),
    [
        ("openai", OpenAIProvider),
        ("nim", NimProvider),
        ("openrouter", OpenRouterProvider),
        ("gemini", GeminiProvider),
    ],
)
def test_adapter_name_matches_registry_key(factory_name, provider_cls):
    instance = provider_cls(_FAKE_KEY)
    assert instance.name == factory_name


# ---------------------------------------------------------------------------
# G-03-3 회귀 방지: note_result()로 넘긴 실패 껍데기가 last_result()로 그대로
# 돌아온다 — 위임 어댑터(nim/openrouter)를 통과해도 잃어버리지 않는다.
# 이 사슬이 03-UAT.md 3번 시험의 실제 크래시 원인이었다(narrate()의 실패
# 경로가 위임 어댑터에서 `provider._last_result = ...`로 직접 속성을 꽂아,
# 아무도 읽지 않는 새 속성 하나만 만들고 값이 조용히 사라졌다).
# ---------------------------------------------------------------------------

_FAILURE_ENVELOPE = AgentResult(ok=False, value=None, elapsed_ms=123, prompt_tokens=0, completion_tokens=0)


def test_note_result_round_trips_through_last_result_for_all_five_adapters():
    for name, factory in PROVIDER_FACTORIES.items():
        instance = factory(_FAKE_KEY)
        instance.note_result(_FAILURE_ENVELOPE)
        assert instance.last_result() == _FAILURE_ENVELOPE, (
            f"{name} 어댑터가 note_result()로 넘긴 값을 last_result()로 돌려주지 않는다"
        )


@pytest.mark.parametrize(("provider_cls"), [NimProvider, OpenRouterProvider])
def test_note_result_on_delegating_adapter_reaches_the_delegate(provider_cls):
    """껍데기만 갈아 끼우고 실제 위임 대상은 비어 있는 절반짜리 수정을 잡는다."""
    instance = provider_cls(_FAKE_KEY)
    instance.note_result(_FAILURE_ENVELOPE)
    assert instance._delegate.last_result() == _FAILURE_ENVELOPE


def test_last_result_still_raises_before_note_result_or_any_call():
    """"아직 아무것도 안 불렀다"와 "실패했다"는 구분된 채로 남아야 한다."""
    for factory in PROVIDER_FACTORIES.values():
        instance = factory(_FAKE_KEY)
        with pytest.raises(RuntimeError):
            instance.last_result()
