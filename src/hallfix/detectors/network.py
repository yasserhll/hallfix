"""Network basics detection (spec §16): interfaces, IPs, gateway, DNS.

Interface/address/route data comes from ``ip -j ...`` (structured JSON,
far more reliable to parse than ``ip addr`` text or raw ``/proc/net/*``).
Goes through the injected ``CommandRunner`` like every other external
command in Hallfix — a fake runner in tests supplies canned JSON. DNS
servers are read from ``/etc/resolv.conf`` under ``root``, same
fake-root pattern as every other detector.

Never performs connectivity checks itself (see ``detectors/internet.py``)
and never contacts anything off-box — this module only reads local
configuration.
"""

from __future__ import annotations

import json
from pathlib import Path

from hallfix.domain.models.command import CommandSpec
from hallfix.domain.models.system import NetworkInfo, NetworkInterface
from hallfix.infrastructure.commands.runner import CommandRunner


class NetworkDetector:
    def __init__(self, *, root: Path = Path("/"), command_runner: CommandRunner) -> None:
        self._root = root
        self._runner = command_runner

    def detect(self) -> NetworkInfo:
        return NetworkInfo(
            interfaces=self._detect_interfaces(),
            default_gateway=self._detect_default_gateway(),
            dns_servers=self._detect_dns_servers(),
        )

    def _run_json(self, argv: tuple[str, ...]) -> object | None:
        result = self._runner.run(CommandSpec(argv=argv, timeout_seconds=5.0))
        if not result.succeeded or not result.stdout.strip():
            return None
        try:
            parsed: object = json.loads(result.stdout)
        except json.JSONDecodeError:
            return None
        return parsed

    def _detect_interfaces(self) -> tuple[NetworkInterface, ...]:
        data = self._run_json(("ip", "-j", "addr", "show"))
        if not isinstance(data, list):
            return ()

        interfaces: list[NetworkInterface] = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            name = entry.get("ifname")
            if not isinstance(name, str):
                continue
            ipv4: list[str] = []
            ipv6: list[str] = []
            for addr in entry.get("addr_info", []) or []:
                if not isinstance(addr, dict):
                    continue
                family = addr.get("family")
                local = addr.get("local")
                if not isinstance(local, str):
                    continue
                if family == "inet":
                    ipv4.append(local)
                elif family == "inet6":
                    ipv6.append(local)
            is_up = str(entry.get("operstate", "")).upper() == "UP"
            interfaces.append(
                NetworkInterface(
                    name=name,
                    ipv4_addresses=tuple(ipv4),
                    ipv6_addresses=tuple(ipv6),
                    is_up=is_up,
                )
            )
        return tuple(interfaces)

    def _detect_default_gateway(self) -> str | None:
        data = self._run_json(("ip", "-j", "route", "show", "default"))
        if not isinstance(data, list) or not data:
            return None
        first = data[0]
        if not isinstance(first, dict):
            return None
        gateway = first.get("gateway")
        return gateway if isinstance(gateway, str) else None

    def _detect_dns_servers(self) -> tuple[str, ...]:
        resolv_path = self._root / "etc" / "resolv.conf"
        if not resolv_path.is_file():
            return ()
        servers: list[str] = []
        for line in resolv_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if stripped.startswith("nameserver"):
                parts = stripped.split()
                if len(parts) >= 2:
                    servers.append(parts[1])
        return tuple(servers)
