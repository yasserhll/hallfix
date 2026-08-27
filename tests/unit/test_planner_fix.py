from __future__ import annotations

from hallfix.application.planner import Planner
from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.models.fix import FixDefinition
from hallfix.domain.models.system import DistributionFamily, PackageManagerKind
from hallfix.domain.planning.action import RepairPackageManagerAction
from tests.fixtures.fake_command_runner import FakeCommandRunner, ok_result
from tests.fixtures.system_context_factory import make_system_context

_FIX = FixDefinition(
    id="fix.package_broken_state",
    description="Repair broken packages.",
    risk_level=RiskLevel.LOW,
    requires_root=True,
    backup_required=False,
    rollback_available=False,
    diagnostic_id="package.broken_state",
    supported_distributions=(DistributionFamily.DEBIAN,),
)

_APT_DEBIAN_CONTEXT = make_system_context(
    manager_kind=PackageManagerKind.APT, family=DistributionFamily.DEBIAN
)


def _planner(broken: bool) -> Planner:
    runner = FakeCommandRunner()
    stdout = "packages in an inconsistent state" if broken else ""
    runner.stub(("dpkg", "--audit"), ok_result(("dpkg", "--audit"), stdout))
    return Planner(command_runner=runner, id_factory=lambda: "HF-PLAN-test")


def test_plan_fix_builds_repair_action_when_broken_state_detected() -> None:
    plan = _planner(broken=True).plan_fix(_FIX, _APT_DEBIAN_CONTEXT)
    assert not plan.is_noop
    action = plan.planned_actions[0].action
    assert isinstance(action, RepairPackageManagerAction)
    assert action.fix_id == "fix.package_broken_state"
    assert action.manager_kind == PackageManagerKind.APT


def test_plan_fix_is_noop_when_nothing_broken() -> None:
    plan = _planner(broken=False).plan_fix(_FIX, _APT_DEBIAN_CONTEXT)
    assert plan.is_noop
    assert "nothing to repair" in plan.description.lower()


def test_plan_fix_noop_when_distribution_unsupported() -> None:
    arch_context = make_system_context(
        manager_kind=PackageManagerKind.PACMAN, family=DistributionFamily.ARCH
    )
    # dpkg check never reached — distribution check short-circuits first,
    # so an unstubbed runner proves that ordering.
    planner = Planner(command_runner=FakeCommandRunner(), id_factory=lambda: "HF-PLAN-test")
    plan = planner.plan_fix(_FIX, arch_context)
    assert plan.is_noop
    assert "not supported" in plan.description.lower()


def test_plan_fix_unknown_fix_id_is_noop() -> None:
    unknown_fix = FixDefinition(
        id="fix.does_not_exist",
        description="d",
        risk_level=RiskLevel.LOW,
        requires_root=True,
        backup_required=False,
        rollback_available=False,
        diagnostic_id="nothing",
    )
    # No dpkg branch matches this fix id, so it never checks broken state.
    planner = Planner(command_runner=FakeCommandRunner(), id_factory=lambda: "HF-PLAN-test")
    plan = planner.plan_fix(unknown_fix, _APT_DEBIAN_CONTEXT)
    assert plan.is_noop


def test_plan_fix_with_no_supported_distributions_restriction_applies_anywhere() -> None:
    unrestricted_fix = FixDefinition(
        id="fix.package_broken_state",
        description="d",
        risk_level=RiskLevel.LOW,
        requires_root=True,
        backup_required=False,
        rollback_available=False,
        diagnostic_id="package.broken_state",
        supported_distributions=(),
    )
    arch_context = make_system_context(
        manager_kind=PackageManagerKind.PACMAN, family=DistributionFamily.ARCH
    )
    plan = _planner(broken=True).plan_fix(unrestricted_fix, arch_context)
    assert not plan.is_noop
