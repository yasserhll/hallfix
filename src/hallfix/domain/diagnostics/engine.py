"""``DiagnosticEngine``: runs every registered check and aggregates health.

Health aggregation rule (documented, deterministic — spec §40 requires
this of any health summary, numeric or not):
CRITICAL if any result is CRITICAL, else UNHEALTHY if any is ERROR, else
DEGRADED if any is WARNING, else HEALTHY. INFO/OK never lower health.
"""

from __future__ import annotations

from hallfix.domain.diagnostics.context import DiagnosticContext
from hallfix.domain.diagnostics.registry import DiagnosticRegistry
from hallfix.domain.models.diagnostic import DiagnosticResult
from hallfix.domain.models.enums import HealthState, Severity

_STATE_BY_WORST_SEVERITY: dict[Severity, HealthState] = {
    Severity.CRITICAL: HealthState.CRITICAL,
    Severity.ERROR: HealthState.UNHEALTHY,
    Severity.WARNING: HealthState.DEGRADED,
}


def aggregate_health(results: tuple[DiagnosticResult, ...]) -> HealthState:
    for severity, state in _STATE_BY_WORST_SEVERITY.items():
        if any(r.severity == severity for r in results):
            return state
    return HealthState.HEALTHY


class DiagnosticEngine:
    def __init__(self, registry: DiagnosticRegistry | None = None) -> None:
        self._registry = registry or DiagnosticRegistry()

    def run(self, context: DiagnosticContext) -> tuple[DiagnosticResult, ...]:
        results: list[DiagnosticResult] = []
        for check in self._registry.checks():
            results.extend(check(context))
        return tuple(results)
