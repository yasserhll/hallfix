"""Typed configuration schema.

Deliberately excludes anything that could disable a mandatory safety rule
(spec §58: "Do NOT allow configuration to disable mandatory safety rules").
There is no field here for confirmation bypass beyond the CLI's own
``--yes`` flag, and no field can widen what SafetyPolicy allows.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class DiskThresholds:
    """Disk usage percentage thresholds (spec §17)."""

    warning: float = 70.0
    high: float = 85.0
    critical: float = 95.0

    def __post_init__(self) -> None:
        if not (0.0 <= self.warning < self.high < self.critical <= 100.0):
            msg = (
                "disk thresholds must satisfy "
                "0 <= warning < high < critical <= 100 "
                f"(got warning={self.warning}, high={self.high}, critical={self.critical})"
            )
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class HallfixConfig:
    """User configuration loaded from ``~/.config/hallfix/config.toml``."""

    language: str = "en"
    color: bool = True
    verbose: bool = False
    report_format: str = "txt"
    preferred_editor: str | None = None
    disk_thresholds: DiskThresholds = field(default_factory=DiskThresholds)

    SUPPORTED_LANGUAGES = ("en", "fr")
    SUPPORTED_REPORT_FORMATS = ("txt", "json", "html")

    def __post_init__(self) -> None:
        if self.language not in self.SUPPORTED_LANGUAGES:
            msg = f"unsupported language: {self.language!r}"
            raise ValueError(msg)
        if self.report_format not in self.SUPPORTED_REPORT_FORMATS:
            msg = f"unsupported report format: {self.report_format!r}"
            raise ValueError(msg)
