"""CPU and memory detection (spec §16/§17), reading stable Linux APIs.

Prefers ``/proc/cpuinfo`` and ``/proc/meminfo`` over shelling out to
``lscpu``/``free`` — stable format, no parsing-locale surprises, and
trivially fakeable in tests via an injected root.
"""

from __future__ import annotations

import platform
from pathlib import Path

from hallfix.domain.models.system import CpuInfo, MemoryInfo


def _parse_proc_table(text: str, separator: str) -> list[dict[str, str]]:
    """Split ``/proc/cpuinfo``-style content into per-processor blocks."""
    blocks: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            if current:
                blocks.append(current)
                current = {}
            continue
        if separator not in line:
            continue
        key, _, value = line.partition(separator)
        current[key.strip()] = value.strip()
    if current:
        blocks.append(current)
    return blocks


class CpuDetector:
    def __init__(self, *, root: Path = Path("/"), architecture: str | None = None) -> None:
        self._root = root
        self._architecture = architecture or platform.machine()

    def detect(self) -> CpuInfo:
        cpuinfo_path = self._root / "proc" / "cpuinfo"
        if not cpuinfo_path.is_file():
            return CpuInfo(model=None, architecture=self._architecture, cores=0, threads=0)

        processors = _parse_proc_table(
            cpuinfo_path.read_text(encoding="utf-8", errors="ignore"), ":"
        )
        threads = len(processors)
        model = processors[0].get("model name") if processors else None

        core_ids: set[tuple[str, str]] = set()
        for proc in processors:
            physical_id = proc.get("physical id", "0")
            core_id = proc.get("core id")
            if core_id is not None:
                core_ids.add((physical_id, core_id))
        cores = len(core_ids) if core_ids else threads

        return CpuInfo(model=model, architecture=self._architecture, cores=cores, threads=threads)


_MEMINFO_KEYS = {
    "MemTotal": "total_bytes",
    "MemAvailable": "available_bytes",
    "SwapTotal": "swap_total_bytes",
    "SwapFree": "swap_free_bytes",
}


class MemoryDetector:
    def __init__(self, *, root: Path = Path("/")) -> None:
        self._root = root

    def detect(self) -> MemoryInfo:
        meminfo_path = self._root / "proc" / "meminfo"
        if not meminfo_path.is_file():
            return MemoryInfo(
                total_bytes=0, available_bytes=0, swap_total_bytes=0, swap_free_bytes=0
            )

        values: dict[str, int] = {}
        for line in meminfo_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if ":" not in line:
                continue
            key, _, rest = line.partition(":")
            key = key.strip()
            if key not in _MEMINFO_KEYS:
                continue
            digits = "".join(ch for ch in rest if ch.isdigit())
            if digits:
                values[_MEMINFO_KEYS[key]] = int(digits) * 1024  # kB -> bytes

        return MemoryInfo(
            total_bytes=values.get("total_bytes", 0),
            available_bytes=values.get("available_bytes", 0),
            swap_total_bytes=values.get("swap_total_bytes", 0),
            swap_free_bytes=values.get("swap_free_bytes", 0),
        )
