from __future__ import annotations

from pathlib import Path

from hallfix.application.planner import Planner
from hallfix.domain.models.state import HallfixState, ToolState
from hallfix.domain.models.system import DistributionFamily, PackageManagerKind
from hallfix.domain.planning.action import InstallPackageAction, UpgradeSystemAction
from hallfix.domain.registries.tool_registry import ToolRegistry
from hallfix.infrastructure.registries.tool_registry_loader import load_tool_registry
from hallfix.infrastructure.state.store import StateStore
from tests.fixtures.fake_command_runner import FakeCommandRunner, ok_result
from tests.fixtures.system_context_factory import make_system_context

_APT_CONTEXT = make_system_context(
    manager_kind=PackageManagerKind.APT, family=DistributionFamily.DEBIAN
)
_NO_MANAGER_CONTEXT = make_system_context(
    manager_kind=PackageManagerKind.UNKNOWN, family=DistributionFamily.DEBIAN
)


def _planner(runner: FakeCommandRunner) -> Planner:
    return Planner(command_runner=runner, id_factory=lambda: "HF-PLAN-test")


def _state_store(tmp_path: Path, state: HallfixState) -> StateStore:
    store = StateStore(path=tmp_path / "state.json")
    store.save(state)
    return store


def test_plan_system_upgrade_builds_single_action() -> None:
    plan = _planner(FakeCommandRunner()).plan_system_upgrade(_APT_CONTEXT)
    assert not plan.is_noop
    assert isinstance(plan.planned_actions[0].action, UpgradeSystemAction)


def test_plan_system_upgrade_noop_without_native_manager() -> None:
    plan = _planner(FakeCommandRunner()).plan_system_upgrade(_NO_MANAGER_CONTEXT)
    assert plan.is_noop


def test_plan_tool_update_builds_action_for_installed_tool() -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("dpkg-query", "-W", "-f=${Status}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Status}", "git"), "install ok installed"),
    )
    tool = load_tool_registry().get("git")
    assert tool is not None
    plan = _planner(runner).plan_tool_update(tool, _APT_CONTEXT)

    assert not plan.is_noop
    assert isinstance(plan.planned_actions[0].action, InstallPackageAction)


def test_plan_tool_update_never_installs_a_missing_tool() -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("dpkg-query", "-W", "-f=${Status}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Status}", "git"), "", exit_code=1),
    )
    tool = load_tool_registry().get("git")
    assert tool is not None
    plan = _planner(runner).plan_tool_update(tool, _APT_CONTEXT)

    assert plan.is_noop
    assert "not installed" in plan.description


def test_plan_tools_update_only_updates_hallfix_managed_tools(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("dpkg-query", "-W", "-f=${Status}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Status}", "git"), "install ok installed"),
    )
    state = HallfixState(
        tools={
            "git": ToolState(present_before_hallfix=False, installed_by_hallfix=True),
            "curl": ToolState(present_before_hallfix=True, installed_by_hallfix=False),
        }
    )
    plan = _planner(runner).plan_tools_update(
        load_tool_registry(), _APT_CONTEXT, _state_store(tmp_path, state)
    )

    assert not plan.is_noop
    assert len(plan.planned_actions) == 1
    assert plan.planned_actions[0].action.package == "git"  # type: ignore[union-attr]


def test_plan_tools_update_reports_unknown_tool_in_notes(tmp_path: Path) -> None:
    state = HallfixState(
        tools={
            "totally-not-a-real-tool": ToolState(
                present_before_hallfix=False, installed_by_hallfix=True
            )
        }
    )
    plan = _planner(FakeCommandRunner()).plan_tools_update(
        ToolRegistry([]), _APT_CONTEXT, _state_store(tmp_path, state)
    )
    assert plan.is_noop
    assert "unknown tool" in plan.notes[0]
