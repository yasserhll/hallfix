"""Native package manager detection (spec §19/§21).

Checks for the presence of the manager's executable under ``root``'s bin
directories rather than using ``shutil.which`` against the real ``PATH`` —
keeps this detector consistent with every other detector's fake-root
testing story, and avoids depending on the *current* process's PATH
(which may differ from what a freshly-booted shell would see).

Detects the *native* (distribution) package manager only — never lets a
user swap this out (spec §21: no ``preferred_package_manager`` concept).
"""

from __future__ import annotations

from pathlib import Path

from hallfix.domain.models.system import PackageManagerInfo, PackageManagerKind

_BIN_DIRS = ("usr/bin", "usr/sbin", "bin", "sbin")

_CANDIDATES: tuple[tuple[str, PackageManagerKind], ...] = (
    ("apt-get", PackageManagerKind.APT),
    ("apt", PackageManagerKind.APT),
    ("dnf", PackageManagerKind.DNF),
    ("pacman", PackageManagerKind.PACMAN),
    ("zypper", PackageManagerKind.ZYPPER),
)


class PackageManagerDetector:
    def __init__(self, *, root: Path = Path("/")) -> None:
        self._root = root

    def detect(self) -> PackageManagerInfo:
        for binary_name, kind in _CANDIDATES:
            for bin_dir in _BIN_DIRS:
                candidate = self._root / bin_dir / binary_name
                if candidate.is_file():
                    return PackageManagerInfo(kind=kind, executable_path=str(candidate))
        return PackageManagerInfo(kind=PackageManagerKind.UNKNOWN, executable_path=None)
