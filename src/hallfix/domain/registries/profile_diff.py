"""Profile diff (spec §36): what's installed, missing, or version-mismatched.

Pure — takes an already-computed ``{tool_id: ToolVerificationResult}``
mapping (verification is I/O; the CLI/application layer runs it per tool
and hands the results in here). Never modifies the system, per spec §36:
"This command must NOT modify the system." There is no "configuration"
section (e.g. spec's "Docker installed but service disabled" example) —
that needs service-status detection, which doesn't exist yet
(`infrastructure/services/` is still an empty stub).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from hallfix.domain.models.profile import ProfileDefinition
from hallfix.domain.models.tool import ToolVerificationResult
from hallfix.domain.registries.tool_registry import ToolRegistry
from hallfix.utils.version import meets_minimum


class ToolDiffStatus(StrEnum):
    INSTALLED = "INSTALLED"
    MISSING = "MISSING"
    VERSION_MISMATCH = "VERSION_MISMATCH"
    UNKNOWN_TOOL = "UNKNOWN_TOOL"


@dataclass(frozen=True, slots=True)
class ToolDiffEntry:
    tool_id: str
    tool_name: str
    status: ToolDiffStatus
    installed_version: str | None = None
    recommended_version: str | None = None


@dataclass(frozen=True, slots=True)
class ProfileDiff:
    profile_id: str
    entries: tuple[ToolDiffEntry, ...]

    @property
    def installed(self) -> tuple[ToolDiffEntry, ...]:
        return tuple(e for e in self.entries if e.status == ToolDiffStatus.INSTALLED)

    @property
    def missing(self) -> tuple[ToolDiffEntry, ...]:
        return tuple(e for e in self.entries if e.status == ToolDiffStatus.MISSING)

    @property
    def version_mismatches(self) -> tuple[ToolDiffEntry, ...]:
        return tuple(e for e in self.entries if e.status == ToolDiffStatus.VERSION_MISMATCH)

    @property
    def unknown_tools(self) -> tuple[ToolDiffEntry, ...]:
        return tuple(e for e in self.entries if e.status == ToolDiffStatus.UNKNOWN_TOOL)


def compute_profile_diff(
    profile: ProfileDefinition,
    tool_registry: ToolRegistry,
    verifications: dict[str, ToolVerificationResult],
) -> ProfileDiff:
    entries: list[ToolDiffEntry] = []
    for tool_id in profile.tools:
        tool = tool_registry.get(tool_id)
        if tool is None:
            entries.append(
                ToolDiffEntry(
                    tool_id=tool_id, tool_name=tool_id, status=ToolDiffStatus.UNKNOWN_TOOL
                )
            )
            continue

        verification = verifications.get(tool_id)
        if verification is None or not verification.executable_found:
            entries.append(
                ToolDiffEntry(tool_id=tool_id, tool_name=tool.name, status=ToolDiffStatus.MISSING)
            )
            continue

        # Only flag a mismatch when the comparison is conclusive (False) —
        # `None` means "couldn't determine" and must not be treated as a
        # mismatch just because `not None` is truthy.
        if (
            tool.recommended_version
            and meets_minimum(verification.installed_version, tool.recommended_version) is False
        ):
            entries.append(
                ToolDiffEntry(
                    tool_id=tool_id,
                    tool_name=tool.name,
                    status=ToolDiffStatus.VERSION_MISMATCH,
                    installed_version=verification.installed_version,
                    recommended_version=tool.recommended_version,
                )
            )
            continue

        entries.append(
            ToolDiffEntry(
                tool_id=tool_id,
                tool_name=tool.name,
                status=ToolDiffStatus.INSTALLED,
                installed_version=verification.installed_version,
            )
        )

    return ProfileDiff(profile_id=profile.id, entries=tuple(entries))
