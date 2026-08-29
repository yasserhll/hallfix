"""Builds a ``SnapshotRecord`` (spec §10) from real system/tool reads.

Lives in ``application/`` for the same reason ``Planner``/``Executor`` do:
it orchestrates domain data (``StateStore``'s ownership records) with real
I/O (``ToolVerifier``) — the domain model itself stays I/O-free.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from hallfix import __version__
from hallfix.detectors.tool_verifier import ToolVerifier
from hallfix.domain.models.snapshot import SnapshotRecord, SnapshotToolEntry
from hallfix.domain.models.system import SystemContext
from hallfix.domain.registries.tool_registry import ToolRegistry
from hallfix.infrastructure.commands.runner import CommandRunner
from hallfix.infrastructure.state.store import StateStore


def _default_clock() -> datetime:
    return datetime.now(UTC)


def _new_snapshot_id() -> str:
    return f"HF-SNAP-{uuid.uuid4().hex[:8]}"


def build_snapshot(
    context: SystemContext,
    tool_registry: ToolRegistry,
    state_store: StateStore,
    *,
    command_runner: CommandRunner,
    id_factory: Callable[[], str] = _new_snapshot_id,
    clock: Callable[[], datetime] = _default_clock,
) -> SnapshotRecord:
    verifier = ToolVerifier(command_runner=command_runner)
    state = state_store.load()

    entries: list[SnapshotToolEntry] = []
    for tool_id, tool_state in sorted(state.tools.items()):
        if not tool_state.installed_by_hallfix:
            continue
        tool = tool_registry.get(tool_id)
        installed_version = verifier.verify(tool).installed_version if tool is not None else None
        entries.append(
            SnapshotToolEntry(
                tool_id=tool_id,
                installed_version=installed_version,
                installed_for=tool_state.installed_for,
            )
        )

    return SnapshotRecord(
        id=id_factory(),
        created_at=clock(),
        hallfix_version=__version__,
        distribution_id=context.distribution.id,
        distribution_version=context.distribution.version_id,
        architecture=context.architecture,
        kernel=context.kernel,
        managed_tools=tuple(entries),
    )
