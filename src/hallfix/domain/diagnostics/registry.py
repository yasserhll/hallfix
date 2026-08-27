"""``DiagnosticRegistry``: holds the checks ``DiagnosticEngine`` runs.

A check is any ``DiagnosticContext -> tuple[DiagnosticResult, ...]``
callable — one check can yield zero, one, or several results.
"""

from __future__ import annotations

from collections.abc import Callable

from hallfix.domain.diagnostics.context import DiagnosticContext
from hallfix.domain.diagnostics.development_checks import (
    check_docker,
    check_environment_variables,
    check_git,
    check_ssh,
)
from hallfix.domain.diagnostics.network_checks import (
    check_default_gateway,
    check_dns_configured,
    check_dns_resolution,
    check_internet_connectivity,
    check_network_interfaces,
)
from hallfix.domain.diagnostics.package_checks import (
    check_package_manager,
    check_package_manager_lock,
)
from hallfix.domain.diagnostics.system_checks import (
    check_cpu,
    check_disk,
    check_environment,
    check_kernel,
    check_os,
    check_ram,
    check_service_manager,
    check_sudo,
)
from hallfix.domain.models.diagnostic import DiagnosticResult

DiagnosticCheck = Callable[[DiagnosticContext], tuple[DiagnosticResult, ...]]

DEFAULT_CHECKS: tuple[DiagnosticCheck, ...] = (
    check_os,
    check_kernel,
    check_environment,
    check_cpu,
    check_ram,
    check_disk,
    check_sudo,
    check_service_manager,
    check_network_interfaces,
    check_default_gateway,
    check_dns_configured,
    check_dns_resolution,
    check_internet_connectivity,
    check_package_manager,
    check_package_manager_lock,
    check_git,
    check_docker,
    check_ssh,
    check_environment_variables,
)

NETWORK_CHECKS: tuple[DiagnosticCheck, ...] = (
    check_network_interfaces,
    check_default_gateway,
    check_dns_configured,
    check_dns_resolution,
    check_internet_connectivity,
)


class DiagnosticRegistry:
    def __init__(self, checks: tuple[DiagnosticCheck, ...] = DEFAULT_CHECKS) -> None:
        self._checks = checks

    def checks(self) -> tuple[DiagnosticCheck, ...]:
        return self._checks
