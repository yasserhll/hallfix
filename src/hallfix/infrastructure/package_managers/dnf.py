"""DNF/rpm adapter (Red Hat family: Fedora, RHEL, Rocky, AlmaLinux).

Installed-state queries go through ``rpm -q`` directly rather than parsing
``dnf`` output — matches the pattern used for ``ZypperManager`` since both
sit on rpm underneath.
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


class DnfManager(PackageManagerBase):
    kind = PackageManagerKind.DNF
    binary = "dnf"
    _lock_path_suffix = "run/dnf.pid"
    _lock_probe = staticmethod(existence_lock_probe)

    def refresh_metadata(self, *, dry_run: bool = False) -> PackageManagerOperationResult:
        if not dry_run and self.check_lock().locked:
            return self._locked_result(dry_run=dry_run)
        result = self._run(
            ("dnf", "makecache"), requires_root=True, timeout_seconds=180.0, dry_run=dry_run
        )
        return PackageManagerOperationResult(
            succeeded=result.succeeded,
            message="DNF metadata refreshed." if result.succeeded else result.stderr,
            dry_run=dry_run,
            command=result,
        )

    def upgrade(self, *, dry_run: bool = False) -> PackageManagerOperationResult:
        if not dry_run and self.check_lock().locked:
            return self._locked_result(dry_run=dry_run)
        result = self._run(
            ("dnf", "upgrade", "-y"), requires_root=True, timeout_seconds=600.0, dry_run=dry_run
        )
        return PackageManagerOperationResult(
            succeeded=result.succeeded,
            message="DNF packages upgraded." if result.succeeded else result.stderr,
            dry_run=dry_run,
            command=result,
        )

    def install(self, package: str, *, dry_run: bool = False) -> PackageOperationResult:
        if not dry_run and self.check_lock().locked:
            return self._locked_package_result(package, "install", dry_run=dry_run)
        result = self._run(("dnf", "install", "-y", package), requires_root=True, dry_run=dry_run)
        already_satisfied = "already installed" in result.stdout.lower()
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
        result = self._run(("dnf", "remove", "-y", package), requires_root=True, dry_run=dry_run)
        already_satisfied = "no packages marked for removal" in result.stdout.lower()
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
        result = self._run(("dnf", "search", query), timeout_seconds=30.0)
        if not result.succeeded:
            return ()
        results: list[PackageSearchResult] = []
        for line in result.stdout.splitlines():
            if line.startswith("=") or " : " not in line:
                continue
            name_arch, _, description = line.partition(" : ")
            name = name_arch.split(".")[0].strip()
            if name:
                results.append(PackageSearchResult(name=name, description=description.strip()))
        return tuple(results)

    def repair(self, *, dry_run: bool = False) -> PackageManagerOperationResult:
        if not dry_run and self.check_lock().locked:
            return self._locked_result(dry_run=dry_run)
        clean_result = self._run(
            ("dnf", "clean", "all"), requires_root=True, timeout_seconds=60.0, dry_run=dry_run
        )
        cache_result = self._run(
            ("dnf", "makecache"), requires_root=True, timeout_seconds=180.0, dry_run=dry_run
        )
        succeeded = clean_result.succeeded and cache_result.succeeded
        return PackageManagerOperationResult(
            succeeded=succeeded,
            message="DNF cache cleaned and rebuilt." if succeeded else cache_result.stderr,
            dry_run=dry_run,
            command=cache_result,
        )
