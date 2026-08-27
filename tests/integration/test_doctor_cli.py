"""Integration: real detection, real reads against this host. `doctor` and
`network *` are entirely read-only, so no restriction on what's exercised.
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from hallfix.cli.app import app

runner = CliRunner()
pytestmark = pytest.mark.integration


def test_doctor_runs_and_reports_health() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code in (0, 1)  # 1 is valid: means UNHEALTHY/CRITICAL was honestly reported
    assert "SYSTEM HEALTH" in result.stdout
    assert "Overall state:" in result.stdout


def test_doctor_json_is_valid_and_structured() -> None:
    result = runner.invoke(app, ["--json", "doctor"])
    payload = json.loads(result.stdout)
    assert payload["health"] in ("HEALTHY", "DEGRADED", "UNHEALTHY", "CRITICAL")
    assert len(payload["results"]) > 10
    assert all("severity" in r for r in payload["results"])


def test_doctor_never_penalizes_absent_optional_tools() -> None:
    result = runner.invoke(app, ["--json", "doctor"])
    payload = json.loads(result.stdout)
    dev_results = [r for r in payload["results"] if r["category"] == "development"]
    for r in dev_results:
        assert r["severity"] in ("OK", "INFO")


def test_network_info_runs() -> None:
    result = runner.invoke(app, ["network", "info"])
    assert result.exit_code == 0
    assert "Default gateway" in result.stdout


def test_network_doctor_runs() -> None:
    result = runner.invoke(app, ["network", "doctor"])
    assert result.exit_code in (0, 1)
    assert "NETWORK DIAGNOSTIC" in result.stdout
    assert "Result:" in result.stdout


def test_network_doctor_json_is_valid() -> None:
    result = runner.invoke(app, ["--json", "network", "doctor"])
    payload = json.loads(result.stdout)
    assert payload["result"] in ("HEALTHY", "DEGRADED", "UNHEALTHY", "CRITICAL")
    assert all(r["category"] == "network" for r in payload["results"])
