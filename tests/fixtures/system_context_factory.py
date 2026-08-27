"""Builds a minimal, valid ``SystemContext`` for tests that need one without
running real detection. Shared by any test exercising compatibility
resolution or planning.
"""

from __future__ import annotations

from hallfix.domain.models.system import (
    CapabilitySet,
    CpuInfo,
    DiskInfo,
    DistributionFamily,
    DistributionInfo,
    EnvironmentInfo,
    MemoryInfo,
    NetworkInfo,
    PackageManagerInfo,
    PackageManagerKind,
    SudoInfo,
    SystemContext,
    VirtualizationKind,
)


def make_system_context(
    *,
    manager_kind: PackageManagerKind,
    family: DistributionFamily,
    architecture: str = "x86_64",
) -> SystemContext:
    return SystemContext(  # noqa: S604 - `shell` is our own dataclass field, not subprocess
        hostname="test",
        username="tester",
        shell="/bin/bash",  # noqa: S604 - our own dataclass field, not subprocess
        kernel="6.0.0",
        architecture=architecture,
        uptime_seconds=100.0,
        distribution=DistributionInfo(
            id="test",
            id_like=(),
            version_id=None,
            version_codename=None,
            pretty_name=None,
            family=family,
        ),
        environment=EnvironmentInfo(kind=VirtualizationKind.BARE_METAL),
        capabilities=CapabilitySet(
            package_management=True,
            systemd=True,
            sudo=True,
            graphical_session=False,
            network_manager=True,
            selinux=False,
            apparmor=False,
            container_runtime=False,
            wsl=False,
            immutable_os=False,
            filesystem_write_access=True,
            internet_access=True,
            ipv4=True,
            ipv6=False,
        ),
        cpu=CpuInfo(model="Test CPU", architecture=architecture, cores=4, threads=8),
        memory=MemoryInfo(total_bytes=0, available_bytes=0, swap_total_bytes=0, swap_free_bytes=0),
        disk=DiskInfo(),
        network=NetworkInfo(),
        package_manager=PackageManagerInfo(kind=manager_kind, executable_path=None),
        sudo=SudoInfo(available=True, running_as_root=False),
    )
