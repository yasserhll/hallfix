from __future__ import annotations

from datetime import UTC, datetime

from hallfix.domain.models.history import ActionOutcome, OperationRecord

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _outcome(**overrides: object) -> ActionOutcome:
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


def test_rollback_eligible_true_for_successful_reversible_outcome() -> None:
    assert _outcome().rollback_eligible is True


def test_rollback_eligible_false_when_not_succeeded() -> None:
    assert _outcome(succeeded=False).rollback_eligible is False


def test_rollback_eligible_false_when_already_satisfied() -> None:
    assert _outcome(already_satisfied=True).rollback_eligible is False


def test_rollback_eligible_false_when_not_reversible() -> None:
    assert _outcome(reversible=False).rollback_eligible is False


def test_rollback_eligible_false_when_no_strategy() -> None:
    assert _outcome(rollback_strategy=None).rollback_eligible is False


def test_rollback_eligible_defaults_to_false() -> None:
    minimal = ActionOutcome(
        action_type="REMOVE_PACKAGE", succeeded=True, already_satisfied=False, message="ok"
    )
    assert minimal.rollback_eligible is False


def _record(*outcomes: ActionOutcome, dry_run: bool = False) -> OperationRecord:
    return OperationRecord(
        id="HF-001",
        timestamp=_NOW,
        command="tool install git",
        plan_id="HF-PLAN-1",
        plan_description="Install Git",
        dry_run=dry_run,
        plan_reversible=True,
        action_outcomes=outcomes,
    )


def test_rollback_eligible_outcomes_filters_correctly() -> None:
    eligible = _outcome()
    ineligible = _outcome(reversible=False)
    record = _record(eligible, ineligible)
    assert record.rollback_eligible_outcomes == (eligible,)


def test_is_rollback_eligible_true_when_any_outcome_qualifies() -> None:
    record = _record(_outcome())
    assert record.is_rollback_eligible is True


def test_is_rollback_eligible_false_when_none_qualify() -> None:
    record = _record(_outcome(reversible=False))
    assert record.is_rollback_eligible is False


def test_is_rollback_eligible_false_for_dry_run_record_even_with_reversible_outcomes() -> None:
    record = _record(_outcome(), dry_run=True)
    assert record.is_rollback_eligible is False


def test_is_rollback_eligible_false_with_no_outcomes() -> None:
    record = _record()
    assert record.is_rollback_eligible is False
