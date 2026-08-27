"""Fake ``CommandRunner`` for unit tests — never touches the real system.

Matches exact argv tuples to canned ``CommandResult``s. Calling with an
unstubbed argv raises ``AssertionError`` rather than silently returning
something plausible-looking, so a test that forgets to stub a call fails
loudly instead of asserting on garbage.
"""

from __future__ import annotations

from hallfix.domain.models.command import CommandResult, CommandSpec


class FakeCommandRunner:
    def __init__(self, responses: dict[tuple[str, ...], CommandResult] | None = None) -> None:
        self._responses = dict(responses or {})
        self.calls: list[CommandSpec] = []

    def stub(self, argv: tuple[str, ...], result: CommandResult) -> None:
        self._responses[argv] = result

    def run(self, spec: CommandSpec) -> CommandResult:
        self.calls.append(spec)
        try:
            return self._responses[spec.argv]
        except KeyError:
            msg = f"FakeCommandRunner: no stubbed response for argv={spec.argv!r}"
            raise AssertionError(msg) from None


def ok_result(argv: tuple[str, ...], stdout: str = "", *, exit_code: int = 0) -> CommandResult:
    return CommandResult(
        argv=argv, exit_code=exit_code, stdout=stdout, stderr="", duration_seconds=0.0
    )
