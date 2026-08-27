from __future__ import annotations

from datetime import UTC, datetime

from hallfix.domain.models.diagnostic import DiagnosticResult
from hallfix.domain.models.enums import HealthState, Severity
from hallfix.domain.models.report import Report
from hallfix.domain.models.system import DistributionFamily, PackageManagerKind
from tests.fixtures.system_context_factory import make_system_context

_SYSTEM = make_system_context(manager_kind=PackageManagerKind.APT, family=DistributionFamily.DEBIAN)
_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _result(
    severity: Severity, *, recommendation: str | None = None, id_: str = "x"
) -> DiagnosticResult:
    return DiagnosticResult(
        id=id_,
        category="test",
        severity=severity,
        title="X",
        description="d",
        recommendation=recommendation,
    )


def test_warnings_filters_by_severity() -> None:
    report = Report(
        generated_at=_NOW,
        system=_SYSTEM,
        diagnostics=(_result(Severity.OK), _result(Severity.WARNING), _result(Severity.ERROR)),
        health=HealthState.DEGRADED,
    )
    assert len(report.warnings) == 1
    assert report.warnings[0].severity == Severity.WARNING


def test_issues_includes_error_and_critical_only() -> None:
    report = Report(
        generated_at=_NOW,
        system=_SYSTEM,
        diagnostics=(
            _result(Severity.OK),
            _result(Severity.WARNING),
            _result(Severity.ERROR),
            _result(Severity.CRITICAL),
        ),
        health=HealthState.CRITICAL,
    )
    assert len(report.issues) == 2
    assert {r.severity for r in report.issues} == {Severity.ERROR, Severity.CRITICAL}


def test_recommendations_deduplicates_and_skips_none() -> None:
    report = Report(
        generated_at=_NOW,
        system=_SYSTEM,
        diagnostics=(
            _result(Severity.WARNING, recommendation="Free disk space.", id_="a"),
            _result(Severity.WARNING, recommendation="Free disk space.", id_="b"),
            _result(Severity.OK, recommendation=None, id_="c"),
            _result(Severity.ERROR, recommendation="Check DNS.", id_="d"),
        ),
        health=HealthState.DEGRADED,
    )
    assert report.recommendations == ("Free disk space.", "Check DNS.")


def test_recommendations_empty_when_none_present() -> None:
    report = Report(
        generated_at=_NOW,
        system=_SYSTEM,
        diagnostics=(_result(Severity.OK),),
        health=HealthState.HEALTHY,
    )
    assert report.recommendations == ()
