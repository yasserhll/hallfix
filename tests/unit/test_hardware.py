from __future__ import annotations

from pathlib import Path

from hallfix.detectors.hardware import CpuDetector, MemoryDetector


def test_cpu_detector_counts_cores_and_threads(fake_systems_dir: Path) -> None:
    cpu = CpuDetector(root=fake_systems_dir / "ubuntu", architecture="x86_64").detect()
    assert cpu.threads == 4
    assert cpu.cores == 2
    assert cpu.model == "Test CPU Model"
    assert cpu.architecture == "x86_64"


def test_cpu_detector_degrades_gracefully_without_cpuinfo(tmp_path: Path) -> None:
    cpu = CpuDetector(root=tmp_path, architecture="aarch64").detect()
    assert cpu.threads == 0
    assert cpu.cores == 0
    assert cpu.model is None
    assert cpu.architecture == "aarch64"


def test_memory_detector_parses_meminfo(fake_systems_dir: Path) -> None:
    memory = MemoryDetector(root=fake_systems_dir / "ubuntu").detect()
    assert memory.total_bytes == 16384000 * 1024
    assert memory.available_bytes == 8192000 * 1024
    assert memory.swap_total_bytes == 2000000 * 1024
    assert memory.swap_free_bytes == 1500000 * 1024


def test_memory_detector_degrades_gracefully_without_meminfo(tmp_path: Path) -> None:
    memory = MemoryDetector(root=tmp_path).detect()
    assert memory.total_bytes == 0
    assert memory.available_bytes == 0
