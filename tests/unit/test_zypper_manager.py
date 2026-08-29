from __future__ import annotations

from pathlib import Path

from hallfix.domain.models.command import CommandResult
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


def test_upgrade_success(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("zypper", "--non-interactive", "update"),
        ok_result(("zypper", "--non-interactive", "update"), "Nothing to do."),
    )
    result = _manager(runner, tmp_path).upgrade()
    assert result.succeeded


def test_repair_runs_verify(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("zypper", "--non-interactive", "verify"),
        ok_result(("zypper", "--non-interactive", "verify"), "Dependencies OK"),
    )
    result = _manager(runner, tmp_path).repair()
    assert result.succeeded


def test_remove_success(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("zypper", "--non-interactive", "remove", "git"),
        ok_result(("zypper", "--non-interactive", "remove", "git"), "Removing: git"),
    )
    result = _manager(runner, tmp_path).remove("git")
    assert result.succeeded
    assert not result.already_satisfied


def test_remove_not_installed_is_already_satisfied(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("zypper", "--non-interactive", "remove", "git"),
        CommandResult(
            argv=("zypper", "--non-interactive", "remove", "git"),
            exit_code=104,
            stdout="",
            stderr="package 'git' not found",
            duration_seconds=0.0,
        ),
    )
    result = _manager(runner, tmp_path).remove("git")
    assert result.succeeded
    assert result.already_satisfied


def test_refresh_metadata_success(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("zypper", "--non-interactive", "refresh"),
        ok_result(("zypper", "--non-interactive", "refresh"), "All repositories refreshed"),
    )
    result = _manager(runner, tmp_path).refresh_metadata()
    assert result.succeeded


def test_is_installed_true_and_false(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(("rpm", "-q", "git"), ok_result(("rpm", "-q", "git"), "git-2.43.0-1.1.x86_64"))
    runner.stub(("rpm", "-q", "missing"), ok_result(("rpm", "-q", "missing"), "", exit_code=1))
    manager = _manager(runner, tmp_path)
    assert manager.is_installed("git")
    assert not manager.is_installed("missing")


def test_get_version_returns_none_when_not_found(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("rpm", "-q", "--qf", "%{VERSION}-%{RELEASE}", "missing"),
        ok_result(("rpm", "-q", "--qf", "%{VERSION}-%{RELEASE}", "missing"), "", exit_code=1),
    )
    result = _manager(runner, tmp_path).get_version("missing")
    assert result is None
