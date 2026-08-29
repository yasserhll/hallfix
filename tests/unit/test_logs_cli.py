from __future__ import annotations

import json
from pathlib import Path

from hallfix.cli.commands.logs import _read_entries


def test_read_entries_empty_when_file_missing(tmp_path: Path) -> None:
    assert _read_entries(tmp_path / "does-not-exist.log") == []


def test_read_entries_parses_json_lines(tmp_path: Path) -> None:
    log_file = tmp_path / "hallfix.log"
    log_file.write_text(
        json.dumps({"timestamp": "t1", "level": "INFO", "message": "one"})
        + "\n"
        + json.dumps({"timestamp": "t2", "level": "WARNING", "message": "two"})
        + "\n",
        encoding="utf-8",
    )
    entries = _read_entries(log_file)
    assert len(entries) == 2
    assert entries[0]["message"] == "one"
    assert entries[1]["level"] == "WARNING"


def test_read_entries_skips_malformed_lines(tmp_path: Path) -> None:
    log_file = tmp_path / "hallfix.log"
    log_file.write_text(
        "not json at all\n" + json.dumps({"timestamp": "t1", "level": "INFO", "message": "ok"}),
        encoding="utf-8",
    )
    entries = _read_entries(log_file)
    assert len(entries) == 1
    assert entries[0]["message"] == "ok"


def test_read_entries_skips_blank_lines(tmp_path: Path) -> None:
    log_file = tmp_path / "hallfix.log"
    log_file.write_text(
        "\n\n" + json.dumps({"timestamp": "t1", "level": "INFO", "message": "ok"}) + "\n\n",
        encoding="utf-8",
    )
    assert len(_read_entries(log_file)) == 1
