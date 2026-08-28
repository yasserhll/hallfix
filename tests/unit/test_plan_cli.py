"""Unit: exercises ``hallfix plan`` branches that real-host integration
tests can't reach deterministically — a MEDIUM+ risk plan's confirmation
notice (host-state-dependent whether e.g. docker is already installed,
same fragility class as the Phase 14 CI fix) and registry-error handling.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from rich.console import Console
from typer.testing import CliRunner

from hallfix.cli.app import app
from hallfix.cli.commands.plan import _render_human
from hallfix.domain.exceptions import RegistryError
from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.models.tool import InstallationStrategy
from hallfix.domain.planning.action import ActionRisk, InstallPackageAction
from hallfix.domain.planning.execution_plan import ExecutionPlan, PlannedAction

runner = CliRunner()


def test_render_human_notes_confirmation_required_for_medium_risk() -> None:
    action = InstallPackageAction(
        tool_id="docker",
        package="docker.io",
        strategy=InstallationStrategy.APT,
        tool_risk_level=RiskLevel.MEDIUM,
    )
    risk = ActionRisk(
        risk_level=RiskLevel.MEDIUM,
        requires_root=True,
        requires_network=True,
        reversible=True,
        rollback_strategy="remove_package",
    )
    plan = ExecutionPlan(
        id="HF-PLAN-1",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        description="Install docker",
        planned_actions=(PlannedAction(action=action, risk=risk, description="Install docker"),),
    )

    console = Console(record=True, no_color=True, width=100)
    _render_human(console, plan)
    output = console.export_text()
    assert "This plan requires explicit confirmation before it can be applied." in output
    assert "MEDIUM risk actions require explicit confirmation" in output


def test_plan_install_registry_error_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise() -> None:
        raise RegistryError("bad tool data")

    monkeypatch.setattr("hallfix.cli.commands.plan.load_tool_registry", _raise)
    result = runner.invoke(app, ["plan", "install", "git"])
    assert result.exit_code == 2
    assert "Tool registry error" in result.stderr


def test_plan_remove_registry_error_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise() -> None:
        raise RegistryError("bad tool data")

    monkeypatch.setattr("hallfix.cli.commands.plan.load_tool_registry", _raise)
    result = runner.invoke(app, ["plan", "remove", "git"])
    assert result.exit_code == 2
    assert "Tool registry error" in result.stderr
