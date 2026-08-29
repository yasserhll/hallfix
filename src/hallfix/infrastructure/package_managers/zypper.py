"""Zypper adapter (SUSE family: openSUSE Leap/Tumbleweed, SLES).

Installed-state queries go through ``rpm -q`` (zypper sits on rpm), same
pattern as ``DnfManager``. ``repair()`` uses zypper's actual ``verify``
subcommand — a real dependency-consistency check, not a workaround.
"""

from __future__ import annotations

from hallfix.domain.models.package import (
    PackageManagerOperationResult,
    PackageOperationResult,
    PackageSearchResult,
)
from hallfix.domain.models.system import PackageManagerKind
from hallfix.infrastructure.package_managers.base import PackageManagerBase
from hallfix.infrastructure.package_managers.lock import existence_lock_probe


class ZypperManager(PackageManagerBase):
    kind = PackageManagerKind.ZYPPER
    binary = "zypper"
    _lock_path_suffix = "run/zypp.pid"
    _lock_probe = staticmethod(existence_lock_probe)

    def refresh_metadata(self, *, dry_run: bool = False) -> PackageManagerOperationResult:
        if not dry_run and self.check_lock().locked:
            return self._locked_result(dry_run=dry_run)
        result = self._run(
            ("zypper", "--non-interactive", "refresh"),
            requires_root=True,
            timeout_seconds=180.0,
            dry_run=dry_run,
        )
        return PackageManagerOperationResult(
            succeeded=result.succeeded,
            message="Zypper metadata refreshed." if result.succeeded else result.stderr,
            dry_run=dry_run,
            command=result,
        )

    def upgrade(self, *, dry_run: bool = False) -> PackageManagerOperationResult:
        if not dry_run and self.check_lock().locked:
            return self._locked_result(dry_run=dry_run)
        result = self._run(
            ("zypper", "--non-interactive", "update"),
            requires_root=True,
            timeout_seconds=600.0,
            dry_run=dry_run,
        )
        return PackageManagerOperationResult(
            succeeded=result.succeeded,
            message="Zypper packages upgraded." if result.succeeded else result.stderr,
            dry_run=dry_run,
            command=result,
        )

    def install(self, package: str, *, dry_run: bool = False) -> PackageOperationResult:
        if not dry_run and self.check_lock().locked:
            return self._locked_package_result(package, "install", dry_run=dry_run)
        result = self._run(
            ("zypper", "--non-interactive", "install", package),
            requires_root=True,
            dry_run=dry_run,
        )
        already_satisfied = "is already installed" in result.stdout.lower()
        return PackageOperationResult(
            package=package,
            action="install",
            succeeded=result.succeeded,
            already_satisfied=already_satisfied,
            installed_version=self.get_version(package)
            if not dry_run and result.succeeded
            else None,
            message=result.stdout if result.succeeded else result.stderr,
            dry_run=dry_run,
            command=result,
        )

    def remove(self, package: str, *, dry_run: bool = False) -> PackageOperationResult:
        if not dry_run and self.check_lock().locked:
            return self._locked_package_result(package, "remove", dry_run=dry_run)
        result = self._run(
            ("zypper", "--non-interactive", "remove", package),
            requires_root=True,
            dry_run=dry_run,
        )
        combined = (result.stdout + result.stderr).lower()
        already_satisfied = "not installed" in combined or "not found" in combined
        succeeded = result.succeeded or already_satisfied
        return PackageOperationResult(
            package=package,
            action="remove",
            succeeded=succeeded,
            already_satisfied=already_satisfied,
            installed_version=None,
            message=result.stdout if succeeded else result.stderr,
            dry_run=dry_run,
            command=result,
        )

    def is_installed(self, package: str) -> bool:
        result = self._run(("rpm", "-q", package), timeout_seconds=10.0)
        return result.succeeded

    def get_version(self, package: str) -> str | None:
        result = self._run(
            ("rpm", "-q", "--qf", "%{VERSION}-%{RELEASE}", package), timeout_seconds=10.0
        )
        if not result.succeeded or not result.stdout.strip():
            return None
        return result.stdout.strip()

    def search(self, query: str) -> tuple[PackageSearchResult, ...]:
        result = self._run(("zypper", "--non-interactive", "search", query), timeout_seconds=30.0)
        if not result.succeeded:
            return ()
        results: list[PackageSearchResult] = []
        for line in result.stdout.splitlines():
            if "|" not in line or line.strip().startswith(("-", "S ")):
                continue
            columns = [c.strip() for c in line.split("|")]
            if len(columns) < 3:
                continue
            name, summary = columns[1], columns[2]
            if not name or name.lower() == "name":
                continue
            results.append(PackageSearchResult(name=name, description=summary or None))
        return tuple(results)

    def repair(self, *, dry_run: bool = False) -> PackageManagerOperationResult:
        if not dry_run and self.check_lock().locked:
            return self._locked_result(dry_run=dry_run)
        result = self._run(
            ("zypper", "--non-interactive", "verify"),
            requires_root=True,
            timeout_seconds=180.0,
            dry_run=dry_run,
        )
        return PackageManagerOperationResult(
            succeeded=result.succeeded,
            message="Zypper dependency verification completed."
            if result.succeeded
            else result.stderr,
            dry_run=dry_run,
            command=result,
        )
