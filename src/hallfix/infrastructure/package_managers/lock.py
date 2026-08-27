"""Package-manager lock probes (spec §20).

Two genuinely different lock semantics exist in the wild, so there are two
probes — using the wrong one for a given manager gives wrong answers:

- **flock-based** (dpkg/apt): the lock file exists permanently on disk
  whether or not an operation is running; the lock itself is an
  ``flock(2)`` held on that file only while apt/dpkg is active. Checking
  mere existence would report "locked" forever, so this probe actually
  attempts a non-blocking exclusive flock and releases it immediately.
- **existence-based** (dnf/pacman/zypper): these managers create their
  pid/lock file only for the duration of an active operation and remove it
  afterward, so plain existence is a reasonable signal. This is a
  best-effort heuristic — a process that crashed without cleaning up would
  produce a false "locked" reading. Documented here rather than silently
  assumed reliable (spec §84: never invent support that hasn't been
  tested).

Never deletes a lock file, under any circumstance (spec §20).
"""

from __future__ import annotations

import errno
import fcntl
from collections.abc import Callable
from pathlib import Path

LockProbeFn = Callable[[Path], bool]
"""path -> True if locked."""


def flock_lock_probe(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        with path.open("rb") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                if exc.errno in (errno.EACCES, errno.EAGAIN):
                    return True
                raise
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)
                return False
    except OSError:
        # Can't even open it (permissions, race) — treat as "unknown, but
        # not confirmed locked" rather than blocking the caller.
        return False


def existence_lock_probe(path: Path) -> bool:
    return path.exists()
