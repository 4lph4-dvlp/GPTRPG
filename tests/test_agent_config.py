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
    ROLE_FALLBACKS,
    STRICT_AGENT_ROLES,
    AgentChoice,
    ConfigNotFound,
    InvalidAgentConfig,
    load_config,
    resolve_provider,
    save_config,
)
from gptrpg.agents.providers import MissingApiKey
from gptrpg.cli.main import main


def test_agent_roles_are_exactly_the_six_roles_in_order():
    assert AGENT_ROLES == (
        "action_classifier",
        "master_gm",
        "situation_judge",
        "scene_entity_judge",
        "clock_judge",
        "outcome_picker",
    )


def test_strict_agent_roles_are_still_the_original_two():
    assert STRICT_AGENT_ROLES == ("action_classifier", "master_gm")


def test_role_fallbacks_cover_exactly_the_four_new_roles():
    assert set(ROLE_FALLBACKS.keys()) == {
        "situation_judge",
        "scene_entity_judge",
        "clock_judge",
        "outcome_picker",
    }
    assert ROLE_FALLBACKS["situation_judge"] == "master_gm"
    assert ROLE_FALLBACKS["scene_entity_judge"] == "action_classifier"
    assert ROLE_FALLBACKS["clock_judge"] == "action_classifier"
    assert ROLE_FALLBACKS["outcome_picker"] == "action_classifier"


# ---------------------------------------------------------------------------
# save_config -> load_config 왕복에서 두 역할 값이 그대로 돌아온다
# ---------------------------------------------------------------------------


def test_save_then_load_round_trips_both_roles(tmp_path):
    """두 역할짜리 저장 파일이 `load_config`를 거쳐도 그 두 역할의 값은
    글자 그대로 그대로 돌아온다 — `ROLE_FALLBACKS`가 나머지 세 역할을 채우기
    때문에 09-01부터는 `load_config(path) == choices`(사전 전체 비교)가
    더 이상 성립하지 않는다(반환값에 세 역할이 더 들어 있다)."""
    path = tmp_path / "agents.json"
    choices = {
        "action_classifier": AgentChoice(provider="anthropic", model="claude-haiku"),
        "master_gm": AgentChoice(provider="openai", model="gpt-5"),
    }
    save_config(path, choices)
    loaded = load_config(path)
    assert loaded["action_classifier"] == choices["action_classifier"]
    assert loaded["master_gm"] == choices["master_gm"]


def test_two_role_config_file_loads_with_fallbacks_and_logs_four_stderr_lines(tmp_path, capsys):
    """회귀 방지 시험 — 기존 두 역할짜리 `agents.json`이 12-06 이후에도 예외
    없이 그대로 로드된다. `clock_judge`/`scene_entity_judge`/`outcome_picker`는
    `action_classifier`의 선택을, `situation_judge`는 `master_gm`의 선택을
    물려받고, 대체가 일어났다는 사실이 표준오류에 네 줄로 남는다."""
    path = tmp_path / "agents.json"
    choices = {
        "action_classifier": AgentChoice(provider="anthropic", model="claude-haiku"),
        "master_gm": AgentChoice(provider="openai", model="gpt-5"),
    }
    save_config(path, choices)

    loaded = load_config(path)

    assert set(loaded.keys()) == set(AGENT_ROLES)
    assert loaded["clock_judge"] == loaded["action_classifier"]
    assert loaded["scene_entity_judge"] == loaded["action_classifier"]
    assert loaded["outcome_picker"] == loaded["action_classifier"]
    assert loaded["situation_judge"] == loaded["master_gm"]

    err_lines = [line for line in capsys.readouterr().err.splitlines() if line.strip()]
    assert len(err_lines) == 4


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


