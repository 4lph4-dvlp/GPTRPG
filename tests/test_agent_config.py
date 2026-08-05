"""역할별 제공자·모델 선택 영속화 — 저장 파일 왕복, 자격 증명 비저장, 큰 소리로 실패(D-33).

임시 디렉터리 경로로 왕복 시험을 쓴다. `main(["agents", "show"/"select", ...])`은
`tests/test_cli.py`의 방식 그대로 하위 프로세스 없이 그 자리에서 부른다.
"""

import json
import os

import pytest

from gptrpg.agents import providers as providers_module
from gptrpg.agents.config import (
    AGENT_ROLES,
    AgentChoice,
    ConfigNotFound,
    InvalidAgentConfig,
    load_config,
    resolve_provider,
    save_config,
)
from gptrpg.agents.providers import MissingApiKey
from gptrpg.cli.main import main


def test_agent_roles_are_exactly_the_two_locked_roles():
    assert AGENT_ROLES == ("action_classifier", "master_gm")


# ---------------------------------------------------------------------------
# save_config -> load_config 왕복에서 두 역할 값이 그대로 돌아온다
# ---------------------------------------------------------------------------


def test_save_then_load_round_trips_both_roles(tmp_path):
    path = tmp_path / "agents.json"
    choices = {
        "action_classifier": AgentChoice(provider="anthropic", model="claude-haiku"),
        "master_gm": AgentChoice(provider="openai", model="gpt-5"),
    }
    save_config(path, choices)
    assert load_config(path) == choices


# ---------------------------------------------------------------------------
# 저장 파일 원문에 환경 변수 값이 하나도 없다 — 자격 증명은 저장되지 않는다
# ---------------------------------------------------------------------------


def test_saved_file_never_contains_env_var_values(tmp_path, monkeypatch):
    secret = "sk-super-secret-value-should-not-leak"
    monkeypatch.setenv("ANTHROPIC_API_KEY", secret)
    path = tmp_path / "agents.json"
    save_config(
        path,
        {
            "action_classifier": AgentChoice(provider="anthropic", model="claude-haiku"),
            "master_gm": AgentChoice(provider="anthropic", model="claude-haiku"),
        },
    )
    text = path.read_text(encoding="utf-8")
    assert secret not in text
    # 저장 파일에는 provider/model 두 칸 외에는 아무것도 없다
    payload = json.loads(text)
    for role_payload in payload.values():
        assert set(role_payload.keys()) == {"provider", "model"}


# ---------------------------------------------------------------------------
# 파일이 없을 때 ConfigNotFound — 빈 사전이나 임의의 기본값을 돌려주지 않는다
# ---------------------------------------------------------------------------


def test_load_config_raises_config_not_found_when_file_missing(tmp_path):
    with pytest.raises(ConfigNotFound):
        load_config(tmp_path / "does-not-exist.json")


def test_load_config_raises_invalid_agent_config_when_role_missing(tmp_path):
    path = tmp_path / "agents.json"
    path.write_text(
        json.dumps({"action_classifier": {"provider": "anthropic", "model": "x"}}),
        encoding="utf-8",
    )
    with pytest.raises(InvalidAgentConfig):
        load_config(path)


