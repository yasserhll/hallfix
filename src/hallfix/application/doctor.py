"""Doctor (spec §40): assembles a ``DiagnosticContext`` from real I/O, then
runs ``DiagnosticEngine`` (pure) over it.

This is the only place the extra I/O beyond a plain ``SystemContext`` gets
gathered: the package manager lock check, tool verification for a small
fixed set of dev-environment tools, and the DNS resolution probe (only
attempted when raw connectivity is already up — no point probing DNS
through a dead network).
"""

from __future__ import annotations

import os
from pathlib import Path

from hallfix.config.manager import ConfigurationManager
from hallfix.detectors.dns_resolution import DnsResolutionChecker, check_dns_resolution
from hallfix.detectors.internet import ConnectivityChecker, check_internet_connectivity
from hallfix.detectors.package_health import check_dpkg_broken_state
from hallfix.detectors.system import SystemDetector
from hallfix.detectors.tool_verifier import ToolVerifier
from hallfix.domain.diagnostics.context import DiagnosticContext
from hallfix.domain.diagnostics.engine import DiagnosticEngine
from hallfix.domain.diagnostics.registry import DiagnosticRegistry
from hallfix.domain.models.diagnostic import DiagnosticResult
from hallfix.domain.models.system import PackageManagerKind
from hallfix.domain.models.tool import ToolVerificationResult
from hallfix.infrastructure.commands.runner import CommandRunner
from hallfix.infrastructure.package_managers.registry import create_package_manager
from hallfix.infrastructure.registries.tool_registry_loader import load_tool_registry

_DEV_ENV_TOOL_IDS = ("git", "docker", "ssh")


def build_diagnostic_context(
    *,
    command_runner: CommandRunner,
    root: Path = Path("/"),
    connectivity_checker: ConnectivityChecker = check_internet_connectivity,
    dns_checker: DnsResolutionChecker = check_dns_resolution,
) -> DiagnosticContext:
    system = SystemDetector(
        root=root, command_runner=command_runner, connectivity_checker=connectivity_checker
    ).detect()
    config = ConfigurationManager().load()

    lock = None
    manager = create_package_manager(
        system.package_manager.kind, command_runner=command_runner, root=root
    )
    if manager is not None:
        lock = manager.check_lock()

    dns_ok = dns_checker() if system.capabilities.internet_access else None

    broken_state = None
    if system.package_manager.kind == PackageManagerKind.APT:
        broken_state = check_dpkg_broken_state(command_runner)

    verifier = ToolVerifier(command_runner=command_runner)
    tool_registry = load_tool_registry()
    verifications: dict[str, ToolVerificationResult] = {}
    for tool_id in _DEV_ENV_TOOL_IDS:
        tool = tool_registry.get(tool_id)
        if tool is not None:
            verifications[tool_id] = verifier.verify(tool)

    return DiagnosticContext(
        system=system,
        disk_thresholds=config.disk_thresholds,
        package_manager_lock=lock,
        dns_resolution_ok=dns_ok,
        package_broken_state=broken_state,
        tool_verifications=verifications,
        env=dict(os.environ),
    )


def run_doctor(
    *,
    command_runner: CommandRunner,
    root: Path = Path("/"),
    registry: DiagnosticRegistry | None = None,
    connectivity_checker: ConnectivityChecker = check_internet_connectivity,
    dns_checker: DnsResolutionChecker = check_dns_resolution,
) -> tuple[DiagnosticResult, ...]:
    context = build_diagnostic_context(
        command_runner=command_runner,
        root=root,
        connectivity_checker=connectivity_checker,
        dns_checker=dns_checker,
    )
    return DiagnosticEngine(registry).run(context)
