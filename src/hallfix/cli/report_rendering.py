"""TXT/HTML rendering for ``hallfix report`` (spec §55). JSON needs no
dedicated renderer — ``dataclasses.asdict`` + ``json.dumps`` is the same
pattern used by every other ``--json`` command in this CLI.
"""

from __future__ import annotations

from html import escape

from hallfix.domain.models.report import ManagedToolSummary, Report

_MiB = 1024**3


def render_txt(report: Report) -> str:
    system = report.system
    lines: list[str] = []
    lines.append("HALLFIX SYSTEM REPORT")
    lines.append(f"Generated: {report.generated_at.isoformat()}")
    lines.append("")

    lines.append("SYSTEM INFORMATION")
    lines.append(f"OS: {system.distribution.pretty_name or system.distribution.id}")
    lines.append(f"Kernel: {system.kernel}")
    lines.append(f"Architecture: {system.architecture}")
    lines.append(f"Environment: {system.environment.kind.value}")
    lines.append(f"Hostname: {system.hostname}")
    lines.append("")

    lines.append("HARDWARE")
    lines.append(
        f"CPU: {system.cpu.model or 'unknown'} ({system.cpu.cores}c/{system.cpu.threads}t)"
    )
    lines.append(f"RAM: {system.memory.total_bytes / _MiB:.1f} GiB total")
    for fs in system.disk.filesystems:
        if fs.filesystem_type == "squashfs":  # see docs/architecture.md: always ~100% by design
            continue
        lines.append(f"Disk {fs.mount_point}: {fs.usage_percent}% used ({fs.filesystem_type})")
    lines.append("")

    lines.append("NETWORK")
    for iface in system.network.interfaces:
        addresses = ", ".join(iface.ipv4_addresses + iface.ipv6_addresses) or "no address"
        lines.append(f"{iface.name}: {addresses}")
    lines.append(f"Default gateway: {system.network.default_gateway or 'none'}")
    lines.append(f"DNS servers: {', '.join(system.network.dns_servers) or 'none configured'}")
    lines.append("")

    lines.append("CAPABILITIES")
    caps = system.capabilities
    lines.append(f"Package manager: {system.package_manager.kind.value}")
    lines.append(f"systemd: {caps.systemd}  sudo: {caps.sudo}  internet: {caps.internet_access}")
    lines.append("")

    lines.append(f"MANAGED TOOLS ({len(report.managed_tools)})")
    for tool in report.managed_tools:
        origin = "installed by Hallfix" if tool.installed_by_hallfix else "already present"
        state = f"found (v{tool.installed_version})" if tool.executable_found else "not found"
        lines.append(f"{tool.tool_id}: {origin}, {state}")
    lines.append("")

    lines.append(f"DETECTED ISSUES ({len(report.warnings) + len(report.issues)})")
    for result in (*report.issues, *report.warnings):
        lines.append(f"[{result.severity.value}] {result.title}: {result.description}")
    lines.append("")

    if report.recommendations:
        lines.append("RECOMMENDATIONS")
        for recommendation in report.recommendations:
            lines.append(f"- {recommendation}")
        lines.append("")

    lines.append(f"RECENT OPERATIONS ({len(report.recent_operations)})")
    for op in report.recent_operations:
        summary = "dry-run" if op.dry_run else f"{op.succeeded_count} ok, {op.failed_count} failed"
        lines.append(f"{op.id}  {op.command}  ({summary})")
    lines.append("")

    lines.append(f"Overall health: {report.health.value}")
    return "\n".join(lines) + "\n"


def render_html(report: Report) -> str:
    system = report.system

    def _rows(items: list[tuple[str, str]]) -> str:
        return "\n".join(f"<tr><th>{escape(k)}</th><td>{escape(v)}</td></tr>" for k, v in items)

    def _list(items: list[str]) -> str:
        if not items:
            return "<p><em>None.</em></p>"
        return "<ul>" + "".join(f"<li>{escape(i)}</li>" for i in items) + "</ul>"

    system_rows = _rows(
        [
            ("OS", system.distribution.pretty_name or system.distribution.id),
            ("Kernel", system.kernel),
            ("Architecture", system.architecture),
            ("Environment", system.environment.kind.value),
            ("Hostname", system.hostname),
            ("CPU", f"{system.cpu.model or 'unknown'} ({system.cpu.cores}c/{system.cpu.threads}t)"),
            ("RAM", f"{system.memory.total_bytes / _MiB:.1f} GiB total"),
            ("Package manager", system.package_manager.kind.value),
        ]
    )

    def _tool_state(t: ManagedToolSummary) -> str:
        if not t.executable_found:
            return "not found"
        if t.installed_version:
            return f"found v{t.installed_version}"
        return "found"

    tools = [
        f"{t.tool_id}: {'installed by Hallfix' if t.installed_by_hallfix else 'already present'}, "
        f"{_tool_state(t)}"
        for t in report.managed_tools
    ]
    issues = [
        f"[{r.severity.value}] {r.title}: {r.description}"
        for r in (*report.issues, *report.warnings)
    ]
    operations = [
        f"{op.id}  {op.command}  "
        f"({'dry-run' if op.dry_run else f'{op.succeeded_count} ok, {op.failed_count} failed'})"
        for op in report.recent_operations
    ]

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Hallfix System Report</title>
<style>
  body {{
    font-family: -apple-system, sans-serif; max-width: 860px; margin: 2rem auto;
    padding: 0 1rem; color: #1a1a1a;
  }}
  h1 {{ font-size: 1.4rem; }}
  h2 {{
    font-size: 1.1rem; margin-top: 2rem; border-bottom: 1px solid #ddd;
    padding-bottom: 0.25rem;
  }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ text-align: left; padding: 0.3rem 0.6rem; border-bottom: 1px solid #eee; }}
  th {{ width: 12rem; color: #555; font-weight: 600; }}
  .health {{
    display: inline-block; padding: 0.2rem 0.6rem; border-radius: 0.3rem;
    font-weight: 600;
  }}
  .health-HEALTHY {{ background: #d4edda; color: #155724; }}
  .health-DEGRADED {{ background: #fff3cd; color: #856404; }}
  .health-UNHEALTHY, .health-CRITICAL {{ background: #f8d7da; color: #721c24; }}
</style>
</head>
<body>
<h1>Hallfix System Report</h1>
<p>Generated: {escape(report.generated_at.isoformat())}</p>
<p>Overall health:
  <span class="health health-{escape(report.health.value)}">{escape(report.health.value)}</span>
</p>

<h2>System Information</h2>
<table>{system_rows}</table>

<h2>Managed Tools ({len(report.managed_tools)})</h2>
{_list(tools)}

<h2>Detected Issues ({len(issues)})</h2>
{_list(issues)}

<h2>Recommendations</h2>
{_list(list(report.recommendations))}

<h2>Recent Operations ({len(report.recent_operations)})</h2>
{_list(operations)}
</body>
</html>
"""
