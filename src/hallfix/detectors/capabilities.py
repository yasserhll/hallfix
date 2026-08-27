"""Capability detection (spec §15).

Behavior should depend on capabilities rather than distribution names, so
this detector is the single place that answers "can this system do X" —
callers (diagnostics, planner, later phases) check a flag here instead of
re-deriving it. Takes already-detected ``NetworkInfo``/``SudoInfo``/
``PackageManagerInfo`` as input rather than re-detecting them, to avoid two
places disagreeing about the same fact.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from hallfix.domain.models.system import (
    CapabilitySet,
    NetworkInfo,
    PackageManagerInfo,
    PackageManagerKind,
    SudoInfo,
)

_BIN_DIRS = ("usr/bin", "usr/sbin", "bin", "sbin")
_NETWORK_MANAGER_BINARIES = ("nmcli",)
_CONTAINER_RUNTIME_BINARIES = ("docker", "podman")


def _binary_exists(root: Path, names: tuple[str, ...]) -> bool:
    return any((root / bin_dir / name).is_file() for bin_dir in _BIN_DIRS for name in names)


def _default_writable_check(root: Path) -> bool:
    probe_dir = Path(tempfile.gettempdir()) if root == Path("/") else root
    try:
        with tempfile.NamedTemporaryFile(dir=probe_dir):
            return True
    except OSError:
        return False


class CapabilityDetector:
    def __init__(self, *, root: Path = Path("/"), env: dict[str, str] | None = None) -> None:
        self._root = root
        self._env = env if env is not None else dict(os.environ)

    def detect(
        self,
        *,
        network: NetworkInfo,
        sudo: SudoInfo,
        package_manager: PackageManagerInfo,
        is_wsl: bool,
        internet_reachable: bool,
    ) -> CapabilitySet:
        return CapabilitySet(
            package_management=package_manager.kind != PackageManagerKind.UNKNOWN,
            systemd=(self._root / "run" / "systemd" / "system").is_dir(),
            sudo=sudo.available,
            graphical_session=bool(self._env.get("DISPLAY") or self._env.get("WAYLAND_DISPLAY")),
            network_manager=_binary_exists(self._root, _NETWORK_MANAGER_BINARIES),
            selinux=(self._root / "sys" / "fs" / "selinux").is_dir(),
            apparmor=(self._root / "sys" / "kernel" / "security" / "apparmor").is_dir(),
            container_runtime=_binary_exists(self._root, _CONTAINER_RUNTIME_BINARIES),
            wsl=is_wsl,
            immutable_os=(self._root / "run" / "ostree-booted").is_file(),
            filesystem_write_access=_default_writable_check(self._root),
            internet_access=internet_reachable,
            ipv4=network.has_ipv4,
            ipv6=network.has_ipv6,
        )
