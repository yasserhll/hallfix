from __future__ import annotations

import socket

import pytest

from hallfix.detectors.dns_resolution import check_dns_resolution


def test_returns_true_when_resolution_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **kw: [("dummy",)])
    assert check_dns_resolution() is True


def test_returns_false_on_os_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*args: object, **kwargs: object) -> None:
        raise OSError("nodename nor servname provided")

    monkeypatch.setattr(socket, "getaddrinfo", _raise)
    assert check_dns_resolution() is False


def test_restores_default_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    original = socket.getdefaulttimeout()
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **kw: [("dummy",)])
    check_dns_resolution(timeout=1.0)
    assert socket.getdefaulttimeout() == original
