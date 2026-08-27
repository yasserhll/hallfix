"""BackupRecord (spec §46). Pure data — ``infrastructure/filesystem/backup.py``
does the actual copy I/O.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BackupRecord:
    original_path: str
    backup_path: str
    created_at: str  # ISO 8601 — stored as text so it round-trips through JSON/history cleanly
