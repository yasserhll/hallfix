"""Tool registry domain models (spec §25/§67).

Data-driven by design: adding a tool means adding a YAML file under
``src/hallfix/data/tools/``, not editing Python (spec §25: "Prefer
data-driven definitions"). Everything here is pure data — parsing and
validating already-loaded dicts happens in
``domain/registries/tool_registry.py``; reading the YAML files themselves
is I/O and lives in ``infrastructure/registries/``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.models.system import DistributionFamily


class InstallationStrategy(StrEnum):
    """spec §23. Ordering below is declaration order, not trust order —
    see ``domain/registries/compatibility.py`` for trust-priority resolution."""

    APT = "APT"
    DNF = "DNF"
    PACMAN = "PACMAN"
    ZYPPER = "ZYPPER"
    PIP = "PIP"
    PIPX = "PIPX"
    NPM = "NPM"
    CARGO = "CARGO"
    COMPOSER = "COMPOSER"
    OFFICIAL_REPOSITORY = "OFFICIAL_REPOSITORY"
    SIGNED_BINARY = "SIGNED_BINARY"


NATIVE_INSTALLATION_STRATEGIES = frozenset(
    {
        InstallationStrategy.APT,
        InstallationStrategy.DNF,
        InstallationStrategy.PACMAN,
        InstallationStrategy.ZYPPER,
    }
)


@dataclass(frozen=True, slots=True)
class VerificationSpec:
    """How to confirm a tool actually works after installation (spec §26)."""

    executable: str
    version_command: tuple[str, ...] | None = None
    version_regex: str | None = None


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    id: str
    name: str
    description: str
    category: str
    profiles: tuple[str, ...] = field(default_factory=tuple)
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    installation_strategies: tuple[InstallationStrategy, ...] = field(default_factory=tuple)
    package_mappings: dict[InstallationStrategy, str] = field(default_factory=dict)
    verification: VerificationSpec | None = None
    supported_distributions: tuple[DistributionFamily, ...] = field(default_factory=tuple)
    supported_architectures: tuple[str, ...] = field(default_factory=tuple)
    minimum_version: str | None = None
    recommended_version: str | None = None
    optional: bool = False
    risk_level: RiskLevel = RiskLevel.LOW
    requires_root: bool = True
    documentation_url: str | None = None


@dataclass(frozen=True, slots=True)
class ToolVerificationResult:
    """Outcome of actually checking whether a tool works (spec §26).

    Distinct from ``PackageOperationResult`` — a package transaction can
    succeed while the tool itself is still broken (missing shared lib,
    wrong PATH, etc.), which is exactly the gap §26 exists to catch.
    """

    tool_id: str
    executable_found: bool
    installed_version: str | None
    meets_minimum_version: (
        bool | None
    )  # None = not determinable (no minimum declared, or no version found)
    meets_recommended_version: bool | None
