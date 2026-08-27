from __future__ import annotations

from pathlib import Path

from hallfix.infrastructure.state.store import StateStore


def test_load_missing_file_returns_empty_state(tmp_path: Path) -> None:
    store = StateStore(path=tmp_path / "state.json")
    state = store.load()
    assert state.tools == {}


def test_record_installed_then_load_round_trips(tmp_path: Path) -> None:
    store = StateStore(path=tmp_path / "state.json")
    store.record_installed("docker")
    state = store.load()
    assert state.tools["docker"].installed_by_hallfix is True
    assert state.tools["docker"].present_before_hallfix is False


def test_record_installed_tracks_profile(tmp_path: Path) -> None:
    store = StateStore(path=tmp_path / "state.json")
    store.record_installed("docker", profile="developer")
    store.record_installed("docker", profile="devops")
    state = store.load()
    assert state.tools["docker"].installed_for == ("developer", "devops")


def test_record_installed_does_not_duplicate_profile(tmp_path: Path) -> None:
    store = StateStore(path=tmp_path / "state.json")
    store.record_installed("docker", profile="developer")
    store.record_installed("docker", profile="developer")
    state = store.load()
    assert state.tools["docker"].installed_for == ("developer",)


def test_record_already_present_does_not_overwrite_hallfix_ownership(tmp_path: Path) -> None:
    store = StateStore(path=tmp_path / "state.json")
    store.record_installed("git")
    store.record_already_present("git")  # must be a no-op
    state = store.load()
    assert state.tools["git"].installed_by_hallfix is True


def test_record_already_present_tracks_new_tool(tmp_path: Path) -> None:
    store = StateStore(path=tmp_path / "state.json")
    store.record_already_present("curl")
    state = store.load()
    assert state.tools["curl"].present_before_hallfix is True
    assert state.tools["curl"].installed_by_hallfix is False


def test_record_removed_deletes_tracked_entry(tmp_path: Path) -> None:
    store = StateStore(path=tmp_path / "state.json")
    store.record_installed("docker")
    store.record_removed("docker")
    state = store.load()
    assert "docker" not in state.tools


def test_record_removed_is_safe_for_untracked_tool(tmp_path: Path) -> None:
    store = StateStore(path=tmp_path / "state.json")
    store.record_removed("never-tracked")  # must not raise
    assert store.load().tools == {}


def test_is_owned_by_hallfix(tmp_path: Path) -> None:
    store = StateStore(path=tmp_path / "state.json")
    store.record_installed("docker")
    store.record_already_present("git")
    assert store.is_owned_by_hallfix("docker") is True
    assert store.is_owned_by_hallfix("git") is False
    assert store.is_owned_by_hallfix("never-seen") is False


def test_save_is_atomic_no_tmp_file_left_behind(tmp_path: Path) -> None:
    store = StateStore(path=tmp_path / "state.json")
    store.record_installed("docker")
    assert (tmp_path / "state.json").is_file()
    assert not (tmp_path / "state.json.tmp").exists()


def test_corrupt_state_file_treated_as_empty(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text("{not valid json", encoding="utf-8")
    store = StateStore(path=state_path)
    assert store.load().tools == {}


def test_non_dict_json_treated_as_empty(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text("[1, 2, 3]", encoding="utf-8")
    store = StateStore(path=state_path)
    assert store.load().tools == {}
