"""Loads the default ``ToolRegistry`` from ``src/hallfix/data/tools/``."""

from __future__ import annotations

from pathlib import Path

from hallfix.domain.registries.tool_registry import ToolRegistry
from hallfix.infrastructure.registries.yaml_loader import load_yaml_documents

DEFAULT_TOOLS_DIR = Path(__file__).resolve().parents[2] / "data" / "tools"


def load_tool_registry(directory: Path = DEFAULT_TOOLS_DIR) -> ToolRegistry:
    return ToolRegistry(load_yaml_documents(directory))
