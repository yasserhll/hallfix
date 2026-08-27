"""Maps a detected ``PackageManagerKind`` to its concrete adapter (spec §19).

Deliberately the *only* place that knows every concrete manager class —
callers ask for a manager by kind, never import ``AptManager`` etc.
directly, so adding a new manager later means touching one file.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from hallfix.domain.models.system import PackageManagerKind
from hallfix.infrastructure.commands.runner import CommandRunner
from hallfix.infrastructure.package_managers.apt import AptManager
from hallfix.infrastructure.package_managers.base import PackageManager
from hallfix.infrastructure.package_managers.dnf import DnfManager
from hallfix.infrastructure.package_managers.pacman import PacmanManager
from hallfix.infrastructure.package_managers.zypper import ZypperManager

_MANAGERS: dict[PackageManagerKind, Callable[..., PackageManager]] = {
    PackageManagerKind.APT: AptManager,
    PackageManagerKind.DNF: DnfManager,
    PackageManagerKind.PACMAN: PacmanManager,
    PackageManagerKind.ZYPPER: ZypperManager,
}


def create_package_manager(
    kind: PackageManagerKind,
    *,
    command_runner: CommandRunner,
    root: Path = Path("/"),
) -> PackageManager | None:
    """Returns the adapter for ``kind``, or ``None`` for `UNKNOWN`."""
    manager_class = _MANAGERS.get(kind)
    if manager_class is None:
        return None
    return manager_class(command_runner=command_runner, root=root)
