from __future__ import annotations

from hallfix.application.planner import Planner
from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.models.system import DistributionFamily, PackageManagerKind
from hallfix.domain.models.tool import InstallationStrategy, ToolDefinition
from hallfix.domain.planning.action import InstallPackageAction, RemovePackageAction
from tests.fixtures.fake_command_runner import FakeCommandRunner, ok_result
from tests.fixtures.system_context_factory import make_system_context

_GIT = ToolDefinition(
    id="git",
    name="Git",
    description="VCS",
    category="essentials",
    installation_strategies=(InstallationStrategy.APT,),
    package_mappings={InstallationStrategy.APT: "git"},
    risk_level=RiskLevel.LOW,
)

_DOCKER = ToolDefinition(
    id="docker",
    name="Docker",
    description="Containers",
    category="containers",
    installation_strategies=(InstallationStrategy.APT,),
    package_mappings={InstallationStrategy.APT: "docker.io"},
    risk_level=RiskLevel.MEDIUM,
)

_BLACK = ToolDefinition(
    id="black",
    name="Black",
    description="Formatter",
    category="development",
    installation_strategies=(InstallationStrategy.PIP,),
    package_mappings={InstallationStrategy.PIP: "black"},
)

_UNSUPPORTED_HERE = ToolDefinition(
    id="thing",
    name="Thing",
    description="Only on pacman",
    category="misc",
    installation_strategies=(InstallationStrategy.PACMAN,),
    package_mappings={InstallationStrategy.PACMAN: "thing"},
)

_APT_CONTEXT = make_system_context(
    manager_kind=PackageManagerKind.APT, family=DistributionFamily.DEBIAN
)


def _fixed_id_planner(runner: FakeCommandRunner) -> Planner:
    return Planner(command_runner=runner, id_factory=lambda: "HF-PLAN-test")


def test_plan_install_builds_action_when_not_installed() -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("dpkg-query", "-W", "-f=${Status}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Status}", "git"), "", exit_code=1),
    )
    plan = _fixed_id_planner(runner).plan_tool_install(_GIT, _APT_CONTEXT)
    assert not plan.is_noop
    assert plan.estimated_changes == 1
    action = plan.planned_actions[0].action
    assert isinstance(action, InstallPackageAction)
    assert action.package == "git"
    assert action.strategy == InstallationStrategy.APT
    assert plan.risk_level == RiskLevel.LOW
    assert plan.requires_root is True


def test_plan_install_is_noop_when_already_installed() -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("dpkg-query", "-W", "-f=${Status}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Status}", "git"), "install ok installed"),
    )
    runner.stub(
        ("dpkg-query", "-W", "-f=${Version}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Version}", "git"), "1:2.43.0-1"),
    )
    plan = _fixed_id_planner(runner).plan_tool_install(_GIT, _APT_CONTEXT)
    assert plan.is_noop
    assert "already installed" in plan.description.lower() or "already installed" in str(
        plan.description
    )


def test_plan_install_docker_carries_medium_risk() -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("dpkg-query", "-W", "-f=${Status}", "docker.io"),
        ok_result(("dpkg-query", "-W", "-f=${Status}", "docker.io"), "", exit_code=1),
    )
    plan = _fixed_id_planner(runner).plan_tool_install(_DOCKER, _APT_CONTEXT)
    assert plan.risk_level == RiskLevel.MEDIUM


def test_plan_install_below_minimum_version_still_plans_install() -> None:
    tool = ToolDefinition(
        id="git",
        name="Git",
        description="VCS",
        category="essentials",
        installation_strategies=(InstallationStrategy.APT,),
        package_mappings={InstallationStrategy.APT: "git"},
        minimum_version="9.99",
    )
    runner = FakeCommandRunner()
    runner.stub(
        ("dpkg-query", "-W", "-f=${Status}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Status}", "git"), "install ok installed"),
    )
    runner.stub(
        ("dpkg-query", "-W", "-f=${Version}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Version}", "git"), "1:2.43.0-1"),
    )
    plan = _fixed_id_planner(runner).plan_tool_install(tool, _APT_CONTEXT)
    assert not plan.is_noop


def test_plan_install_unresolvable_strategy_is_noop() -> None:
    runner = FakeCommandRunner()  # unstubbed: must never be called
    plan = _fixed_id_planner(runner).plan_tool_install(_UNSUPPORTED_HERE, _APT_CONTEXT)
    assert plan.is_noop
    assert runner.calls == []


def test_plan_install_non_native_strategy_is_noop_with_explanation() -> None:
    runner = FakeCommandRunner()  # unstubbed: must never be called
    plan = _fixed_id_planner(runner).plan_tool_install(_BLACK, _APT_CONTEXT)
    assert plan.is_noop
    assert "cannot execute yet" in plan.description
    assert runner.calls == []


def test_plan_remove_builds_action_when_installed() -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("dpkg-query", "-W", "-f=${Status}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Status}", "git"), "install ok installed"),
    )
    plan = _fixed_id_planner(runner).plan_tool_remove(_GIT, _APT_CONTEXT)
    assert not plan.is_noop
    action = plan.planned_actions[0].action
    assert isinstance(action, RemovePackageAction)
    assert plan.reversible is False  # RiskEvaluator never claims remove is reversible


def test_plan_remove_is_noop_when_not_installed() -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("dpkg-query", "-W", "-f=${Status}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Status}", "git"), "", exit_code=1),
    )
    plan = _fixed_id_planner(runner).plan_tool_remove(_GIT, _APT_CONTEXT)
    assert plan.is_noop


def test_plan_refresh_metadata_uses_native_strategy() -> None:
    runner = FakeCommandRunner()
    plan = _fixed_id_planner(runner).plan_refresh_metadata(_APT_CONTEXT)
    assert not plan.is_noop
    assert plan.planned_actions[0].action.strategy == InstallationStrategy.APT
    assert runner.calls == []  # no reads needed to plan a refresh


def test_plan_refresh_metadata_noop_for_unknown_manager() -> None:
    ctx = make_system_context(
        manager_kind=PackageManagerKind.UNKNOWN, family=DistributionFamily.UNKNOWN
    )
    runner = FakeCommandRunner()
    plan = _fixed_id_planner(runner).plan_refresh_metadata(ctx)
    assert plan.is_noop
