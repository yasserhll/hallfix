from __future__ import annotations

import sys
from pathlib import Path

from hallfix.domain.models.command import CommandSpec
from hallfix.infrastructure.commands.runner import (
    DryRunCommandRunner,
    SubprocessCommandRunner,
    build_command_runner,
)
from hallfix.infrastructure.logging.logger import setup_logging


def test_subprocess_runner_captures_stdout_and_exit_code(tmp_path: Path) -> None:
    setup_logging(log_directory=tmp_path, quiet=True)
    spec = CommandSpec(argv=(sys.executable, "-c", "print('hello-hallfix')"))
    result = SubprocessCommandRunner().run(spec)
    assert result.succeeded
    assert result.exit_code == 0
    assert "hello-hallfix" in result.stdout


def test_subprocess_runner_reports_nonzero_exit_code(tmp_path: Path) -> None:
    setup_logging(log_directory=tmp_path, quiet=True)
    spec = CommandSpec(argv=(sys.executable, "-c", "import sys; sys.exit(3)"))
    result = SubprocessCommandRunner().run(spec)
    assert not result.succeeded
    assert result.exit_code == 3


def test_subprocess_runner_handles_missing_executable(tmp_path: Path) -> None:
    setup_logging(log_directory=tmp_path, quiet=True)
    spec = CommandSpec(argv=("hallfix-definitely-not-a-real-command-xyz",))
    result = SubprocessCommandRunner().run(spec)
    assert result.exit_code == 127
    assert not result.succeeded


def test_subprocess_runner_times_out(tmp_path: Path) -> None:
    setup_logging(log_directory=tmp_path, quiet=True)
    spec = CommandSpec(
        argv=(sys.executable, "-c", "import time; time.sleep(5)"),
        timeout_seconds=0.2,
    )
    result = SubprocessCommandRunner().run(spec)
    assert result.timed_out
    assert not result.succeeded


def test_subprocess_runner_redacts_argv_positions(tmp_path: Path) -> None:
    setup_logging(log_directory=tmp_path, quiet=True)
    spec = CommandSpec(
        argv=(sys.executable, "-c", "print('ok')", "--token=secret"),
        redact_argv_indices=(3,),
    )
    result = SubprocessCommandRunner().run(spec)
    assert "secret" not in result.argv[3]
    assert "REDACTED" in result.argv[3]


def test_dry_run_runner_never_executes(tmp_path: Path) -> None:
    setup_logging(log_directory=tmp_path, quiet=True)
    marker = tmp_path / "should-not-exist"
    spec = CommandSpec(
        argv=(sys.executable, "-c", f"open({str(marker)!r}, 'w').close()"),
    )
    result = DryRunCommandRunner().run(spec)
    assert result.dry_run
    assert result.exit_code == 0
    assert not marker.exists()


def test_build_command_runner_selects_dry_run() -> None:
    assert isinstance(build_command_runner(dry_run=True), DryRunCommandRunner)
    assert isinstance(build_command_runner(dry_run=False), SubprocessCommandRunner)
