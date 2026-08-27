"""``build_report`` against a fake root and fake command runner — no real
subprocess or network calls. Also verifies the report generator doesn't
double up on detection I/O (a real bug caught and fixed while writing
this phase: calling both ``run_doctor`` and ``build_diagnostic_context``
separately would have run every check twice).
"""

from __future__ import annotations

import json
from pathlib import Path

from hallfix.application.report_generator import build_report
from hallfix.domain.models.history import ActionOutcome
from hallfix.infrastructure.state.history_store import HistoryStore
from hallfix.infrastructure.state.store import StateStore
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


def test_build_report_assembles_system_and_diagnostics(fake_systems_dir: Path) -> None:
    report = build_report(
        command_runner=_runner(),
        root=fake_systems_dir / "ubuntu",
        connectivity_checker=lambda: True,
        dns_checker=lambda: True,
    )
    assert report.system.distribution.id == "ubuntu"
    assert len(report.diagnostics) > 10
    assert report.health is not None


def test_build_report_does_not_duplicate_detection_io(fake_systems_dir: Path) -> None:
    runner = _runner()
    build_report(
        command_runner=runner,
        root=fake_systems_dir / "ubuntu",
        connectivity_checker=lambda: True,
        dns_checker=lambda: True,
    )
    addr_calls = [c for c in runner.calls if c.argv == ("ip", "-j", "addr", "show")]
    audit_calls = [c for c in runner.calls if c.argv == ("dpkg", "--audit")]
    git_calls = [c for c in runner.calls if c.argv == ("git", "--version")]
    assert len(addr_calls) == 1, "network detection ran more than once"
    assert len(audit_calls) == 1, "dpkg --audit ran more than once"
    assert len(git_calls) == 1, "git verification ran more than once"


def test_build_report_managed_tools_empty_when_no_state(fake_systems_dir: Path) -> None:
    report = build_report(
        command_runner=_runner(),
        root=fake_systems_dir / "ubuntu",
        connectivity_checker=lambda: True,
        dns_checker=lambda: True,
    )
    assert report.managed_tools == ()


def test_build_report_recent_operations_empty_when_no_history(fake_systems_dir: Path) -> None:
    report = build_report(
        command_runner=_runner(),
        root=fake_systems_dir / "ubuntu",
        connectivity_checker=lambda: True,
        dns_checker=lambda: True,
    )
    assert report.recent_operations == ()


def test_build_report_includes_managed_tools_from_state_store(fake_systems_dir: Path) -> None:
    StateStore().record_installed("git")
    runner = _runner()
    runner.stub(
        ("dpkg-query", "-W", "-f=${Version}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Version}", "git"), "2.43.0"),
    )

    report = build_report(
        command_runner=runner,
        root=fake_systems_dir / "ubuntu",
        connectivity_checker=lambda: True,
        dns_checker=lambda: True,
    )

    assert len(report.managed_tools) == 1
    summary = report.managed_tools[0]
    assert summary.tool_id == "git"
    assert summary.installed_by_hallfix is True
    assert summary.executable_found is True


def test_build_report_includes_recent_operations_from_history_store(fake_systems_dir: Path) -> None:
    HistoryStore().append(
        command="tool install git",
        plan_id="p1",
        plan_description="Install Git",
        dry_run=False,
        plan_reversible=True,
        action_outcomes=(
            ActionOutcome(
                action_type="INSTALL_PACKAGE", succeeded=True, already_satisfied=False, message="ok"
            ),
        ),
    )

    report = build_report(
        command_runner=_runner(),
        root=fake_systems_dir / "ubuntu",
        connectivity_checker=lambda: True,
        dns_checker=lambda: True,
    )

    assert len(report.recent_operations) == 1
    assert report.recent_operations[0].command == "tool install git"


def test_build_report_recent_operations_most_recent_first_and_limited(
    fake_systems_dir: Path,
) -> None:
    history = HistoryStore()
    for i in range(15):
        history.append(
            command=f"op {i}", plan_id="p", plan_description="d", dry_run=True, plan_reversible=True
        )

    report = build_report(
        command_runner=_runner(),
        root=fake_systems_dir / "ubuntu",
        connectivity_checker=lambda: True,
        dns_checker=lambda: True,
        history_limit=10,
    )

    assert len(report.recent_operations) == 10
    assert report.recent_operations[0].command == "op 14"  # most recent first
    assert report.recent_operations[-1].command == "op 5"
