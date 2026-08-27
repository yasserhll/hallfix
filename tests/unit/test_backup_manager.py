from __future__ import annotations

import stat
from datetime import UTC, datetime
from pathlib import Path

import pytest

from hallfix.domain.exceptions import BackupError
from hallfix.domain.models.backup import BackupRecord
from hallfix.infrastructure.filesystem.backup import BackupManager

_FIXED_NOW = datetime(2026, 3, 5, 14, 30, 45, tzinfo=UTC)


def test_backup_creates_file_with_spec_naming_convention(tmp_path: Path) -> None:
    original = tmp_path / "example.conf"
    original.write_text("setting=1\n", encoding="utf-8")

    record = BackupManager().backup(original, now=_FIXED_NOW)

    assert record.backup_path == str(tmp_path / "example.conf.hallfix-backup-20260305-143045")
    assert Path(record.backup_path).is_file()


def test_backup_content_matches_original(tmp_path: Path) -> None:
    original = tmp_path / "example.conf"
    original.write_text("setting=1\nother=2\n", encoding="utf-8")

    record = BackupManager().backup(original, now=_FIXED_NOW)

    assert Path(record.backup_path).read_text(encoding="utf-8") == "setting=1\nother=2\n"


def test_backup_preserves_mode(tmp_path: Path) -> None:
    original = tmp_path / "example.conf"
    original.write_text("x", encoding="utf-8")
    original.chmod(0o640)

    record = BackupManager().backup(original, now=_FIXED_NOW)

    backup_mode = stat.S_IMODE(Path(record.backup_path).stat().st_mode)
    assert backup_mode == 0o640


def test_backup_no_temp_file_left_behind(tmp_path: Path) -> None:
    original = tmp_path / "example.conf"
    original.write_text("x", encoding="utf-8")

    BackupManager().backup(original, now=_FIXED_NOW)

    leftovers = list(tmp_path.glob("*.hallfix-tmp"))
    assert leftovers == []


def test_backup_nonexistent_file_raises() -> None:
    with pytest.raises(BackupError):
        BackupManager().backup(Path("/nonexistent/does-not-exist.conf"))


def test_backup_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(BackupError):
        BackupManager().backup(tmp_path)


def test_restore_round_trip_restores_original_content(tmp_path: Path) -> None:
    original = tmp_path / "example.conf"
    original.write_text("original content\n", encoding="utf-8")
    manager = BackupManager()
    record = manager.backup(original, now=_FIXED_NOW)

    original.write_text("modified content\n", encoding="utf-8")
    manager.restore(record)

    assert original.read_text(encoding="utf-8") == "original content\n"


def test_restore_preserves_mode(tmp_path: Path) -> None:
    original = tmp_path / "example.conf"
    original.write_text("x", encoding="utf-8")
    original.chmod(0o600)
    manager = BackupManager()
    record = manager.backup(original, now=_FIXED_NOW)

    original.chmod(0o644)
    manager.restore(record)

    assert stat.S_IMODE(original.stat().st_mode) == 0o600


def test_restore_missing_backup_raises(tmp_path: Path) -> None:
    fake_record = BackupRecord(
        original_path=str(tmp_path / "example.conf"),
        backup_path=str(tmp_path / "example.conf.hallfix-backup-20260101-000000"),
        created_at=_FIXED_NOW.isoformat(),
    )
    with pytest.raises(BackupError):
        BackupManager().restore(fake_record)


def test_restore_no_temp_file_left_behind(tmp_path: Path) -> None:
    original = tmp_path / "example.conf"
    original.write_text("x", encoding="utf-8")
    manager = BackupManager()
    record = manager.backup(original, now=_FIXED_NOW)

    manager.restore(record)

    leftovers = list(tmp_path.glob("*.hallfix-tmp"))
    assert leftovers == []


def test_backup_record_created_at_is_iso_format(tmp_path: Path) -> None:
    original = tmp_path / "example.conf"
    original.write_text("x", encoding="utf-8")

    record = BackupManager().backup(original, now=_FIXED_NOW)

    assert record.created_at == _FIXED_NOW.isoformat()
