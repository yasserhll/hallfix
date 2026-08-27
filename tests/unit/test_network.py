from __future__ import annotations

import json
from pathlib import Path

from hallfix.detectors.network import NetworkDetector
from tests.fixtures.fake_command_runner import FakeCommandRunner, ok_result

_ADDR_JSON = json.dumps(
    [
        {
            "ifname": "lo",
            "operstate": "UNKNOWN",
            "addr_info": [{"family": "inet", "local": "127.0.0.1"}],
        },
        {
            "ifname": "eth0",
            "operstate": "UP",
            "addr_info": [
                {"family": "inet", "local": "192.168.1.50"},
                {"family": "inet6", "local": "fe80::1"},
            ],
        },
    ]
)

_ROUTE_JSON = json.dumps([{"dst": "default", "gateway": "192.168.1.1", "dev": "eth0"}])


def _runner_with_ip_output() -> FakeCommandRunner:
    runner = FakeCommandRunner()
    runner.stub(("ip", "-j", "addr", "show"), ok_result(("ip", "-j", "addr", "show"), _ADDR_JSON))
    runner.stub(
        ("ip", "-j", "route", "show", "default"),
        ok_result(("ip", "-j", "route", "show", "default"), _ROUTE_JSON),
    )
    return runner


def test_network_detector_parses_interfaces_and_addresses(fake_systems_dir: Path) -> None:
    detector = NetworkDetector(
        root=fake_systems_dir / "ubuntu", command_runner=_runner_with_ip_output()
    )
    info = detector.detect()
    names = {iface.name for iface in info.interfaces}
    assert names == {"lo", "eth0"}
    eth0 = next(i for i in info.interfaces if i.name == "eth0")
    assert eth0.ipv4_addresses == ("192.168.1.50",)
    assert eth0.ipv6_addresses == ("fe80::1",)
    assert eth0.is_up
    assert info.has_ipv4
    assert info.has_ipv6


def test_network_detector_parses_default_gateway(fake_systems_dir: Path) -> None:
    detector = NetworkDetector(
        root=fake_systems_dir / "ubuntu", command_runner=_runner_with_ip_output()
    )
    info = detector.detect()
    assert info.default_gateway == "192.168.1.1"


def test_network_detector_parses_dns_servers(fake_systems_dir: Path) -> None:
    detector = NetworkDetector(
        root=fake_systems_dir / "ubuntu", command_runner=_runner_with_ip_output()
    )
    info = detector.detect()
    assert info.dns_servers == ("1.1.1.1", "8.8.8.8")


def test_network_detector_degrades_gracefully_when_ip_command_fails(fake_systems_dir: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(
        ("ip", "-j", "addr", "show"), ok_result(("ip", "-j", "addr", "show"), "", exit_code=1)
    )
    runner.stub(
        ("ip", "-j", "route", "show", "default"),
        ok_result(("ip", "-j", "route", "show", "default"), "", exit_code=1),
    )
    detector = NetworkDetector(root=fake_systems_dir / "ubuntu", command_runner=runner)
    info = detector.detect()
    assert info.interfaces == ()
    assert info.default_gateway is None


def test_network_detector_degrades_gracefully_on_invalid_json(fake_systems_dir: Path) -> None:
    runner = FakeCommandRunner()
    runner.stub(("ip", "-j", "addr", "show"), ok_result(("ip", "-j", "addr", "show"), "not json"))
    runner.stub(
        ("ip", "-j", "route", "show", "default"),
        ok_result(("ip", "-j", "route", "show", "default"), "not json"),
    )
    detector = NetworkDetector(root=fake_systems_dir / "ubuntu", command_runner=runner)
    info = detector.detect()
    assert info.interfaces == ()


def test_network_detector_no_resolv_conf_returns_empty_dns(tmp_path: Path) -> None:
    runner = _runner_with_ip_output()
    detector = NetworkDetector(root=tmp_path, command_runner=runner)
    info = detector.detect()
    assert info.dns_servers == ()
