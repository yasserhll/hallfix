"""APT/dpkg adapter (Debian family: Debian, Ubuntu, Mint, Pop!_OS, Kali, ...).

Uses ``apt-get`` (not ``apt``) for scripted use — ``apt`` explicitly warns
its output format is unstable and meant for interactive use. Installed-state
queries go through ``dpkg-query`` rather than parsing ``apt-get`` output.
"""

from __future__ import annotations

import os

from hallfix.domain.models.package import (
    PackageManagerOperationResult,
    PackageOperationResult,
    PackageSearchResult,
)
from hallfix.domain.models.system import PackageManagerKind
from hallfix.infrastructure.package_managers.base import PackageManagerBase
from hallfix.infrastructure.package_managers.lock import flock_lock_probe

_NONINTERACTIVE_ENV = dict(os.environ) | {"DEBIAN_FRONTEND": "noninteractive"}


class AptManager(PackageManagerBase):
    kind = PackageManagerKind.APT
    binary = "apt-get"
    _lock_path_suffix = "var/lib/dpkg/lock-frontend"
    _lock_probe = staticmethod(flock_lock_probe)

    def refresh_metadata(self, *, dry_run: bool = False) -> PackageManagerOperationResult:
        if not dry_run and self.check_lock().locked:
            return self._locked_result(dry_run=dry_run)
        result = self._run(
            ("apt-get", "update"),
            requires_root=True,
            timeout_seconds=180.0,
            dry_run=dry_run,
        )
        return PackageManagerOperationResult(
            succeeded=result.succeeded,
            message="APT metadata refreshed." if result.succeeded else result.stderr,
            dry_run=dry_run,
            command=result,
        )

    def upgrade(self, *, dry_run: bool = False) -> PackageManagerOperationResult:
        if not dry_run and self.check_lock().locked:
            return self._locked_result(dry_run=dry_run)
        result = self._run(
            ("apt-get", "upgrade", "-y"),
            requires_root=True,
            env=_NONINTERACTIVE_ENV,
            timeout_seconds=600.0,
            dry_run=dry_run,
        )
        return PackageManagerOperationResult(
            succeeded=result.succeeded,
            message="APT packages upgraded." if result.succeeded else result.stderr,
            dry_run=dry_run,
            command=result,
        )

    def install(self, package: str, *, dry_run: bool = False) -> PackageOperationResult:
        if not dry_run and self.check_lock().locked:
            return self._locked_package_result(package, "install", dry_run=dry_run)
        result = self._run(
            ("apt-get", "install", "-y", package),
            requires_root=True,
            env=_NONINTERACTIVE_ENV,
            dry_run=dry_run,
        )
        already_satisfied = "already the newest version" in result.stdout
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
            ("apt-get", "remove", "-y", package),
            requires_root=True,
            env=_NONINTERACTIVE_ENV,
            dry_run=dry_run,
        )
        already_satisfied = "is not installed" in result.stdout or "not installed" in result.stderr
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
        result = self._run(("dpkg-query", "-W", "-f=${Status}", package), timeout_seconds=10.0)
        return result.succeeded and "install ok installed" in result.stdout

    def get_version(self, package: str) -> str | None:
        result = self._run(("dpkg-query", "-W", "-f=${Version}", package), timeout_seconds=10.0)
        if not result.succeeded or not result.stdout.strip():
            return None
        return result.stdout.strip()

    def search(self, query: str) -> tuple[PackageSearchResult, ...]:
        result = self._run(("apt-cache", "search", query), timeout_seconds=30.0)
        if not result.succeeded:
            return ()
        results: list[PackageSearchResult] = []
        for line in result.stdout.splitlines():
            if " - " not in line:
                continue
            name, _, description = line.partition(" - ")
            results.append(PackageSearchResult(name=name.strip(), description=description.strip()))
        return tuple(results)

    def repair(self, *, dry_run: bool = False) -> PackageManagerOperationResult:
        if not dry_run and self.check_lock().locked:
            return self._locked_result(dry_run=dry_run)
        configure_result = self._run(
            ("dpkg", "--configure", "-a"),
            requires_root=True,
            timeout_seconds=180.0,
            dry_run=dry_run,
        )
        fix_result = self._run(
            ("apt-get", "install", "--fix-broken", "-y"),
            requires_root=True,
            env=_NONINTERACTIVE_ENV,
            timeout_seconds=180.0,
            dry_run=dry_run,
        )
        succeeded = configure_result.succeeded and fix_result.succeeded
        return PackageManagerOperationResult(
            succeeded=succeeded,
            message="APT/dpkg repair completed." if succeeded else fix_result.stderr,
            dry_run=dry_run,
            command=fix_result,
        )
