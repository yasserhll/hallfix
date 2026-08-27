from __future__ import annotations

import dataclasses
import json
from datetime import UTC, datetime

from hallfix.cli.report_rendering import render_html, render_txt
from hallfix.domain.models.diagnostic import DiagnosticResult
from hallfix.domain.models.enums import HealthState, Severity
from hallfix.domain.models.history import OperationRecord
from hallfix.domain.models.report import ManagedToolSummary, Report
from hallfix.domain.models.system import DistributionFamily, PackageManagerKind
from tests.fixtures.system_context_factory import make_system_context

_SYSTEM = make_system_context(manager_kind=PackageManagerKind.APT, family=DistributionFamily.DEBIAN)
_NOW = datetime(2026, 3, 5, 12, 0, 0, tzinfo=UTC)

_REPORT = Report(
    generated_at=_NOW,
    system=_SYSTEM,
    diagnostics=(
        DiagnosticResult(
            id="system.disk",
            category="system",
            severity=Severity.WARNING,
            title="Storage",
            description="Highest usage: / at 80%",
            recommendation="Disk usage is elevated.",
        ),
    ),
    health=HealthState.DEGRADED,
    managed_tools=(
        ManagedToolSummary(
            tool_id="git",
            installed_by_hallfix=True,
            present_before_hallfix=False,
            executable_found=True,
            installed_version="2.43.0",
        ),
    ),
    recent_operations=(
        OperationRecord(
            id="HF-001",
            timestamp=_NOW,
            command="tool install git",
            plan_id="p1",
            plan_description="Install Git",
            dry_run=False,
            plan_reversible=True,
        ),
    ),
)


def test_render_txt_includes_expected_sections() -> None:
    text = render_txt(_REPORT)
    assert "HALLFIX SYSTEM REPORT" in text
    assert "SYSTEM INFORMATION" in text
    assert "MANAGED TOOLS" in text
    assert "git: installed by Hallfix" in text
    assert "DETECTED ISSUES" in text
    assert "[WARNING] Storage" in text
    assert "RECOMMENDATIONS" in text
    assert "Disk usage is elevated." in text
    assert "RECENT OPERATIONS" in text
    assert "HF-001" in text
    assert "Overall health: DEGRADED" in text


def test_render_txt_omits_recommendations_section_when_empty() -> None:
    empty_report = Report(
        generated_at=_NOW, system=_SYSTEM, diagnostics=(), health=HealthState.HEALTHY
    )
    text = render_txt(empty_report)
    assert "RECOMMENDATIONS" not in text


def test_render_txt_skips_squashfs_filesystems() -> None:
    text = render_txt(_REPORT)
    assert "squashfs" not in text


def test_render_html_is_well_formed_and_escapes_content() -> None:
    html = render_html(_REPORT)
    assert html.startswith("<!doctype html>")
    assert "<title>Hallfix System Report</title>" in html
    assert "health-DEGRADED" in html
    assert "git: installed by Hallfix" in html


def test_render_html_escapes_dangerous_characters() -> None:
    malicious_report = Report(
        generated_at=_NOW,
        system=_SYSTEM,
        diagnostics=(
            DiagnosticResult(
                id="x",
                category="test",
                severity=Severity.WARNING,
                title="X",
                description="<script>alert(1)</script>",
            ),
        ),
        health=HealthState.DEGRADED,
    )
    html = render_html(malicious_report)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_html_report_is_valid_enough_to_have_balanced_tags() -> None:
    html = render_html(_REPORT)
    assert html.count("<table>") == html.count("</table>")
    assert html.count("<ul>") == html.count("</ul>")


def test_report_json_serializable_via_dataclasses_asdict() -> None:
    payload = json.dumps(dataclasses.asdict(_REPORT), default=str)
    parsed = json.loads(payload)
    assert parsed["health"] == "DEGRADED"
    assert parsed["managed_tools"][0]["tool_id"] == "git"
