from __future__ import annotations

from datetime import UTC, datetime

from hallfix.application.executor import Executor
from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.models.system import PackageManagerKind
from hallfix.domain.planning.action import ActionRisk, RepairPackageManagerAction
from hallfix.domain.planning.execution_plan import ExecutionPlan, PlannedAction
from hallfix.domain.registries.tool_registry import ToolRegistry
from tests.fixtures.fake_command_runner import FakeCommandRunner, ok_result

_RISK = ActionRisk(
    risk_level=RiskLevel.LOW,
    requires_root=True,
    requires_network=False,
    reversible=False,
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


def test_execute_repair_success() -> None:
    runner = FakeCommandRunner()
    runner.stub(("dpkg", "--configure", "-a"), ok_result(("dpkg", "--configure", "-a"), ""))
    runner.stub(
        ("apt-get", "install", "--fix-broken", "-y"),
        ok_result(("apt-get", "install", "--fix-broken", "-y"), "0 upgraded"),
    )
    action = RepairPackageManagerAction(
        fix_id="fix.package_broken_state",
        manager_kind=PackageManagerKind.APT,
        fix_risk_level=RiskLevel.LOW,
    )
    executor = Executor(command_runner=runner, tool_registry=ToolRegistry([]))
    result = executor.execute_plan(_plan(action))

    assert result.fully_succeeded
    assert result.action_results[0].verification is None  # repair never runs tool verification


def test_execute_repair_dry_run_never_touches_runner() -> None:
    runner = FakeCommandRunner()  # unstubbed: must never be called
    action = RepairPackageManagerAction(
        fix_id="fix.package_broken_state",
        manager_kind=PackageManagerKind.APT,
        fix_risk_level=RiskLevel.LOW,
    )
    executor = Executor(command_runner=runner, tool_registry=ToolRegistry([]))
    result = executor.execute_plan(_plan(action), dry_run=True)

    assert result.action_results[0].dry_run
    assert runner.calls == []


def test_execute_repair_failure_reported() -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("dpkg", "--configure", "-a"), ok_result(("dpkg", "--configure", "-a"), "", exit_code=1)
    )
    runner.stub(
        ("apt-get", "install", "--fix-broken", "-y"),
        ok_result(("apt-get", "install", "--fix-broken", "-y"), "", exit_code=100),
    )
    action = RepairPackageManagerAction(
        fix_id="fix.package_broken_state",
        manager_kind=PackageManagerKind.APT,
        fix_risk_level=RiskLevel.LOW,
    )
    executor = Executor(command_runner=runner, tool_registry=ToolRegistry([]))
    result = executor.execute_plan(_plan(action))

    assert not result.fully_succeeded
