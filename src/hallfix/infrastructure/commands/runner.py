"""CommandRunner: the single path through which Hallfix executes external commands.

Rules enforced here (spec §47):
  - never ``shell=True``;
  - argv is always a list, never a concatenated string;
  - dry-run is a first-class mode, not a bolt-on;
  - every invocation is logged with sensitive argv positions redacted.

``requires_root`` is recorded on the result but this runner does *not*
decide privilege-escalation strategy (e.g. whether to prepend ``sudo``) —
that belongs to the Executor/privilege-management layer in a later phase,
so CommandRunner stays a single-responsibility subprocess wrapper.
"""

from __future__ import annotations

import subprocess
import time
from typing import Protocol

from hallfix.domain.models.command import CommandResult, CommandSpec
from hallfix.infrastructure.logging.logger import get_logger
from hallfix.infrastructure.logging.redaction import REDACTED

_TIMEOUT_EXIT_CODE = 124


class CommandRunner(Protocol):
    """Structural interface every command runner (real or fake) must satisfy."""

    def run(self, spec: CommandSpec) -> CommandResult: ...


def _redacted_argv(argv: tuple[str, ...], indices: tuple[int, ...]) -> tuple[str, ...]:
    if not indices:
        return argv
    redact_set = set(indices)
    return tuple(REDACTED if i in redact_set else arg for i, arg in enumerate(argv))


def _decode(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


class SubprocessCommandRunner:
    """Real ``CommandRunner`` backed by :mod:`subprocess`."""

    def run(self, spec: CommandSpec) -> CommandResult:
        logger = get_logger()
        safe_argv = _redacted_argv(spec.argv, spec.redact_argv_indices)

        started = time.monotonic()
        try:
            completed = subprocess.run(  # noqa: S603 - argv is always a list, never shell
                list(spec.argv),
                cwd=spec.cwd,
                env=spec.env if spec.env else None,
                capture_output=True,
                text=True,
                timeout=spec.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.monotonic() - started
            logger.warning(
                "command timed out",
                extra={"argv": safe_argv, "timeout_seconds": spec.timeout_seconds},
            )
            return CommandResult(
                argv=safe_argv,
                exit_code=_TIMEOUT_EXIT_CODE,
                stdout=_decode(exc.stdout),
                stderr=_decode(exc.stderr),
                duration_seconds=duration,
                timed_out=True,
            )
        except FileNotFoundError as exc:
            duration = time.monotonic() - started
            # DEBUG, not ERROR: a missing executable is a completely normal
            # outcome for an existence probe (e.g. ToolVerifier checking an
            # optional tool) — the returned exit_code=127 already tells the
            # caller what happened; it's the caller's call whether that's
            # alarming, not the runner's.
            logger.debug("command not found", extra={"argv": safe_argv, "error": str(exc)})
            return CommandResult(
                argv=safe_argv,
                exit_code=127,
                stdout="",
                stderr=str(exc),
                duration_seconds=duration,
            )

        duration = time.monotonic() - started
        result = CommandResult(
            argv=safe_argv,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_seconds=duration,
        )
        logger.debug(
            "command completed",
            extra={
                "argv": safe_argv,
                "exit_code": result.exit_code,
                "duration_seconds": duration,
            },
        )
        return result


class DryRunCommandRunner:
    """``CommandRunner`` that never touches the system — used when ``--dry-run`` is set."""

    def run(self, spec: CommandSpec) -> CommandResult:
        safe_argv = _redacted_argv(spec.argv, spec.redact_argv_indices)
        get_logger().info("dry-run: command skipped", extra={"argv": safe_argv})
        return CommandResult(
            argv=safe_argv,
            exit_code=0,
            stdout="",
            stderr="",
            duration_seconds=0.0,
            dry_run=True,
        )


def build_command_runner(*, dry_run: bool) -> CommandRunner:
    """Factory selecting the right runner — the only place this decision is made."""
    if dry_run:
        return DryRunCommandRunner()
    return SubprocessCommandRunner()
