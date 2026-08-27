from __future__ import annotations

from pathlib import Path

import pytest

from hallfix.config.manager import ConfigurationManager
from hallfix.domain.exceptions import ConfigurationError


def test_missing_file_returns_defaults(tmp_path: Path) -> None:
    config = ConfigurationManager(path=tmp_path / "does-not-exist.toml").load()
    assert config.language == "en"
    assert config.color is True
    assert config.disk_thresholds.warning == 70.0


def test_loads_valid_toml(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
        language = "fr"
        color = false

        [disk_thresholds]
        warning = 60.0
        high = 80.0
        critical = 90.0
        """,
        encoding="utf-8",
    )
    config = ConfigurationManager(path=config_path).load()
    assert config.language == "fr"
    assert config.color is False
    assert config.disk_thresholds.warning == 60.0
    assert config.disk_thresholds.critical == 90.0


def test_invalid_toml_raises_configuration_error(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text("not [ valid toml", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        ConfigurationManager(path=config_path).load()


def test_unknown_language_raises_configuration_error(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text('language = "klingon"\n', encoding="utf-8")
    with pytest.raises(ConfigurationError):
        ConfigurationManager(path=config_path).load()


def test_unknown_keys_are_ignored_not_fatal(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text('future_field = "whatever"\nlanguage = "en"\n', encoding="utf-8")
    config = ConfigurationManager(path=config_path).load()
    assert config.language == "en"
