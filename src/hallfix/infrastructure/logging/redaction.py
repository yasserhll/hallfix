"""Secret redaction for structured logs (spec §57).

Two redaction strategies, applied together:

1. Key-based: any mapping key matching a sensitive-name pattern has its
   value replaced, regardless of what the value looks like.
2. Pattern-based: raw string messages are scanned for ``key=value`` /
   ``key: value`` shapes using the same sensitive-name list, since a
   command's stdout/stderr often isn't structured.

This is deliberately conservative (over-redact rather than under-redact) —
a log message that loses a non-secret value is a much smaller problem than
a leaked credential.
"""

from __future__ import annotations

import re
from typing import Any

REDACTED = "***REDACTED***"

_SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "passwd",
    "token",
    "secret",
    "api_key",
    "apikey",
    "credential",
    "private_key",
    "access_key",
    "auth",
    "ssh_key",
)

_KEY_VALUE_PATTERN = re.compile(
    r"(?P<key>\b(?:"
    + "|".join(re.escape(f) for f in _SENSITIVE_KEY_FRAGMENTS)
    + r")\w*)\s*([:=])\s*(?P<value>[^\s,;]+)",
    re.IGNORECASE,
)


def is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(fragment in lowered for fragment in _SENSITIVE_KEY_FRAGMENTS)


def redact_text(text: str) -> str:
    """Redact ``key=value``/``key: value`` occurrences of sensitive data in free text."""

    def _replace(match: re.Match[str]) -> str:
        return f"{match.group('key')}{match.group(2)}{REDACTED}"

    return _KEY_VALUE_PATTERN.sub(_replace, text)


def redact_mapping(data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``data`` with sensitive values replaced, recursively.

    A dict-valued field is always recursed into, even if its own key name
    looks sensitive (e.g. an ``auth: {...}`` section) — replacing the whole
    substructure would also destroy non-sensitive sibling fields inside it.
    Leaf (non-dict) values are redacted outright when their key matches.
    """
    result: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = redact_mapping(value)
        elif is_sensitive_key(key):
            result[key] = REDACTED
        elif isinstance(value, str):
            result[key] = redact_text(value)
        else:
            result[key] = value
    return result


def redact_env(env: dict[str, str]) -> dict[str, str]:
    """Redact an environment mapping before it is ever logged."""
    return {k: (REDACTED if is_sensitive_key(k) else v) for k, v in env.items()}
