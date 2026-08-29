"""Snapshot domain model (spec §10): a point-in-time record of Hallfix's
own view of the machine — "This does NOT need to create a complete
filesystem snapshot. It should record relevant Hallfix state." Pure data;
building one from real system/tool reads happens in
``application/snapshot.py``, persisting it happens in
``infrastructure/state/snapshot_store.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SnapshotToolEntry:
    tool_id: str
    installed_version: str | None
    installed_for: tuple[str, ...]  # profile ids that requested this tool


@dataclass(frozen=True, slots=True)
class SnapshotRecord:
    id: str
    created_at: datetime
    hallfix_version: str
    distribution_id: str
    distribution_version: str | None
    architecture: str
    kernel: str
    managed_tools: tuple[SnapshotToolEntry, ...] = field(default_factory=tuple)

    @property
    def profiles(self) -> tuple[str, ...]:
        """Distinct profile ids referenced by any managed tool, in first-seen
        order — derived, never stored redundantly."""
        seen: list[str] = []
        for tool in self.managed_tools:
            for profile_id in tool.installed_for:
                if profile_id not in seen:
                    seen.append(profile_id)
        return tuple(seen)
