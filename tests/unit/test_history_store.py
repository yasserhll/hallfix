from __future__ import annotations

from pathlib import Path

from hallfix.domain.models.history import ActionOutcome
from hallfix.infrastructure.state.history_store import HistoryStore


def test_list_all_empty_when_no_file(tmp_path: Path) -> None:
    store = HistoryStore(path=tmp_path / "history.jsonl")
    assert store.list_all() == ()


def test_append_assigns_sequential_ids(tmp_path: Path) -> None:
    store = HistoryStore(path=tmp_path / "history.jsonl")
    first = store.append(
        command="tool install git",
        plan_id="HF-PLAN-1",
        plan_description="d",
        dry_run=False,
        plan_reversible=True,
    )
    second = store.append(
        command="tool install curl",
        plan_id="HF-PLAN-2",
        plan_description="d",
        dry_run=False,
        plan_reversible=True,
    )
    assert first.id == "HF-001"
    assert second.id == "HF-002"


def test_append_and_list_round_trips(tmp_path: Path) -> None:
    store = HistoryStore(path=tmp_path / "history.jsonl")
    store.append(
        command="tool install git",
        plan_id="HF-PLAN-1",
        plan_description="Install Git",
        dry_run=False,
        plan_reversible=True,
        action_outcomes=(
            ActionOutcome(
                action_type="INSTALL_PACKAGE", succeeded=True, already_satisfied=False, message="ok"
            ),
        ),
    )
    records = store.list_all()
    assert len(records) == 1
    record = records[0]
    assert record.command == "tool install git"
    assert record.action_outcomes[0].succeeded is True
    assert record.succeeded_count == 1
    assert record.failed_count == 0


def test_get_finds_by_id(tmp_path: Path) -> None:
    store = HistoryStore(path=tmp_path / "history.jsonl")
    store.append(
        command="a", plan_id="p1", plan_description="d", dry_run=False, plan_reversible=True
    )
    store.append(
        command="b", plan_id="p2", plan_description="d", dry_run=False, plan_reversible=True
    )
    record = store.get("HF-002")
    assert record is not None
    assert record.command == "b"


def test_get_returns_none_for_unknown_id(tmp_path: Path) -> None:
    store = HistoryStore(path=tmp_path / "history.jsonl")
    assert store.get("HF-999") is None


def test_redacts_secrets_in_command_and_message(tmp_path: Path) -> None:
    store = HistoryStore(path=tmp_path / "history.jsonl")
    store.append(
        command="tool install git --token=hunter2secret",
        plan_id="p1",
        plan_description="d",
        dry_run=False,
        plan_reversible=True,
        action_outcomes=(
            ActionOutcome(
                action_type="INSTALL_PACKAGE",
                succeeded=True,
                already_satisfied=False,
                message="password=hunter2secret",
            ),
        ),
    )
    raw_content = (tmp_path / "history.jsonl").read_text(encoding="utf-8")
    assert "hunter2secret" not in raw_content
    assert "REDACTED" in raw_content


def test_skips_corrupt_trailing_line(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    store = HistoryStore(path=path)
    store.append(
        command="a", plan_id="p1", plan_description="d", dry_run=False, plan_reversible=True
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"id": "HF-002", "incomplete\n')  # simulated crash mid-write

    records = store.list_all()
    assert len(records) == 1
    assert records[0].command == "a"


def test_blank_lines_are_ignored(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    store = HistoryStore(path=path)
    store.append(
        command="a", plan_id="p1", plan_description="d", dry_run=False, plan_reversible=True
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n\n")
    assert len(store.list_all()) == 1


def test_next_id_accounts_for_existing_records_on_fresh_store_instance(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    HistoryStore(path=path).append(
        command="a", plan_id="p1", plan_description="d", dry_run=False, plan_reversible=True
    )
    second_record = HistoryStore(path=path).append(
        command="b", plan_id="p2", plan_description="d", dry_run=False, plan_reversible=True
    )
    assert second_record.id == "HF-002"
