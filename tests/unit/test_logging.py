from __future__ import annotations

import json
from pathlib import Path

from hallfix.infrastructure.logging.logger import setup_logging


def test_log_file_contains_json_lines(tmp_path: Path) -> None:
    logger = setup_logging(log_directory=tmp_path, quiet=True)
    logger.info("system detected", extra={"distro": "ubuntu"})

    log_file = tmp_path / "hallfix.log"
    assert log_file.is_file()
    line = log_file.read_text(encoding="utf-8").strip().splitlines()[0]
    payload = json.loads(line)
    assert payload["message"] == "system detected"
    assert payload["level"] == "INFO"
    assert payload["distro"] == "ubuntu"
    assert "timestamp" in payload


def test_log_file_redacts_secrets_in_message(tmp_path: Path) -> None:
    logger = setup_logging(log_directory=tmp_path, quiet=True)
    logger.warning("failed login password=hunter2")

    content = (tmp_path / "hallfix.log").read_text(encoding="utf-8")
    assert "hunter2" not in content
    assert "REDACTED" in content


def test_log_file_redacts_secrets_in_extra_fields(tmp_path: Path) -> None:
    logger = setup_logging(log_directory=tmp_path, quiet=True)
    logger.info("token issued", extra={"api_key": "sk-live-12345"})

    content = (tmp_path / "hallfix.log").read_text(encoding="utf-8")
    assert "sk-live-12345" not in content
    assert "REDACTED" in content


def test_setup_logging_is_idempotent_no_duplicate_handlers(tmp_path: Path) -> None:
    logger1 = setup_logging(log_directory=tmp_path, quiet=True)
    logger2 = setup_logging(log_directory=tmp_path, quiet=True)
    assert logger1 is logger2
    assert len(logger2.handlers) == 1  # quiet=True -> file handler only
