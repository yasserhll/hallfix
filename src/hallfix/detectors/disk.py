"""Disk/filesystem detection (spec §16/§17).

Mount list comes from ``/proc/mounts`` (stable, fakeable via ``root``).
Usage figures come from a small injectable function rather than calling
``os.statvfs``/``shutil.disk_usage`` directly, since those only work
against paths that are actually mounted on this machine — tests need to
supply canned usage numbers for a fake mount point.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from hallfix.domain.models.system import DiskInfo, MountedFilesystem

DiskUsageFn = Callable[[str], tuple[int, int, int]]
"""mount_point -> (total_bytes, used_bytes, available_bytes)."""

_PSEUDO_FS_TYPES = frozenset(
    {
        "proc",
        "sysfs",
        "devtmpfs",
        "devpts",
        "tmpfs",
        "cgroup",
        "cgroup2",
        "mqueue",
        "pstore",
        "debugfs",
        "tracefs",
        "securityfs",
        "configfs",
        "binfmt_misc",
        "autofs",
        "nsfs",
        "hugetlbfs",
        "fusectl",
        "bpf",
        "ramfs",
        "efivarfs",
        "rpc_pipefs",
    }
)


def real_disk_usage(mount_point: str) -> tuple[int, int, int]:
    import shutil

    usage = shutil.disk_usage(mount_point)
    return usage.total, usage.used, usage.free


class DiskDetector:
    def __init__(
        self,
        *,
        root: Path = Path("/"),
        usage_fn: DiskUsageFn = real_disk_usage,
    ) -> None:
        self._root = root
        self._usage_fn = usage_fn

    def detect(self) -> DiskInfo:
        mounts_path = self._root / "proc" / "mounts"
        if not mounts_path.is_file():
            return DiskInfo()

        filesystems: list[MountedFilesystem] = []
        for line in mounts_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            device, mount_point, fs_type = parts[0], parts[1], parts[2]
            if fs_type in _PSEUDO_FS_TYPES:
                continue

            try:
                total, used, available = self._usage_fn(mount_point)
            except OSError:
                continue

            filesystems.append(
                MountedFilesystem(
                    mount_point=mount_point,
                    device=device,
                    filesystem_type=fs_type,
                    total_bytes=total,
                    used_bytes=used,
                    available_bytes=available,
                )
            )

        return DiskInfo(filesystems=tuple(filesystems))
