"""DNS resolution check — distinct from ``detectors/internet.py``.

``check_internet_connectivity`` deliberately connects to a raw IP,
bypassing DNS entirely, so it can tell "no route out" apart from "DNS is
broken". This module is the other half: does hostname resolution actually
work. Together they let a diagnostic distinguish spec §18's example
exactly — raw connectivity fine, DNS resolution failing.
"""

from __future__ import annotations

import socket
from collections.abc import Callable

DnsResolutionChecker = Callable[[], bool]

_PROBE_HOSTNAME = "example.com"
_PROBE_TIMEOUT_SECONDS = 3.0


def check_dns_resolution(
    *, hostname: str = _PROBE_HOSTNAME, timeout: float = _PROBE_TIMEOUT_SECONDS
) -> bool:
    original_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        socket.getaddrinfo(hostname, None)
        return True
    except OSError:
        return False
    finally:
        socket.setdefaulttimeout(original_timeout)
