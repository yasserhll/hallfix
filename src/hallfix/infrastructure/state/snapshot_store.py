"""SnapshotStore (spec §10): persists ``SnapshotRecord``s, one JSON file per
snapshot under ``state_home()/snapshots/``. Atomic writes via temp-file +
``Path.replace``, same pattern as ``StateStore`` — a crash mid-write must
never leave a half-written snapshot file under its final name. An
unreadable snapshot file is skipped (with a warning), not fatal, matching
StateStore/HistoryStore's "corrupt data is recoverable, refusing to start
is not" stance.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from hallfix.domain.models.snapshot import SnapshotRecord, SnapshotToolEntry
from hallfix.infrastructure.logging.logger import get_logger
from hallfix.utils.paths import state_home


def _default_directory() -> Path:
    return state_home() / "snapshots"


def _serialize(record: SnapshotRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "created_at": record.created_at.isoformat(),
        "hallfix_version": record.hallfix_version,
        "distribution_id": record.distribution_id,
        "distribution_version": record.distribution_version,
        "architecture": record.architecture,
        "kernel": record.kernel,
        "managed_tools": [
            {
                "tool_id": t.tool_id,
                "installed_version": t.installed_version,
                "installed_for": list(t.installed_for),
            }
            for t in record.managed_tools
        ],
    }


def _deserialize(data: dict[str, Any]) -> SnapshotRecord:
    tools = tuple(
        SnapshotToolEntry(
            tool_id=t["tool_id"],
            installed_version=t.get("installed_version"),
            installed_for=tuple(t.get("installed_for", []) or []),
        )
        for t in data.get("managed_tools", [])
    )
    return SnapshotRecord(
        id=data["id"],
        created_at=datetime.fromisoformat(data["created_at"]),
        hallfix_version=data["hallfix_version"],
        distribution_id=data["distribution_id"],
        distribution_version=data.get("distribution_version"),
        architecture=data["architecture"],
        kernel=data["kernel"],
        managed_tools=tools,
    )


class SnapshotStore:
    def __init__(self, *, directory: Path | None = None) -> None:
        self._directory = directory or _default_directory()

    def save(self, record: SnapshotRecord) -> Path:
        self._directory.mkdir(parents=True, exist_ok=True)
        path = self._directory / f"{record.id}.json"
        payload = json.dumps(_serialize(record), indent=2, sort_keys=True)
        tmp_path = path.with_name(path.name + ".tmp")
        tmp_path.write_text(payload, encoding="utf-8")
        tmp_path.replace(path)
        return path

    def list_all(self) -> tuple[SnapshotRecord, ...]:
        if not self._directory.is_dir():
            return ()
        records: list[SnapshotRecord] = []
        for path in sorted(self._directory.glob("*.json")):
            try:
                records.append(_deserialize(json.loads(path.read_text(encoding="utf-8"))))
            except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
                get_logger().warning(
                    "skipping unreadable snapshot file",
                    extra={"path": str(path), "error": str(exc)},
                )
        return tuple(records)

    def get(self, snapshot_id: str) -> SnapshotRecord | None:
        for record in self.list_all():
            if record.id == snapshot_id:
                return record
        return None
