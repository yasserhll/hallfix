"""``DiagnosticContext``: every already-gathered fact a diagnostic check needs.

Assembling this requires real I/O (detection, a package manager lock
check, tool verification, a DNS resolution probe) — that happens in
``application/doctor.py``. Every check function in this package then
receives an already-built context and stays pure, per the domain layer's
zero-I/O rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hallfix.config.schema import DiskThresholds
from hallfix.domain.models.package import LockStatus
from hallfix.domain.models.system import SystemContext
from hallfix.domain.models.tool import ToolVerificationResult


@dataclass(frozen=True, slots=True)
class DiagnosticContext:
    system: SystemContext
    disk_thresholds: DiskThresholds
    package_manager_lock: LockStatus | None = None
    dns_resolution_ok: bool | None = None  # None = not tested (e.g. no raw connectivity)
    package_broken_state: bool | None = None  # None = not checked (non-APT system)
    tool_verifications: dict[str, ToolVerificationResult] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)