def test_agents_show_prints_all_six_roles_without_key_values(tmp_path, capsys, monkeypatch):
    """12-06: 두 역할짜리 파일로도 `agents show`는 여섯 줄을 찍는다 —
    `ROLE_FALLBACKS`가 나머지 네 역할을 채우기 때문이다."""
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
    lines = [line for line in out.splitlines() if line.strip()]
    assert len(lines) == len(AGENT_ROLES) == 6
    for role in AGENT_ROLES:
        assert role in out
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
    """09-01: `AGENT_ROLES`가 다섯으로 늘어난 뒤로 `--role` 없는 `agents select`는
    다섯 역할을 전부 돈다(그 자체가 맞는 동작 — 490~451줄대 파서 관례). 이
    시험의 원래 뜻(「두 역할을 각각 따로 돈다」)은 `--role`을 하나씩 지정해
    두 번 부르는 것으로 그대로 유지한다 — 다섯 역할 전체를 다 채워야 하는
    입력 목록에 새 역할이 늘 때마다 이 시험이 다시 깨지는 것을 막는다."""
    provider_a = _StubProvider("stub-a", ["model-a1", "model-a2"])
    provider_b = _StubProvider("stub-b", ["model-b1"])

    monkeypatch.setitem(providers_module.PROVIDER_ENV_VARS, "stub-a", "STUB_A_KEY")
    monkeypatch.setitem(providers_module.PROVIDER_FACTORIES, "stub-a", lambda api_key: provider_a)
    monkeypatch.setitem(providers_module.PROVIDER_ENV_VARS, "stub-b", "STUB_B_KEY")
    monkeypatch.setitem(providers_module.PROVIDER_FACTORIES, "stub-b", lambda api_key: provider_b)

    # 실제 다섯 제공자 키가 개발자 셸에 남아 있어도 이 시험 결과가 흔들리지 않도록
    # os.environ 자체를 두 스텁 키만 있는 값으로 완전히 바꿔치기한다.
    monkeypatch.setattr(os, "environ", {"STUB_A_KEY": "x", "STUB_B_KEY": "y"})

    path = tmp_path / "agents.json"

    # available_providers는 이름을 정렬해 돌려준다 -> ["stub-a", "stub-b"]
    # action_classifier: stub-a(1번) 고르고 모델 2번(model-a2)
    answers_a = iter(["1", "2"])
    monkeypatch.setattr("builtins.input", lambda *_args: next(answers_a))
    exit_code = main(
        ["agents", "select", "--config", str(path), "--role", "action_classifier"]
    )
    assert exit_code == 0

    # master_gm: stub-b(2번) 고르고 모델 1번(model-b1)
    answers_b = iter(["2", "1"])
    monkeypatch.setattr("builtins.input", lambda *_args: next(answers_b))
    exit_code = main(["agents", "select", "--config", str(path), "--role", "master_gm"])
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


# ---------------------------------------------------------------------------
# G-11-2 — `agents set`/`agents show`가 실측 미달 모델을 stderr에 경고한다
# ---------------------------------------------------------------------------


def test_agents_set_with_known_undersized_model_warns_on_stderr_but_still_saves(
    tmp_path, capsys
):
    """경고가 저장을 막지 않는다 — 종료 코드 0, 파일에 그대로 저장된다."""
    path = tmp_path / "agents.json"
    exit_code = main(
        [
            "agents",
            "set",
            "--config",
            str(path),
            "--role",
            "action_classifier",
            "--provider",
            "nim",
            "--model",
            "meta/llama-3.1-8b-instruct",
        ]
    )
    assert exit_code == 0

    err = capsys.readouterr().err
    assert "경고" in err
    assert "action_classifier" in err
    assert "meta/llama-3.1-8b-instruct" in err

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["action_classifier"] == {
        "provider": "nim",
        "model": "meta/llama-3.1-8b-instruct",
    }


def test_agents_set_with_recommended_model_has_no_warning(tmp_path, capsys):
    path = tmp_path / "agents.json"
    exit_code = main(
        [
            "agents",
            "set",
            "--config",
            str(path),
            "--role",
            "master_gm",
            "--provider",
            "nim",
            "--model",
            "nvidia/nemotron-3-ultra-550b-a55b",
        ]
    )
    assert exit_code == 0
    assert "경고" not in capsys.readouterr().err


def test_agents_show_warns_on_stderr_for_known_undersized_model_without_polluting_stdout(
    tmp_path, capsys
):
    path = tmp_path / "agents.json"
    save_config(
        path,
        {
            "action_classifier": AgentChoice(
                provider="nim", model="meta/llama-3.1-8b-instruct"
            ),
            "master_gm": AgentChoice(
                provider="nim", model="nvidia/nemotron-3-ultra-550b-a55b"
            ),
        },
    )

    exit_code = main(["agents", "show", "--config", str(path)])
    assert exit_code == 0

    out, err = capsys.readouterr()
    # `agents show`는 여전히 AGENT_ROLES 개수만큼만 stdout에 찍는다 — 경고가
    # 이 계약을 깨지 않는다(`test_agents_show_prints_all_six_roles_without_key_values`
    # 회귀 방지와 같은 이유).
    lines = [line for line in out.splitlines() if line.strip()]
    assert len(lines) == len(AGENT_ROLES) == 6
    warning_lines = [line for line in err.splitlines() if line.startswith("경고")]
    assert len(warning_lines) == 1
    assert "action_classifier" in warning_lines[0]
    assert "master_gm" not in warning_lines[0]  # master_gm은 권장값이므로 경고가 없다
