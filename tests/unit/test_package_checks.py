from __future__ import annotations

from hallfix.domain.diagnostics.package_checks import (
    check_package_manager,
    check_package_manager_lock,
)
from hallfix.domain.models.enums import Severity
from hallfix.domain.models.package import LockStatus
from hallfix.domain.models.system import DistributionFamily, PackageManagerKind
from tests.fixtures.diagnostic_context_factory import make_diagnostic_context
from tests.fixtures.system_context_factory import make_system_context


def test_package_manager_ok_when_known() -> None:
    ctx = make_diagnostic_context()  # default is APT
    (result,) = check_package_manager(ctx)
    assert result.severity == Severity.OK


def test_package_manager_warning_when_unknown() -> None:
    system = make_system_context(
        manager_kind=PackageManagerKind.UNKNOWN, family=DistributionFamily.UNKNOWN
    )
    ctx = make_diagnostic_context(system=system)
    (result,) = check_package_manager(ctx)
    assert result.severity == Severity.WARNING


def test_lock_info_when_not_checked() -> None:
    ctx = make_diagnostic_context(package_manager_lock=None)
    (result,) = check_package_manager_lock(ctx)
    assert result.severity == Severity.INFO


def test_lock_ok_when_unlocked() -> None:
    ctx = make_diagnostic_context(package_manager_lock=LockStatus(locked=False, lock_path=None))
    (result,) = check_package_manager_lock(ctx)
    assert result.severity == Severity.OK


def test_lock_warning_when_locked() -> None:
    ctx = make_diagnostic_context(
        package_manager_lock=LockStatus(locked=True, lock_path="/var/lib/dpkg/lock-frontend")
    )
    (result,) = check_package_manager_lock(ctx)
    assert result.severity == Severity.WARNING
    assert result.evidence == ("/var/lib/dpkg/lock-frontend",)
