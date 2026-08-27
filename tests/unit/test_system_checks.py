from __future__ import annotations

from hallfix.config.schema import DiskThresholds
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
from hallfix.domain.models.enums import Severity
from hallfix.domain.models.system import (
    CapabilitySet,
    CpuInfo,
    DiskInfo,
    DistributionFamily,
    EnvironmentInfo,
    MemoryInfo,
    MountedFilesystem,
    PackageManagerKind,
    SudoInfo,
    VirtualizationKind,
)
from tests.fixtures.diagnostic_context_factory import make_diagnostic_context
from tests.fixtures.system_context_factory import make_system_context

_APT_DEBIAN = {"manager_kind": PackageManagerKind.APT, "family": DistributionFamily.DEBIAN}

_NO_SYSTEMD_CAPABILITIES = CapabilitySet(
    package_management=True,
    systemd=False,
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
)


def test_check_os_reports_pretty_name() -> None:
    ctx = make_diagnostic_context()
    (result,) = check_os(ctx)
    assert result.severity == Severity.OK


def test_check_kernel_ok() -> None:
    ctx = make_diagnostic_context()
    (result,) = check_kernel(ctx)
    assert result.severity == Severity.OK
    assert result.description == "6.0.0"


def test_check_environment_reports_wsl() -> None:
    system = make_system_context(
        **_APT_DEBIAN, environment=EnvironmentInfo(kind=VirtualizationKind.WSL2)
    )
    ctx = make_diagnostic_context(system=system)
    (result,) = check_environment(ctx)
    assert result.severity == Severity.INFO
    assert result.description == "WSL2"


def test_check_cpu_ok_when_detected() -> None:
    ctx = make_diagnostic_context()
    (result,) = check_cpu(ctx)
    assert result.severity == Severity.OK


def test_check_cpu_warning_when_threads_zero() -> None:
    system = make_system_context(
        **_APT_DEBIAN, cpu=CpuInfo(model=None, architecture="x86_64", cores=0, threads=0)
    )
    ctx = make_diagnostic_context(system=system)
    (result,) = check_cpu(ctx)
    assert result.severity == Severity.WARNING


def test_check_ram_warning_when_total_zero() -> None:
    ctx = make_diagnostic_context()  # default memory has total_bytes=0
    (result,) = check_ram(ctx)
    assert result.severity == Severity.WARNING


def test_check_ram_ok_when_detected() -> None:
    system = make_system_context(
        **_APT_DEBIAN,
        memory=MemoryInfo(
            total_bytes=16 * 1024**3,
            available_bytes=8 * 1024**3,
            swap_total_bytes=0,
            swap_free_bytes=0,
        ),
    )
    ctx = make_diagnostic_context(system=system)
    (result,) = check_ram(ctx)
    assert result.severity == Severity.OK
    assert "16.0 GiB" in result.description


def _fs(mount: str, total: int, used: int) -> MountedFilesystem:
    return MountedFilesystem(
        mount_point=mount,
        device="/dev/x",
        filesystem_type="ext4",
        total_bytes=total,
        used_bytes=used,
        available_bytes=total - used,
    )


def test_check_disk_ok_below_warning_threshold() -> None:
    system = make_system_context(**_APT_DEBIAN, disk=DiskInfo(filesystems=(_fs("/", 100, 50),)))
    ctx = make_diagnostic_context(system=system, disk_thresholds=DiskThresholds())
    (result,) = check_disk(ctx)
    assert result.severity == Severity.OK


def test_check_disk_warning_at_elevated_usage() -> None:
    system = make_system_context(**_APT_DEBIAN, disk=DiskInfo(filesystems=(_fs("/", 100, 75),)))
    ctx = make_diagnostic_context(system=system)
    (result,) = check_disk(ctx)
    assert result.severity == Severity.WARNING


def test_check_disk_error_between_high_and_critical() -> None:
    system = make_system_context(**_APT_DEBIAN, disk=DiskInfo(filesystems=(_fs("/", 100, 90),)))
    ctx = make_diagnostic_context(system=system)
    (result,) = check_disk(ctx)
    assert result.severity == Severity.ERROR


def test_check_disk_critical_above_critical_threshold() -> None:
    system = make_system_context(**_APT_DEBIAN, disk=DiskInfo(filesystems=(_fs("/", 100, 96),)))
    ctx = make_diagnostic_context(system=system, disk_thresholds=DiskThresholds())
    (result,) = check_disk(ctx)
    assert result.severity == Severity.CRITICAL
    assert result.recommendation is not None


def test_check_disk_warning_when_no_filesystems() -> None:
    ctx = make_diagnostic_context()  # default disk has no filesystems
    (result,) = check_disk(ctx)
    assert result.severity == Severity.WARNING


def test_check_disk_ignores_squashfs_always_full_by_design() -> None:
    squashfs = MountedFilesystem(
        mount_point="/snap/core/1",
        device="/dev/loop0",
        filesystem_type="squashfs",
        total_bytes=100,
        used_bytes=100,
        available_bytes=0,
    )
    system = make_system_context(
        **_APT_DEBIAN, disk=DiskInfo(filesystems=(squashfs, _fs("/", 100, 50)))
    )
    ctx = make_diagnostic_context(system=system)
    (result,) = check_disk(ctx)
    assert result.severity == Severity.OK
    assert len(result.evidence) == 1


def test_check_disk_warning_when_only_squashfs_present() -> None:
    squashfs = MountedFilesystem(
        mount_point="/snap/core/1",
        device="/dev/loop0",
        filesystem_type="squashfs",
        total_bytes=100,
        used_bytes=100,
        available_bytes=0,
    )
    system = make_system_context(**_APT_DEBIAN, disk=DiskInfo(filesystems=(squashfs,)))
    ctx = make_diagnostic_context(system=system)
    (result,) = check_disk(ctx)
    assert result.severity == Severity.WARNING
    assert result.description == "No filesystems detected."


def test_check_disk_evidence_lists_every_filesystem() -> None:
    system = make_system_context(
        **_APT_DEBIAN, disk=DiskInfo(filesystems=(_fs("/", 100, 50), _fs("/boot", 100, 10)))
    )
    ctx = make_diagnostic_context(system=system)
    (result,) = check_disk(ctx)
    assert len(result.evidence) == 2


def test_check_sudo_ok_when_available_and_not_root() -> None:
    ctx = make_diagnostic_context()
    (result,) = check_sudo(ctx)
    assert result.severity == Severity.OK


def test_check_sudo_info_when_running_as_root() -> None:
    system = make_system_context(**_APT_DEBIAN, sudo=SudoInfo(available=True, running_as_root=True))
    ctx = make_diagnostic_context(system=system)
    (result,) = check_sudo(ctx)
    assert result.severity == Severity.INFO


def test_check_sudo_warning_when_unavailable() -> None:
    system = make_system_context(
        **_APT_DEBIAN, sudo=SudoInfo(available=False, running_as_root=False)
    )
    ctx = make_diagnostic_context(system=system)
    (result,) = check_sudo(ctx)
    assert result.severity == Severity.WARNING


def test_check_service_manager_ok_with_systemd() -> None:
    ctx = make_diagnostic_context()
    (result,) = check_service_manager(ctx)
    assert result.severity == Severity.OK


def test_check_service_manager_info_without_systemd() -> None:
    system = make_system_context(**_APT_DEBIAN, capabilities=_NO_SYSTEMD_CAPABILITIES)
    ctx = make_diagnostic_context(system=system)
    (result,) = check_service_manager(ctx)
    assert result.severity == Severity.INFO
