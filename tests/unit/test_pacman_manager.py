from __future__ import annotations

from pathlib import Path

from hallfix.domain.models.command import CommandResult
from hallfix.infrastructure.package_managers.pacman import PacmanManager
from tests.fixtures.fake_command_runner import FakeCommandRunner, ok_result


def _manager(runner: FakeCommandRunner, root: Path) -> PacmanManager:
    return PacmanManager(command_runner=runner, root=root)


def test_install_success(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("pacman", "-S", "--noconfirm", "--needed", "git"),
        ok_result(("pacman", "-S", "--noconfirm", "--needed", "git"), "installing git..."),
    )
    runner.stub(("pacman", "-Q", "git"), ok_result(("pacman", "-Q", "git"), "git 2.44.0-1"))
    result = _manager(runner, tmp_path).install("git")
    assert result.succeeded
    assert result.installed_version == "2.44.0-1"


def test_install_already_up_to_date_is_already_satisfied(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("pacman", "-S", "--noconfirm", "--needed", "git"),
        ok_result(
            ("pacman", "-S", "--noconfirm", "--needed", "git"),
            "warning: git-2.44.0-1 is up to date -- skipping\n",
        ),
    )
    runner.stub(("pacman", "-Q", "git"), ok_result(("pacman", "-Q", "git"), "git 2.44.0-1"))
    result = _manager(runner, tmp_path).install("git")
    assert result.already_satisfied


def test_remove_treats_target_not_found_as_success(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("pacman", "-R", "--noconfirm", "ghost"),
        CommandResult(
            argv=("pacman", "-R", "--noconfirm", "ghost"),
            exit_code=1,
            stdout="",
            stderr="error: target not found: ghost\n",
            duration_seconds=0.05,
        ),
    )
    result = _manager(runner, tmp_path).remove("ghost")
    assert result.succeeded
    assert result.already_satisfied


def test_search_parses_repo_name_version_and_description(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("pacman", "-Ss", "git"),
        ok_result(
            ("pacman", "-Ss", "git"),
            "extra/git 2.44.0-1\n    the fast distributed version control system\n",
        ),
    )
    results = _manager(runner, tmp_path).search("git")
    assert len(results) == 1
    assert results[0].name == "git"
    assert results[0].version == "2.44.0-1"
    assert results[0].description == "the fast distributed version control system"


def test_upgrade_runs_full_sync_and_upgrade(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(("pacman", "-Syu", "--noconfirm"), ok_result(("pacman", "-Syu", "--noconfirm"), ""))
    result = _manager(runner, tmp_path).upgrade()
    assert result.succeeded


def test_repair_forces_full_resync(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(("pacman", "-Syy", "--noconfirm"), ok_result(("pacman", "-Syy", "--noconfirm"), ""))
    result = _manager(runner, tmp_path).repair()
    assert result.succeeded
