from __future__ import annotations

from pathlib import Path

from hallfix.detectors.disk import DiskDetector


def _fake_usage(mount_point: str) -> tuple[int, int, int]:
    sizes = {"/": (100_000_000_000, 85_000_000_000, 15_000_000_000)}
    return sizes.get(mount_point, (0, 0, 0))


def test_disk_detector_parses_mounts_and_excludes_pseudo_fs(fake_systems_dir: Path) -> None:
    disk = DiskDetector(root=fake_systems_dir / "ubuntu", usage_fn=_fake_usage).detect()
    mount_points = {fs.mount_point for fs in disk.filesystems}
    assert "/" in mount_points
    assert "/proc" not in mount_points  # pseudo fs excluded
    assert "/tmp" not in mount_points  # noqa: S108 - asserting exclusion, not using the path


def test_disk_detector_computes_usage_percent(fake_systems_dir: Path) -> None:
    disk = DiskDetector(root=fake_systems_dir / "ubuntu", usage_fn=_fake_usage).detect()
    root_fs = next(fs for fs in disk.filesystems if fs.mount_point == "/")
    assert root_fs.usage_percent == 85.0


def test_disk_detector_degrades_gracefully_without_proc_mounts(tmp_path: Path) -> None:
    disk = DiskDetector(root=tmp_path, usage_fn=_fake_usage).detect()
    assert disk.filesystems == ()


def test_disk_detector_skips_mount_points_that_raise_oserror(fake_systems_dir: Path) -> None:
    def raising_usage(mount_point: str) -> tuple[int, int, int]:
        raise OSError("no such mount")

    disk = DiskDetector(root=fake_systems_dir / "ubuntu", usage_fn=raising_usage).detect()
    assert disk.filesystems == ()
