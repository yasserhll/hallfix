from __future__ import annotations

import socket
from contextlib import contextmanager
from typing import Any

import pytest

from hallfix.detectors.internet import check_internet_connectivity


@contextmanager
def _fake_socket() -> Any:
    yield object()


def test_returns_true_when_connection_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "create_connection", lambda *a, **kw: _fake_socket())
    assert check_internet_connectivity() is True


def test_returns_false_on_os_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*args: object, **kwargs: object) -> None:
        raise OSError("network unreachable")

    monkeypatch.setattr(socket, "create_connection", _raise)
    assert check_internet_connectivity() is False


def test_returns_false_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        socket, "create_connection", lambda *a, **kw: (_ for _ in ()).throw(TimeoutError())
    )
    assert check_internet_connectivity() is False
