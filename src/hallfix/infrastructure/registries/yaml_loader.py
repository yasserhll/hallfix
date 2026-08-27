"""Reads registry YAML files from disk into raw dicts.

Deliberately the only I/O in the tool/profile registry pipeline — everything
downstream (``domain/registries/*``) parses and validates already-loaded
data, per the domain layer's zero-I/O rule.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from hallfix.domain.exceptions import RegistryError


def load_yaml_documents(directory: Path) -> list[dict[str, Any]]:
    if not directory.is_dir():
        return []

    documents: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            msg = f"invalid YAML in {path}: {exc}"
            raise RegistryError(msg) from exc
        if data is None:
            continue
        if not isinstance(data, dict):
            msg = f"{path}: expected a YAML mapping at the top level, got {type(data).__name__}"
            raise RegistryError(msg)
        documents.append(data)
    return documents
