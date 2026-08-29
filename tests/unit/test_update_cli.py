"""Unit: registry-error handling for ``hallfix update system``/``tools`` —
same reasoning as test_plan_cli.py: not worth reaching via a real host.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from hallfix.cli.app import app
from hallfix.domain.exceptions import RegistryError

runner = CliRunner()


def _raise() -> None:
    raise RegistryError("bad tool data")


def test_update_system_registry_error_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("hallfix.cli.commands.update.load_tool_registry", _raise)
    result = runner.invoke(app, ["update", "system"])
    assert result.exit_code == 2
    assert "Tool registry error" in result.stderr


def test_update_tools_registry_error_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("hallfix.cli.commands.update.load_tool_registry", _raise)
    result = runner.invoke(app, ["update", "tools"])
    assert result.exit_code == 2
    assert "Tool registry error" in result.stderr
