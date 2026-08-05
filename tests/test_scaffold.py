"""프로젝트 골격이 서 있는지 확인한다."""

import importlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_package_and_subpackages_import() -> None:
    for module_name in (
        "gptrpg",
        "gptrpg.rules_core",
        "gptrpg.event_log",
        "gptrpg.session_actor",
        "gptrpg.cli",
    ):
        importlib.import_module(module_name)


def test_pytest_config_present() -> None:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.pytest.ini_options]" in pyproject
