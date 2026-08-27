"""Structured exception hierarchy for Hallfix.

Every error a user can hit must be catchable at a meaningful boundary and
must carry enough context to produce an actionable message (see spec §79).
Bare ``Exception``/``ValueError`` should never cross a module boundary.
"""

from __future__ import annotations


class HallfixError(Exception):
    """Base class for all Hallfix domain errors."""


class DetectionError(HallfixError):
    """Raised when system/environment/capability detection cannot proceed."""


class CommandExecutionError(HallfixError):
    """Raised when an external command fails in a way the caller must handle."""

    def __init__(self, message: str, *, exit_code: int | None = None) -> None:
        super().__init__(message)
        self.exit_code = exit_code


class ConfigurationError(HallfixError):
    """Raised when user configuration is invalid or cannot be loaded."""


class RegistryError(HallfixError):
    """Raised when tool/profile/fix registry data is invalid (spec §25: validate at startup)."""


class SafetyPolicyViolation(HallfixError):
    """Raised when an action is blocked by SafetyPolicy and execution must stop."""


class BackupError(HallfixError):
    """Raised when a backup or restore operation cannot be completed."""
