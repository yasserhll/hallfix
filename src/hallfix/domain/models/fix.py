"""FixRegistry domain model (spec §42).

Only one fix exists as of Phase 10, deliberately: cross-referencing
spec §43's "never automatically perform risky repairs involving
bootloader/partition tables/firewall/SSH/network configuration/
filesystem repair/kernel replacement/drivers" against Phase 9's actual
diagnostics leaves exactly one genuinely safe, well-understood candidate —
repairing broken/half-configured dpkg package state, which is exactly
what ``PackageManager.repair()`` already does (Phase 3). Disk space,
package manager locks, and DNS/network configuration are all diagnosed
but deliberately have no automated fix; padding this registry with
unsafe or fake fixes just to look more complete would violate spec §84's
"never invent support that hasn't been tested."
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.models.system import DistributionFamily


@dataclass(frozen=True, slots=True)
class FixDefinition:
    id: str
    description: str
    risk_level: RiskLevel
    requires_root: bool
    backup_required: bool
    rollback_available: bool
    diagnostic_id: str
    supported_distributions: tuple[DistributionFamily, ...] = field(default_factory=tuple)
