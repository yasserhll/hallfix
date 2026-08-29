"""Integration: real detection, real (isolated) SnapshotStore. Never
modifies the target system — only writes to Hallfix's own state dir."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from hallfix.cli.app import app

runner = CliRunner()
pytestmark = pytest.mark.integration


def test_snapshot_runs_and_reports_saved_path() -> None:
    result = runner.invoke(app, ["snapshot"])
    assert result.exit_code == 0
    assert "Snapshot HF-SNAP-" in result.stdout
    assert "saved to" in result.stdout


def test_snapshot_json_is_valid() -> None:
    result = runner.invoke(app, ["--json", "snapshot"])
    payload = json.loads(result.stdout)
    assert payload["id"].startswith("HF-SNAP-")
    assert "managed_tools" in payload
