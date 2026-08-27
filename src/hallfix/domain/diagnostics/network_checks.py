"""Network-category diagnostics (spec §18/§40).

Never performs a scan, probe of a remote host, or any offensive action —
everything here just interprets already-gathered local configuration
(``SystemContext.network``) plus the two connectivity probes computed
once during context assembly (``dns_resolution_ok``, and raw connectivity
already folded into ``capabilities.internet_access``).
"""

from __future__ import annotations

from hallfix.domain.diagnostics.context import DiagnosticContext
from hallfix.domain.models.diagnostic import DiagnosticResult
from hallfix.domain.models.enums import Severity


def check_network_interfaces(ctx: DiagnosticContext) -> tuple[DiagnosticResult, ...]:
    interfaces = [i for i in ctx.system.network.interfaces if i.is_up and i.name != "lo"]
    if not interfaces:
        return (
            DiagnosticResult(
                id="network.interfaces",
                category="network",
                severity=Severity.WARNING,
                title="Network interfaces",
                description="No active non-loopback interface detected.",
                recommendation="Check physical/virtual network connectivity.",
            ),
        )
    evidence = tuple(
        f"{i.name}: {', '.join(i.ipv4_addresses + i.ipv6_addresses) or 'no address'}"
        for i in interfaces
    )
    return (
        DiagnosticResult(
            id="network.interfaces",
            category="network",
            severity=Severity.OK,
            title="Network interfaces",
            description=f"{len(interfaces)} active interface(s).",
            evidence=evidence,
        ),
    )


def check_default_gateway(ctx: DiagnosticContext) -> tuple[DiagnosticResult, ...]:
    gateway = ctx.system.network.default_gateway
    if gateway is None:
        return (
            DiagnosticResult(
                id="network.gateway",
                category="network",
                severity=Severity.WARNING,
                title="Default gateway",
                description="No default gateway configured.",
                recommendation="Check routing configuration.",
            ),
        )
    return (
        DiagnosticResult(
            id="network.gateway",
            category="network",
            severity=Severity.OK,
            title="Default gateway",
            description=gateway,
        ),
    )


def check_dns_configured(ctx: DiagnosticContext) -> tuple[DiagnosticResult, ...]:
    servers = ctx.system.network.dns_servers
    if not servers:
        return (
            DiagnosticResult(
                id="network.dns_configured",
                category="network",
                severity=Severity.WARNING,
                title="DNS configuration",
                description="No DNS servers configured.",
                recommendation="Check /etc/resolv.conf.",
            ),
        )
    return (
        DiagnosticResult(
            id="network.dns_configured",
            category="network",
            severity=Severity.OK,
            title="DNS configuration",
            description=f"{len(servers)} DNS server(s) configured.",
            evidence=servers,
        ),
    )


def check_dns_resolution(ctx: DiagnosticContext) -> tuple[DiagnosticResult, ...]:
    if ctx.dns_resolution_ok is None:
        return (
            DiagnosticResult(
                id="network.dns_resolution",
                category="network",
                severity=Severity.INFO,
                title="DNS resolution",
                description="Not tested (no raw Internet connectivity).",
            ),
        )
    if ctx.dns_resolution_ok:
        return (
            DiagnosticResult(
                id="network.dns_resolution",
                category="network",
                severity=Severity.OK,
                title="DNS resolution",
                description="Hostname resolution succeeded.",
            ),
        )
    return (
        DiagnosticResult(
            id="network.dns_resolution",
            category="network",
            severity=Severity.ERROR,
            title="DNS resolution",
            description="Hostname resolution failed.",
            recommendation="Inspect DNS/resolver configuration and the resolver service.",
        ),
    )


def check_internet_connectivity(ctx: DiagnosticContext) -> tuple[DiagnosticResult, ...]:
    if ctx.system.capabilities.internet_access:
        return (
            DiagnosticResult(
                id="network.internet",
                category="network",
                severity=Severity.OK,
                title="Internet connectivity",
                description="Raw Internet connectivity available.",
            ),
        )
    return (
        DiagnosticResult(
            id="network.internet",
            category="network",
            severity=Severity.WARNING,
            title="Internet connectivity",
            description="No raw Internet connectivity detected.",
            recommendation="Check network cabling/Wi-Fi and default route.",
        ),
    )
