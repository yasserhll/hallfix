"""Integration: real HistoryStore (isolated per test via the autouse XDG
fixture) against this host. Never exercises a real rollback mutation —
on a fresh, empty history there is nothing eligible anyway, which is
itself the thing being verified.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from hallfix.cli.app import app

runner = CliRunner()
pytestmark = pytest.mark.integration


def test_rollback_with_no_history_reports_nothing_found() -> None:
    result = runner.invoke(app, ["rollback"])
    assert result.exit_code == 0
    assert "No rollback-eligible operations found" in result.stdout


def test_rollback_unknown_operation_id_fails_cleanly() -> None:
    result = runner.invoke(app, ["rollback", "HF-999"])
    assert result.exit_code == 1


def test_rollback_after_noop_install_has_nothing_eligible() -> None:
    install_result = runner.invoke(app, ["tool", "install", "git"])
    assert install_result.exit_code == 0  # git already installed -> no-op, no history detail

    rollback_result = runner.invoke(app, ["rollback"])
    assert rollback_result.exit_code == 0
    assert "No rollback-eligible operations found" in rollback_result.stdout
