"""역할별 제공자·모델 선택을 담는 작은 JSON 선호 파일 하나를 다루는 모듈.

사건 기록 저장소(`event_log`)의 순번·동시성 기계는 베끼지 않는다 — 이 파일이
다루는 문제는 그것과 다르다: 운영자 한 사람이 한 번 고른 선택을 다음 실행에서
다시 묻지 않도록 저장하는 것뿐이다(D-33). 저장 파일에는 제공자 이름과 모델
식별자 두 칸만 들어간다 — API 키는 이 파일에 절대 들어가지 않는다. 키는 매
실행마다 `os.environ`에서 다시 읽는다(`resolve_provider`가 그 자리다).

**왜 큰 소리로 실패하는 쪽을 골랐는지:** 이것은 플레이어가 아니라 운영자가
쓰는 도구다(`gptrpg agents select`/`gptrpg turn`을 손으로 돌리는 사람). 저장된
설정이 잘못됐거나 저장된 제공자의 키가 나중에 사라졌을 때, 다른 제공자로
조용히 갈아타면 어느 모델로 잰 숫자인지 Phase 6이 알 수 없게 된다(RESEARCH.md
Open Question 3 권고, `key_links` 참조) — 그래서 `load_config`/`resolve_provider`
둘 다 조용한 대체 없이 즉시 예외를 던진다. `get_rulebook`/`UnknownRulebook`이
세운 규율과 같은 이유다.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from gptrpg.agents.providers import PROVIDER_ENV_VARS, get_provider
from gptrpg.agents.providers.base import Provider

AGENT_ROLES: tuple[str, ...] = ("action_classifier", "master_gm")
"""D-32가 요구하는 두 에이전트 역할 — 각자 따로 제공자·모델을 고른다."""

DEFAULT_CONFIG_PATH = Path(".gptrpg/agents.json")
"""저장 파일의 기본 경로. `.gitignore`에 `.gptrpg/`가 있어 저장소에 안 들어간다."""


@dataclass(frozen=True)
class AgentChoice:
    """한 역할에 대해 고른 제공자·모델 한 짝."""

    provider: str
    model: str


class ConfigNotFound(Exception):
    """저장 파일이 없을 때 던진다. 빈 사전이나 임의의 기본값을 돌려주지 않는다."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"설정 파일이 없다: {path} — 먼저 'gptrpg agents select'를 실행하세요")
        self.path = path


class InvalidAgentConfig(Exception):
    """저장 파일의 모양이 기대와 다를 때 던진다(역할 누락·알 수 없는 제공자 이름)."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"설정 파일이 올바르지 않다 ({path}): {reason}")
        self.path = path
        self.reason = reason


def save_config(path: Path, choices: Mapping[str, AgentChoice]) -> None:
    """역할별 선택을 JSON으로 저장한다. 제공자 이름·모델 식별자 두 칸 외에는 아무것도 쓰지 않는다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        role: {"provider": choice.provider, "model": choice.model} for role, choice in choices.items()
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_config(path: Path) -> dict[str, AgentChoice]:
    """저장된 역할별 선택을 읽는다.

    파일이 없으면 `ConfigNotFound`. 두 역할 중 하나라도 빠졌거나 제공자
    이름이 `PROVIDER_ENV_VARS`에 없으면 `InvalidAgentConfig`.
    """
    if not path.exists():
        raise ConfigNotFound(path)

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InvalidAgentConfig(path, f"JSON 형식이 아니다: {exc}") from exc

    choices: dict[str, AgentChoice] = {}
    for role in AGENT_ROLES:
        entry = raw.get(role)
        if not isinstance(entry, dict) or "provider" not in entry or "model" not in entry:
            raise InvalidAgentConfig(path, f"역할 {role!r}의 선택이 없다")
        provider_name = entry["provider"]
        if provider_name not in PROVIDER_ENV_VARS:
            raise InvalidAgentConfig(path, f"알 수 없는 제공자 이름: {provider_name!r}")
        choices[role] = AgentChoice(provider=provider_name, model=entry["model"])
    return choices


def load_partial_config(path: Path) -> dict[str, AgentChoice]:
    """**고치기 위해** 읽는 경로 — 읽을 수 있는 역할만 담아 돌려주고 예외를 던지지 않는다.

    `load_config`와 목적이 다르다. `load_config`는 **쓰기 위해** 읽으므로 두
    역할이 다 채워져 있지 않으면 큰 소리로 실패해야 한다(그 함수 도크스트링의
    "왜 큰 소리로 실패하는 쪽을 골랐는지" 참조 — 어느 모델로 잰 숫자인지
    Phase 6이 알 수 없게 되는 것을 막는다). 반면 `agents set`/`agents select`는
    **파일을 완성해 가는 도중**에 파일을 읽는다 — 역할 하나를 막 저장한
    직후의 파일은 정의상 아직 불완전하다.

    이 함수가 없으면 실제로 값이 사라진다: `agents set --role A`로 A만 저장한
    파일을 `agents set --role B`가 `load_config`로 읽으면 「역할 B의 선택이
    없다」로 `InvalidAgentConfig`가 나고, 호출부는 빈 사전에서 다시 시작해
    **B만 남기고 A를 지운다.** 두 번 쳐서 두 역할을 채우는 것이 불가능해진다.

    파일이 없으면 빈 사전. JSON이 깨졌으면 빈 사전. 개별 역할 항목이 모양을
    어겼거나 알 수 없는 제공자 이름이면 그 항목만 건너뛴다 — 어느 경우에도
    예외를 던지지 않는다. 이 함수의 반환값을 **호출에 쓰면 안 된다**(그
    자리는 `load_config`다).
    """
    if not path.exists():
        return {}

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(raw, dict):
        return {}

    choices: dict[str, AgentChoice] = {}
    for role in AGENT_ROLES:
        entry = raw.get(role)
        if not isinstance(entry, dict):
            continue
        provider_name = entry.get("provider")
        model = entry.get("model")
        if not isinstance(provider_name, str) or not isinstance(model, str):
            continue
        if provider_name not in PROVIDER_ENV_VARS:
            continue
        choices[role] = AgentChoice(provider=provider_name, model=model)
    return choices


def resolve_provider(role: str, choices: Mapping[str, AgentChoice], env: Mapping[str, str]) -> Provider:
    """그 역할의 저장된 제공자를 실제로 만든다.

    환경에 키가 없으면 `MissingApiKey`가 그대로 위로 올라간다 — 다른
    제공자로 갈아타는 갈래를 만들지 않는다.
    """
    choice = choices[role]
    return get_provider(choice.provider, env)
