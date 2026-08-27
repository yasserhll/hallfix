"""Structured results for package manager operations (spec §19/§67).

Never printed strings — every operation returns one of these, so callers
(Planner, Executor, diagnostics, and later the CLI) can make decisions
without re-parsing output.
"""

from __future__ import annotations

from dataclasses import dataclass

from hallfix.domain.models.command import CommandResult


@dataclass(frozen=True, slots=True)
class LockStatus:
    """Whether the package manager's own concurrency lock is currently held.

    Hallfix never deletes a lock file (spec §20) — this is read-only.
    """

    locked: bool
    lock_path: str | None


@dataclass(frozen=True, slots=True)
class PackageOperationResult:
    """Outcome of installing or removing a single package."""

    package: str
    action: str  # "install" | "remove"
    succeeded: bool
    already_satisfied: bool
    installed_version: str | None
    message: str
    dry_run: bool
    command: CommandResult | None = None


@dataclass(frozen=True, slots=True)
class PackageManagerOperationResult:
    """Outcome of a manager-wide operation: refresh_metadata / repair."""

    succeeded: bool
    message: str
    dry_run: bool
    skipped_due_to_lock: bool = False
    command: CommandResult | None = None


@dataclass(frozen=True, slots=True)
class PackageSearchResult:
    name: str
    description: str | None = None
    version: str | None = None
