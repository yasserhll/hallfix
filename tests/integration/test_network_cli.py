"""Integration: real detection against this host. ``network info``/``network
doctor`` are both read-only (spec §18: no scan, no remote probe beyond a
local connectivity check) — safe to run for real.
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from hallfix.cli.app import app

runner = CliRunner()
pytestmark = pytest.mark.integration


def test_network_info_runs() -> None:
    result = runner.invoke(app, ["network", "info"])
    assert result.exit_code == 0
    assert "Default gateway:" in result.stdout


def test_network_info_json_is_valid() -> None:
    result = runner.invoke(app, ["--json", "network", "info"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "interfaces" in payload


def test_network_doctor_runs() -> None:
    result = runner.invoke(app, ["network", "doctor"])
    assert result.exit_code in (0, 1)  # 1 iff this host's network is actually unhealthy
    assert "NETWORK DIAGNOSTIC" in result.stdout


def test_network_doctor_json_is_valid() -> None:
    result = runner.invoke(app, ["--json", "network", "doctor"])
    assert result.exit_code in (0, 1)
    payload = json.loads(result.stdout)
    assert "result" in payload
    assert "results" in payload
