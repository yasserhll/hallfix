"""Shared scaffolding for package manager adapters (spec §19).

``PackageManager`` is the structural interface everything else (Planner,
Executor, ToolRegistry in later phases) programs against.
``PackageManagerBase`` gives concrete adapters (apt/dnf/pacman/zypper) a
common ``_run``/dry-run/lock-check implementation so each subclass only has
to declare its own command syntax and output parsing.

Dry-run applies only to mutating calls (``install``/``remove``/
``refresh_metadata``/``repair``), each taking its own ``dry_run`` flag —
read-only calls (``is_installed``, ``get_version``, ``search``, ``detect``,
``check_lock``) always execute for real, since they're used to build an
accurate plan and dry-run has no meaning for a read (see
``docs/architecture.md``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from hallfix.domain.models.command import CommandResult, CommandSpec
from hallfix.domain.models.package import (
    LockStatus,
    PackageManagerOperationResult,
    PackageOperationResult,
    PackageSearchResult,
)
from hallfix.domain.models.system import PackageManagerKind
from hallfix.infrastructure.commands.runner import CommandRunner, DryRunCommandRunner
from hallfix.infrastructure.package_managers.lock import LockProbeFn


class PackageManager(Protocol):
    kind: PackageManagerKind

    def detect(self) -> bool: ...
    def check_lock(self) -> LockStatus: ...
    def refresh_metadata(self, *, dry_run: bool = False) -> PackageManagerOperationResult: ...
    def install(self, package: str, *, dry_run: bool = False) -> PackageOperationResult: ...
    def remove(self, package: str, *, dry_run: bool = False) -> PackageOperationResult: ...
    def is_installed(self, package: str) -> bool: ...
    def get_version(self, package: str) -> str | None: ...
    def search(self, query: str) -> tuple[PackageSearchResult, ...]: ...
    def repair(self, *, dry_run: bool = False) -> PackageManagerOperationResult: ...


class PackageManagerBase:
    kind: PackageManagerKind
    binary: str
    _lock_path_suffix: str
    _lock_probe: LockProbeFn

    def __init__(self, *, command_runner: CommandRunner, root: Path = Path("/")) -> None:
        self._command_runner = command_runner
        self._root = root

    def _run(
        self,
        argv: tuple[str, ...],
        *,
        requires_root: bool = False,
        timeout_seconds: float = 120.0,
        env: dict[str, str] | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        spec = CommandSpec(
            argv=argv,
            timeout_seconds=timeout_seconds,
            env=env,
            requires_root=requires_root,
        )
        runner = DryRunCommandRunner() if dry_run else self._command_runner
        return runner.run(spec)

    def detect(self) -> bool:
        result = self._run((self.binary, "--version"), timeout_seconds=10.0)
        return result.succeeded

    def check_lock(self) -> LockStatus:
        lock_path = self._root / self._lock_path_suffix
        locked = self._lock_probe(lock_path)
        return LockStatus(locked=locked, lock_path=str(lock_path) if locked else None)

    def _locked_result(self, *, dry_run: bool) -> PackageManagerOperationResult:
        return PackageManagerOperationResult(
            succeeded=False,
            message="Package manager is currently busy. Hallfix will not force through a lock.",
            dry_run=dry_run,
            skipped_due_to_lock=True,
        )

    def _locked_package_result(
        self, package: str, action: str, *, dry_run: bool
    ) -> PackageOperationResult:
        return PackageOperationResult(
            package=package,
            action=action,
            succeeded=False,
            already_satisfied=False,
            installed_version=None,
            message="Package manager is currently busy. Hallfix will not force through a lock.",
            dry_run=dry_run,
        )
