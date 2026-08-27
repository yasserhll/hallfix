from __future__ import annotations

from pathlib import Path

import pytest

from hallfix.detectors.distribution import DistributionDetector, parse_os_release
from hallfix.domain.exceptions import DetectionError
from hallfix.domain.models.system import DistributionFamily


@pytest.mark.parametrize(
    ("fixture", "expected_id", "expected_family"),
    [
        ("ubuntu", "ubuntu", DistributionFamily.DEBIAN),
        ("debian", "debian", DistributionFamily.DEBIAN),
        ("fedora", "fedora", DistributionFamily.REDHAT),
        ("arch", "arch", DistributionFamily.ARCH),
    ],
)
def test_detects_known_distributions(
    fake_systems_dir: Path, fixture: str, expected_id: str, expected_family: DistributionFamily
) -> None:
    detector = DistributionDetector(root=fake_systems_dir / fixture)
    info = detector.detect()
    assert info.id == expected_id
    assert info.family == expected_family
    assert info.pretty_name is not None


def test_ubuntu_id_like_falls_back_to_debian_family(fake_systems_dir: Path) -> None:
    info = DistributionDetector(root=fake_systems_dir / "ubuntu").detect()
    assert "debian" in info.id_like


def test_raises_detection_error_when_no_os_release(tmp_path: Path) -> None:
    with pytest.raises(DetectionError):
        DistributionDetector(root=tmp_path).detect()


def test_parse_os_release_handles_quoted_and_bare_values() -> None:
    text = 'ID=ubuntu\nPRETTY_NAME="Ubuntu 24.04.1 LTS"\nVERSION_ID="24.04"\n'
    fields = parse_os_release(text)
    assert fields["ID"] == "ubuntu"
    assert fields["PRETTY_NAME"] == "Ubuntu 24.04.1 LTS"
    assert fields["VERSION_ID"] == "24.04"


def test_parse_os_release_ignores_comments_and_blank_lines() -> None:
    text = "# comment\n\nID=debian\n"
    fields = parse_os_release(text)
    assert fields == {"ID": "debian"}


def test_unknown_id_like_derivative_resolves_via_id_like(tmp_path: Path) -> None:
    etc = tmp_path / "etc"
    etc.mkdir()
    (etc / "os-release").write_text(
        'ID=popos\nID_LIKE="ubuntu debian"\nPRETTY_NAME="Pop!_OS"\n', encoding="utf-8"
    )
    info = DistributionDetector(root=tmp_path).detect()
    assert info.family == DistributionFamily.DEBIAN
