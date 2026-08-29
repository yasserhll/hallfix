from __future__ import annotations

from hallfix.domain.models.profile import ProfileDefinition
from hallfix.domain.models.tool import ToolVerificationResult
from hallfix.domain.registries.recommendation import compute_recommendation
from hallfix.domain.registries.tool_registry import ToolRegistry

_GIT_RAW = {
    "id": "git",
    "name": "Git",
    "description": "VCS",
    "category": "essentials",
    "installation_strategies": ["APT"],
    "package_mappings": {"APT": "git"},
    "verification": {"executable": "git", "version_command": ["git", "--version"]},
}
_DOCKER_RAW = {
    "id": "docker",
    "name": "Docker",
    "description": "Containers",
    "category": "containers",
    "installation_strategies": ["APT"],
    "package_mappings": {"APT": "docker.io"},
    "verification": {"executable": "docker", "version_command": ["docker", "--version"]},
}
_NODE_RAW = {
    "id": "nodejs",
    "name": "Node.js",
    "description": "JS runtime",
    "category": "languages",
    "installation_strategies": ["APT"],
    "package_mappings": {"APT": "nodejs"},
    "verification": {"executable": "node", "version_command": ["node", "--version"]},
}

_REGISTRY = ToolRegistry([_GIT_RAW, _DOCKER_RAW, _NODE_RAW])

_DEVELOPER = ProfileDefinition(
    id="developer", name="Developer", description="d", tools=("git", "docker", "nodejs")
)
_DEVOPS = ProfileDefinition(id="devops", name="DevOps", description="o", tools=("git", "docker"))


def _found() -> ToolVerificationResult:
    return ToolVerificationResult(
        tool_id="x",
        executable_found=True,
        installed_version="1.0",
        meets_minimum_version=None,
        meets_recommended_version=None,
    )


def test_best_match_picked_by_highest_installed_ratio() -> None:
    # git+docker installed: devops is 2/2 = 100%, developer is 2/3 = 66%.
    verifications = {"git": _found(), "docker": _found()}
    result = compute_recommendation((_DEVELOPER, _DEVOPS), _REGISTRY, verifications)
    assert result.best_match is not None
    assert result.best_match.profile_id == "devops"


def test_missing_tools_listed_for_best_match() -> None:
    # Only git installed: devops is 1/2 = 50%, developer is 1/3 = 33%, so
    # devops wins and should report docker as missing.
    result = compute_recommendation((_DEVELOPER, _DEVOPS), _REGISTRY, {"git": _found()})
    assert result.best_match is not None
    assert result.best_match.profile_id == "devops"
    missing_ids = {e.tool_id for e in result.best_match.diff.missing}
    assert missing_ids == {"docker"}


def test_no_best_match_when_nothing_installed() -> None:
    result = compute_recommendation((_DEVELOPER, _DEVOPS), _REGISTRY, {})
    assert result.best_match is None


def test_matches_cover_every_profile() -> None:
    result = compute_recommendation((_DEVELOPER, _DEVOPS), _REGISTRY, {"git": _found()})
    assert {m.profile_id for m in result.matches} == {"developer", "devops"}
