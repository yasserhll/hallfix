"""``FixRegistry`` (spec §42).

Hardcoded in Python rather than YAML, unlike Tool/ProfileRegistry —
there's exactly one fix (see ``domain/models/fix.py`` for why), and each
fix needs real execution logic wired to it in ``Executor``, not just a
package-name mapping. A data-file pipeline for one entry would be
premature; revisit if this registry grows past a handful of fixes.
"""

from __future__ import annotations

from hallfix.domain.exceptions import RegistryError
from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.models.fix import FixDefinition
from hallfix.domain.models.system import DistributionFamily

_FIXES: tuple[FixDefinition, ...] = (
    FixDefinition(
        id="fix.package_broken_state",
        description="Configure half-installed packages and repair broken dependencies "
        "(dpkg --configure -a + apt-get install --fix-broken).",
        risk_level=RiskLevel.LOW,
        requires_root=True,
        backup_required=False,
        rollback_available=False,
        diagnostic_id="package.broken_state",
        supported_distributions=(DistributionFamily.DEBIAN,),
    ),
)


class FixRegistry:
    def __init__(self, fixes: tuple[FixDefinition, ...] = _FIXES) -> None:
        self._fixes = {f.id: f for f in fixes}

    def get(self, fix_id: str) -> FixDefinition | None:
        return self._fixes.get(fix_id)

    def require(self, fix_id: str) -> FixDefinition:
        fix = self._fixes.get(fix_id)
        if fix is None:
            msg = f"no such fix: {fix_id!r}"
            raise RegistryError(msg)
        return fix

    def list_all(self) -> tuple[FixDefinition, ...]:
        return tuple(sorted(self._fixes.values(), key=lambda f: f.id))

    def for_diagnostic(self, diagnostic_id: str) -> FixDefinition | None:
        return next((f for f in self._fixes.values() if f.diagnostic_id == diagnostic_id), None)
