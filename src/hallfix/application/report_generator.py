"""ReportGenerator (spec §55): assembles a ``Report`` from real I/O.

Nothing here detects anything new — it reuses ``run_doctor`` (Phase 9),
``StateStore`` (Phase 7), ``HistoryStore`` (Phase 7/11), and
``ToolVerifier`` (Phase 4) exactly as they already exist. "Never include
secrets" (spec §55) is satisfied structurally, not by an extra redaction
pass here: ``HistoryStore`` already redacts free text at write time,
``StateStore`` only ever holds booleans/tool ids, and ``SystemContext`` is
detection data — there is nothing secret-shaped in any of these sources
for a report to accidentally surface.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from hallfix.application.doctor import build_diagnostic_context
from hallfix.detectors.dns_resolution import DnsResolutionChecker, check_dns_resolution
from hallfix.detectors.internet import ConnectivityChecker, check_internet_connectivity
from hallfix.detectors.tool_verifier import ToolVerifier
from hallfix.domain.diagnostics.engine import DiagnosticEngine, aggregate_health
from hallfix.domain.models.report import ManagedToolSummary, Report
from hallfix.infrastructure.commands.runner import CommandRunner
from hallfix.infrastructure.registries.tool_registry_loader import load_tool_registry
from hallfix.infrastructure.state.history_store import HistoryStore
from hallfix.infrastructure.state.store import StateStore

_DEFAULT_HISTORY_LIMIT = 10


def build_report(
    *,
    command_runner: CommandRunner,
    root: Path = Path("/"),
    connectivity_checker: ConnectivityChecker = check_internet_connectivity,
    dns_checker: DnsResolutionChecker = check_dns_resolution,
    history_limit: int = _DEFAULT_HISTORY_LIMIT,
    now: datetime | None = None,
) -> Report:
    # Build the context once and run the engine directly, rather than
    # calling run_doctor() (which would build an equivalent context a
    # second time internally) and build_diagnostic_context() separately —
    # that would double every read this does (detection, lock check,
    # dpkg --audit, tool verification, DNS probe).
    context = build_diagnostic_context(
        command_runner=command_runner,
        root=root,
        connectivity_checker=connectivity_checker,
        dns_checker=dns_checker,
    )
    diagnostics = DiagnosticEngine().run(context)
    health = aggregate_health(diagnostics)

    state = StateStore().load()
    tool_registry = load_tool_registry()
    verifier = ToolVerifier(command_runner=command_runner)
    managed_tools = []
    for tool_id, tool_state in sorted(state.tools.items()):
        tool = tool_registry.get(tool_id)
        verification = verifier.verify(tool) if tool is not None else None
        managed_tools.append(
            ManagedToolSummary(
                tool_id=tool_id,
                installed_by_hallfix=tool_state.installed_by_hallfix,
                present_before_hallfix=tool_state.present_before_hallfix,
                executable_found=verification.executable_found if verification else False,
                installed_version=verification.installed_version if verification else None,
            )
        )

    all_operations = HistoryStore().list_all()
    recent_operations = tuple(reversed(all_operations[-history_limit:]))

    return Report(
        generated_at=now or datetime.now(UTC),
        system=context.system,
        diagnostics=diagnostics,
        health=health,
        managed_tools=tuple(managed_tools),
        recent_operations=recent_operations,
    )
