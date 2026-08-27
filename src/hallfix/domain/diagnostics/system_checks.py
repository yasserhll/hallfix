"""System-category diagnostics (spec §40): OS, kernel, environment, CPU, RAM,
disk, sudo. Pure — everything needed is already on ``DiagnosticContext``.
"""

from __future__ import annotations

from hallfix.domain.diagnostics.context import DiagnosticContext
from hallfix.domain.models.diagnostic import DiagnosticResult
from hallfix.domain.models.enums import Severity


def check_os(ctx: DiagnosticContext) -> tuple[DiagnosticResult, ...]:
    distro = ctx.system.distribution
    name = distro.pretty_name or distro.id
    return (
        DiagnosticResult(
            id="system.os",
            category="system",
            severity=Severity.OK,
            title="OS",
            description=name,
            evidence=(f"family={distro.family.value}",),
        ),
    )


def check_kernel(ctx: DiagnosticContext) -> tuple[DiagnosticResult, ...]:
    return (
        DiagnosticResult(
            id="system.kernel",
            category="system",
            severity=Severity.OK,
            title="Kernel",
            description=ctx.system.kernel,
        ),
    )


def check_environment(ctx: DiagnosticContext) -> tuple[DiagnosticResult, ...]:
    env = ctx.system.environment
    return (
        DiagnosticResult(
            id="system.environment",
            category="system",
            severity=Severity.INFO,
            title="Environment",
            description=env.kind.value,
            evidence=(env.detail,) if env.detail else (),
        ),
    )


def check_cpu(ctx: DiagnosticContext) -> tuple[DiagnosticResult, ...]:
    cpu = ctx.system.cpu
    if cpu.threads == 0:
        return (
            DiagnosticResult(
                id="system.cpu",
                category="system",
                severity=Severity.WARNING,
                title="CPU",
                description="Could not detect CPU information.",
                recommendation="Check /proc/cpuinfo availability.",
            ),
        )
    return (
        DiagnosticResult(
            id="system.cpu",
            category="system",
            severity=Severity.OK,
            title="CPU",
            description=cpu.model or "Unknown model",
            evidence=(f"{cpu.cores} cores / {cpu.threads} threads", f"arch={cpu.architecture}"),
        ),
    )


def check_ram(ctx: DiagnosticContext) -> tuple[DiagnosticResult, ...]:
    memory = ctx.system.memory
    if memory.total_bytes == 0:
        return (
            DiagnosticResult(
                id="system.ram",
                category="system",
                severity=Severity.WARNING,
                title="RAM",
                description="Could not detect memory information.",
                recommendation="Check /proc/meminfo availability.",
            ),
        )
    total_gib = memory.total_bytes / (1024**3)
    available_gib = memory.available_bytes / (1024**3)
    return (
        DiagnosticResult(
            id="system.ram",
            category="system",
            severity=Severity.OK,
            title="RAM",
            description=f"{total_gib:.1f} GiB total",
            evidence=(f"{available_gib:.1f} GiB available",),
        ),
    )


def check_disk(ctx: DiagnosticContext) -> tuple[DiagnosticResult, ...]:
    # squashfs (snap packages, etc.) is a fixed-size read-only image and is
    # always ~100% "used" by design — real, but not disk-space-emergency
    # signal. Excluded here (not just at display time, per the earlier
    # `system info` fix) since this result also drives the exit code.
    filesystems = tuple(
        fs for fs in ctx.system.disk.filesystems if fs.filesystem_type != "squashfs"
    )
    if not filesystems:
        return (
            DiagnosticResult(
                id="system.disk",
                category="system",
                severity=Severity.WARNING,
                title="Storage",
                description="No filesystems detected.",
                recommendation="Check /proc/mounts availability.",
            ),
        )

    worst = max(filesystems, key=lambda fs: fs.usage_percent)
    thresholds = ctx.disk_thresholds
    severity: Severity
    recommendation: str | None
    if worst.usage_percent >= thresholds.critical:
        severity = Severity.CRITICAL
        recommendation = "Free disk space before installing additional software."
    elif worst.usage_percent >= thresholds.high:
        severity = Severity.ERROR
        recommendation = "Disk usage is high; free space soon."
    elif worst.usage_percent >= thresholds.warning:
        severity = Severity.WARNING
        recommendation = "Disk usage is elevated."
    else:
        severity = Severity.OK
        recommendation = None

    evidence = tuple(f"{fs.mount_point}: {fs.usage_percent}%" for fs in filesystems)
    return (
        DiagnosticResult(
            id="system.disk",
            category="system",
            severity=severity,
            title="Storage",
            description=f"Highest usage: {worst.mount_point} at {worst.usage_percent}%",
            evidence=evidence,
            recommendation=recommendation,
        ),
    )


def check_sudo(ctx: DiagnosticContext) -> tuple[DiagnosticResult, ...]:
    sudo = ctx.system.sudo
    if sudo.running_as_root:
        return (
            DiagnosticResult(
                id="system.sudo",
                category="system",
                severity=Severity.INFO,
                title="Sudo",
                description="Running as root; privilege escalation not needed.",
            ),
        )
    if not sudo.available:
        return (
            DiagnosticResult(
                id="system.sudo",
                category="system",
                severity=Severity.WARNING,
                title="Sudo",
                description="sudo is not available.",
                recommendation="Operations requiring administrator privileges will not be "
                "possible.",
            ),
        )
    return (
        DiagnosticResult(
            id="system.sudo",
            category="system",
            severity=Severity.OK,
            title="Sudo",
            description="sudo is available.",
        ),
    )


def check_service_manager(ctx: DiagnosticContext) -> tuple[DiagnosticResult, ...]:
    if ctx.system.capabilities.systemd:
        return (
            DiagnosticResult(
                id="system.service_manager",
                category="system",
                severity=Severity.OK,
                title="Service manager",
                description="systemd detected.",
            ),
        )
    return (
        DiagnosticResult(
            id="system.service_manager",
            category="system",
            severity=Severity.INFO,
            title="Service manager",
            description="No systemd detected (container, WSL1, or minimal system).",
        ),
    )
