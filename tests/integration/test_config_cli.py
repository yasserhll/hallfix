"""Integration: real ConfigurationManager, real (isolated) config path.
Read-only end to end."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from hallfix.cli.app import app

runner = CliRunner()
pytestmark = pytest.mark.integration


def test_config_runs() -> None:
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "Configuration file:" in result.stdout
    assert "language" in result.stdout


def test_config_json_is_valid() -> None:
    result = runner.invoke(app, ["--json", "config"])
    payload = json.loads(result.stdout)
    assert "path" in payload
    assert payload["config"]["language"] == "en"
