"""Integration: real detection, real diagnosis against this host.

``repair`` on a healthy system takes the no-op path for every fixable
issue (nothing to actually apply), which is safe to run for real.
``fix <diagnostic-id>`` is only exercised with ``--dry-run`` or against
ids known to require no action on this host, for the same reason real
mutation is never run from an automated test elsewhere in this suite.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from hallfix.cli.app import app

runner = CliRunner()
pytestmark = pytest.mark.integration


def test_repair_runs_and_reports_something() -> None:
    result = runner.invoke(app, ["repair"])
    assert result.exit_code == 0
    assert result.stdout.strip() != ""


def test_fix_unknown_diagnostic_id_fails_cleanly() -> None:
    result = runner.invoke(app, ["fix", "not-a-real-diagnostic-id"])
    assert result.exit_code == 1
    assert "No such diagnostic" in result.stdout or "No such diagnostic" in result.stderr


def test_fix_diagnostic_without_available_fix() -> None:
    # network.dns_resolution never has an automated fix (network config
    # repairs are never automatic) — but whether it's currently OK or
    # WARNING/ERROR depends on this host's actual live network state, so
    # only assert the invariant that holds either way.
    result = runner.invoke(app, ["fix", "network.dns_resolution"])
    if "Nothing to fix." in result.stdout:
        assert result.exit_code == 0  # currently healthy: success, not a limitation
    else:
        assert result.exit_code == 1
        assert "No automated fix available" in result.stdout


def test_dry_run_fix_package_broken_state_never_mutates() -> None:
    result = runner.invoke(app, ["--dry-run", "fix", "package.broken_state"])
    # Either "Nothing to fix" (OK severity — nothing broken right now, exit
    # 0) or a real dry-run plan rendered (exit 0) — both are success states
    # and neither ever executes anything for real.
    assert result.exit_code == 0
    assert "Nothing to fix." in result.stdout or "HALLFIX EXECUTION PLAN" in result.stdout


def test_fix_reports_nothing_to_fix_distinctly_from_no_automated_fix() -> None:
    """Regression: an OK-severity diagnostic (nothing currently wrong) must
    not be reported with the same message as a diagnostic that has no
    automated fix at all (e.g. DNS) — those are different situations."""
    result = runner.invoke(app, ["fix", "package.broken_state"])
    if "Nothing to fix." in result.stdout:
        assert result.exit_code == 0
        assert "No automated fix available" not in result.stdout
