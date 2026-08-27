from __future__ import annotations

from hallfix.domain.diagnostics.development_checks import (
    check_docker,
    check_environment_variables,
    check_git,
    check_ssh,
)
from hallfix.domain.models.enums import Severity
from hallfix.domain.models.tool import ToolVerificationResult
from tests.fixtures.diagnostic_context_factory import make_diagnostic_context


def _found(version: str = "2.43.0") -> ToolVerificationResult:
    return ToolVerificationResult(
        tool_id="x",
        executable_found=True,
        installed_version=version,
        meets_minimum_version=None,
        meets_recommended_version=None,
    )


def test_git_info_when_absent_never_warning() -> None:
    ctx = make_diagnostic_context(tool_verifications={})
    (result,) = check_git(ctx)
    assert result.severity == Severity.INFO  # absence is never penalized (spec §40)


def test_git_ok_when_present() -> None:
    ctx = make_diagnostic_context(tool_verifications={"git": _found("2.43.0")})
    (result,) = check_git(ctx)
    assert result.severity == Severity.OK
    assert "2.43.0" in result.description


def test_docker_info_when_absent() -> None:
    ctx = make_diagnostic_context(tool_verifications={})
    (result,) = check_docker(ctx)
    assert result.severity == Severity.INFO


def test_ssh_ok_when_present() -> None:
    ctx = make_diagnostic_context(tool_verifications={"ssh": _found("9.6")})
    (result,) = check_ssh(ctx)
    assert result.severity == Severity.OK


def test_environment_variables_ok_when_all_set() -> None:
    ctx = make_diagnostic_context(env={"HOME": "/home/x", "PATH": "/usr/bin", "SHELL": "/bin/bash"})
    (result,) = check_environment_variables(ctx)
    assert result.severity == Severity.OK


def test_environment_variables_warning_when_missing() -> None:
    ctx = make_diagnostic_context(env={"HOME": "/home/x"})
    (result,) = check_environment_variables(ctx)
    assert result.severity == Severity.WARNING
    assert "PATH" in result.description
    assert "SHELL" in result.description
