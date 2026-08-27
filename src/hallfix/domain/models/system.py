"""Domain models produced by detectors (spec §16/§67).

All fields are plain data — detectors populate these, nothing here performs
I/O. Kept in one module because these types form a single cohesive concept
(what Hallfix knows about the machine), not because of laziness about
splitting files; ``domain/models/command.py`` is the sibling precedent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class DistributionFamily(StrEnum):
    DEBIAN = "DEBIAN"
    REDHAT = "REDHAT"
    ARCH = "ARCH"
    SUSE = "SUSE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class DistributionInfo:
    id: str
    id_like: tuple[str, ...]
    version_id: str | None
    version_codename: str | None
    pretty_name: str | None
    family: DistributionFamily


class VirtualizationKind(StrEnum):
    BARE_METAL = "BARE_METAL"
    VIRTUAL_MACHINE = "VIRTUAL_MACHINE"
    WSL1 = "WSL1"
    WSL2 = "WSL2"
    DOCKER = "DOCKER"
    PODMAN = "PODMAN"
    LXC = "LXC"
    SYSTEMD_NSPAWN = "SYSTEMD_NSPAWN"
    UNKNOWN_VIRTUALIZED = "UNKNOWN_VIRTUALIZED"


@dataclass(frozen=True, slots=True)
class EnvironmentInfo:
    kind: VirtualizationKind
    detail: str | None = None

    @property
    def is_wsl(self) -> bool:
        return self.kind in (VirtualizationKind.WSL1, VirtualizationKind.WSL2)

    @property
    def is_container(self) -> bool:
        return self.kind in (
            VirtualizationKind.DOCKER,
            VirtualizationKind.PODMAN,
            VirtualizationKind.LXC,
            VirtualizationKind.SYSTEMD_NSPAWN,
        )


class PackageManagerKind(StrEnum):
    APT = "APT"
    DNF = "DNF"
    PACMAN = "PACMAN"
    ZYPPER = "ZYPPER"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class PackageManagerInfo:
    kind: PackageManagerKind
    executable_path: str | None


@dataclass(frozen=True, slots=True)
class SudoInfo:
    available: bool
    running_as_root: bool


@dataclass(frozen=True, slots=True)
class CpuInfo:
    model: str | None
    architecture: str
    cores: int
    threads: int


@dataclass(frozen=True, slots=True)
class MemoryInfo:
    total_bytes: int
    available_bytes: int
    swap_total_bytes: int
    swap_free_bytes: int


@dataclass(frozen=True, slots=True)
class MountedFilesystem:
    mount_point: str
    device: str
    filesystem_type: str
    total_bytes: int
    used_bytes: int
    available_bytes: int

    @property
    def usage_percent(self) -> float:
        if self.total_bytes == 0:
            return 0.0
        return round(self.used_bytes / self.total_bytes * 100, 1)


@dataclass(frozen=True, slots=True)
class DiskInfo:
    filesystems: tuple[MountedFilesystem, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class NetworkInterface:
    name: str
    ipv4_addresses: tuple[str, ...] = field(default_factory=tuple)
    ipv6_addresses: tuple[str, ...] = field(default_factory=tuple)
    is_up: bool = True


@dataclass(frozen=True, slots=True)
class NetworkInfo:
    interfaces: tuple[NetworkInterface, ...] = field(default_factory=tuple)
    default_gateway: str | None = None
    dns_servers: tuple[str, ...] = field(default_factory=tuple)
    internet_reachable: bool | None = None  # None = not checked

    @property
    def has_ipv4(self) -> bool:
        return any(iface.ipv4_addresses for iface in self.interfaces)

    @property
    def has_ipv6(self) -> bool:
        return any(iface.ipv6_addresses for iface in self.interfaces)


@dataclass(frozen=True, slots=True)
class CapabilitySet:
    package_management: bool
    systemd: bool
    sudo: bool
    graphical_session: bool
    network_manager: bool
    selinux: bool
    apparmor: bool
    container_runtime: bool
    wsl: bool
    immutable_os: bool
    filesystem_write_access: bool
    internet_access: bool
    ipv4: bool
    ipv6: bool


@dataclass(frozen=True, slots=True)
class SystemContext:
    """Everything Hallfix knows about the machine, assembled by SystemDetector."""

    hostname: str
    username: str
    shell: str | None
    kernel: str
    architecture: str
    uptime_seconds: float | None

    distribution: DistributionInfo
    environment: EnvironmentInfo
    capabilities: CapabilitySet
    cpu: CpuInfo
    memory: MemoryInfo
    disk: DiskInfo
    network: NetworkInfo
    package_manager: PackageManagerInfo
    sudo: SudoInfo
