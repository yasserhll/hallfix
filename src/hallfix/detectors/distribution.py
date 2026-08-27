"""Distribution detection via ``/etc/os-release`` (spec §12).

Never assumes Ubuntu because ``apt`` exists — this reads only the standard
os-release fields and falls back through ``ID_LIKE`` for derivatives
(Pop!_OS, Mint, etc.) rather than hardcoding a derivative list.
"""

from __future__ import annotations

import shlex
from pathlib import Path

from hallfix.domain.exceptions import DetectionError
from hallfix.domain.models.system import DistributionFamily, DistributionInfo

_OS_RELEASE_CANDIDATES = ("etc/os-release", "usr/lib/os-release")

_FAMILY_BY_ID = {
    "debian": DistributionFamily.DEBIAN,
    "ubuntu": DistributionFamily.DEBIAN,
    "linuxmint": DistributionFamily.DEBIAN,
    "pop": DistributionFamily.DEBIAN,
    "kali": DistributionFamily.DEBIAN,
    "raspbian": DistributionFamily.DEBIAN,
    "fedora": DistributionFamily.REDHAT,
    "rhel": DistributionFamily.REDHAT,
    "rocky": DistributionFamily.REDHAT,
    "almalinux": DistributionFamily.REDHAT,
    "centos": DistributionFamily.REDHAT,
    "arch": DistributionFamily.ARCH,
    "manjaro": DistributionFamily.ARCH,
    "endeavouros": DistributionFamily.ARCH,
    "opensuse": DistributionFamily.SUSE,
    "opensuse-leap": DistributionFamily.SUSE,
    "opensuse-tumbleweed": DistributionFamily.SUSE,
    "sles": DistributionFamily.SUSE,
}


def parse_os_release(text: str) -> dict[str, str]:
    """Parse ``KEY=VALUE`` os-release content, honoring shell-style quoting."""
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, raw_value = stripped.partition("=")
        try:
            (value,) = shlex.split(raw_value) if raw_value.strip() else ("",)
        except ValueError:
            value = raw_value.strip().strip('"').strip("'")
        fields[key.strip()] = value
    return fields


def _resolve_family(distro_id: str, id_like: tuple[str, ...]) -> DistributionFamily:
    for candidate in (distro_id, *id_like):
        family = _FAMILY_BY_ID.get(candidate)
        if family is not None:
            return family
    return DistributionFamily.UNKNOWN


class DistributionDetector:
    """Detects the Linux distribution from ``/etc/os-release`` under ``root``."""

    def __init__(self, *, root: Path = Path("/")) -> None:
        self._root = root

    def detect(self) -> DistributionInfo:
        for candidate in _OS_RELEASE_CANDIDATES:
            path = self._root / candidate
            if path.is_file():
                return self._parse(path)
        msg = f"no os-release file found under {self._root} (checked {_OS_RELEASE_CANDIDATES})"
        raise DetectionError(msg)

    def _parse(self, path: Path) -> DistributionInfo:
        fields = parse_os_release(path.read_text(encoding="utf-8"))
        distro_id = fields.get("ID", "linux")
        id_like = tuple(fields.get("ID_LIKE", "").split())
        family = _resolve_family(distro_id, id_like)
        return DistributionInfo(
            id=distro_id,
            id_like=id_like,
            version_id=fields.get("VERSION_ID"),
            version_codename=fields.get("VERSION_CODENAME"),
            pretty_name=fields.get("PRETTY_NAME"),
            family=family,
        )
