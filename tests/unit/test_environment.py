from __future__ import annotations

from pathlib import Path

from hallfix.detectors.environment import EnvironmentDetector
from hallfix.domain.models.system import VirtualizationKind


def test_ubuntu_fixture_is_bare_metal(fake_systems_dir: Path) -> None:
    info = EnvironmentDetector(root=fake_systems_dir / "ubuntu").detect()
    assert info.kind == VirtualizationKind.BARE_METAL


def test_wsl_ubuntu_fixture_detected_as_wsl2(fake_systems_dir: Path) -> None:
    info = EnvironmentDetector(root=fake_systems_dir / "wsl_ubuntu").detect()
    assert info.kind == VirtualizationKind.WSL2
    assert info.is_wsl


def test_docker_fixture_detected_as_docker(fake_systems_dir: Path) -> None:
    info = EnvironmentDetector(root=fake_systems_dir / "docker_container").detect()
    assert info.kind == VirtualizationKind.DOCKER
    assert info.is_container


def test_vm_fixture_detected_as_virtual_machine(fake_systems_dir: Path) -> None:
    info = EnvironmentDetector(root=fake_systems_dir / "vm_qemu").detect()
    assert info.kind == VirtualizationKind.VIRTUAL_MACHINE
    assert info.detail is not None and "qemu" in info.detail.lower()


def test_wsl1_detected_when_no_wsl2_marker(tmp_path: Path) -> None:
    kernel_dir = tmp_path / "proc" / "sys" / "kernel"
    kernel_dir.mkdir(parents=True)
    (kernel_dir / "osrelease").write_text("4.4.0-19041-Microsoft\n", encoding="utf-8")
    info = EnvironmentDetector(root=tmp_path).detect()
    assert info.kind == VirtualizationKind.WSL1


def test_systemd_nspawn_container_marker(tmp_path: Path) -> None:
    container_dir = tmp_path / "run" / "systemd"
    container_dir.mkdir(parents=True)
    (container_dir / "container").write_text("systemd-nspawn\n", encoding="utf-8")
    info = EnvironmentDetector(root=tmp_path).detect()
    assert info.kind == VirtualizationKind.SYSTEMD_NSPAWN


def test_podman_containerenv_marker(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True)
    (run_dir / ".containerenv").write_text("", encoding="utf-8")
    info = EnvironmentDetector(root=tmp_path).detect()
    assert info.kind == VirtualizationKind.PODMAN


def test_empty_root_defaults_to_bare_metal(tmp_path: Path) -> None:
    info = EnvironmentDetector(root=tmp_path).detect()
    assert info.kind == VirtualizationKind.BARE_METAL
