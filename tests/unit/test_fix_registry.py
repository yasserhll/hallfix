from __future__ import annotations

import pytest

from hallfix.domain.exceptions import RegistryError
from hallfix.domain.models.enums import RiskLevel
from hallfix.domain.models.system import DistributionFamily
from hallfix.domain.registries.fix_registry import FixRegistry


def test_default_registry_contains_package_broken_state_fix() -> None:
    registry = FixRegistry()
    fix = registry.get("fix.package_broken_state")
    assert fix is not None
    assert fix.risk_level == RiskLevel.LOW
    assert fix.diagnostic_id == "package.broken_state"
    assert fix.supported_distributions == (DistributionFamily.DEBIAN,)


def test_no_fix_is_high_or_critical_risk() -> None:
    """Spec §43: only well-understood LOW-risk fixes should be automated."""
    registry = FixRegistry()
    for fix in registry.list_all():
        assert fix.risk_level == RiskLevel.LOW


def test_no_fix_claims_rollback_available() -> None:
    """None of Hallfix's fixes have a real undo mechanism yet — spec §11:
    never claim rollback is available when it is not."""
    registry = FixRegistry()
    for fix in registry.list_all():
        assert fix.rollback_available is False


def test_get_returns_none_for_unknown_id() -> None:
    registry = FixRegistry()
    assert registry.get("fix.does_not_exist") is None


def test_require_raises_for_unknown_id() -> None:
    registry = FixRegistry()
    with pytest.raises(RegistryError):
        registry.require("fix.does_not_exist")


def test_for_diagnostic_finds_matching_fix() -> None:
    registry = FixRegistry()
    fix = registry.for_diagnostic("package.broken_state")
    assert fix is not None
    assert fix.id == "fix.package_broken_state"


def test_for_diagnostic_returns_none_when_no_fix_maps_to_it() -> None:
    registry = FixRegistry()
    assert registry.for_diagnostic("network.dns_resolution") is None


def test_list_all_sorted_by_id() -> None:
    registry = FixRegistry()
    ids = [f.id for f in registry.list_all()]
    assert ids == sorted(ids)
