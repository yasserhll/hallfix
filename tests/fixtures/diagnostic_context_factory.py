"""Builds a minimal ``DiagnosticContext`` for diagnostic-check unit tests."""

from __future__ import annotations

from hallfix.config.schema import DiskThresholds
from hallfix.domain.diagnostics.context import DiagnosticContext
from hallfix.domain.models.package import LockStatus
from hallfix.domain.models.system import DistributionFamily, PackageManagerKind, SystemContext
from hallfix.domain.models.tool import ToolVerificationResult
from tests.fixtures.system_context_factory import make_system_context


def make_diagnostic_context(
    *,
    system: SystemContext | None = None,
    disk_thresholds: DiskThresholds | None = None,
    package_manager_lock: LockStatus | None = None,
    dns_resolution_ok: bool | None = None,
    package_broken_state: bool | None = None,
    tool_verifications: dict[str, ToolVerificationResult] | None = None,
    env: dict[str, str] | None = None,
) -> DiagnosticContext:
    return DiagnosticContext(
        system=system
        or make_system_context(
            manager_kind=PackageManagerKind.APT, family=DistributionFamily.DEBIAN
        ),
        disk_thresholds=disk_thresholds or DiskThresholds(),
        package_manager_lock=package_manager_lock,
        dns_resolution_ok=dns_resolution_ok,
        package_broken_state=package_broken_state,
        tool_verifications=tool_verifications or {},
        env=env
        if env is not None
        else {"HOME": "/home/tester", "PATH": "/usr/bin", "SHELL": "/bin/bash"},
    )
