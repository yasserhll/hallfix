"""Unit: exercises ``hallfix recommend`` branches that real-host integration
tests can't reach deterministically (whether anything matches) or
shouldn't (registry errors)."""

from __future__ import annotations

import pytest
from rich.console import Console
from typer.testing import CliRunner

from hallfix.cli.app import app
from hallfix.cli.commands.recommend import _render
from hallfix.domain.exceptions import RegistryError
from hallfix.domain.registries.recommendation import RecommendationResult

runner = CliRunner()


def test_render_reports_no_match_when_nothing_installed() -> None:
    console = Console(record=True, no_color=True, width=100)
    _render(console, RecommendationResult(matches=()))
    output = console.export_text()
    assert "No installed tools matched any known profile yet." in output
    assert "No changes have been made." in output


def test_recommend_profile_registry_error_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise() -> None:
        raise RegistryError("bad profile data")

    monkeypatch.setattr("hallfix.cli.commands.recommend.load_profile_registry", _raise)
    result = runner.invoke(app, ["recommend"])
    assert result.exit_code == 2
    assert "Profile registry error" in result.stderr


def test_recommend_tool_registry_error_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise() -> None:
        raise RegistryError("bad tool data")

    monkeypatch.setattr("hallfix.cli.commands.recommend.load_tool_registry", _raise)
    result = runner.invoke(app, ["recommend"])
    assert result.exit_code == 2
    assert "Tool registry error" in result.stderr
