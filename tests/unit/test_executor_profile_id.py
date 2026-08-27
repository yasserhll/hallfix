from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from hallfix.application.executor import Executor
from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.models.tool import InstallationStrategy
from hallfix.domain.planning.action import ActionRisk, InstallPackageAction
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


def test_profile_id_is_recorded_as_installed_for(tmp_path: Path) -> None:
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
    risk = ActionRisk(
        risk_level=RiskLevel.LOW,
        requires_root=True,
        requires_network=True,
        reversible=True,
        rollback_strategy=None,
    )
    plan = ExecutionPlan(
        id="HF-1",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        description="d",
        planned_actions=(PlannedAction(action=action, risk=risk, description="d"),),
    )

    executor = Executor(
        command_runner=runner, tool_registry=ToolRegistry([_GIT_RAW]), state_store=state_store
    )
    executor.execute_plan(plan, profile_id="developer")

    tool_state = state_store.get_tool_state("git")
    assert tool_state is not None
    assert tool_state.installed_for == ("developer",)


def test_no_profile_id_leaves_installed_for_empty(tmp_path: Path) -> None:
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
    risk = ActionRisk(
        risk_level=RiskLevel.LOW,
        requires_root=True,
        requires_network=True,
        reversible=True,
        rollback_strategy=None,
    )
    plan = ExecutionPlan(
        id="HF-1",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        description="d",
        planned_actions=(PlannedAction(action=action, risk=risk, description="d"),),
    )

    executor = Executor(
        command_runner=runner, tool_registry=ToolRegistry([_GIT_RAW]), state_store=state_store
    )
    executor.execute_plan(plan)

    tool_state = state_store.get_tool_state("git")
    assert tool_state is not None
    assert tool_state.installed_for == ()