def test_load_config_raises_invalid_agent_config_for_unknown_provider_name(tmp_path):
    path = tmp_path / "agents.json"
    path.write_text(
        json.dumps(
            {
                "action_classifier": {"provider": "not-a-real-provider", "model": "x"},
                "master_gm": {"provider": "anthropic", "model": "y"},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(InvalidAgentConfig):
        load_config(path)


# ---------------------------------------------------------------------------
# 저장된 제공자의 키가 없으면 MissingApiKey — 다른 제공자로 갈아타지 않는다
# ---------------------------------------------------------------------------


def test_resolve_provider_raises_missing_api_key_when_env_unset():
    choices = {"action_classifier": AgentChoice(provider="anthropic", model="claude-haiku")}
    with pytest.raises(MissingApiKey):
        resolve_provider("action_classifier", choices, {})


# ---------------------------------------------------------------------------
# 두 역할에 다른 제공자·모델을 저장했다가 읽으면 서로 다른 값이 그대로 나온다 (D-32)
# ---------------------------------------------------------------------------


def test_two_roles_can_hold_different_provider_and_model(tmp_path):
    path = tmp_path / "agents.json"
    choices = {
        "action_classifier": AgentChoice(provider="anthropic", model="claude-haiku"),
        "master_gm": AgentChoice(provider="openai", model="gpt-5"),
    }
    save_config(path, choices)
    loaded = load_config(path)
    assert loaded["action_classifier"] != loaded["master_gm"]


# ---------------------------------------------------------------------------
# `gptrpg agents show` — 저장된 두 역할을 출력하고 키 값은 없다
# ---------------------------------------------------------------------------


def test_agents_show_prints_both_roles_without_key_values(tmp_path, capsys, monkeypatch):
    secret = "sk-super-secret-value-should-not-leak"
    monkeypatch.setenv("ANTHROPIC_API_KEY", secret)
    path = tmp_path / "agents.json"
    save_config(
        path,
        {
            "action_classifier": AgentChoice(provider="anthropic", model="claude-haiku"),
            "master_gm": AgentChoice(provider="openai", model="gpt-5"),
        },
    )

    exit_code = main(["agents", "show", "--config", str(path)])
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "action_classifier" in out
    assert "master_gm" in out
    assert "claude-haiku" in out
    assert "gpt-5" in out
    assert secret not in out


def test_agents_show_exits_nonzero_with_one_line_message_when_config_missing(tmp_path, capsys):
    exit_code = main(["agents", "show", "--config", str(tmp_path / "does-not-exist.json")])
    assert exit_code != 0

    err = capsys.readouterr().err.strip()
    assert err != ""
    assert "\n" not in err  # 한 줄 메시지 — 원시 역추적이 아니다


# ---------------------------------------------------------------------------
# `gptrpg agents select` — 두 역할을 각각 따로 돈다(D-32), 결과가 저장된다(D-33)
# ---------------------------------------------------------------------------


class _StubProvider:
    """`agents select` 시험 전용 — 네트워크를 전혀 타지 않는다."""

    def __init__(self, name: str, models: list[str]) -> None:
        self.name = name
        self._models = models

    def list_models(self) -> list[str]:
        return self._models

    def complete(self, **_kwargs):  # pragma: no cover - select 흐름은 complete를 부르지 않는다
        raise NotImplementedError

    def stream(self, **_kwargs):  # pragma: no cover
        raise NotImplementedError

    def last_result(self):  # pragma: no cover
        raise NotImplementedError


def test_agents_select_lets_each_role_pick_independently(tmp_path, monkeypatch, capsys):
    provider_a = _StubProvider("stub-a", ["model-a1", "model-a2"])
    provider_b = _StubProvider("stub-b", ["model-b1"])

    monkeypatch.setitem(providers_module.PROVIDER_ENV_VARS, "stub-a", "STUB_A_KEY")
    monkeypatch.setitem(providers_module.PROVIDER_FACTORIES, "stub-a", lambda api_key: provider_a)
    monkeypatch.setitem(providers_module.PROVIDER_ENV_VARS, "stub-b", "STUB_B_KEY")
    monkeypatch.setitem(providers_module.PROVIDER_FACTORIES, "stub-b", lambda api_key: provider_b)

    # 실제 다섯 제공자 키가 개발자 셸에 남아 있어도 이 시험 결과가 흔들리지 않도록
    # os.environ 자체를 두 스텁 키만 있는 값으로 완전히 바꿔치기한다.
    monkeypatch.setattr(os, "environ", {"STUB_A_KEY": "x", "STUB_B_KEY": "y"})

    # available_providers는 이름을 정렬해 돌려준다 -> ["stub-a", "stub-b"]
    # 역할1(action_classifier): stub-a(1번) 고르고 모델 2번(model-a2)
    # 역할2(master_gm): stub-b(2번) 고르고 모델 1번(model-b1)
    answers = iter(["1", "2", "2", "1"])
    monkeypatch.setattr("builtins.input", lambda *_args: next(answers))

    path = tmp_path / "agents.json"
    exit_code = main(["agents", "select", "--config", str(path)])
    assert exit_code == 0

    loaded = load_config(path)
    assert loaded["action_classifier"] == AgentChoice(provider="stub-a", model="model-a2")
    assert loaded["master_gm"] == AgentChoice(provider="stub-b", model="model-b1")
    assert loaded["action_classifier"] != loaded["master_gm"]

    out = capsys.readouterr().out
    assert str(path) in out


def test_agents_select_with_no_available_providers_exits_nonzero_and_lists_env_vars(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(os, "environ", {})
    exit_code = main(["agents", "select", "--config", str(tmp_path / "agents.json")])
    assert exit_code != 0

    err = capsys.readouterr().err
    for env_var in providers_module.PROVIDER_ENV_VARS.values():
        assert env_var in err
