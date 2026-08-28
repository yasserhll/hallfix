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


class ConfigurationError(HallfixError):
    """Raised when user configuration is invalid or cannot be loaded."""


class RegistryError(HallfixError):
    """Raised when tool/profile/fix registry data is invalid (spec §25: validate at startup)."""


class BackupError(HallfixError):
    """Raised when a backup or restore operation cannot be completed."""
