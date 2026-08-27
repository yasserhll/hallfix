from __future__ import annotations

from hallfix.domain.models.command import CommandResult
from hallfix.domain.models.enums import RiskLevel, Severity, SupportLevel


def test_command_result_succeeded_true_on_zero_exit() -> None:
    result = CommandResult(argv=("true",), exit_code=0, stdout="", stderr="", duration_seconds=0.01)
    assert result.succeeded


def test_command_result_succeeded_false_on_nonzero_exit() -> None:
    result = CommandResult(
        argv=("false",), exit_code=1, stdout="", stderr="", duration_seconds=0.01
    )
    assert not result.succeeded


def test_command_result_succeeded_false_when_timed_out() -> None:
    result = CommandResult(
        argv=("sleep",),
        exit_code=0,
        stdout="",
        stderr="",
        duration_seconds=1.0,
        timed_out=True,
    )
    assert not result.succeeded


def test_enums_have_expected_members() -> None:
    assert {s.value for s in Severity} == {"INFO", "OK", "WARNING", "ERROR", "CRITICAL"}
    assert {r.value for r in RiskLevel} == {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert {s.value for s in SupportLevel} == {
        "SUPPORTED",
        "EXPERIMENTAL",
        "DETECTED_ONLY",
        "UNSUPPORTED",
    }
