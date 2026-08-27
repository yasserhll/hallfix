from __future__ import annotations

from pathlib import Path

import pytest

from hallfix.domain.exceptions import RegistryError
from hallfix.infrastructure.registries.yaml_loader import load_yaml_documents


def test_loads_multiple_yaml_files_sorted_by_name(tmp_path: Path) -> None:
    (tmp_path / "b.yaml").write_text("id: b\n", encoding="utf-8")
    (tmp_path / "a.yaml").write_text("id: a\n", encoding="utf-8")
    docs = load_yaml_documents(tmp_path)
    assert [d["id"] for d in docs] == ["a", "b"]


def test_missing_directory_returns_empty_list(tmp_path: Path) -> None:
    assert load_yaml_documents(tmp_path / "does-not-exist") == []


def test_empty_yaml_file_is_skipped(tmp_path: Path) -> None:
    (tmp_path / "empty.yaml").write_text("", encoding="utf-8")
    assert load_yaml_documents(tmp_path) == []


def test_non_mapping_top_level_raises_registry_error(tmp_path: Path) -> None:
    (tmp_path / "list.yaml").write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(RegistryError):
        load_yaml_documents(tmp_path)


def test_invalid_yaml_raises_registry_error(tmp_path: Path) -> None:
    (tmp_path / "broken.yaml").write_text("id: [unterminated\n", encoding="utf-8")
    with pytest.raises(RegistryError):
        load_yaml_documents(tmp_path)


def test_ignores_non_yaml_files(tmp_path: Path) -> None:
    (tmp_path / "readme.md").write_text("not yaml\n", encoding="utf-8")
    (tmp_path / "tool.yaml").write_text("id: tool\n", encoding="utf-8")
    docs = load_yaml_documents(tmp_path)
    assert len(docs) == 1
    assert docs[0]["id"] == "tool"
