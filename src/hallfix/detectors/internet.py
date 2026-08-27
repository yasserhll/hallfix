"""Raw Internet connectivity check (spec §16/§18).

Deliberately just a TCP reachability probe — no DNS resolution assumptions,
no HTTP. This answers "is there a route out" only; anything more specific
(DNS resolution failing while raw connectivity works, per the §18 example)
is a job for the Phase 9 network diagnostics, which compose this with a DNS
check. Kept as an injectable callable so tests never touch the real
network.
"""

from __future__ import annotations

import socket
from collections.abc import Callable

ConnectivityChecker = Callable[[], bool]

_PROBE_HOST = "1.1.1.1"
_PROBE_PORT = 443
_PROBE_TIMEOUT_SECONDS = 1.5


def check_internet_connectivity(
    *,
    host: str = _PROBE_HOST,
    port: int = _PROBE_PORT,
    timeout: float = _PROBE_TIMEOUT_SECONDS,
) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
