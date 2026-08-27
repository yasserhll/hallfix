"""Report (spec §55) — pure data assembled by
``application/report_generator.py``, rendered by ``cli/report_rendering.py``.

Never includes secrets: every source this draws from is already
secret-safe (``HistoryStore`` redacts at write time, ``StateStore`` is
booleans/ids, ``SystemContext`` is detection data) — nothing new to
redact here, but see the report generator's docstring for the full
reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from hallfix.domain.models.diagnostic import DiagnosticResult
from hallfix.domain.models.enums import HealthState, Severity
from hallfix.domain.models.history import OperationRecord
from hallfix.domain.models.system import SystemContext


@dataclass(frozen=True, slots=True)
class ManagedToolSummary:
    tool_id: str
    installed_by_hallfix: bool
    present_before_hallfix: bool
    executable_found: bool
    installed_version: str | None


@dataclass(frozen=True, slots=True)
class Report:
    generated_at: datetime
    system: SystemContext
    diagnostics: tuple[DiagnosticResult, ...]
    health: HealthState
    managed_tools: tuple[ManagedToolSummary, ...] = field(default_factory=tuple)
    recent_operations: tuple[OperationRecord, ...] = field(default_factory=tuple)

    @property
    def warnings(self) -> tuple[DiagnosticResult, ...]:
        return tuple(d for d in self.diagnostics if d.severity == Severity.WARNING)

    @property
    def issues(self) -> tuple[DiagnosticResult, ...]:
        return tuple(
            d for d in self.diagnostics if d.severity in (Severity.ERROR, Severity.CRITICAL)
        )

    @property
    def recommendations(self) -> tuple[str, ...]:
        seen: list[str] = []
        for d in self.diagnostics:
            if d.recommendation and d.recommendation not in seen:
                seen.append(d.recommendation)
        return tuple(seen)
