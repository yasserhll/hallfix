"""Tool verification (spec §26): package transaction success is not enough.

Runs the tool's declared ``version_command`` through the injected
``CommandRunner`` — a missing executable surfaces as exit code 127 (see
``SubprocessCommandRunner``'s ``FileNotFoundError`` handling), which this
module reads as "not found" rather than treating it as a generic failure.
Read-only: never installs, never modifies anything.
"""

from __future__ import annotations

import re

from hallfix.domain.models.command import CommandSpec
from hallfix.domain.models.tool import ToolDefinition, ToolVerificationResult
from hallfix.infrastructure.commands.runner import CommandRunner
from hallfix.utils.version import meets_minimum

_NOT_FOUND_EXIT_CODE = 127
_DEFAULT_VERSION_PATTERN = re.compile(r"(\d+\.\d+(?:\.\d+)?)")


def _extract_version(text: str, pattern: str | None) -> str | None:
    regex = re.compile(pattern) if pattern else _DEFAULT_VERSION_PATTERN
    match = regex.search(text)
    if not match:
        return None
    return match.group(1) if match.groups() else match.group(0)


class ToolVerifier:
    def __init__(self, *, command_runner: CommandRunner) -> None:
        self._command_runner = command_runner

    def verify(self, tool: ToolDefinition) -> ToolVerificationResult:
        if tool.verification is None or tool.verification.version_command is None:
            return ToolVerificationResult(
                tool_id=tool.id,
                executable_found=False,
                installed_version=None,
                meets_minimum_version=None,
                meets_recommended_version=None,
            )

        result = self._command_runner.run(
            CommandSpec(argv=tool.verification.version_command, timeout_seconds=10.0)
        )

        if result.exit_code == _NOT_FOUND_EXIT_CODE:
            return ToolVerificationResult(
                tool_id=tool.id,
                executable_found=False,
                installed_version=None,
                meets_minimum_version=None,
                meets_recommended_version=None,
            )

        combined_output = result.stdout + result.stderr
        version = _extract_version(combined_output, tool.verification.version_regex)

        return ToolVerificationResult(
            tool_id=tool.id,
            executable_found=True,
            installed_version=version,
            meets_minimum_version=meets_minimum(version, tool.minimum_version),
            meets_recommended_version=meets_minimum(version, tool.recommended_version),
        )
