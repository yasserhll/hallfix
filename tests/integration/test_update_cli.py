"""Integration: real registries + real detection against this host. Only
exercises --dry-run for the mutating subcommands (system/tools), same
reasoning as test_tool_install_cli.py — real mutation is never run from an
automated test. `update hallfix` never mutates anything (it's purely
informational), so it's exercised for real."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from hallfix.cli.app import app
from hallfix.domain.models.state import HallfixState, ToolState
from hallfix.infrastructure.state.store import StateStore

runner = CliRunner()
pytestmark = pytest.mark.integration


def test_update_hallfix_reports_unavailable() -> None:
    result = runner.invoke(app, ["update", "hallfix"])
    assert result.exit_code == 0
    assert "no distribution channel" in result.stdout.lower()


def test_update_hallfix_json_is_valid() -> None:
    result = runner.invoke(app, ["--json", "update", "hallfix"])
    payload = json.loads(result.stdout)
    assert payload["available"] is False


def test_dry_run_update_system_shows_plan_or_noop() -> None:
    result = runner.invoke(app, ["--dry-run", "update", "system"])
    assert result.exit_code == 0
    assert "No changes were made." in result.stdout


def test_dry_run_update_tools_shows_plan_or_noop() -> None:
    result = runner.invoke(app, ["--dry-run", "update", "tools"])
    assert result.exit_code == 0
    assert "No changes were made." in result.stdout


def test_update_tools_reports_unknown_tool_in_notes() -> None:
    # Isolated StateStore (autouse XDG fixture): a Hallfix-managed tool id
    # that isn't in the registry is a deterministic, host-independent way
    # to reach plan_tools_update's "unknown tool, skipped" note.
    StateStore().save(
        HallfixState(
            tools={
                "totally-not-a-real-tool": ToolState(
                    present_before_hallfix=False, installed_by_hallfix=True
                )
            }
        )
    )
    result = runner.invoke(app, ["update", "tools"])
    assert result.exit_code == 0
    assert "unknown tool, skipped" in result.stdout
