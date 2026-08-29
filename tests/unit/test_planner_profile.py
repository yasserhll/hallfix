from __future__ import annotations

from pathlib import Path

from hallfix.application.planner import Planner
from hallfix.domain.models.profile import ProfileDefinition
from hallfix.domain.models.state import HallfixState, ToolState
from hallfix.domain.models.system import DistributionFamily, PackageManagerKind
from hallfix.domain.planning.action import InstallPackageAction, RemovePackageAction
from hallfix.domain.registries.tool_registry import ToolRegistry
from hallfix.infrastructure.registries.tool_registry_loader import load_tool_registry
from hallfix.infrastructure.state.store import StateStore
from tests.fixtures.fake_command_runner import FakeCommandRunner, ok_result
from tests.fixtures.system_context_factory import make_system_context

_APT_CONTEXT = make_system_context(
    manager_kind=PackageManagerKind.APT, family=DistributionFamily.DEBIAN
)


def _planner(runner: FakeCommandRunner) -> Planner:
    return Planner(command_runner=runner, id_factory=lambda: "HF-PLAN-test")


def test_profile_install_builds_actions_for_uninstalled_tools() -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("dpkg-query", "-W", "-f=${Status}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Status}", "git"), "", exit_code=1),
    )
    runner.stub(
        ("dpkg-query", "-W", "-f=${Status}", "curl"),
        ok_result(("dpkg-query", "-W", "-f=${Status}", "curl"), "", exit_code=1),
    )
    profile = ProfileDefinition(id="dev", name="Dev", description="d", tools=("git", "curl"))
    plan = _planner(runner).plan_profile_install(profile, load_tool_registry(), _APT_CONTEXT)

    assert not plan.is_noop
    assert plan.estimated_changes == 2
    packages = {
        a.action.package for a in plan.planned_actions if isinstance(a.action, InstallPackageAction)
    }
    assert packages == {"git", "curl"}


def test_profile_install_skips_already_installed_tools_via_notes() -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("dpkg-query", "-W", "-f=${Status}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Status}", "git"), "install ok installed"),
    )
    runner.stub(
        ("dpkg-query", "-W", "-f=${Version}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Version}", "git"), "2.45.0"),
    )
    profile = ProfileDefinition(id="dev", name="Dev", description="d", tools=("git",))
    plan = _planner(runner).plan_profile_install(profile, load_tool_registry(), _APT_CONTEXT)

    assert plan.is_noop
    assert len(plan.notes) == 1
    assert "already installed" in plan.notes[0].lower()


def test_profile_install_reports_unknown_tool_in_notes() -> None:
    runner = FakeCommandRunner()  # unstubbed: must never be called for the unknown tool
    profile = ProfileDefinition(
        id="dev", name="Dev", description="d", tools=("totally-not-a-real-tool",)
    )
    plan = _planner(runner).plan_profile_install(profile, ToolRegistry([]), _APT_CONTEXT)

    assert plan.is_noop
    assert "unknown tool" in plan.notes[0]
    assert runner.calls == []


def test_profile_install_mixes_installed_and_uninstalled_tools() -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("dpkg-query", "-W", "-f=${Status}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Status}", "git"), "install ok installed"),
    )
    runner.stub(
        ("dpkg-query", "-W", "-f=${Version}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Version}", "git"), "2.45.0"),
    )
    runner.stub(
        ("dpkg-query", "-W", "-f=${Status}", "curl"),
        ok_result(("dpkg-query", "-W", "-f=${Status}", "curl"), "", exit_code=1),
    )
    profile = ProfileDefinition(id="dev", name="Dev", description="d", tools=("git", "curl"))
    plan = _planner(runner).plan_profile_install(profile, load_tool_registry(), _APT_CONTEXT)

    assert plan.estimated_changes == 1
    assert len(plan.notes) == 1
    assert plan.planned_actions[0].action.package == "curl"  # type: ignore[union-attr]


def _state_store(tmp_path: Path, state: HallfixState) -> StateStore:
    store = StateStore(path=tmp_path / "state.json")
    store.save(state)
    return store


def test_profile_remove_plans_tools_owned_solely_by_this_profile(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("dpkg-query", "-W", "-f=${Status}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Status}", "git"), "install ok installed"),
    )
    profile = ProfileDefinition(id="dev", name="Dev", description="d", tools=("git",))
    state = HallfixState(
        tools={
            "git": ToolState(
                present_before_hallfix=False, installed_by_hallfix=True, installed_for=("dev",)
            )
        }
    )
    plan = _planner(runner).plan_profile_remove(
        profile, load_tool_registry(), _APT_CONTEXT, _state_store(tmp_path, state)
    )

    assert not plan.is_noop
    assert isinstance(plan.planned_actions[0].action, RemovePackageAction)
    assert plan.planned_actions[0].action.package == "git"


def test_profile_remove_skips_tool_still_shared_with_another_profile(tmp_path: Path) -> None:
    runner = FakeCommandRunner()  # unstubbed: must never be called for a skipped tool
    profile = ProfileDefinition(id="dev", name="Dev", description="d", tools=("git",))
    state = HallfixState(
        tools={
            "git": ToolState(
                present_before_hallfix=False,
                installed_by_hallfix=True,
                installed_for=("dev", "devops"),
            )
        }
    )
    plan = _planner(runner).plan_profile_remove(
        profile, load_tool_registry(), _APT_CONTEXT, _state_store(tmp_path, state)
    )

    assert plan.is_noop
    assert "also used by: devops" in plan.notes[0]
    assert runner.calls == []


def test_profile_remove_skips_tool_not_managed_by_hallfix(tmp_path: Path) -> None:
    runner = FakeCommandRunner()  # unstubbed: must never touch a tool Hallfix didn't install
    profile = ProfileDefinition(id="dev", name="Dev", description="d", tools=("git",))
    state = HallfixState(
        tools={"git": ToolState(present_before_hallfix=True, installed_by_hallfix=False)}
    )
    plan = _planner(runner).plan_profile_remove(
        profile, load_tool_registry(), _APT_CONTEXT, _state_store(tmp_path, state)
    )

    assert plan.is_noop
    assert "not installed by Hallfix" in plan.notes[0]
    assert runner.calls == []


def test_profile_remove_skips_tool_never_observed_at_all(tmp_path: Path) -> None:
    runner = FakeCommandRunner()  # unstubbed
    profile = ProfileDefinition(id="dev", name="Dev", description="d", tools=("git",))
    plan = _planner(runner).plan_profile_remove(
        profile, load_tool_registry(), _APT_CONTEXT, _state_store(tmp_path, HallfixState())
    )

    assert plan.is_noop
    assert "not installed by Hallfix" in plan.notes[0]
    assert runner.calls == []


def test_profile_remove_reports_unknown_tool_in_notes(tmp_path: Path) -> None:
    runner = FakeCommandRunner()  # unstubbed
    profile = ProfileDefinition(
        id="dev", name="Dev", description="d", tools=("totally-not-a-real-tool",)
    )
    plan = _planner(runner).plan_profile_remove(
        profile, ToolRegistry([]), _APT_CONTEXT, _state_store(tmp_path, HallfixState())
    )

    assert plan.is_noop
    assert "unknown tool" in plan.notes[0]
    assert runner.calls == []
