from __future__ import annotations

from hallfix.domain.diagnostics.engine import DiagnosticEngine, aggregate_health
from hallfix.domain.diagnostics.registry import DiagnosticRegistry
from hallfix.domain.models.diagnostic import DiagnosticResult
from hallfix.domain.models.enums import HealthState, Severity
from tests.fixtures.diagnostic_context_factory import make_diagnostic_context


def _result(severity: Severity) -> DiagnosticResult:
    return DiagnosticResult(
        id="test.x", category="test", severity=severity, title="X", description="d"
    )


def test_aggregate_health_all_ok_is_healthy() -> None:
    results = (_result(Severity.OK), _result(Severity.INFO))
    assert aggregate_health(results) == HealthState.HEALTHY


def test_aggregate_health_warning_is_degraded() -> None:
    results = (_result(Severity.OK), _result(Severity.WARNING))
    assert aggregate_health(results) == HealthState.DEGRADED


def test_aggregate_health_error_is_unhealthy() -> None:
    results = (_result(Severity.WARNING), _result(Severity.ERROR))
    assert aggregate_health(results) == HealthState.UNHEALTHY


def test_aggregate_health_critical_wins_over_everything() -> None:
    results = (_result(Severity.CRITICAL), _result(Severity.ERROR), _result(Severity.WARNING))
    assert aggregate_health(results) == HealthState.CRITICAL


def test_aggregate_health_empty_is_healthy() -> None:
    assert aggregate_health(()) == HealthState.HEALTHY


def test_engine_runs_every_registered_check() -> None:
    calls = []

    def check_a(ctx: object) -> tuple[DiagnosticResult, ...]:
        calls.append("a")
        return (_result(Severity.OK),)

    def check_b(ctx: object) -> tuple[DiagnosticResult, ...]:
        calls.append("b")
        return (_result(Severity.WARNING), _result(Severity.OK))

    engine = DiagnosticEngine(DiagnosticRegistry((check_a, check_b)))  # type: ignore[arg-type]
    results = engine.run(make_diagnostic_context())

    assert calls == ["a", "b"]
    assert len(results) == 3


def test_engine_uses_default_registry_when_none_given() -> None:
    engine = DiagnosticEngine()
    results = engine.run(make_diagnostic_context())
    assert len(results) > 0
