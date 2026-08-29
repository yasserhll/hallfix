"""Integration: real registries + real verification against this host.
Read-only end to end, so safe to run without a fake root."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from hallfix.cli.app import app

runner = CliRunner()
pytestmark = pytest.mark.integration


def test_recommend_runs_and_never_modifies() -> None:
    result = runner.invoke(app, ["recommend"])
    assert result.exit_code == 0
    assert "No changes have been made." in result.stdout


def test_recommend_json_is_valid() -> None:
    result = runner.invoke(app, ["--json", "recommend"])
    payload = json.loads(result.stdout)
    assert "best_match" in payload
    assert "matches" in payload
    assert isinstance(payload["matches"], list)
