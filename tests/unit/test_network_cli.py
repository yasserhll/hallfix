"""Unit: exercises ``hallfix network doctor``'s rendering branches that
depend on this host actually being unhealthy — not safe to rely on a real
host for, so tested directly against a synthetic diagnostic result.
"""

from __future__ import annotations

from rich.console import Console

from hallfix.cli.commands.network import _render
from hallfix.domain.models.diagnostic import DiagnosticResult
from hallfix.domain.models.enums import HealthState, Severity


def test_render_lists_recommended_actions_for_failing_results() -> None:
    results = (
        DiagnosticResult(
            id="network.dns_resolution",
            category="network",
            severity=Severity.ERROR,
            title="DNS resolution",
            description="Could not resolve example.com",
            recommendation="Check /etc/resolv.conf.",
        ),
    )
    console = Console(record=True, no_color=True, width=100)
    _render(console, results, HealthState.UNHEALTHY)
    output = console.export_text()
    assert "Recommended actions:" in output
    assert "1. Check /etc/resolv.conf." in output
    assert "Result: UNHEALTHY" in output


def test_render_omits_recommendations_section_when_all_ok() -> None:
    results = (
        DiagnosticResult(
            id="network.dns_resolution",
            category="network",
            severity=Severity.OK,
            title="DNS resolution",
            description="Resolved example.com",
        ),
    )
    console = Console(record=True, no_color=True, width=100)
    _render(console, results, HealthState.HEALTHY)
    output = console.export_text()
    assert "Recommended actions:" not in output
