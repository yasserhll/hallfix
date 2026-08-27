"""Integration test: exercises real detection (real subprocess ``ip`` calls,
a real internet reachability probe) against the actual host, not a fake
root. Kept separate from tests/unit per spec §70 — unit tests never touch
the real system, this one deliberately does.
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from hallfix.cli.app import app

runner = CliRunner()
pytestmark = pytest.mark.integration


def test_system_info_json_runs_against_real_host() -> None:
    result = runner.invoke(app, ["--json", "system", "info"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "distribution" in payload
    assert "capabilities" in payload
    assert payload["distribution"]["id"]


def test_system_info_human_output_runs_against_real_host() -> None:
    result = runner.invoke(app, ["system", "info"])
    assert result.exit_code == 0
    assert result.stdout.strip() != ""
