"""Shared enums used across domain models.

Kept minimal for Phase 1: only the enums that the foundation layer
(config, logging, CommandRunner, CLI skeleton) already needs to reference.
Planning-specific enums (ActionType, etc.) are introduced in Phase 5.
"""

from __future__ import annotations

from enum import StrEnum


class Severity(StrEnum):
    """Severity of a diagnostic finding."""

    INFO = "INFO"
    OK = "OK"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class RiskLevel(StrEnum):
    """Risk level of a planned action or fix."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SupportLevel(StrEnum):
    """How confidently Hallfix supports a given distribution/tool combination."""

    SUPPORTED = "SUPPORTED"
    EXPERIMENTAL = "EXPERIMENTAL"
    DETECTED_ONLY = "DETECTED_ONLY"
    UNSUPPORTED = "UNSUPPORTED"
