"""Top-level orchestrator: assembles every detector's output into one ``SystemContext``.

This is the only place that decides detection order and wires one
detector's output into another's input (e.g. ``EnvironmentInfo.is_wsl``
feeding ``CapabilityDetector``). Individual detectors stay independently
testable; this module is what Phase 9's ``doctor`` and everything else
will call.
"""

from __future__ import annotations

import getpass
import os
import platform
import socket
from pathlib import Path

from hallfix.detectors.capabilities import CapabilityDetector
from hallfix.detectors.disk import DiskDetector, DiskUsageFn, real_disk_usage
from hallfix.detectors.distribution import DistributionDetector
from hallfix.detectors.environment import EnvironmentDetector
from hallfix.detectors.hardware import CpuDetector, MemoryDetector
from hallfix.detectors.internet import ConnectivityChecker, check_internet_connectivity
from hallfix.detectors.network import NetworkDetector
from hallfix.detectors.package_manager import PackageManagerDetector
from hallfix.detectors.sudo import SudoDetector
from hallfix.domain.models.system import SystemContext
from hallfix.infrastructure.commands.runner import CommandRunner


class SystemDetector:
    """Runs every detector and returns one immutable ``SystemContext``."""

    def __init__(
        self,
        *,
        root: Path = Path("/"),
        command_runner: CommandRunner,
        env: dict[str, str] | None = None,
        connectivity_checker: ConnectivityChecker = check_internet_connectivity,
        disk_usage_fn: DiskUsageFn = real_disk_usage,
    ) -> None:
        self._root = root
        self._env = env if env is not None else dict(os.environ)
        self._connectivity_checker = connectivity_checker

        self._distribution_detector = DistributionDetector(root=root)
        self._environment_detector = EnvironmentDetector(root=root)
        self._cpu_detector = CpuDetector(root=root)
        self._memory_detector = MemoryDetector(root=root)
        self._disk_detector = DiskDetector(root=root, usage_fn=disk_usage_fn)
        self._network_detector = NetworkDetector(root=root, command_runner=command_runner)
        self._package_manager_detector = PackageManagerDetector(root=root)
        self._sudo_detector = SudoDetector(root=root)
        self._capability_detector = CapabilityDetector(root=root, env=self._env)

    def detect(self) -> SystemContext:
        distribution = self._distribution_detector.detect()
        environment = self._environment_detector.detect()
        cpu = self._cpu_detector.detect()
        memory = self._memory_detector.detect()
        disk = self._disk_detector.detect()
        network = self._network_detector.detect()
        package_manager = self._package_manager_detector.detect()
        sudo = self._sudo_detector.detect()
        internet_reachable = self._connectivity_checker()

        capabilities = self._capability_detector.detect(
            network=network,
            sudo=sudo,
            package_manager=package_manager,
            is_wsl=environment.is_wsl,
            internet_reachable=internet_reachable,
        )

        return SystemContext(
            hostname=self._detect_hostname(),
            username=self._detect_username(),
            shell=self._env.get("SHELL"),
            kernel=self._detect_kernel(),
            architecture=cpu.architecture,
            uptime_seconds=self._detect_uptime(),
            distribution=distribution,
            environment=environment,
            capabilities=capabilities,
            cpu=cpu,
            memory=memory,
            disk=disk,
            network=network,
            package_manager=package_manager,
            sudo=sudo,
        )

    def _detect_hostname(self) -> str:
        hostname_path = self._root / "etc" / "hostname"
        if hostname_path.is_file():
            content = hostname_path.read_text(encoding="utf-8", errors="ignore").strip()
            if content:
                return content
        return socket.gethostname()

    def _detect_username(self) -> str:
        return self._env.get("USER") or self._env.get("LOGNAME") or getpass.getuser()

    def _detect_kernel(self) -> str:
        osrelease_path = self._root / "proc" / "sys" / "kernel" / "osrelease"
        if osrelease_path.is_file():
            content = osrelease_path.read_text(encoding="utf-8", errors="ignore").strip()
            if content:
                return content
        return platform.release()

    def _detect_uptime(self) -> float | None:
        uptime_path = self._root / "proc" / "uptime"
        if not uptime_path.is_file():
            return None
        try:
            first_field = uptime_path.read_text(encoding="utf-8", errors="ignore").split()[0]
            return float(first_field)
        except (IndexError, ValueError):
            return None
