from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from hallfix.application.executor import Executor
from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.models.tool import InstallationStrategy
from hallfix.domain.planning.action import ActionRisk, InstallPackageAction, RemovePackageAction
from hallfix.domain.planning.execution_plan import ExecutionPlan, PlannedAction
from hallfix.domain.registries.tool_registry import ToolRegistry
from hallfix.infrastructure.state.store import StateStore
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

_RISK = ActionRisk(
    risk_level=RiskLevel.LOW,
    requires_root=True,
    requires_network=True,
    reversible=True,
    rollback_strategy=None,
)


def _plan(action: object) -> ExecutionPlan:
    planned = PlannedAction(action=action, risk=_RISK, description="test")  # type: ignore[arg-type]
    return ExecutionPlan(
        id="HF-1",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        description="d",
        planned_actions=(planned,),
    )


def test_successful_install_records_ownership(tmp_path: Path) -> None:
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

    state_store = StateStore(path=tmp_path / "state.json")
    action = InstallPackageAction(
        tool_id="git",
        package="git",
        strategy=InstallationStrategy.APT,
        tool_risk_level=RiskLevel.LOW,
    )
    executor = Executor(
        command_runner=runner, tool_registry=ToolRegistry([_GIT_RAW]), state_store=state_store
    )
    executor.execute_plan(_plan(action))

    assert state_store.is_owned_by_hallfix("git") is True


def test_dry_run_never_touches_state_store(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    state_store = StateStore(path=tmp_path / "state.json")
    action = InstallPackageAction(
        tool_id="git",
        package="git",
        strategy=InstallationStrategy.APT,
        tool_risk_level=RiskLevel.LOW,
    )
    executor = Executor(
        command_runner=runner, tool_registry=ToolRegistry([_GIT_RAW]), state_store=state_store
    )
    executor.execute_plan(_plan(action), dry_run=True)

    assert not (tmp_path / "state.json").exists()
    assert state_store.get_tool_state("git") is None


def test_failed_install_does_not_record_ownership(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("apt-get", "install", "-y", "broken"),
        ok_result(("apt-get", "install", "-y", "broken"), "", exit_code=100),
    )
    state_store = StateStore(path=tmp_path / "state.json")
    action = InstallPackageAction(
        tool_id="broken",
        package="broken",
        strategy=InstallationStrategy.APT,
        tool_risk_level=RiskLevel.LOW,
    )
    executor = Executor(
        command_runner=runner, tool_registry=ToolRegistry([]), state_store=state_store
    )
    executor.execute_plan(_plan(action))

    assert state_store.get_tool_state("broken") is None


def test_successful_remove_clears_ownership(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("apt-get", "remove", "-y", "git"),
        ok_result(("apt-get", "remove", "-y", "git"), "Removing"),
    )
    state_store = StateStore(path=tmp_path / "state.json")
    state_store.record_installed("git")

    action = RemovePackageAction(
        tool_id="git",
        package="git",
        strategy=InstallationStrategy.APT,
        tool_risk_level=RiskLevel.LOW,
    )
    executor = Executor(
        command_runner=runner, tool_registry=ToolRegistry([_GIT_RAW]), state_store=state_store
    )
    executor.execute_plan(_plan(action))

    assert state_store.get_tool_state("git") is None


def test_executor_without_state_store_still_works() -> None:
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
    action = InstallPackageAction(
        tool_id="git",
        package="git",
        strategy=InstallationStrategy.APT,
        tool_risk_level=RiskLevel.LOW,
    )
    executor = Executor(command_runner=runner, tool_registry=ToolRegistry([_GIT_RAW]))
    result = executor.execute_plan(_plan(action))
    assert result.fully_succeeded
