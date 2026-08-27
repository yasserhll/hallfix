from __future__ import annotations

from pathlib import Path

import pytest

from hallfix.detectors.package_manager import PackageManagerDetector
from hallfix.domain.models.system import PackageManagerKind


@pytest.mark.parametrize(
    ("fixture", "expected_kind"),
    [
        ("ubuntu", PackageManagerKind.APT),
        ("debian", PackageManagerKind.APT),
        ("fedora", PackageManagerKind.DNF),
        ("arch", PackageManagerKind.PACMAN),
    ],
)
def test_detects_native_package_manager(
    fake_systems_dir: Path, fixture: str, expected_kind: PackageManagerKind
) -> None:
    info = PackageManagerDetector(root=fake_systems_dir / fixture).detect()
    assert info.kind == expected_kind
    assert info.executable_path is not None


def test_unknown_when_no_manager_present(tmp_path: Path) -> None:
    info = PackageManagerDetector(root=tmp_path).detect()
    assert info.kind == PackageManagerKind.UNKNOWN
    assert info.executable_path is None
