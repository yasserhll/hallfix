"""XDG base directory helpers.

Centralized here so config, logging, and (in later phases) StateStore/
HistoryStore all agree on where things live, and so tests can override the
home directory in one place instead of monkeypatching ``Path.home()`` in
every module.
"""

from __future__ import annotations

import os
from pathlib import Path


def config_home(*, home: Path | None = None) -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base) / "hallfix"
    return (home or Path.home()) / ".config" / "hallfix"


def state_home(*, home: Path | None = None) -> Path:
    base = os.environ.get("XDG_STATE_HOME")
    if base:
        return Path(base) / "hallfix"
    return (home or Path.home()) / ".local" / "state" / "hallfix"


def log_dir(*, home: Path | None = None) -> Path:
    return state_home(home=home) / "logs"


def config_file(*, home: Path | None = None) -> Path:
    return config_home(home=home) / "config.toml"
