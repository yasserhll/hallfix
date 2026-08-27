"""Reliable-enough version comparison (spec §53).

Deliberately simple: extracts the leading dotted-numeric run (e.g. ``2.43``
out of ``git version 2.43.0``) and compares component-wise. This is not a
full PEP 440/semver parser — it doesn't need to be, since it only ever
compares Hallfix's own ``minimum_version``/``recommended_version``
declarations against a tool's own version output, both of which are
ordinary dotted-numeric versions in practice. Returns ``None`` rather than
guessing when either side isn't parseable.
"""

from __future__ import annotations

import re

_VERSION_PATTERN = re.compile(r"\d+(?:\.\d+)*")


def parse_version(text: str) -> tuple[int, ...] | None:
    match = _VERSION_PATTERN.search(text)
    if not match:
        return None
    return tuple(int(part) for part in match.group().split("."))


def compare_versions(a: str, b: str) -> int | None:
    """Returns -1/0/1 (a < b / a == b / a > b), or None if either is unparseable."""
    parsed_a, parsed_b = parse_version(a), parse_version(b)
    if parsed_a is None or parsed_b is None:
        return None
    length = max(len(parsed_a), len(parsed_b))
    padded_a = parsed_a + (0,) * (length - len(parsed_a))
    padded_b = parsed_b + (0,) * (length - len(parsed_b))
    if padded_a < padded_b:
        return -1
    if padded_a > padded_b:
        return 1
    return 0


def meets_minimum(installed: str | None, minimum: str | None) -> bool | None:
    if installed is None or minimum is None:
        return None
    comparison = compare_versions(installed, minimum)
    return None if comparison is None else comparison >= 0
