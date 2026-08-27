"""Loads the default ``ProfileRegistry`` from ``src/hallfix/data/profiles/``."""

from __future__ import annotations

from pathlib import Path

from hallfix.domain.registries.profile_registry import ProfileRegistry
from hallfix.infrastructure.registries.yaml_loader import load_yaml_documents

DEFAULT_PROFILES_DIR = Path(__file__).resolve().parents[2] / "data" / "profiles"


def load_profile_registry(directory: Path = DEFAULT_PROFILES_DIR) -> ProfileRegistry:
    return ProfileRegistry(load_yaml_documents(directory))
