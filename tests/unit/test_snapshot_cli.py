"""Unit: exercises ``hallfix snapshot`` branches that real-host integration
tests can't reach deterministically (this dev host isn't Hallfix-managed,
so the "has managed tools" table branch never fires there) or shouldn't
(registry errors)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from rich.console import Console
from typer.testing import CliRunner

from hallfix.cli.app import app
from hallfix.cli.commands.snapshot import _render
from hallfix.domain.exceptions import RegistryError
from hallfix.domain.models.snapshot import SnapshotRecord, SnapshotToolEntry
from hallfix.domain.models.system import DistributionFamily, PackageManagerKind
from tests.fixtures.system_context_factory import make_system_context

runner = CliRunner()

_CONTEXT = make_system_context(
    manager_kind=PackageManagerKind.APT, family=DistributionFamily.DEBIAN
)


def test_render_shows_no_managed_tools_message() -> None:
    record = SnapshotRecord(
        id="HF-SNAP-1",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        hallfix_version="0.1.2",
        distribution_id="test",
        distribution_version=None,
        architecture="x86_64",
        kernel="6.0.0",
    )
    console = Console(record=True, no_color=True, width=100)
    _render(console, record, _CONTEXT, Path("HF-SNAP-1.json"))
    output = console.export_text()
    assert "No Hallfix-managed tools recorded yet." in output


def test_render_shows_managed_tools_table() -> None:
    record = SnapshotRecord(
        id="HF-SNAP-2",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        hallfix_version="0.1.2",
        distribution_id="test",
        distribution_version=None,
        architecture="x86_64",
        kernel="6.0.0",
        managed_tools=(
            SnapshotToolEntry(tool_id="git", installed_version="2.45.0", installed_for=("dev",)),
        ),
    )
    console = Console(record=True, no_color=True, width=100)
    _render(console, record, _CONTEXT, Path("HF-SNAP-2.json"))
    output = console.export_text()
    assert "git" in output
    assert "2.45.0" in output
    assert "dev" in output


def test_snapshot_registry_error_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise() -> None:
        raise RegistryError("bad tool data")

    monkeypatch.setattr("hallfix.cli.commands.snapshot.load_tool_registry", _raise)
    result = runner.invoke(app, ["snapshot"])
    assert result.exit_code == 2
    assert "Tool registry error" in result.stderr
