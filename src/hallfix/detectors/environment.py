"""Environment detection: bare metal / VM / WSL / container (spec §14).

Order matters: WSL and container checks run before generic VM detection,
since a WSL2 instance also reports a Microsoft/Hyper-V DMI vendor and would
otherwise be misclassified as a plain VM.

WSL1 vs WSL2 distinction: both patch the kernel release string. WSL2 ships
a real Linux kernel whose release contains "WSL2"; WSL1 (a translation
layer, not a real kernel) reports "Microsoft" without "WSL2". This is the
same heuristic used by common WSL-detection tooling.
"""

from __future__ import annotations

from pathlib import Path

from hallfix.domain.models.system import EnvironmentInfo, VirtualizationKind

_VM_VENDOR_MARKERS = (
    "qemu",
    "vmware",
    "virtualbox",
    "innotek gmbh",
    "microsoft corporation",  # Hyper-V
    "xen",
    "kvm",
    "bochs",
    "parallels",
)

_CONTAINER_TYPE_MAP = {
    "docker": VirtualizationKind.DOCKER,
    "podman": VirtualizationKind.PODMAN,
    "lxc": VirtualizationKind.LXC,
    "lxc-libvirt": VirtualizationKind.LXC,
    "systemd-nspawn": VirtualizationKind.SYSTEMD_NSPAWN,
}


class EnvironmentDetector:
    """Detects the virtualization/container environment under ``root``."""

    def __init__(self, *, root: Path = Path("/")) -> None:
        self._root = root

    def detect(self) -> EnvironmentInfo:
        wsl = self._detect_wsl()
        if wsl is not None:
            return wsl

        container = self._detect_container()
        if container is not None:
            return container

        vm = self._detect_vm()
        if vm is not None:
            return vm

        return EnvironmentInfo(kind=VirtualizationKind.BARE_METAL)

    def _detect_wsl(self) -> EnvironmentInfo | None:
        osrelease_path = self._root / "proc" / "sys" / "kernel" / "osrelease"
        version_path = self._root / "proc" / "version"
        text = ""
        for path in (osrelease_path, version_path):
            if path.is_file():
                text += path.read_text(encoding="utf-8", errors="ignore").lower()

        if "microsoft" not in text:
            return None
        kind = VirtualizationKind.WSL2 if "wsl2" in text else VirtualizationKind.WSL1
        return EnvironmentInfo(kind=kind)

    def _detect_container(self) -> EnvironmentInfo | None:
        container_marker = self._root / "run" / "systemd" / "container"
        if container_marker.is_file():
            content = container_marker.read_text(encoding="utf-8", errors="ignore").strip().lower()
            kind = _CONTAINER_TYPE_MAP.get(content)
            if kind is not None:
                return EnvironmentInfo(kind=kind, detail=content)
            return EnvironmentInfo(kind=VirtualizationKind.UNKNOWN_VIRTUALIZED, detail=content)

        if (self._root / ".dockerenv").exists():
            return EnvironmentInfo(kind=VirtualizationKind.DOCKER)

        containerenv = self._root / "run" / ".containerenv"
        if containerenv.exists():
            return EnvironmentInfo(kind=VirtualizationKind.PODMAN)

        cgroup_path = self._root / "proc" / "1" / "cgroup"
        if cgroup_path.is_file():
            content = cgroup_path.read_text(encoding="utf-8", errors="ignore").lower()
            for marker, kind in _CONTAINER_TYPE_MAP.items():
                if marker in content:
                    return EnvironmentInfo(kind=kind)

        return None

    def _detect_vm(self) -> EnvironmentInfo | None:
        dmi_dir = self._root / "sys" / "class" / "dmi" / "id"
        for field in ("product_name", "sys_vendor", "bios_vendor"):
            path = dmi_dir / field
            if not path.is_file():
                continue
            value = path.read_text(encoding="utf-8", errors="ignore").strip()
            lowered = value.lower()
            for marker in _VM_VENDOR_MARKERS:
                if marker in lowered:
                    return EnvironmentInfo(kind=VirtualizationKind.VIRTUAL_MACHINE, detail=value)
        return None
