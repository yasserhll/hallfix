from __future__ import annotations

from datetime import UTC, datetime

from hallfix.application.executor import Executor
from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.models.tool import InstallationStrategy
from hallfix.domain.planning.action import (
    ActionRisk,
    InstallPackageAction,
    RemovePackageAction,
    UpdatePackageIndexAction,
)
from hallfix.domain.planning.execution_plan import ExecutionPlan, PlannedAction
from hallfix.domain.registries.tool_registry import ToolRegistry
from tests.fixtures.fake_command_runner import FakeCommandRunner, ok_result

_GIT_RAW = {
    "id": "git",
    "name": "Git",
    "description": "VCS",
    "category": "essentials",
    "installation_strategies": ["APT"],
    "package_mappings": {"APT": "git"},
    "verification": {"executable": "git", "version_command": ["git", "--version"]},
}


def _install_action(package: str = "git") -> InstallPackageAction:
    return InstallPackageAction(
        tool_id="git",
        package=package,
        strategy=InstallationStrategy.APT,
        tool_risk_level=RiskLevel.LOW,
    )


def _plan(action: object) -> ExecutionPlan:
    risk = ActionRisk(
        risk_level=RiskLevel.LOW,
        requires_root=True,
        requires_network=True,
        reversible=True,
        rollback_strategy=None,
    )
    planned = PlannedAction(action=action, risk=risk, description="test")  # type: ignore[arg-type]
    return ExecutionPlan(
        id="HF-1",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        description="d",
        planned_actions=(planned,),
    )


def test_execute_install_success_runs_verification() -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("apt-get", "install", "-y", "git"),
        ok_result(("apt-get", "install", "-y", "git"), "Setting up git"),
    )
    runner.stub(
        ("dpkg-query", "-W", "-f=${Version}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Version}", "git"), "2.43.0"),
    )
    runner.stub(("git", "--version"), ok_result(("git", "--version"), "git version 2.43.0"))

    registry = ToolRegistry([_GIT_RAW])
    executor = Executor(command_runner=runner, tool_registry=registry)
    result = executor.execute_plan(_plan(_install_action()))

    assert result.fully_succeeded
    assert result.succeeded_count == 1
    action_result = result.action_results[0]
    assert action_result.verification is not None
    assert action_result.verification.executable_found
    assert action_result.verification.installed_version == "2.43.0"


def test_execute_install_dry_run_never_touches_runner_and_skips_verification() -> None:
    runner = FakeCommandRunner()  # unstubbed: must never be called
    registry = ToolRegistry([_GIT_RAW])
    executor = Executor(command_runner=runner, tool_registry=registry)
    result = executor.execute_plan(_plan(_install_action()), dry_run=True)

    assert result.dry_run
    assert result.action_results[0].dry_run
    assert result.action_results[0].verification is None
    assert runner.calls == []


def test_execute_install_failure_skips_verification() -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("apt-get", "install", "-y", "nonexistent-pkg"),
        ok_result(("apt-get", "install", "-y", "nonexistent-pkg"), "", exit_code=100),
    )
    registry = ToolRegistry([_GIT_RAW])
    executor = Executor(command_runner=runner, tool_registry=registry)
    result = executor.execute_plan(_plan(_install_action("nonexistent-pkg")))

    assert not result.fully_succeeded
    assert result.action_results[0].verification is None


def test_execute_install_missing_from_registry_skips_verification_but_still_succeeds() -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("apt-get", "install", "-y", "git"),
        ok_result(("apt-get", "install", "-y", "git"), "Setting up git"),
    )
    runner.stub(
        ("dpkg-query", "-W", "-f=${Version}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Version}", "git"), "2.43.0"),
    )
    empty_registry = ToolRegistry([])
    executor = Executor(command_runner=runner, tool_registry=empty_registry)
    result = executor.execute_plan(_plan(_install_action()))

    assert result.action_results[0].succeeded
    assert result.action_results[0].verification is None


def test_execute_remove() -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("apt-get", "remove", "-y", "git"),
        ok_result(("apt-get", "remove", "-y", "git"), "Removing"),
    )
    registry = ToolRegistry([_GIT_RAW])
    action = RemovePackageAction(
        tool_id="git",
        package="git",
        strategy=InstallationStrategy.APT,
        tool_risk_level=RiskLevel.LOW,
    )
    executor = Executor(command_runner=runner, tool_registry=registry)
    result = executor.execute_plan(_plan(action))
    assert result.fully_succeeded
    assert result.action_results[0].verification is None  # never verify after removal


def test_execute_refresh() -> None:
    runner = FakeCommandRunner()
    runner.stub(("apt-get", "update"), ok_result(("apt-get", "update"), "Fetched"))
    registry = ToolRegistry([])
    action = UpdatePackageIndexAction(strategy=InstallationStrategy.APT)
    executor = Executor(command_runner=runner, tool_registry=registry)
    result = executor.execute_plan(_plan(action))
    assert result.fully_succeeded


def test_failure_isolation_across_multiple_actions() -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("apt-get", "install", "-y", "git"),
        ok_result(("apt-get", "install", "-y", "git"), "Setting up git"),
    )
    runner.stub(
        ("dpkg-query", "-W", "-f=${Version}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Version}", "git"), "2.43.0"),
    )
    runner.stub(("git", "--version"), ok_result(("git", "--version"), "git version 2.43.0"))
    runner.stub(
        ("apt-get", "install", "-y", "broken-pkg"),
        ok_result(("apt-get", "install", "-y", "broken-pkg"), "", exit_code=100),
    )

    risk = ActionRisk(
        risk_level=RiskLevel.LOW,
        requires_root=True,
        requires_network=True,
        reversible=True,
        rollback_strategy=None,
    )
    good = PlannedAction(action=_install_action("git"), risk=risk, description="install git")
    bad = PlannedAction(
        action=_install_action("broken-pkg"), risk=risk, description="install broken-pkg"
    )
    plan = ExecutionPlan(
        id="HF-1",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        description="d",
        planned_actions=(good, bad),
    )

    registry = ToolRegistry([_GIT_RAW])
    executor = Executor(command_runner=runner, tool_registry=registry)
    result = executor.execute_plan(plan)

    assert not result.fully_succeeded
    assert result.succeeded_count == 1
    assert result.failed_count == 1
    assert result.action_results[0].succeeded
    assert not result.action_results[1].succeeded
