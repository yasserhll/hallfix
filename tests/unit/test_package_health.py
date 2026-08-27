from __future__ import annotations

from hallfix.detectors.package_health import check_dpkg_broken_state
from tests.fixtures.fake_command_runner import FakeCommandRunner, ok_result


def test_returns_false_when_audit_output_empty() -> None:
    runner = FakeCommandRunner()
    runner.stub(("dpkg", "--audit"), ok_result(("dpkg", "--audit"), ""))
    assert check_dpkg_broken_state(runner) is False


def test_returns_true_when_audit_reports_issues() -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("dpkg", "--audit"),
        ok_result(
            ("dpkg", "--audit"), "The following packages are in an inconsistent state:\n git"
        ),
    )
    assert check_dpkg_broken_state(runner) is True


def test_returns_false_when_command_fails() -> None:
    runner = FakeCommandRunner()
    runner.stub(("dpkg", "--audit"), ok_result(("dpkg", "--audit"), "", exit_code=127))
    assert check_dpkg_broken_state(runner) is False
