"""Sudo availability detection (spec §16).

Reports whether a ``sudo`` binary exists and whether the current process is
already root. Deliberately does *not* attempt ``sudo -n true`` or inspect
group membership — that would mean invoking a privileged command purely
for detection, and either false-negatives on valid but unconfigured setups
or side effects. "Available" here means "the tool exists to be used", not
"is authorized" — spec §84: sudo availability is never treated as blanket
authorization anyway.
"""

from __future__ import annotations

import os
from pathlib import Path

from hallfix.domain.models.system import SudoInfo

_BIN_DIRS = ("usr/bin", "usr/sbin", "bin", "sbin")


class SudoDetector:
    def __init__(self, *, root: Path = Path("/"), euid: int | None = None) -> None:
        self._root = root
        self._euid = euid if euid is not None else os.geteuid()

    def detect(self) -> SudoInfo:
        available = any((self._root / bin_dir / "sudo").is_file() for bin_dir in _BIN_DIRS)
        return SudoInfo(available=available, running_as_root=self._euid == 0)
