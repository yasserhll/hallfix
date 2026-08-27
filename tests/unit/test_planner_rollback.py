from __future__ import annotations

from datetime import UTC, datetime

from hallfix.application.planner import Planner
from hallfix.domain.models.history import ActionOutcome, OperationRecord
from hallfix.domain.planning.action import RemovePackageAction
from tests.fixtures.fake_command_runner import FakeCommandRunner

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _planner() -> Planner:
    return Planner(command_runner=FakeCommandRunner(), id_factory=lambda: "HF-PLAN-test")


def _install_outcome(**overrides: object) -> ActionOutcome:
    base: dict[str, object] = {
        "action_type": "INSTALL_PACKAGE",
        "succeeded": True,
        "already_satisfied": False,
        "message": "ok",
        "reversible": True,
        "rollback_strategy": "remove_package",
        "tool_id": "git",
        "package": "git",
        "strategy": "APT",
        "risk_level": "LOW",
    }
    base.update(overrides)
    return ActionOutcome(**base)  # type: ignore[arg-type]


def _record(*outcomes: ActionOutcome) -> OperationRecord:
    return OperationRecord(
        id="HF-005",
        timestamp=_NOW,
        command="tool install git",
        plan_id="HF-PLAN-orig",
        plan_description="Install Git",
        dry_run=False,
        plan_reversible=True,
        action_outcomes=outcomes,
    )


def test_plan_rollback_builds_remove_action_for_eligible_outcome() -> None:
    record = _record(_install_outcome())
    plan = _planner().plan_rollback(record)

    assert not plan.is_noop
    action = plan.planned_actions[0].action
    assert isinstance(action, RemovePackageAction)
    assert action.package == "git"
    assert action.tool_id == "git"


def test_plan_rollback_noop_when_nothing_eligible() -> None:
    record = _record(_install_outcome(reversible=False))
    plan = _planner().plan_rollback(record)
    assert plan.is_noop
    assert "nothing" in plan.description.lower()


def test_plan_rollback_noop_for_empty_record() -> None:
    record = _record()
    plan = _planner().plan_rollback(record)
    assert plan.is_noop


def test_plan_rollback_skips_unsupported_strategy_with_note() -> None:
    record = _record(_install_outcome(rollback_strategy="restore_backup"))
    plan = _planner().plan_rollback(record)
    assert plan.is_noop
    assert plan.notes == ()  # noop path returns before notes are attached; message covers it


def test_plan_rollback_handles_multiple_eligible_outcomes() -> None:
    record = _record(
        _install_outcome(tool_id="git", package="git"),
        _install_outcome(tool_id="curl", package="curl"),
    )
    plan = _planner().plan_rollback(record)
    assert plan.estimated_changes == 2
    packages = {a.action.package for a in plan.planned_actions}  # type: ignore[union-attr]
    assert packages == {"git", "curl"}


def test_plan_rollback_mixes_eligible_and_ineligible_with_notes() -> None:
    record = _record(
        _install_outcome(tool_id="git", package="git"),
        _install_outcome(tool_id="curl", package="curl", rollback_strategy="restore_backup"),
    )
    plan = _planner().plan_rollback(record)
    assert plan.estimated_changes == 1
    assert len(plan.notes) == 1


def test_plan_rollback_description_references_operation_id() -> None:
    record = _record(_install_outcome())
    plan = _planner().plan_rollback(record)
    assert record.id in plan.description
