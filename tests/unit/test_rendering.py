from __future__ import annotations

from datetime import UTC, datetime

from rich.console import Console

from hallfix.cli.rendering import render_execution_result, render_plan_human
from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.models.tool import InstallationStrategy, ToolVerificationResult
from hallfix.domain.planning.action import ActionRisk, InstallPackageAction
from hallfix.domain.planning.execution_plan import ExecutionPlan, PlannedAction
from hallfix.domain.planning.execution_result import ActionExecutionResult, PlanExecutionResult

_NOW = datetime(2026, 1, 1, tzinfo=UTC)

_RISK = ActionRisk(
    risk_level=RiskLevel.LOW,
    requires_root=True,
    requires_network=True,
    reversible=True,
    rollback_strategy="remove_package",
)

_ACTION = InstallPackageAction(
    tool_id="git", package="git", strategy=InstallationStrategy.APT, tool_risk_level=RiskLevel.LOW
)


def _console() -> Console:
    return Console(record=True, no_color=True, width=100)


def _plan(*, noop: bool) -> ExecutionPlan:
    planned = (
        () if noop else (PlannedAction(action=_ACTION, risk=_RISK, description="Install git"),)
    )
    return ExecutionPlan(
        id="HF-PLAN-1",
        created_at=_NOW,
        description="Install git" if not noop else "Nothing to do",
        planned_actions=planned,
        notes=("heads up",) if not noop else (),
    )


def test_render_plan_human_noop() -> None:
    console = _console()
    render_plan_human(console, _plan(noop=True))
    output = console.export_text()
    assert "No actions required. No changes were made." in output


def test_render_plan_human_with_actions() -> None:
    console = _console()
    render_plan_human(console, _plan(noop=False))
    output = console.export_text()
    assert "Install git" in output
    assert "heads up" in output
    assert "Requires administrator privileges: YES" in output
    assert "Requires Internet: YES" in output
    assert "Reversible: YES" in output
    assert "No changes were made." in output


def test_render_execution_result_success_with_verification() -> None:
    console = _console()
    result = PlanExecutionResult(
        plan_id="HF-PLAN-1",
        dry_run=False,
        action_results=(
            ActionExecutionResult(
                action=_ACTION,
                succeeded=True,
                already_satisfied=False,
                message="Installed git",
                dry_run=False,
                verification=ToolVerificationResult(
                    tool_id="git",
                    executable_found=True,
                    installed_version="2.40.0",
                    meets_minimum_version=True,
                    meets_recommended_version=True,
                ),
            ),
        ),
    )

    render_execution_result(console, result)
    output = console.export_text()
    assert "✓ Installed git" in output
    assert "Executable found (version 2.40.0)" in output
    assert "Successful: 1  Failed: 0" in output
    assert "Completed with warnings." not in output


def test_render_execution_result_failure_and_missing_verification() -> None:
    console = _console()
    result = PlanExecutionResult(
        plan_id="HF-PLAN-1",
        dry_run=False,
        action_results=(
            ActionExecutionResult(
                action=_ACTION,
                succeeded=False,
                already_satisfied=False,
                message="Install failed",
                dry_run=False,
                verification=ToolVerificationResult(
                    tool_id="git",
                    executable_found=False,
                    installed_version=None,
                    meets_minimum_version=None,
                    meets_recommended_version=None,
                ),
            ),
        ),
    )

    render_execution_result(console, result)
    output = console.export_text()
    assert "✗ Install failed" in output
    assert "Executable not found after installation" in output
    assert "Successful: 0  Failed: 1" in output
    assert "Completed with warnings." in output
