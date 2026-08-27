from __future__ import annotations

from pathlib import Path

from hallfix.domain.models.system import PackageManagerKind
from hallfix.infrastructure.package_managers.apt import AptManager
from hallfix.infrastructure.package_managers.dnf import DnfManager
from hallfix.infrastructure.package_managers.pacman import PacmanManager
from hallfix.infrastructure.package_managers.registry import create_package_manager
from hallfix.infrastructure.package_managers.zypper import ZypperManager
from tests.fixtures.fake_command_runner import FakeCommandRunner


def test_creates_correct_adapter_per_kind(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    assert isinstance(
        create_package_manager(PackageManagerKind.APT, command_runner=runner, root=tmp_path),
        AptManager,
    )
    assert isinstance(
        create_package_manager(PackageManagerKind.DNF, command_runner=runner, root=tmp_path),
        DnfManager,
    )
    assert isinstance(
        create_package_manager(PackageManagerKind.PACMAN, command_runner=runner, root=tmp_path),
        PacmanManager,
    )
    assert isinstance(
        create_package_manager(PackageManagerKind.ZYPPER, command_runner=runner, root=tmp_path),
        ZypperManager,
    )


def test_unknown_kind_returns_none(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    assert (
        create_package_manager(PackageManagerKind.UNKNOWN, command_runner=runner, root=tmp_path)
        is None
    )
