from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from hallfix.domain.models.snapshot import SnapshotRecord, SnapshotToolEntry
from hallfix.infrastructure.state.snapshot_store import SnapshotStore

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _record(record_id: str = "HF-SNAP-1") -> SnapshotRecord:
    return SnapshotRecord(
        id=record_id,
        created_at=_NOW,
        hallfix_version="0.1.2",
        distribution_id="ubuntu",
        distribution_version="24.04",
        architecture="x86_64",
        kernel="6.0.0",
        managed_tools=(
            SnapshotToolEntry(tool_id="git", installed_version="2.45.0", installed_for=("dev",)),
        ),
    )


def test_save_then_get_round_trips(tmp_path: Path) -> None:
    store = SnapshotStore(directory=tmp_path)
    record = _record()
    store.save(record)

    loaded = store.get(record.id)
    assert loaded == record


def test_save_returns_path_under_directory(tmp_path: Path) -> None:
    store = SnapshotStore(directory=tmp_path)
    path = store.save(_record())
    assert path.parent == tmp_path
    assert path.name == "HF-SNAP-1.json"


def test_list_all_empty_when_directory_missing(tmp_path: Path) -> None:
    store = SnapshotStore(directory=tmp_path / "does-not-exist")
    assert store.list_all() == ()


def test_get_returns_none_for_unknown_id(tmp_path: Path) -> None:
    store = SnapshotStore(directory=tmp_path)
    store.save(_record())
    assert store.get("HF-SNAP-nope") is None


def test_list_all_skips_unreadable_file(tmp_path: Path) -> None:
    store = SnapshotStore(directory=tmp_path)
    store.save(_record())
    (tmp_path / "corrupt.json").write_text("not json", encoding="utf-8")
    records = store.list_all()
    assert len(records) == 1
    assert records[0].id == "HF-SNAP-1"


def test_profiles_property_deduplicates_across_tools() -> None:
    record = SnapshotRecord(
        id="x",
        created_at=_NOW,
        hallfix_version="0.1.2",
        distribution_id="ubuntu",
        distribution_version=None,
        architecture="x86_64",
        kernel="6.0.0",
        managed_tools=(
            SnapshotToolEntry(tool_id="git", installed_version=None, installed_for=("dev", "ops")),
            SnapshotToolEntry(tool_id="curl", installed_version=None, installed_for=("dev",)),
        ),
    )
    assert record.profiles == ("dev", "ops")
