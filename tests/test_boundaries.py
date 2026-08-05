"""경계 계약(.importlinter)이 실제로 규칙 코어를 가둔다는 것을 증명한다.

검사기가 0으로 끝나는 것만으로는 계약이 살아 있다는 증명이 되지 않는다 —
의도적으로 계약을 깨는 두 번째 테스트가 있어야 "있는 척"이 아님을 보인다.
"""

from pathlib import Path

import pytest
from importlinter import api  # noqa: F401  트리거: importlinter.configuration.configure()
from importlinter.application.use_cases import lint_imports

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROBE_PATH = PROJECT_ROOT / "src" / "gptrpg" / "rules_core" / "_boundary_probe.py"
AGENTS_PROBE_PATH = PROJECT_ROOT / "src" / "gptrpg" / "agents" / "_boundary_probe.py"


def test_import_contracts_are_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    """정상 상태에서는 두 계약(forbidden + layers) 모두 깨지지 않는다."""
    monkeypatch.chdir(PROJECT_ROOT)
    assert lint_imports(config_filename=".importlinter", is_debug_mode=True) is True


def test_contract_actually_catches_a_violation(monkeypatch: pytest.MonkeyPatch) -> None:
    """rules_core에 random을 가져다 쓰는 모듈을 넣으면 계약이 실제로 깨진다."""
    monkeypatch.chdir(PROJECT_ROOT)
    PROBE_PATH.write_text("import random\n\nvalue = random.random()\n", encoding="utf-8")
    try:
        assert lint_imports(config_filename=".importlinter", is_debug_mode=True) is False
    finally:
        PROBE_PATH.unlink(missing_ok=True)
        pycache = PROBE_PATH.parent / "__pycache__"
        if pycache.is_dir():
            for cached in pycache.glob(f"{PROBE_PATH.stem}.*"):
                cached.unlink(missing_ok=True)


def test_contract_3_actually_catches_an_agents_violation(monkeypatch: pytest.MonkeyPatch) -> None:
    """agents에 sqlite3를 가져다 쓰는 모듈을 넣으면 contract:3이 실제로 깨진다.

    contract:1(rules_core)은 위 테스트로 이미 증명됐지만, 이 리뷰가 검증하도록
    요청받은 경계는 contract:3(agents는 사건 저장소를 모른다)이다 — 같은
    forbidden 메커니즘을 쓴다는 추론만으로는 부족하다(WR-02).
    """
    monkeypatch.chdir(PROJECT_ROOT)
    AGENTS_PROBE_PATH.write_text("import sqlite3\n\nvalue = sqlite3.sqlite_version\n", encoding="utf-8")
    try:
        assert lint_imports(config_filename=".importlinter", is_debug_mode=True) is False
    finally:
        AGENTS_PROBE_PATH.unlink(missing_ok=True)
        pycache = AGENTS_PROBE_PATH.parent / "__pycache__"
        if pycache.is_dir():
            for cached in pycache.glob(f"{AGENTS_PROBE_PATH.stem}.*"):
                cached.unlink(missing_ok=True)
