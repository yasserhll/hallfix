from __future__ import annotations

from pathlib import Path

from hallfix.domain.models.command import CommandResult
from hallfix.domain.models.package import LockStatus
from hallfix.infrastructure.package_managers.apt import AptManager
from tests.fixtures.fake_command_runner import FakeCommandRunner, ok_result


def _manager(runner: FakeCommandRunner, root: Path) -> AptManager:
    return AptManager(command_runner=runner, root=root)


def test_detect_true_when_version_command_succeeds(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(("apt-get", "--version"), ok_result(("apt-get", "--version"), "apt 2.7.0"))
    assert _manager(runner, tmp_path).detect() is True


def test_detect_false_when_version_command_fails(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(("apt-get", "--version"), ok_result(("apt-get", "--version"), "", exit_code=127))
    assert _manager(runner, tmp_path).detect() is False


def test_install_success_looks_up_installed_version(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("apt-get", "install", "-y", "git"),
        ok_result(("apt-get", "install", "-y", "git"), "Setting up git ..."),
    )
    runner.stub(
        ("dpkg-query", "-W", "-f=${Version}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Version}", "git"), "1:2.43.0-1"),
    )
    result = _manager(runner, tmp_path).install("git")
    assert result.succeeded
    assert not result.already_satisfied
    assert result.installed_version == "1:2.43.0-1"
    assert result.dry_run is False


def test_install_detects_already_satisfied(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("apt-get", "install", "-y", "git"),
        ok_result(("apt-get", "install", "-y", "git"), "git is already the newest version.\n"),
    )
    runner.stub(
        ("dpkg-query", "-W", "-f=${Version}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Version}", "git"), "1:2.43.0-1"),
    )
    result = _manager(runner, tmp_path).install("git")
    assert result.already_satisfied


def test_install_dry_run_never_calls_real_runner(tmp_path: Path) -> None:
    runner = FakeCommandRunner()  # no stubs at all
    result = _manager(runner, tmp_path).install("git", dry_run=True)
    assert result.dry_run is True
    assert result.succeeded
    assert runner.calls == []  # dry-run bypassed the injected runner entirely


def test_install_skipped_when_lock_held(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    runner = FakeCommandRunner()  # unstubbed: install must never be attempted
    manager = _manager(runner, tmp_path)
    monkeypatch.setattr(manager, "check_lock", lambda: LockStatus(locked=True, lock_path="/x"))
    result = manager.install("git")
    assert not result.succeeded
    assert "busy" in result.message
    assert runner.calls == []


def test_remove_treats_not_installed_as_success(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("apt-get", "remove", "-y", "ghost-package"),
        CommandResult(
            argv=("apt-get", "remove", "-y", "ghost-package"),
            exit_code=100,
            stdout="Package 'ghost-package' is not installed, so not removed\n",
            stderr="",
            duration_seconds=0.1,
        ),
    )
    result = _manager(runner, tmp_path).remove("ghost-package")
    assert result.succeeded
    assert result.already_satisfied


def test_is_installed_true(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("dpkg-query", "-W", "-f=${Status}", "git"),
        ok_result(("dpkg-query", "-W", "-f=${Status}", "git"), "install ok installed"),
    )
    assert _manager(runner, tmp_path).is_installed("git") is True


def test_is_installed_false_for_unknown_package(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("dpkg-query", "-W", "-f=${Status}", "nope"),
        ok_result(("dpkg-query", "-W", "-f=${Status}", "nope"), "", exit_code=1),
    )
    assert _manager(runner, tmp_path).is_installed("nope") is False


def test_search_parses_name_and_description(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("apt-cache", "search", "git"),
        ok_result(
            ("apt-cache", "search", "git"),
            "git - fast, scalable, distributed revision control system\n"
            "git-lfs - Git extension for versioning large files\n",
        ),
    )
    results = _manager(runner, tmp_path).search("git")
    assert len(results) == 2
    assert results[0].name == "git"
    assert results[0].description == "fast, scalable, distributed revision control system"
    assert results[1].name == "git-lfs"


def test_upgrade_success(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("apt-get", "upgrade", "-y"),
        ok_result(("apt-get", "upgrade", "-y"), "0 upgraded, 0 newly installed"),
    )
    result = _manager(runner, tmp_path).upgrade()
    assert result.succeeded


def test_upgrade_skipped_when_lock_held(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    runner = FakeCommandRunner()  # unstubbed: upgrade must never be attempted
    manager = _manager(runner, tmp_path)
    monkeypatch.setattr(manager, "check_lock", lambda: LockStatus(locked=True, lock_path="/x"))
    result = manager.upgrade()
    assert not result.succeeded
    assert "busy" in result.message
    assert runner.calls == []


def test_upgrade_dry_run_never_calls_real_runner(tmp_path: Path) -> None:
    runner = FakeCommandRunner()  # no stubs at all
    result = _manager(runner, tmp_path).upgrade(dry_run=True)
    assert result.dry_run is True
    assert result.succeeded
    assert runner.calls == []


def test_repair_runs_configure_then_fix_broken(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(("dpkg", "--configure", "-a"), ok_result(("dpkg", "--configure", "-a"), ""))
    runner.stub(
        ("apt-get", "install", "--fix-broken", "-y"),
        ok_result(("apt-get", "install", "--fix-broken", "-y"), "0 upgraded"),
    )
    result = _manager(runner, tmp_path).repair()
    assert result.succeeded
    assert len(runner.calls) == 2
