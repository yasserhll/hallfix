"""Development-environment diagnostics (spec §40).

Git/Docker/SSH absence is never WARNING/ERROR — spec §40: "Do not
penalize a machine because optional software is absent." Presence is
INFO (nice to note, not a health signal); absence is INFO too, just
saying so.
"""

from __future__ import annotations

from hallfix.domain.diagnostics.context import DiagnosticContext
from hallfix.domain.models.diagnostic import DiagnosticResult
from hallfix.domain.models.enums import Severity


def _tool_presence_check(
    ctx: DiagnosticContext, *, tool_id: str, diagnostic_id: str, title: str
) -> tuple[DiagnosticResult, ...]:
    verification = ctx.tool_verifications.get(tool_id)
    if verification is None or not verification.executable_found:
        return (
            DiagnosticResult(
                id=diagnostic_id,
                category="development",
                severity=Severity.INFO,
                title=title,
                description="Not installed.",
            ),
        )
    version = verification.installed_version or "unknown version"
    return (
        DiagnosticResult(
            id=diagnostic_id,
            category="development",
            severity=Severity.OK,
            title=title,
            description=f"Installed ({version}).",
        ),
    )


def check_git(ctx: DiagnosticContext) -> tuple[DiagnosticResult, ...]:
    return _tool_presence_check(ctx, tool_id="git", diagnostic_id="development.git", title="Git")


def check_docker(ctx: DiagnosticContext) -> tuple[DiagnosticResult, ...]:
    return _tool_presence_check(
        ctx, tool_id="docker", diagnostic_id="development.docker", title="Docker"
    )


def check_ssh(ctx: DiagnosticContext) -> tuple[DiagnosticResult, ...]:
    return _tool_presence_check(ctx, tool_id="ssh", diagnostic_id="development.ssh", title="SSH")


def check_environment_variables(ctx: DiagnosticContext) -> tuple[DiagnosticResult, ...]:
    missing = [name for name in ("HOME", "PATH", "SHELL") if not ctx.env.get(name)]
    if missing:
        return (
            DiagnosticResult(
                id="development.environment_variables",
                category="development",
                severity=Severity.WARNING,
                title="Environment variables",
                description=f"Missing or empty: {', '.join(missing)}.",
                recommendation="Check shell profile/session environment setup.",
            ),
        )
    return (
        DiagnosticResult(
            id="development.environment_variables",
            category="development",
            severity=Severity.OK,
            title="Environment variables",
            description="HOME, PATH, and SHELL are set.",
        ),
    )
