from __future__ import annotations

from hallfix.detectors.tool_verifier import ToolVerifier
from hallfix.domain.models.tool import ToolDefinition, VerificationSpec
from tests.fixtures.fake_command_runner import FakeCommandRunner, ok_result


def _tool(**overrides: object) -> ToolDefinition:
    defaults: dict[str, object] = {
        "id": "git",
        "name": "Git",
        "description": "VCS",
        "category": "essentials",
        "verification": VerificationSpec(
            executable="git", version_command=("git", "--version"), version_regex=None
        ),
        "minimum_version": None,
        "recommended_version": None,
    }
    defaults.update(overrides)
    return ToolDefinition(**defaults)  # type: ignore[arg-type]


def test_executable_found_and_version_extracted() -> None:
    runner = FakeCommandRunner()
    runner.stub(("git", "--version"), ok_result(("git", "--version"), "git version 2.43.0"))
    result = ToolVerifier(command_runner=runner).verify(_tool())
    assert result.executable_found
    assert result.installed_version == "2.43.0"


def test_executable_not_found_reports_false() -> None:
    runner = FakeCommandRunner()
    runner.stub(("git", "--version"), ok_result(("git", "--version"), "", exit_code=127))
    result = ToolVerifier(command_runner=runner).verify(_tool())
    assert not result.executable_found
    assert result.installed_version is None


def test_custom_version_regex_used() -> None:
    runner = FakeCommandRunner()
    runner.stub(("git", "--version"), ok_result(("git", "--version"), "gitVERSION=2.43.0-custom"))
    tool = _tool(
        verification=VerificationSpec(
            executable="git",
            version_command=("git", "--version"),
            version_regex=r"VERSION=(\d+\.\d+\.\d+)",
        )
    )
    result = ToolVerifier(command_runner=runner).verify(tool)
    assert result.installed_version == "2.43.0"


def test_meets_minimum_version_computed() -> None:
    runner = FakeCommandRunner()
    runner.stub(("git", "--version"), ok_result(("git", "--version"), "git version 2.43.0"))
    tool = _tool(minimum_version="2.30", recommended_version="2.50")
    result = ToolVerifier(command_runner=runner).verify(tool)
    assert result.meets_minimum_version is True
    assert result.meets_recommended_version is False


def test_no_verification_spec_reports_not_found() -> None:
    runner = FakeCommandRunner()
    tool = _tool(verification=None)
    result = ToolVerifier(command_runner=runner).verify(tool)
    assert not result.executable_found
    assert runner.calls == []


def test_no_version_command_reports_not_found() -> None:
    runner = FakeCommandRunner()
    tool = _tool(verification=VerificationSpec(executable="git", version_command=None))
    result = ToolVerifier(command_runner=runner).verify(tool)
    assert not result.executable_found
    assert runner.calls == []
