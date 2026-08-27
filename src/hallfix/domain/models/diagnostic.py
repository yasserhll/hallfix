"""Structured diagnostic result (spec §39).

Every diagnostic returns this — never a printed string. ``id`` is a stable
dotted namespace (``"system.disk"``, ``"network.dns_resolution"``), not a
sequential number, so it stays meaningful as checks are added/removed and
can be safely referenced by ``fix_id`` once a FixRegistry exists
(Phase 10 — ``fix_available``/``fix_id`` are always ``False``/``None`` for
now; nothing in Hallfix can auto-fix anything yet).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hallfix.domain.models.enums import Severity


@dataclass(frozen=True, slots=True)
class DiagnosticResult:
    id: str
    category: str
    severity: Severity
    title: str
    description: str
    evidence: tuple[str, ...] = field(default_factory=tuple)
    recommendation: str | None = None
    fix_available: bool = False
    fix_id: str | None = None
