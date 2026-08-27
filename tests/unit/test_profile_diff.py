from __future__ import annotations

from hallfix.domain.models.profile import ProfileDefinition
from hallfix.domain.models.tool import ToolVerificationResult
from hallfix.domain.registries.profile_diff import ToolDiffStatus, compute_profile_diff
from hallfix.domain.registries.tool_registry import ToolRegistry

_GIT_RAW = {
    "id": "git",
    "name": "Git",
    "description": "VCS",
    "category": "essentials",
    "installation_strategies": ["APT"],
    "package_mappings": {"APT": "git"},
    "verification": {"executable": "git", "version_command": ["git", "--version"]},
    "recommended_version": "2.40",
}

_CURL_RAW = {
    "id": "curl",
    "name": "curl",
    "description": "HTTP client",
    "category": "essentials",
    "installation_strategies": ["APT"],
    "package_mappings": {"APT": "curl"},
    "verification": {"executable": "curl", "version_command": ["curl", "--version"]},
}

_HTOP_RAW = {
    "id": "htop",
    "name": "htop",
    "description": "Process viewer",
    "category": "utilities",
    "installation_strategies": ["APT"],
    "package_mappings": {"APT": "htop"},
    "verification": {"executable": "htop", "version_command": ["htop", "--version"]},
}

_PROFILE = ProfileDefinition(
    id="developer",
    name="Developer",
    description="d",
    # "htop" is registered but deliberately given no verification result in
    # tests below (truly missing from the system); "unknown-tool" isn't
    # registered at all (a bad profile reference) — these are different
    # failure modes and must be reported differently.
    tools=("git", "curl", "htop", "unknown-tool"),
)

_REGISTRY = ToolRegistry([_GIT_RAW, _CURL_RAW, _HTOP_RAW])


def _verified(version: str) -> ToolVerificationResult:
    return ToolVerificationResult(
        tool_id="x",
        executable_found=True,
        installed_version=version,
        meets_minimum_version=None,
        meets_recommended_version=None,
    )


def _not_found() -> ToolVerificationResult:
    return ToolVerificationResult(
        tool_id="x",
        executable_found=False,
        installed_version=None,
        meets_minimum_version=None,
        meets_recommended_version=None,
    )


def test_installed_tool_reported() -> None:
    diff = compute_profile_diff(
        _PROFILE, _REGISTRY, {"git": _verified("2.45.0"), "curl": _verified("8.0.0")}
    )
    assert {e.tool_id for e in diff.installed} == {"git", "curl"}


def test_missing_tool_reported() -> None:
    diff = compute_profile_diff(_PROFILE, _REGISTRY, {"git": _verified("2.45.0")})
    missing_ids = {e.tool_id for e in diff.missing}
    assert "curl" in missing_ids
    assert "htop" in missing_ids


def test_not_found_verification_reported_as_missing() -> None:
    diff = compute_profile_diff(
        _PROFILE, _REGISTRY, {"git": _not_found(), "curl": _verified("8.0.0")}
    )
    assert any(e.tool_id == "git" for e in diff.missing)


def test_version_below_recommended_reported_as_mismatch() -> None:
    diff = compute_profile_diff(
        _PROFILE, _REGISTRY, {"git": _verified("2.10.0"), "curl": _verified("8.0.0")}
    )
    mismatch_ids = {e.tool_id for e in diff.version_mismatches}
    assert "git" in mismatch_ids
    entry = next(e for e in diff.version_mismatches if e.tool_id == "git")
    assert entry.installed_version == "2.10.0"
    assert entry.recommended_version == "2.40"


def test_unparseable_version_not_treated_as_mismatch() -> None:
    diff = compute_profile_diff(
        _PROFILE, _REGISTRY, {"git": _verified("unknown"), "curl": _verified("8.0.0")}
    )
    assert not any(e.tool_id == "git" for e in diff.version_mismatches)
    assert any(e.tool_id == "git" for e in diff.installed)


def test_unknown_tool_reported_separately() -> None:
    diff = compute_profile_diff(_PROFILE, _REGISTRY, {})
    unknown_ids = {e.tool_id for e in diff.unknown_tools}
    assert unknown_ids == {"unknown-tool"}


def test_status_enum_values_are_mutually_exclusive_per_entry() -> None:
    diff = compute_profile_diff(
        _PROFILE, _REGISTRY, {"git": _verified("2.45.0"), "curl": _not_found()}
    )
    statuses = {e.tool_id: e.status for e in diff.entries}
    assert statuses["git"] == ToolDiffStatus.INSTALLED
    assert statuses["curl"] == ToolDiffStatus.MISSING
    assert statuses["htop"] == ToolDiffStatus.MISSING
    assert statuses["unknown-tool"] == ToolDiffStatus.UNKNOWN_TOOL
