"""Integration: real detection, real reads against this host. `report` is
entirely read-only — generating one never modifies the system, so no
restriction on what's exercised here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hallfix.cli.app import app

runner = CliRunner()
pytestmark = pytest.mark.integration


def test_report_txt_default() -> None:
    result = runner.invoke(app, ["report"])
    assert result.exit_code == 0
    assert "HALLFIX SYSTEM REPORT" in result.stdout
    assert "Overall health:" in result.stdout


def test_report_json_via_format_flag() -> None:
    result = runner.invoke(app, ["report", "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "health" in payload
    assert "system" in payload


def test_report_json_via_global_json_flag() -> None:
    result = runner.invoke(app, ["--json", "report"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "health" in payload


def test_report_html() -> None:
    result = runner.invoke(app, ["report", "--format", "html"])
    assert result.exit_code == 0
    assert "<!doctype html>" in result.stdout


def test_report_unknown_format_fails_cleanly() -> None:
    result = runner.invoke(app, ["report", "--format", "pdf"])
    assert result.exit_code == 1


def test_report_writes_to_output_file(tmp_path: Path) -> None:
    output_path = tmp_path / "report.html"
    result = runner.invoke(app, ["report", "--format", "html", "--output", str(output_path)])
    assert result.exit_code == 0
    assert output_path.is_file()
    assert "<!doctype html>" in output_path.read_text(encoding="utf-8")
    assert str(output_path) in result.stdout
