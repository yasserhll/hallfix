"""BackupManager (spec §46): atomic file backups before Hallfix modifies a
managed configuration file.

No ``Action`` calls this yet — Hallfix has no ``WRITE_FILE``/``MODIFY_FILE``
action type (spec §5's action vocabulary is added incrementally, per the
design note in ``domain/planning/action.py``). Built now as real, tested,
standalone infrastructure because backup capability is a Phase 11
deliverable in its own right and is exactly what a future config-editing
action will need — the same way Phase 1's ``CommandRunner`` existed before
Phase 2's detectors became its first real caller.

Backup naming matches spec §46's example exactly:
``/etc/example.conf.hallfix-backup-YYYYMMDD-HHMMSS``. Both backup and
restore write via a temp file in the same directory, then ``Path.replace``
— atomic on POSIX, same pattern as ``StateStore``.

Ownership preservation is best-effort ("when applicable" per spec §46):
if the current process lacks permission to ``chown`, that step is
skipped rather than failing the whole operation — Hallfix degrading
gracefully over an unprivileged detail, not crashing.
"""

from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from hallfix.domain.exceptions import BackupError
from hallfix.domain.models.backup import BackupRecord

_BACKUP_SUFFIX_FORMAT = "%Y%m%d-%H%M%S"


def _atomic_copy(source: Path, destination: Path) -> None:
    """Copies ``source`` to ``destination`` via a same-directory temp file
    + atomic rename, preserving mode/mtime always and ownership when the
    current process has permission to.
    """
    tmp_path = destination.with_name(destination.name + ".hallfix-tmp")
    try:
        shutil.copy2(source, tmp_path)  # content + mode + mtime
        try:
            stat = source.stat()
            os.chown(tmp_path, stat.st_uid, stat.st_gid)
        except OSError:
            pass  # not permitted (not root / not owner) — best-effort only
        tmp_path.replace(destination)
    finally:
        tmp_path.unlink(missing_ok=True)


class BackupManager:
    def backup(self, path: Path, *, now: datetime | None = None) -> BackupRecord:
        if not path.is_file():
            msg = f"cannot back up {path}: not a regular file"
            raise BackupError(msg)

        timestamp = (now or datetime.now(UTC)).strftime(_BACKUP_SUFFIX_FORMAT)
        backup_path = path.with_name(f"{path.name}.hallfix-backup-{timestamp}")
        try:
            _atomic_copy(path, backup_path)
        except OSError as exc:
            msg = f"failed to back up {path}: {exc}"
            raise BackupError(msg) from exc

        return BackupRecord(
            original_path=str(path),
            backup_path=str(backup_path),
            created_at=(now or datetime.now(UTC)).isoformat(),
        )

    def restore(self, record: BackupRecord) -> None:
        backup_path = Path(record.backup_path)
        original_path = Path(record.original_path)
        if not backup_path.is_file():
            msg = f"cannot restore {original_path}: backup {backup_path} not found"
            raise BackupError(msg)

        try:
            _atomic_copy(backup_path, original_path)
        except OSError as exc:
            msg = f"failed to restore {original_path} from {backup_path}: {exc}"
            raise BackupError(msg) from exc
