from __future__ import annotations

import fcntl
import multiprocessing
from pathlib import Path

from hallfix.infrastructure.package_managers.lock import existence_lock_probe, flock_lock_probe


def test_flock_probe_false_when_file_missing(tmp_path: Path) -> None:
    assert flock_lock_probe(tmp_path / "does-not-exist") is False


def test_flock_probe_false_when_file_exists_but_unlocked(tmp_path: Path) -> None:
    lock_path = tmp_path / "lock"
    lock_path.touch()
    assert flock_lock_probe(lock_path) is False


def test_flock_probe_does_not_modify_or_delete_the_file(tmp_path: Path) -> None:
    lock_path = tmp_path / "lock"
    lock_path.write_text("original content", encoding="utf-8")
    flock_lock_probe(lock_path)
    assert lock_path.exists()
    assert lock_path.read_text(encoding="utf-8") == "original content"


def _hold_lock(
    path_str: str,
    ready: multiprocessing.synchronize.Event,
    release: multiprocessing.synchronize.Event,
) -> None:
    with open(path_str, "rb") as handle:  # noqa: PTH123 - simplest correct flock target
        fcntl.flock(handle, fcntl.LOCK_EX)
        ready.set()
        release.wait(timeout=10)


def test_flock_probe_detects_lock_held_by_another_process(tmp_path: Path) -> None:
    lock_path = tmp_path / "lock"
    lock_path.touch()
    ready = multiprocessing.Event()
    release = multiprocessing.Event()
    proc = multiprocessing.Process(target=_hold_lock, args=(str(lock_path), ready, release))
    proc.start()
    try:
        assert ready.wait(timeout=5), "child process failed to acquire the lock in time"
        assert flock_lock_probe(lock_path) is True
    finally:
        release.set()
        proc.join(timeout=5)


def test_existence_probe_true_when_file_present(tmp_path: Path) -> None:
    lock_path = tmp_path / "db.lck"
    lock_path.touch()
    assert existence_lock_probe(lock_path) is True


def test_existence_probe_false_when_file_absent(tmp_path: Path) -> None:
    assert existence_lock_probe(tmp_path / "db.lck") is False
