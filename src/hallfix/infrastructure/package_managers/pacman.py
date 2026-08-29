"""Pacman adapter (Arch family: Arch Linux, Manjaro, EndeavourOS).

``repair()`` is best-effort: pacman has no dedicated repair verb, so this
forces a full database re-sync (``-Syy``). ``refresh_metadata()`` uses a
plain sync (``-Sy``) without ``-u`` — this is the documented "partial
upgrade" pitfall on Arch (installing afterward without a full ``-Syu`` can
pull in a broken dependency combination). ``upgrade()`` is the one place
Hallfix runs ``-u``, and only when the user explicitly asked for a system
upgrade (spec §54's ``hallfix update system``) via the full, correct
``-Syu`` — never as a side effect of metadata refresh or install.
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


class PacmanManager(PackageManagerBase):
    kind = PackageManagerKind.PACMAN
    binary = "pacman"
    _lock_path_suffix = "var/lib/pacman/db.lck"
    _lock_probe = staticmethod(existence_lock_probe)

    def refresh_metadata(self, *, dry_run: bool = False) -> PackageManagerOperationResult:
        if not dry_run and self.check_lock().locked:
            return self._locked_result(dry_run=dry_run)
        result = self._run(
            ("pacman", "-Sy", "--noconfirm"),
            requires_root=True,
            timeout_seconds=180.0,
            dry_run=dry_run,
        )
        return PackageManagerOperationResult(
            succeeded=result.succeeded,
            message="Pacman metadata refreshed." if result.succeeded else result.stderr,
            dry_run=dry_run,
            command=result,
        )

    def upgrade(self, *, dry_run: bool = False) -> PackageManagerOperationResult:
        if not dry_run and self.check_lock().locked:
            return self._locked_result(dry_run=dry_run)
        result = self._run(
            ("pacman", "-Syu", "--noconfirm"),
            requires_root=True,
            timeout_seconds=600.0,
            dry_run=dry_run,
        )
        return PackageManagerOperationResult(
            succeeded=result.succeeded,
            message="Pacman full system upgrade completed." if result.succeeded else result.stderr,
            dry_run=dry_run,
            command=result,
        )

    def install(self, package: str, *, dry_run: bool = False) -> PackageOperationResult:
        if not dry_run and self.check_lock().locked:
            return self._locked_package_result(package, "install", dry_run=dry_run)
        result = self._run(
            ("pacman", "-S", "--noconfirm", "--needed", package),
            requires_root=True,
            dry_run=dry_run,
        )
        already_satisfied = "-- skipping" in result.stdout or "is up to date" in result.stdout
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
            ("pacman", "-R", "--noconfirm", package), requires_root=True, dry_run=dry_run
        )
        already_satisfied = "target not found" in result.stderr
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
        result = self._run(("pacman", "-Q", package), timeout_seconds=10.0)
        return result.succeeded

    def get_version(self, package: str) -> str | None:
        result = self._run(("pacman", "-Q", package), timeout_seconds=10.0)
        if not result.succeeded or not result.stdout.strip():
            return None
        parts = result.stdout.strip().split()
        return parts[1] if len(parts) >= 2 else None

    def search(self, query: str) -> tuple[PackageSearchResult, ...]:
        result = self._run(("pacman", "-Ss", query), timeout_seconds=30.0)
        if not result.succeeded:
            return ()
        results: list[PackageSearchResult] = []
        lines = result.stdout.splitlines()
        i = 0
        while i < len(lines):
            header = lines[i]
            if header and not header[0].isspace() and "/" in header:
                repo_name, _, version = header.partition(" ")
                name = repo_name.split("/", 1)[-1]
                description = None
                if i + 1 < len(lines) and lines[i + 1].startswith((" ", "\t")):
                    description = lines[i + 1].strip()
                    i += 1
                results.append(
                    PackageSearchResult(name=name, description=description, version=version or None)
                )
            i += 1
        return tuple(results)

    def repair(self, *, dry_run: bool = False) -> PackageManagerOperationResult:
        if not dry_run and self.check_lock().locked:
            return self._locked_result(dry_run=dry_run)
        result = self._run(
            ("pacman", "-Syy", "--noconfirm"),
            requires_root=True,
            timeout_seconds=180.0,
            dry_run=dry_run,
        )
        return PackageManagerOperationResult(
            succeeded=result.succeeded,
            message="Pacman database re-synced." if result.succeeded else result.stderr,
            dry_run=dry_run,
            command=result,
        )
