"""Hallfix — Safe Linux System Doctor & Environment Manager."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("hallfix")
except PackageNotFoundError:  # pragma: no cover - only when running from source, uninstalled
    __version__ = "0.0.0"
