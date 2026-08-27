"""dpkg package-state health check.

APT-only: dnf/pacman/zypper have no equivalent universal "list
half-installed packages" command Hallfix has verified. ``dpkg --audit``
prints details of any package left in a broken/half-configured state
(e.g. an interrupted install) and prints nothing when everything is
consistent — read-only, never modifies anything.
"""

from __future__ import annotations

from hallfix.domain.models.command import CommandSpec
from hallfix.infrastructure.commands.runner import CommandRunner


def check_dpkg_broken_state(command_runner: CommandRunner) -> bool:
    """True if dpkg reports any package in a broken/half-installed state."""
    result = command_runner.run(CommandSpec(argv=("dpkg", "--audit"), timeout_seconds=15.0))
    if not result.succeeded:
        return False  # can't determine one way or the other; don't claim broken
    return bool(result.stdout.strip())
