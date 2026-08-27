"""Loads and validates user configuration from TOML.

Uses the stdlib ``tomllib`` reader only (Python 3.11+) — no extra
dependency needed for Phase 1 since Hallfix never writes back a config file
implicitly; a missing file simply means "use defaults".
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from hallfix.config.schema import DiskThresholds, HallfixConfig
from hallfix.domain.exceptions import ConfigurationError
from hallfix.utils.paths import config_file


class ConfigurationManager:
    """Reads ``HallfixConfig`` from disk, falling back to defaults."""

    def __init__(self, *, path: Path | None = None) -> None:
        self._path = path or config_file()

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> HallfixConfig:
        if not self._path.is_file():
            return HallfixConfig()

        try:
            raw = tomllib.loads(self._path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            msg = f"invalid TOML in {self._path}: {exc}"
            raise ConfigurationError(msg) from exc
        except OSError as exc:
            msg = f"could not read {self._path}: {exc}"
            raise ConfigurationError(msg) from exc

        return self._build_config(raw)

    def _build_config(self, raw: dict[str, Any]) -> HallfixConfig:
        thresholds_raw = raw.get("disk_thresholds", {})
        if not isinstance(thresholds_raw, dict):
            msg = "'disk_thresholds' must be a table"
            raise ConfigurationError(msg)

        try:
            threshold_fields = DiskThresholds.__dataclass_fields__
            thresholds = DiskThresholds(
                **{k: v for k, v in thresholds_raw.items() if k in threshold_fields}
            )
            known_fields = HallfixConfig.__dataclass_fields__.keys() - {"disk_thresholds"}
            kwargs = {k: v for k, v in raw.items() if k in known_fields}
            return HallfixConfig(disk_thresholds=thresholds, **kwargs)
        except (TypeError, ValueError) as exc:
            msg = f"invalid configuration in {self._path}: {exc}"
            raise ConfigurationError(msg) from exc
