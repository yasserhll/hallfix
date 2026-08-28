"""Unit: exercises ``hallfix history`` / ``hallfix history show`` against a
crafted ``HistoryStore`` record — no real command execution, so this covers
branches (failed outcomes, JSON output, per-outcome detail rendering) that
``tests/integration/test_history_cli.py`` can't safely reach without a real
failure on the host.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from typer.testing import CliRunner

from hallfix.cli.app import app
from hallfix.domain.models.history import ActionOutcome
from hallfix.infrastructure.state.history_store import HistoryStore

runner = CliRunner()

_OUTCOMES = (
    ActionOutcome(
        action_type="INSTALL_PACKAGE",
        succeeded=True,
        already_satisfied=False,
        message="Installed git",
        reversible=True,
        rollback_strategy="remove_package",
        tool_id="git",
        package="git",
        strategy="APT",
        risk_level="LOW",
    ),
    ActionOutcome(
        action_type="INSTALL_PACKAGE",
        succeeded=False,
        already_satisfied=False,
        message="Install failed: repository unreachable",
        tool_id="curl",
        package="curl",
        strategy="APT",
        risk_level="LOW",
    ),
)


def _seed_record() -> str:
    record = HistoryStore().append(
        command="tool install git curl",
        plan_id="HF-PLAN-1",
        plan_description="Install git, curl",
        dry_run=False,
        plan_reversible=False,
        action_outcomes=_OUTCOMES,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return record.id


def test_list_summary_shows_mixed_success_and_failure_counts() -> None:
    _seed_record()
    result = runner.invoke(app, ["history"])
    assert result.exit_code == 0
    assert "1 ok, 1 failed" in result.stdout


def test_list_json_output() -> None:
    record_id = _seed_record()
    result = runner.invoke(app, ["--json", "history"])
    assert result.exit_code == 0
    records = json.loads(result.stdout)
    assert len(records) == 1
    assert records[0]["id"] == record_id
    assert records[0]["command"] == "tool install git curl"


def test_show_json_output() -> None:
    record_id = _seed_record()
    result = runner.invoke(app, ["--json", "history", "show", record_id])
    assert result.exit_code == 0
    record = json.loads(result.stdout)
    assert record["id"] == record_id
    assert len(record["action_outcomes"]) == 2


def test_show_renders_each_outcome_and_totals() -> None:
    record_id = _seed_record()
    result = runner.invoke(app, ["history", "show", record_id])
    assert result.exit_code == 0
    assert "Installed git" in result.stdout
    assert "Install failed: repository unreachable" in result.stdout
    assert "Successful: 1  Failed: 1" in result.stdout
