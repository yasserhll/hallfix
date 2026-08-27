"""Structured result of an external command execution."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Outcome of running an external command through CommandRunner.

    ``argv`` is stored (redacted) rather than a shell string, matching the
    "no shell command concatenation" rule in spec §47/§78.
    """

    argv: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    dry_run: bool = False
    timed_out: bool = False

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


@dataclass(frozen=True, slots=True)
class CommandSpec:
    """Declarative description of a command to run.

    Kept separate from ``CommandResult`` so CommandRunner has a single typed
    input shape instead of accepting loose keyword soup at every call site.
    """

    argv: tuple[str, ...]
    timeout_seconds: float = 30.0
    env: dict[str, str] | None = None
    cwd: str | None = None
    requires_root: bool = False
    redact_argv_indices: tuple[int, ...] = field(default_factory=tuple)
