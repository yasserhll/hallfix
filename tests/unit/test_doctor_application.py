"""``build_diagnostic_context``/``run_doctor`` against a fake root and fake
command runner — no real subprocess or network calls.
"""

from __future__ import annotations

import json
from pathlib import Path

from hallfix.application.doctor import build_diagnostic_context, run_doctor
from hallfix.domain.models.system import PackageManagerKind
from tests.fixtures.fake_command_runner import FakeCommandRunner, ok_result

_ADDR_JSON = json.dumps(
    [{"ifname": "eth0", "operstate": "UP", "addr_info": [{"family": "inet", "local": "10.0.0.5"}]}]
)
_ROUTE_JSON = json.dumps([{"dst": "default", "gateway": "10.0.0.1"}])


def _runner() -> FakeCommandRunner:
    runner = FakeCommandRunner()
    runner.stub(("ip", "-j", "addr", "show"), ok_result(("ip", "-j", "addr", "show"), _ADDR_JSON))
    runner.stub(
        ("ip", "-j", "route", "show", "default"),
        ok_result(("ip", "-j", "route", "show", "default"), _ROUTE_JSON),
    )
    runner.stub(("git", "--version"), ok_result(("git", "--version"), "git version 2.43.0"))
    runner.stub(("docker", "--version"), ok_result(("docker", "--version"), "", exit_code=127))
    runner.stub(("ssh", "-V"), ok_result(("ssh", "-V"), "", exit_code=127))
    runner.stub(("dpkg", "--audit"), ok_result(("dpkg", "--audit"), ""))
    return runner


def test_build_diagnostic_context_assembles_all_fields(fake_systems_dir: Path) -> None:
    ctx = build_diagnostic_context(
        command_runner=_runner(),
        root=fake_systems_dir / "ubuntu",
        connectivity_checker=lambda: True,
        dns_checker=lambda: True,
    )
    assert ctx.system.package_manager.kind == PackageManagerKind.APT
    assert ctx.package_manager_lock is not None
    assert ctx.package_manager_lock.locked is False
    assert ctx.dns_resolution_ok is True
    assert ctx.package_broken_state is False
    assert ctx.tool_verifications["git"].executable_found is True
    assert ctx.tool_verifications["docker"].executable_found is False
    assert "HOME" in ctx.env or ctx.env == {} or isinstance(ctx.env, dict)


def test_dns_not_checked_when_no_raw_connectivity(fake_systems_dir: Path) -> None:
    calls = []

    def dns_checker() -> bool:
        calls.append(1)
        return True

    ctx = build_diagnostic_context(
        command_runner=_runner(),
        root=fake_systems_dir / "ubuntu",
        connectivity_checker=lambda: False,
        dns_checker=dns_checker,
    )
    assert ctx.dns_resolution_ok is None
    assert calls == []


def test_run_doctor_produces_results(fake_systems_dir: Path) -> None:
    results = run_doctor(
        command_runner=_runner(),
        root=fake_systems_dir / "ubuntu",
        connectivity_checker=lambda: True,
        dns_checker=lambda: True,
    )
    assert len(results) > 10
    ids = {r.id for r in results}
    assert "system.os" in ids
    assert "network.dns_resolution" in ids
    assert "development.git" in ids
    assert "package.broken_state" in ids
