"""Package-category diagnostics (spec §20/§40)."""

from __future__ import annotations

from hallfix.domain.diagnostics.context import DiagnosticContext
from hallfix.domain.models.diagnostic import DiagnosticResult
from hallfix.domain.models.enums import Severity
from hallfix.domain.models.system import PackageManagerKind


def check_package_manager(ctx: DiagnosticContext) -> tuple[DiagnosticResult, ...]:
    manager = ctx.system.package_manager
    if manager.kind == PackageManagerKind.UNKNOWN:
        return (
            DiagnosticResult(
                id="package.manager",
                category="package",
                severity=Severity.WARNING,
                title="Package manager",
                description="No supported package manager detected.",
                recommendation="Hallfix cannot install/remove packages on this system.",
            ),
        )
    return (
        DiagnosticResult(
            id="package.manager",
            category="package",
            severity=Severity.OK,
            title="Package manager",
            description=manager.kind.value,
        ),
    )


def check_package_manager_lock(ctx: DiagnosticContext) -> tuple[DiagnosticResult, ...]:
    lock = ctx.package_manager_lock
    if lock is None:
        return (
            DiagnosticResult(
                id="package.lock",
                category="package",
                severity=Severity.INFO,
                title="Package manager lock",
                description="Not checked (no supported package manager).",
            ),
        )
    if lock.locked:
        return (
            DiagnosticResult(
                id="package.lock",
                category="package",
                severity=Severity.WARNING,
                title="Package manager lock",
                description="Package manager is currently busy.",
                evidence=(lock.lock_path,) if lock.lock_path else (),
                recommendation="Wait for the other package operation to finish.",
            ),
        )
    return (
        DiagnosticResult(
            id="package.lock",
            category="package",
            severity=Severity.OK,
            title="Package manager lock",
            description="Not locked.",
        ),
    )
