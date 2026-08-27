"""Executor (spec §4/§76 Phase 6): applies an ``ExecutionPlan``.

Lives in ``application/`` alongside ``Planner`` — same reason: it
orchestrates domain logic (which package manager backs which strategy)
with real infrastructure (``PackageManager`` adapters, ``ToolVerifier``).

Failure isolation (spec §50): every action in the plan is attempted
independently — one failing does not stop the rest, since our current
action types (single package install/remove/refresh) have no
inter-dependencies the Executor would need to short-circuit on. Real
exceptions (a bug, not an expected failure mode) are not caught here and
are allowed to propagate — silently converting a programming error into a
plausible-looking "failed" result would hide it (spec §78: no silent
exception swallowing).

Verification (spec §26) runs after a successful, real (non-dry-run)
install, using the tool's own declared verification spec from the
registry — a package transaction succeeding is not the same as the tool
actually working.
"""

from __future__ import annotations

from pathlib import Path

from hallfix.detectors.tool_verifier import ToolVerifier
from hallfix.domain.planning.action import (
    Action,
    InstallPackageAction,
    RemovePackageAction,
    UpdatePackageIndexAction,
)
from hallfix.domain.planning.execution_plan import ExecutionPlan
from hallfix.domain.planning.execution_result import ActionExecutionResult, PlanExecutionResult
from hallfix.domain.registries.compatibility import NATIVE_STRATEGY_BY_MANAGER
from hallfix.domain.registries.tool_registry import ToolRegistry
from hallfix.infrastructure.commands.runner import CommandRunner
from hallfix.infrastructure.package_managers.base import PackageManager
from hallfix.infrastructure.package_managers.registry import create_package_manager
from hallfix.infrastructure.state.store import StateStore

_MANAGER_KIND_FOR_STRATEGY = {
    strategy: kind for kind, strategy in NATIVE_STRATEGY_BY_MANAGER.items()
}


class Executor:
    def __init__(
        self,
        *,
        command_runner: CommandRunner,
        tool_registry: ToolRegistry,
        root: Path = Path("/"),
        state_store: StateStore | None = None,
    ) -> None:
        self._command_runner = command_runner
        self._tool_registry = tool_registry
        self._root = root
        self._verifier = ToolVerifier(command_runner=command_runner)
        self._state_store = state_store

    def execute_plan(self, plan: ExecutionPlan, *, dry_run: bool = False) -> PlanExecutionResult:
        results = tuple(
            self._execute_one(planned.action, dry_run=dry_run) for planned in plan.planned_actions
        )
        if not dry_run and self._state_store is not None:
            self._record_ownership(results)
        return PlanExecutionResult(plan_id=plan.id, dry_run=dry_run, action_results=results)

    def _record_ownership(self, results: tuple[ActionExecutionResult, ...]) -> None:
        state_store = self._state_store
        if state_store is None:  # pragma: no cover - caller already checked
            return
        for result in results:
            if not result.succeeded:
                continue
            if isinstance(result.action, InstallPackageAction) and not result.already_satisfied:
                state_store.record_installed(result.action.tool_id)
            elif isinstance(result.action, RemovePackageAction):
                state_store.record_removed(result.action.tool_id)

    def _execute_one(self, action: Action, *, dry_run: bool) -> ActionExecutionResult:
        if isinstance(action, InstallPackageAction):
            return self._execute_install(action, dry_run=dry_run)
        if isinstance(action, RemovePackageAction):
            return self._execute_remove(action, dry_run=dry_run)
        if isinstance(action, UpdatePackageIndexAction):
            return self._execute_refresh(action, dry_run=dry_run)
        msg = f"Executor: no rule for action type {type(action).__name__}"  # pragma: no cover
        raise NotImplementedError(msg)  # pragma: no cover

    def _manager_for(
        self, action: InstallPackageAction | RemovePackageAction | UpdatePackageIndexAction
    ) -> PackageManager:
        kind = _MANAGER_KIND_FOR_STRATEGY[action.strategy]
        manager = create_package_manager(kind, command_runner=self._command_runner, root=self._root)
        if manager is None:  # pragma: no cover - strategy->kind mapping guarantees this
            msg = f"no package manager for strategy {action.strategy.value}"
            raise AssertionError(msg)
        return manager

    def _execute_install(
        self, action: InstallPackageAction, *, dry_run: bool
    ) -> ActionExecutionResult:
        manager = self._manager_for(action)
        result = manager.install(action.package, dry_run=dry_run)

        verification = None
        if result.succeeded and not dry_run:
            tool = self._tool_registry.get(action.tool_id)
            if tool is not None:
                verification = self._verifier.verify(tool)

        return ActionExecutionResult(
            action=action,
            succeeded=result.succeeded,
            already_satisfied=result.already_satisfied,
            message=result.message,
            dry_run=result.dry_run,
            verification=verification,
        )

    def _execute_remove(
        self, action: RemovePackageAction, *, dry_run: bool
    ) -> ActionExecutionResult:
        manager = self._manager_for(action)
        result = manager.remove(action.package, dry_run=dry_run)
        return ActionExecutionResult(
            action=action,
            succeeded=result.succeeded,
            already_satisfied=result.already_satisfied,
            message=result.message,
            dry_run=result.dry_run,
        )

    def _execute_refresh(
        self, action: UpdatePackageIndexAction, *, dry_run: bool
    ) -> ActionExecutionResult:
        manager = self._manager_for(action)
        result = manager.refresh_metadata(dry_run=dry_run)
        return ActionExecutionResult(
            action=action,
            succeeded=result.succeeded,
            already_satisfied=False,
            message=result.message,
            dry_run=result.dry_run,
        )
