"""Shared test fixtures.

Autouse fixture keeps every test off the real filesystem locations
(~/.config/hallfix, ~/.local/state/hallfix) by redirecting XDG env vars to a
per-test tmp directory, and resets the global ``hallfix`` logger so tests
don't leak handlers into each other.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

FAKE_SYSTEMS_DIR = Path(__file__).parent / "fake_systems"


@pytest.fixture
def fake_systems_dir() -> Path:
    return FAKE_SYSTEMS_DIR


@pytest.fixture(autouse=True)
def _isolated_xdg_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    yield
    logger = logging.getLogger("hallfix")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
