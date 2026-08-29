"""Profile recommendation (spec §41): evidence-based, read-only.

Reuses ``compute_profile_diff`` per profile rather than inventing a second
installed/missing algorithm — the same guarantee spec §36 makes for
``profile diff`` ("This command must NOT modify the system") applies here
too (spec §41: "Never install automatically from recommendations.").
"""

from __future__ import annotations

from dataclasses import dataclass

from hallfix.domain.models.profile import ProfileDefinition
from hallfix.domain.models.tool import ToolVerificationResult
from hallfix.domain.registries.profile_diff import ProfileDiff, compute_profile_diff
from hallfix.domain.registries.tool_registry import ToolRegistry


@dataclass(frozen=True, slots=True)
class ProfileMatch:
    profile_id: str
    profile_name: str
    diff: ProfileDiff

    @property
    def match_ratio(self) -> float:
        total = len(self.diff.entries)
        if total == 0:
            return 0.0
        return len(self.diff.installed) / total


@dataclass(frozen=True, slots=True)
class RecommendationResult:
    matches: tuple[ProfileMatch, ...]  # one per profile, in registry order

    @property
    def best_match(self) -> ProfileMatch | None:
        """The profile with the highest installed ratio, among profiles with
        at least one installed tool — a profile with zero matching evidence
        is never "recommended", it's just unrelated to what's on the machine.
        """
        qualifying = tuple(m for m in self.matches if m.diff.installed)
        if not qualifying:
            return None
        return max(qualifying, key=lambda m: m.match_ratio)


def compute_recommendation(
    profiles: tuple[ProfileDefinition, ...],
    tool_registry: ToolRegistry,
    verifications: dict[str, ToolVerificationResult],
) -> RecommendationResult:
    matches = tuple(
        ProfileMatch(
            profile_id=profile.id,
            profile_name=profile.name,
            diff=compute_profile_diff(profile, tool_registry, verifications),
        )
        for profile in profiles
    )
    return RecommendationResult(matches=matches)
