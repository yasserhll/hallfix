"""Integration: real registry + real detection + real command execution
(git --version, etc. against this host). See test_system_info_cli.py for
why this lives in tests/integration rather than tests/unit.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from hallfix.cli.app import app

runner = CliRunner()
pytestmark = pytest.mark.integration


def test_tool_list_runs() -> None:
    result = runner.invoke(app, ["tool", "list"])
    assert result.exit_code == 0
    assert "git" in result.stdout


def test_tool_list_filters_by_category() -> None:
    result = runner.invoke(app, ["tool", "list", "--category", "essentials"])
    assert result.exit_code == 0
    assert "git" in result.stdout
    assert "docker" not in result.stdout


def test_tool_search_finds_git() -> None:
    result = runner.invoke(app, ["tool", "search", "version control"])
    assert result.exit_code == 0
    assert "git" in result.stdout


def test_tool_info_git_runs() -> None:
    result = runner.invoke(app, ["tool", "info", "git"])
    assert result.exit_code == 0
    assert "Git" in result.stdout
    assert "Compatibility" in result.stdout


def test_tool_info_unknown_tool_fails_cleanly() -> None:
    result = runner.invoke(app, ["tool", "info", "not-a-real-tool"])
    assert result.exit_code == 1
