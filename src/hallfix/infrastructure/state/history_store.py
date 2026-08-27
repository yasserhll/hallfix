"""HistoryStore (spec §9): append-only operation log.

JSON Lines rather than one big JSON array on purpose: appending a single
line via an ``O_APPEND``-opened file descriptor is atomic on POSIX for
writes under ``PIPE_BUF`` (4096 bytes on Linux) — no concurrent writer can
interleave a partial line, and there's no "rewrite the whole file" step
that could lose *all* history if interrupted mid-write, unlike a single
big JSON document would need. A truncated/corrupt trailing line (a crash
mid-write) is skipped on read, not treated as fatal.

Redacts free-text fields (command, action messages) through the same
redaction used for logs (spec §9: "Never store passwords, API tokens,
private keys, credentials or secrets").
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hallfix.domain.models.history import ActionOutcome, OperationRecord
from hallfix.infrastructure.logging.logger import get_logger
from hallfix.infrastructure.logging.redaction import redact_text
from hallfix.utils.paths import state_home


def _default_path() -> Path:
    return state_home() / "history.jsonl"


def _serialize(record: OperationRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "timestamp": record.timestamp.isoformat(),
        "command": redact_text(record.command),
        "plan_id": record.plan_id,
        "plan_description": redact_text(record.plan_description),
        "dry_run": record.dry_run,
        "plan_reversible": record.plan_reversible,
        "action_outcomes": [
            {
                "action_type": o.action_type,
                "succeeded": o.succeeded,
                "already_satisfied": o.already_satisfied,
                "message": redact_text(o.message),
                "reversible": o.reversible,
                "rollback_strategy": o.rollback_strategy,
                "tool_id": o.tool_id,
                "package": redact_text(o.package) if o.package else o.package,
                "strategy": o.strategy,
                "risk_level": o.risk_level,
            }
            for o in record.action_outcomes
        ],
    }


def _deserialize(data: dict[str, Any]) -> OperationRecord:
    outcomes = tuple(
        ActionOutcome(
            action_type=o["action_type"],
            succeeded=bool(o["succeeded"]),
            already_satisfied=bool(o["already_satisfied"]),
            message=o["message"],
            # `.get(...)` with a default, not direct indexing: history
            # lines written before this field existed must still parse —
            # they correctly come back as not rollback-eligible, since
            # Hallfix genuinely doesn't have the detail to safely roll
            # them back either way.
            reversible=bool(o.get("reversible", False)),
            rollback_strategy=o.get("rollback_strategy"),
            tool_id=o.get("tool_id"),
            package=o.get("package"),
            strategy=o.get("strategy"),
            risk_level=o.get("risk_level"),
        )
        for o in data.get("action_outcomes", [])
    )
    return OperationRecord(
        id=data["id"],
        timestamp=datetime.fromisoformat(data["timestamp"]),
        command=data["command"],
        plan_id=data["plan_id"],
        plan_description=data["plan_description"],
        dry_run=bool(data["dry_run"]),
        plan_reversible=bool(data["plan_reversible"]),
        action_outcomes=outcomes,
    )


class HistoryStore:
    def __init__(self, *, path: Path | None = None) -> None:
        self._path = path or _default_path()

    def _next_id(self) -> str:
        return f"HF-{len(self.list_all()) + 1:03d}"

    def append(
        self,
        *,
        command: str,
        plan_id: str,
        plan_description: str,
        dry_run: bool,
        plan_reversible: bool,
        action_outcomes: tuple[ActionOutcome, ...] = (),
        now: datetime | None = None,
    ) -> OperationRecord:
        record = OperationRecord(
            id=self._next_id(),
            timestamp=now or datetime.now(UTC),
            command=command,
            plan_id=plan_id,
            plan_description=plan_description,
            dry_run=dry_run,
            plan_reversible=plan_reversible,
            action_outcomes=action_outcomes,
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(_serialize(record), sort_keys=True) + "\n"
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(line)
        return record

    def list_all(self) -> tuple[OperationRecord, ...]:
        if not self._path.is_file():
            return ()
        records: list[OperationRecord] = []
        for line_number, line in enumerate(
            self._path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                records.append(_deserialize(json.loads(line)))
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                get_logger().warning(
                    "skipping unreadable history line",
                    extra={"path": str(self._path), "line": line_number, "error": str(exc)},
                )
        return tuple(records)

    def get(self, operation_id: str) -> OperationRecord | None:
        for record in self.list_all():
            if record.id == operation_id:
                return record
        return None
