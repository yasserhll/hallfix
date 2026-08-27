"""StateStore (spec §8): tracks what Hallfix changed, atomically.

A single JSON snapshot, rewritten in full on every save via temp-file +
``Path.replace`` — atomic on POSIX when the temp file is on the same
filesystem as the target (guaranteed here: both live under the same state
directory). A crash mid-write leaves either the old file or nothing named
``.tmp`` lying around; it never leaves ``state.json`` half-written.

A corrupt/unreadable state file is treated as "no state recorded yet"
rather than crashing Hallfix — losing ownership tracking is recoverable
(everything just looks un-managed again); refusing to start is not
something spec §2's "fail gracefully" tolerates for a file that only
Hallfix itself writes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hallfix.domain.models.state import HallfixState, ToolState
from hallfix.infrastructure.logging.logger import get_logger
from hallfix.utils.paths import state_home


def _default_path() -> Path:
    return state_home() / "state.json"


def _serialize(state: HallfixState) -> dict[str, Any]:
    return {
        "tools": {
            tool_id: {
                "present_before_hallfix": ts.present_before_hallfix,
                "installed_by_hallfix": ts.installed_by_hallfix,
                "installed_for": list(ts.installed_for),
            }
            for tool_id, ts in state.tools.items()
        }
    }


def _deserialize(data: dict[str, Any]) -> HallfixState:
    tools_raw = data.get("tools")
    if not isinstance(tools_raw, dict):
        return HallfixState()

    tools: dict[str, ToolState] = {}
    for tool_id, raw in tools_raw.items():
        if not isinstance(raw, dict):
            continue
        tools[tool_id] = ToolState(
            present_before_hallfix=bool(raw.get("present_before_hallfix", False)),
            installed_by_hallfix=bool(raw.get("installed_by_hallfix", False)),
            installed_for=tuple(raw.get("installed_for", []) or []),
        )
    return HallfixState(tools=tools)


class StateStore:
    def __init__(self, *, path: Path | None = None) -> None:
        self._path = path or _default_path()

    def load(self) -> HallfixState:
        if not self._path.is_file():
            return HallfixState()
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            get_logger().warning(
                "state file unreadable, treating as empty",
                extra={"path": str(self._path), "error": str(exc)},
            )
            return HallfixState()
        if not isinstance(raw, dict):
            return HallfixState()
        return _deserialize(raw)

    def save(self, state: HallfixState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(_serialize(state), indent=2, sort_keys=True)
        tmp_path = self._path.with_name(self._path.name + ".tmp")
        tmp_path.write_text(payload, encoding="utf-8")
        tmp_path.replace(self._path)

    def record_installed(self, tool_id: str, *, profile: str | None = None) -> None:
        state = self.load()
        existing = state.tools.get(tool_id)
        installed_for = existing.installed_for if existing else ()
        if profile and profile not in installed_for:
            installed_for = (*installed_for, profile)
        self.save(
            state.with_tool(
                tool_id,
                ToolState(
                    present_before_hallfix=False,
                    installed_by_hallfix=True,
                    installed_for=installed_for,
                ),
            )
        )

    def record_already_present(self, tool_id: str) -> None:
        """Record a tool Hallfix observed but did not install.

        No-op if the tool is already tracked — this must never overwrite
        a real ``installed_by_hallfix=True`` fact just because a later
        read happens to see it present too.
        """
        state = self.load()
        if tool_id in state.tools:
            return
        self.save(
            state.with_tool(
                tool_id, ToolState(present_before_hallfix=True, installed_by_hallfix=False)
            )
        )

    def record_removed(self, tool_id: str) -> None:
        state = self.load()
        self.save(state.without_tool(tool_id))

    def is_owned_by_hallfix(self, tool_id: str) -> bool:
        tool_state = self.load().tools.get(tool_id)
        return tool_state.installed_by_hallfix if tool_state else False

    def get_tool_state(self, tool_id: str) -> ToolState | None:
        return self.load().tools.get(tool_id)
