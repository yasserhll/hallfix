from __future__ import annotations

from pathlib import Path

from hallfix.domain.models.package import LockStatus
from hallfix.infrastructure.package_managers.dnf import DnfManager
from tests.fixtures.fake_command_runner import FakeCommandRunner, ok_result


def _manager(runner: FakeCommandRunner, root: Path) -> DnfManager:
    return DnfManager(command_runner=runner, root=root)


def test_install_success(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("dnf", "install", "-y", "git"),
        ok_result(("dnf", "install", "-y", "git"), "Installed: git"),
    )
    runner.stub(
        ("rpm", "-q", "--qf", "%{VERSION}-%{RELEASE}", "git"),
        ok_result(("rpm", "-q", "--qf", "%{VERSION}-%{RELEASE}", "git"), "2.43.0-1.fc40"),
    )
    result = _manager(runner, tmp_path).install("git")
    assert result.succeeded
    assert result.installed_version == "2.43.0-1.fc40"


def test_install_dry_run_does_not_touch_runner(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    result = _manager(runner, tmp_path).install("git", dry_run=True)
    assert result.dry_run and result.succeeded
    assert runner.calls == []


def test_install_skipped_when_locked(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    runner = FakeCommandRunner()
    manager = _manager(runner, tmp_path)
    monkeypatch.setattr(manager, "check_lock", lambda: LockStatus(locked=True, lock_path="/x"))
    result = manager.install("git")
    assert not result.succeeded
    assert runner.calls == []


def test_is_installed_uses_rpm(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(("rpm", "-q", "git"), ok_result(("rpm", "-q", "git"), "git-2.43.0-1.fc40"))
    assert _manager(runner, tmp_path).is_installed("git") is True


def test_search_parses_name_dot_arch_colon_description(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("dnf", "search", "git"),
        ok_result(
            ("dnf", "search", "git"),
            "=== Name Matched: git ===\ngit.x86_64 : Fast Version Control System\n",
        ),
    )
    results = _manager(runner, tmp_path).search("git")
    assert len(results) == 1
    assert results[0].name == "git"
    assert results[0].description == "Fast Version Control System"


def test_repair_cleans_and_rebuilds_cache(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(("dnf", "clean", "all"), ok_result(("dnf", "clean", "all"), ""))
    runner.stub(("dnf", "makecache"), ok_result(("dnf", "makecache"), ""))
    result = _manager(runner, tmp_path).repair()
    assert result.succeeded
