from __future__ import annotations

from pathlib import Path

from hallfix.infrastructure.package_managers.zypper import ZypperManager
from tests.fixtures.fake_command_runner import FakeCommandRunner, ok_result


def _manager(runner: FakeCommandRunner, root: Path) -> ZypperManager:
    return ZypperManager(command_runner=runner, root=root)


def test_install_success(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("zypper", "--non-interactive", "install", "git"),
        ok_result(("zypper", "--non-interactive", "install", "git"), "Installing: git"),
    )
    runner.stub(
        ("rpm", "-q", "--qf", "%{VERSION}-%{RELEASE}", "git"),
        ok_result(("rpm", "-q", "--qf", "%{VERSION}-%{RELEASE}", "git"), "2.43.0-1.1"),
    )
    result = _manager(runner, tmp_path).install("git")
    assert result.succeeded
    assert result.installed_version == "2.43.0-1.1"


def test_install_already_installed(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("zypper", "--non-interactive", "install", "git"),
        ok_result(
            ("zypper", "--non-interactive", "install", "git"),
            "'git' is already installed.\n",
        ),
    )
    runner.stub(
        ("rpm", "-q", "--qf", "%{VERSION}-%{RELEASE}", "git"),
        ok_result(("rpm", "-q", "--qf", "%{VERSION}-%{RELEASE}", "git"), "2.43.0-1.1"),
    )
    result = _manager(runner, tmp_path).install("git")
    assert result.already_satisfied


def test_search_parses_pipe_delimited_table(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("zypper", "--non-interactive", "search", "git"),
        ok_result(
            ("zypper", "--non-interactive", "search", "git"),
            "S | Name | Summary                | Type\n"
            "--+------+------------------------+-----\n"
            "i | git  | Fast Version Control   | package\n",
        ),
    )
    results = _manager(runner, tmp_path).search("git")
    assert len(results) == 1
    assert results[0].name == "git"
    assert results[0].description == "Fast Version Control"


def test_repair_runs_verify(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("zypper", "--non-interactive", "verify"),
        ok_result(("zypper", "--non-interactive", "verify"), "Dependencies OK"),
    )
    result = _manager(runner, tmp_path).repair()
    assert result.succeeded
