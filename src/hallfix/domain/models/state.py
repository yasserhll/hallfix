"""StateStore domain models (spec §8).

"Never assume that an installed package was installed by Hallfix" — every
tracked tool records both facts independently: whether Hallfix installed
it, and (for later phases) whether it was already there before Hallfix
ever touched it. Pure data; ``infrastructure/state/store.py`` does the
actual reading/writing.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass(frozen=True, slots=True)
class ToolState:
    present_before_hallfix: bool
    installed_by_hallfix: bool
    installed_for: tuple[str, ...] = ()  # profile ids that requested this tool (Phase 8+)


@dataclass(frozen=True, slots=True)
class HallfixState:
    tools: dict[str, ToolState] = field(default_factory=dict)

    def with_tool(self, tool_id: str, tool_state: ToolState) -> HallfixState:
        updated = dict(self.tools)
        updated[tool_id] = tool_state
        return replace(self, tools=updated)

    def without_tool(self, tool_id: str) -> HallfixState:
        if tool_id not in self.tools:
            return self
        updated = dict(self.tools)
        del updated[tool_id]
        return replace(self, tools=updated)
