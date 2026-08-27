from __future__ import annotations

from pathlib import Path

from hallfix.detectors.capabilities import CapabilityDetector
from hallfix.domain.models.system import (
    NetworkInfo,
    NetworkInterface,
    PackageManagerInfo,
    PackageManagerKind,
    SudoInfo,
)

_NETWORK = NetworkInfo(
    interfaces=(NetworkInterface(name="eth0", ipv4_addresses=("10.0.0.5",)),),
)
_PACKAGE_MANAGER = PackageManagerInfo(
    kind=PackageManagerKind.APT, executable_path="/usr/bin/apt-get"
)
_SUDO = SudoInfo(available=True, running_as_root=False)


def test_systemd_capability_true_when_present(fake_systems_dir: Path) -> None:
    caps = CapabilityDetector(root=fake_systems_dir / "ubuntu", env={}).detect(
        network=_NETWORK,
        sudo=_SUDO,
        package_manager=_PACKAGE_MANAGER,
        is_wsl=False,
        internet_reachable=True,
    )
    assert caps.systemd is True
    assert caps.package_management is True
    assert caps.sudo is True
    assert caps.ipv4 is True
    assert caps.ipv6 is False
    assert caps.internet_access is True


def test_systemd_capability_false_when_absent(fake_systems_dir: Path) -> None:
    caps = CapabilityDetector(root=fake_systems_dir / "no_systemd", env={}).detect(
        network=_NETWORK,
        sudo=_SUDO,
        package_manager=_PACKAGE_MANAGER,
        is_wsl=False,
        internet_reachable=False,
    )
    assert caps.systemd is False
    assert caps.internet_access is False


def test_selinux_capability_detected(fake_systems_dir: Path) -> None:
    caps = CapabilityDetector(root=fake_systems_dir / "fedora", env={}).detect(
        network=_NETWORK,
        sudo=_SUDO,
        package_manager=_PACKAGE_MANAGER,
        is_wsl=False,
        internet_reachable=True,
    )
    assert caps.selinux is True


def test_graphical_session_from_env(fake_systems_dir: Path) -> None:
    caps = CapabilityDetector(root=fake_systems_dir / "ubuntu", env={"DISPLAY": ":0"}).detect(
        network=_NETWORK,
        sudo=_SUDO,
        package_manager=_PACKAGE_MANAGER,
        is_wsl=False,
        internet_reachable=True,
    )
    assert caps.graphical_session is True


def test_no_graphical_session_without_display_env(fake_systems_dir: Path) -> None:
    caps = CapabilityDetector(root=fake_systems_dir / "ubuntu", env={}).detect(
        network=_NETWORK,
        sudo=_SUDO,
        package_manager=_PACKAGE_MANAGER,
        is_wsl=False,
        internet_reachable=True,
    )
    assert caps.graphical_session is False


def test_wsl_flag_passed_through(fake_systems_dir: Path) -> None:
    caps = CapabilityDetector(root=fake_systems_dir / "wsl_ubuntu", env={}).detect(
        network=_NETWORK,
        sudo=_SUDO,
        package_manager=_PACKAGE_MANAGER,
        is_wsl=True,
        internet_reachable=True,
    )
    assert caps.wsl is True
