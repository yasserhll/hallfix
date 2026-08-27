from __future__ import annotations

from hallfix.domain.diagnostics.network_checks import (
    check_default_gateway,
    check_dns_configured,
    check_dns_resolution,
    check_internet_connectivity,
    check_network_interfaces,
)
from hallfix.domain.models.enums import Severity
from hallfix.domain.models.system import (
    CapabilitySet,
    DistributionFamily,
    NetworkInfo,
    NetworkInterface,
    PackageManagerKind,
)
from tests.fixtures.diagnostic_context_factory import make_diagnostic_context
from tests.fixtures.system_context_factory import make_system_context

_APT_DEBIAN = {"manager_kind": PackageManagerKind.APT, "family": DistributionFamily.DEBIAN}


def _caps(**overrides: bool) -> CapabilitySet:
    base: dict[str, bool] = {
        "package_management": True,
        "systemd": True,
        "sudo": True,
        "graphical_session": False,
        "network_manager": True,
        "selinux": False,
        "apparmor": False,
        "container_runtime": False,
        "wsl": False,
        "immutable_os": False,
        "filesystem_write_access": True,
        "internet_access": True,
        "ipv4": True,
        "ipv6": False,
    }
    base.update(overrides)
    return CapabilitySet(**base)


def test_interfaces_ok_when_active_non_loopback_present() -> None:
    system = make_system_context(
        **_APT_DEBIAN,
        network=NetworkInfo(
            interfaces=(NetworkInterface(name="eth0", ipv4_addresses=("10.0.0.5",), is_up=True),)
        ),
    )
    ctx = make_diagnostic_context(system=system)
    (result,) = check_network_interfaces(ctx)
    assert result.severity == Severity.OK


def test_interfaces_warning_when_none_active() -> None:
    system = make_system_context(
        **_APT_DEBIAN,
        network=NetworkInfo(
            interfaces=(NetworkInterface(name="lo", ipv4_addresses=("127.0.0.1",)),)
        ),
    )
    ctx = make_diagnostic_context(system=system)
    (result,) = check_network_interfaces(ctx)
    assert result.severity == Severity.WARNING


def test_gateway_ok_when_configured() -> None:
    system = make_system_context(**_APT_DEBIAN, network=NetworkInfo(default_gateway="192.168.1.1"))
    ctx = make_diagnostic_context(system=system)
    (result,) = check_default_gateway(ctx)
    assert result.severity == Severity.OK


def test_gateway_warning_when_missing() -> None:
    system = make_system_context(**_APT_DEBIAN, network=NetworkInfo(default_gateway=None))
    ctx = make_diagnostic_context(system=system)
    (result,) = check_default_gateway(ctx)
    assert result.severity == Severity.WARNING


def test_dns_configured_ok() -> None:
    system = make_system_context(**_APT_DEBIAN, network=NetworkInfo(dns_servers=("1.1.1.1",)))
    ctx = make_diagnostic_context(system=system)
    (result,) = check_dns_configured(ctx)
    assert result.severity == Severity.OK


def test_dns_configured_warning_when_none() -> None:
    system = make_system_context(**_APT_DEBIAN, network=NetworkInfo(dns_servers=()))
    ctx = make_diagnostic_context(system=system)
    (result,) = check_dns_configured(ctx)
    assert result.severity == Severity.WARNING


def test_dns_resolution_info_when_not_tested() -> None:
    ctx = make_diagnostic_context(dns_resolution_ok=None)
    (result,) = check_dns_resolution(ctx)
    assert result.severity == Severity.INFO


def test_dns_resolution_ok_when_true() -> None:
    ctx = make_diagnostic_context(dns_resolution_ok=True)
    (result,) = check_dns_resolution(ctx)
    assert result.severity == Severity.OK


def test_dns_resolution_error_when_false() -> None:
    ctx = make_diagnostic_context(dns_resolution_ok=False)
    (result,) = check_dns_resolution(ctx)
    assert result.severity == Severity.ERROR
    assert result.recommendation is not None


def test_internet_ok_when_reachable() -> None:
    system = make_system_context(**_APT_DEBIAN, capabilities=_caps(internet_access=True))
    ctx = make_diagnostic_context(system=system)
    (result,) = check_internet_connectivity(ctx)
    assert result.severity == Severity.OK


def test_internet_warning_when_unreachable() -> None:
    system = make_system_context(**_APT_DEBIAN, capabilities=_caps(internet_access=False))
    ctx = make_diagnostic_context(system=system)
    (result,) = check_internet_connectivity(ctx)
    assert result.severity == Severity.WARNING


def test_the_spec_example_scenario_dns_failure_with_raw_connectivity() -> None:
    """Mirrors spec §18's exact example: raw connectivity fine, DNS resolution failing."""
    system = make_system_context(**_APT_DEBIAN, capabilities=_caps(internet_access=True))
    ctx = make_diagnostic_context(system=system, dns_resolution_ok=False)
    internet_result = check_internet_connectivity(ctx)[0]
    dns_result = check_dns_resolution(ctx)[0]
    assert internet_result.severity == Severity.OK
    assert dns_result.severity == Severity.ERROR
