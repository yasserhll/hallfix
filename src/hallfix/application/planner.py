"""Planner (spec §5): builds an ``ExecutionPlan`` for a tool install/remove.

Lives in ``application/``, not ``domain/planning/``, because it needs real
reads (``PackageManager.is_installed``/``get_version``) to decide
idempotence — the domain layer stays I/O-free, and this is exactly what
the application layer is for: orchestrating domain logic (RiskEvaluator,
compatibility resolution) with infrastructure (CommandRunner, package
manager adapters).

Building a plan never modifies the system — the only "dry-run" concept
that exists yet, since there is no Executor to actually apply a plan
(that's Phase 6). Every read here (``is_installed``, ``get_version``) is
real regardless of any future ``--dry-run`` flag, matching the read/write
distinction established in Phase 3.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from hallfix.detectors.package_health import check_dpkg_broken_state
from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.models.fix import FixDefinition
from hallfix.domain.models.history import OperationRecord
from hallfix.domain.models.profile import ProfileDefinition
from hallfix.domain.models.system import SystemContext
from hallfix.domain.models.tool import (
    NATIVE_INSTALLATION_STRATEGIES,
    InstallationStrategy,
    ToolDefinition,
)
from hallfix.domain.planning.action import (
    InstallPackageAction,
    RemovePackageAction,
    RepairPackageManagerAction,
    UpdatePackageIndexAction,
)
from hallfix.domain.planning.execution_plan import ExecutionPlan, PlannedAction
from hallfix.domain.planning.risk_evaluator import RiskEvaluator
from hallfix.domain.registries.compatibility import (
    NATIVE_STRATEGY_BY_MANAGER,
    resolve_installation_strategy,
)
from hallfix.domain.registries.tool_registry import ToolRegistry
from hallfix.infrastructure.commands.runner import CommandRunner
from hallfix.infrastructure.package_managers.registry import create_package_manager
from hallfix.infrastructure.state.store import StateStore
from hallfix.utils.version import meets_minimum


def _default_clock() -> datetime:
    return datetime.now(UTC)


def _new_plan_id() -> str:
    return f"HF-PLAN-{uuid.uuid4().hex[:8]}"


class Planner:
    def __init__(
        self,
        *,
        command_runner: CommandRunner,
        root: Path = Path("/"),
        clock: Callable[[], datetime] = _default_clock,
        id_factory: Callable[[], str] = _new_plan_id,
    ) -> None:
        self._command_runner = command_runner
        self._root = root
        self._clock = clock
        self._id_factory = id_factory
        self._risk_evaluator = RiskEvaluator()

    def plan_tool_install(self, tool: ToolDefinition, context: SystemContext) -> ExecutionPlan:
        strategy = resolve_installation_strategy(tool, context)
        if strategy is None:
            return self._empty_plan(
                f"No usable installation strategy for {tool.name} on this system."
            )
        if strategy not in NATIVE_INSTALLATION_STRATEGIES:
            return self._empty_plan(
                f"{tool.name} requires strategy {strategy.value}, which Hallfix cannot execute yet."
            )

        manager = create_package_manager(
            context.package_manager.kind, command_runner=self._command_runner, root=self._root
        )
        if manager is None:  # pragma: no cover - guaranteed by resolve_installation_strategy
            return self._empty_plan(f"No package manager available for {tool.name}.")

        package = tool.package_mappings[strategy]
        if manager.is_installed(package):
            installed_version = manager.get_version(package)
            if meets_minimum(installed_version, tool.minimum_version) is not False:
                suffix = f" (version {installed_version})" if installed_version else ""
                return self._empty_plan(f"{tool.name} is already installed{suffix}.")

        action = InstallPackageAction(
            tool_id=tool.id, package=package, strategy=strategy, tool_risk_level=tool.risk_level
        )
        risk = self._risk_evaluator.evaluate(action)
        planned = PlannedAction(
            action=action,
            risk=risk,
            description=f"Install {tool.name} via {strategy.value} (package: {package})",
        )
        return self._build_plan(f"Install {tool.name}", [planned])

    def plan_tool_remove(self, tool: ToolDefinition, context: SystemContext) -> ExecutionPlan:
        strategy = resolve_installation_strategy(tool, context)
        if strategy is None or strategy not in NATIVE_INSTALLATION_STRATEGIES:
            return self._empty_plan(f"No usable removal strategy for {tool.name} on this system.")

        manager = create_package_manager(
            context.package_manager.kind, command_runner=self._command_runner, root=self._root
        )
        if manager is None:  # pragma: no cover - guaranteed by resolve_installation_strategy
            return self._empty_plan(f"No package manager available for {tool.name}.")

        package = tool.package_mappings[strategy]
        if not manager.is_installed(package):
            return self._empty_plan(f"{tool.name} is not installed.")

        action = RemovePackageAction(
            tool_id=tool.id, package=package, strategy=strategy, tool_risk_level=tool.risk_level
        )
        risk = self._risk_evaluator.evaluate(action)
        planned = PlannedAction(
            action=action,
            risk=risk,
            description=f"Remove {tool.name} via {strategy.value} (package: {package})",
        )
        return self._build_plan(f"Remove {tool.name}", [planned])

    def plan_profile_install(
        self, profile: ProfileDefinition, tool_registry: ToolRegistry, context: SystemContext
    ) -> ExecutionPlan:
        """Builds one plan covering every tool in the profile.

        Reuses ``plan_tool_install`` per tool rather than duplicating its
        idempotence/compatibility logic — spec §35: custom profiles (and,
        by the same reasoning, every profile) must go through the same
        Planner, never a second install path.
        """
        planned: list[PlannedAction] = []
        notes: list[str] = []

        for tool_id in profile.tools:
            tool = tool_registry.get(tool_id)
            if tool is None:
                notes.append(f"{tool_id}: unknown tool, skipped")
                continue
            single_plan = self.plan_tool_install(tool, context)
            if single_plan.is_noop:
                notes.append(f"{tool.name}: {single_plan.description}")
                continue
            planned.extend(single_plan.planned_actions)

        description = (
            f"Install {profile.name} profile: {len(planned)} to install, "
            f"{len(notes)} already satisfied or unavailable"
        )
        return ExecutionPlan(
            id=self._id_factory(),
            created_at=self._clock(),
            description=description,
            planned_actions=tuple(planned),
            notes=tuple(notes),
        )

    def plan_profile_remove(
        self,
        profile: ProfileDefinition,
        tool_registry: ToolRegistry,
        context: SystemContext,
        state_store: StateStore,
    ) -> ExecutionPlan:
        """Builds one plan removing this profile's Hallfix-managed tools.

        Spec §37: "Never remove shared dependencies blindly" — a tool is
        only planned for removal when Hallfix actually installed it (never
        a pre-existing tool Hallfix merely observed) *and* no other profile
        still claims it via ``StateStore``'s ``installed_for`` ownership
        record. Reuses ``plan_tool_remove`` per surviving tool for the same
        reason ``plan_profile_install`` reuses ``plan_tool_install`` — one
        Planner path, never a second removal system.
        """
        planned: list[PlannedAction] = []
        notes: list[str] = []

        for tool_id in profile.tools:
            tool = tool_registry.get(tool_id)
            if tool is None:
                notes.append(f"{tool_id}: unknown tool, skipped")
                continue

            tool_state = state_store.get_tool_state(tool_id)
            if tool_state is None or not tool_state.installed_by_hallfix:
                notes.append(f"{tool.name}: not installed by Hallfix, skipped")
                continue

            other_owners = tuple(p for p in tool_state.installed_for if p != profile.id)
            if other_owners:
                notes.append(
                    f"{tool.name} is also used by: {', '.join(other_owners)}. Removal skipped."
                )
                continue

            single_plan = self.plan_tool_remove(tool, context)
            if single_plan.is_noop:
                notes.append(f"{tool.name}: {single_plan.description}")
                continue
            planned.extend(single_plan.planned_actions)

        description = (
            f"Remove {profile.name} profile: {len(planned)} to remove, "
            f"{len(notes)} skipped or already absent"
        )
        return ExecutionPlan(
            id=self._id_factory(),
            created_at=self._clock(),
            description=description,
            planned_actions=tuple(planned),
            notes=tuple(notes),
        )

    def plan_refresh_metadata(self, context: SystemContext) -> ExecutionPlan:
        native_strategy = NATIVE_STRATEGY_BY_MANAGER.get(context.package_manager.kind)
        if native_strategy is None:
            return self._empty_plan("No native package manager detected on this system.")

        action = UpdatePackageIndexAction(strategy=native_strategy)
        risk = self._risk_evaluator.evaluate(action)
        planned = PlannedAction(
            action=action,
            risk=risk,
            description=f"Refresh {native_strategy.value} package metadata",
        )
        return self._build_plan("Refresh package metadata", [planned])

    def plan_fix(self, fix: FixDefinition, context: SystemContext) -> ExecutionPlan:
        """Builds a plan for one fix — spec §43: always diagnose first, and a
        fix is applied through the exact same Planner/SafetyPolicy/Executor
        path as any other system change, never a separate mechanism.
        """
        if (
            fix.supported_distributions
            and context.distribution.family not in fix.supported_distributions
        ):
            return self._empty_plan(
                f"{fix.id} is not supported on {context.distribution.family.value} systems."
            )

        if fix.id == "fix.package_broken_state":
            if not check_dpkg_broken_state(self._command_runner):
                return self._empty_plan("No broken package state detected; nothing to repair.")
            action = RepairPackageManagerAction(
                fix_id=fix.id,
                manager_kind=context.package_manager.kind,
                fix_risk_level=fix.risk_level,
            )
            risk = self._risk_evaluator.evaluate(action)
            planned = PlannedAction(action=action, risk=risk, description=fix.description)
            return self._build_plan(f"Apply fix: {fix.id}", [planned])

        return self._empty_plan(f"No execution handler for fix {fix.id}.")

    def plan_rollback(self, record: OperationRecord) -> ExecutionPlan:
        """Builds a plan undoing whatever *is* safely undoable in ``record``
        — spec §11: never claim rollback is available when it is not, so
        this only ever acts on outcomes that were themselves marked
        reversible with a known strategy at record time, never on the
        record's aggregate ``plan_reversible`` flag.
        """
        eligible = record.rollback_eligible_outcomes
        if not eligible:
            return self._empty_plan(
                f"{record.id} has nothing that can be automatically rolled back."
            )

        planned: list[PlannedAction] = []
        notes: list[str] = []
        for outcome in eligible:
            if outcome.rollback_strategy != "remove_package":
                notes.append(
                    f"{outcome.tool_id or outcome.action_type}: unsupported rollback strategy"
                )
                continue
            if not outcome.tool_id or not outcome.package or not outcome.strategy:
                notes.append(f"{outcome.tool_id or outcome.action_type}: incomplete history detail")
                continue
            action = RemovePackageAction(
                tool_id=outcome.tool_id,
                package=outcome.package,
                strategy=InstallationStrategy(outcome.strategy),
                tool_risk_level=RiskLevel(outcome.risk_level)
                if outcome.risk_level
                else RiskLevel.LOW,
            )
            risk = self._risk_evaluator.evaluate(action)
            planned.append(
                PlannedAction(
                    action=action,
                    risk=risk,
                    description=f"Undo install: remove {outcome.package} (from {record.id})",
                )
            )

        if not planned:
            return self._empty_plan(f"{record.id}: nothing could be reconstructed for rollback.")

        return ExecutionPlan(
            id=self._id_factory(),
            created_at=self._clock(),
            description=f"Roll back {record.id}: {record.command}",
            planned_actions=tuple(planned),
            notes=tuple(notes),
        )

    def _empty_plan(self, description: str) -> ExecutionPlan:
        return ExecutionPlan(
            id=self._id_factory(), created_at=self._clock(), description=description
        )

    def _build_plan(self, description: str, planned: list[PlannedAction]) -> ExecutionPlan:
        return ExecutionPlan(
            id=self._id_factory(),
            created_at=self._clock(),
            description=description,
            planned_actions=tuple(planned),
        )
