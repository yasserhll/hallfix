from __future__ import annotations

from pathlib import Path

from hallfix.detectors.sudo import SudoDetector


def test_sudo_available_when_binary_present(fake_systems_dir: Path) -> None:
    info = SudoDetector(root=fake_systems_dir / "ubuntu", euid=1000).detect()
    assert info.available
    assert not info.running_as_root


def test_sudo_unavailable_without_binary(tmp_path: Path) -> None:
    info = SudoDetector(root=tmp_path, euid=1000).detect()
    assert not info.available


def test_running_as_root_reported(fake_systems_dir: Path) -> None:
    info = SudoDetector(root=fake_systems_dir / "ubuntu", euid=0).detect()
    assert info.running_as_root
