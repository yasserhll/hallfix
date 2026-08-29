from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from hallfix.application.snapshot import build_snapshot
from hallfix.domain.models.state import HallfixState, ToolState
from hallfix.domain.models.system import DistributionFamily, PackageManagerKind
from hallfix.infrastructure.registries.tool_registry_loader import load_tool_registry
from hallfix.infrastructure.state.store import StateStore
from tests.fixtures.fake_command_runner import FakeCommandRunner, ok_result
from tests.fixtures.system_context_factory import make_system_context

_CONTEXT = make_system_context(
    manager_kind=PackageManagerKind.APT, family=DistributionFamily.DEBIAN
)


def _state_store(tmp_path: Path, state: HallfixState) -> StateStore:
    store = StateStore(path=tmp_path / "state.json")
    store.save(state)
    return store


def test_snapshot_includes_only_hallfix_managed_tools(tmp_path: Path) -> None:
    state = HallfixState(
        tools={
            "git": ToolState(
                present_before_hallfix=False, installed_by_hallfix=True, installed_for=("dev",)
            ),
            "curl": ToolState(present_before_hallfix=True, installed_by_hallfix=False),
        }
    )
    runner = FakeCommandRunner()
    runner.stub(("git", "--version"), ok_result(("git", "--version"), "git version 2.45.0"))

    record = build_snapshot(
        _CONTEXT,
        load_tool_registry(),
        _state_store(tmp_path, state),
        command_runner=runner,
        id_factory=lambda: "HF-SNAP-test",
        clock=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert [t.tool_id for t in record.managed_tools] == ["git"]
    assert record.managed_tools[0].installed_version == "2.45.0"
    assert record.managed_tools[0].installed_for == ("dev",)


def test_snapshot_carries_distribution_and_hallfix_version(tmp_path: Path) -> None:
    record = build_snapshot(
        _CONTEXT,
        load_tool_registry(),
        _state_store(tmp_path, HallfixState()),
        command_runner=FakeCommandRunner(),
        id_factory=lambda: "HF-SNAP-test",
    )
    assert record.distribution_id == "test"
    assert record.architecture == "x86_64"
    assert record.kernel == "6.0.0"
    assert record.hallfix_version
    assert record.managed_tools == ()


def test_snapshot_skips_tool_not_in_registry(tmp_path: Path) -> None:
    state = HallfixState(
        tools={
            "totally-not-a-real-tool": ToolState(
                present_before_hallfix=False, installed_by_hallfix=True
            )
        }
    )
    record = build_snapshot(
        _CONTEXT,
        load_tool_registry(),
        _state_store(tmp_path, state),
        command_runner=FakeCommandRunner(),
        id_factory=lambda: "HF-SNAP-test",
    )
    assert record.managed_tools[0].tool_id == "totally-not-a-real-tool"
    assert record.managed_tools[0].installed_version is None
