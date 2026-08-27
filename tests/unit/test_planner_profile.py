from __future__ import annotations

from hallfix.application.planner import Planner
from hallfix.domain.models.profile import ProfileDefinition
from hallfix.domain.models.system import DistributionFamily, PackageManagerKind
from hallfix.domain.planning.action import InstallPackageAction
from hallfix.domain.registries.tool_registry import ToolRegistry
from hallfix.infrastructure.registries.tool_registry_loader import load_tool_registry
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
