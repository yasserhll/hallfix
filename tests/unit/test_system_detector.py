from __future__ import annotations

import json
from pathlib import Path

from hallfix.detectors.system import SystemDetector
from hallfix.domain.models.system import DistributionFamily, PackageManagerKind, VirtualizationKind
from tests.fixtures.fake_command_runner import FakeCommandRunner, ok_result

_ADDR_JSON = json.dumps([])
_ROUTE_JSON = json.dumps([])


def _build_detector(root: Path, *, connectivity: bool = True) -> SystemDetector:
    runner = FakeCommandRunner()
    runner.stub(("ip", "-j", "addr", "show"), ok_result(("ip", "-j", "addr", "show"), _ADDR_JSON))
    runner.stub(
        ("ip", "-j", "route", "show", "default"),
        ok_result(("ip", "-j", "route", "show", "default"), _ROUTE_JSON),
    )

    def usage_fn(mount_point: str) -> tuple[int, int, int]:
        return (100_000_000_000, 50_000_000_000, 50_000_000_000)

    return SystemDetector(
        root=root,
        command_runner=runner,
        env={"USER": "tester", "SHELL": "/bin/bash"},
        connectivity_checker=lambda: connectivity,
        disk_usage_fn=usage_fn,
    )


def test_assembles_full_system_context_for_ubuntu(fake_systems_dir: Path) -> None:
    ctx = _build_detector(fake_systems_dir / "ubuntu").detect()

    assert ctx.distribution.id == "ubuntu"
    assert ctx.distribution.family == DistributionFamily.DEBIAN
    assert ctx.environment.kind == VirtualizationKind.BARE_METAL
    assert ctx.package_manager.kind == PackageManagerKind.APT
    assert ctx.hostname == "test-host"
    assert ctx.username == "tester"
    assert ctx.shell == "/bin/bash"
    assert ctx.cpu.threads == 4
    assert ctx.memory.total_bytes > 0
    assert ctx.uptime_seconds == 123456.78
    assert ctx.capabilities.systemd is True
    assert ctx.capabilities.internet_access is True
    assert ctx.capabilities.package_management is True


def test_assembles_context_for_wsl(fake_systems_dir: Path) -> None:
    ctx = _build_detector(fake_systems_dir / "wsl_ubuntu", connectivity=False).detect()
    assert ctx.environment.kind == VirtualizationKind.WSL2
    assert ctx.capabilities.wsl is True
    assert ctx.capabilities.internet_access is False


def test_hostname_falls_back_to_socket_when_no_etc_hostname(tmp_path: Path) -> None:
    (tmp_path / "etc").mkdir()
    (tmp_path / "etc" / "os-release").write_text(
        'ID=ubuntu\nPRETTY_NAME="Ubuntu"\n', encoding="utf-8"
    )
    ctx = _build_detector(tmp_path).detect()
    assert ctx.hostname  # non-empty, came from socket.gethostname() fallback
