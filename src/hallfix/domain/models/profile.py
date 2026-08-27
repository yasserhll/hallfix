"""Profile registry domain model (spec §27).

Data-driven, same pattern as ``ToolDefinition``: a profile is just a named
bundle of tool ids and categories. "Custom" profiles (spec §35) reuse this
exact type — built on the fly from user-supplied tool ids rather than
loaded from YAML — so the planner never needs a second code path.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ProfileDefinition:
    id: str
    name: str
    description: str
    categories: tuple[str, ...] = field(default_factory=tuple)
    tools: tuple[str, ...] = field(default_factory=tuple)
