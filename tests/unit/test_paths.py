from __future__ import annotations

from pathlib import Path

import pytest

from hallfix.utils.paths import config_file, config_home, log_dir, state_home


def test_paths_respect_xdg_env_vars(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "st"))

    assert config_home() == tmp_path / "cfg" / "hallfix"
    assert state_home() == tmp_path / "st" / "hallfix"
    assert log_dir() == tmp_path / "st" / "hallfix" / "logs"
    assert config_file() == tmp_path / "cfg" / "hallfix" / "config.toml"


def test_paths_fall_back_to_home_when_no_xdg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    fake_home = Path("/fake/home")

    assert config_home(home=fake_home) == fake_home / ".config" / "hallfix"
    assert state_home(home=fake_home) == fake_home / ".local" / "state" / "hallfix"
