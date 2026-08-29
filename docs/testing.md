# Testing

```bash
pytest                      # everything, including integration
pytest -m "not integration" # unit only — faster inner loop
pytest --cov=src/hallfix --cov-report=term-missing
```

## `tests/unit/` — never touches the real system

Every dependency that could touch the host is injected: `FakeCommandRunner`
(`tests/fixtures/fake_command_runner.py`, stub argv → `CommandResult`,
asserts on `.calls` when a command must never run), `ToolRegistry([...])`
built from inline dicts rather than the real YAML, `StateStore`/
`SnapshotStore`/`HistoryStore` pointed at `tmp_path`, and
`make_system_context()`/`diagnostic_context_factory.py` for synthetic
`SystemContext`/diagnostic contexts. Every test in `tests/conftest.py`
also gets `XDG_CONFIG_HOME`/`XDG_STATE_HOME` redirected to a per-test
`tmp_path` automatically (autouse fixture) — real
`~/.config/hallfix`/`~/.local/state/hallfix` are never touched even by a
test that forgets to inject a store explicitly.

## `tests/integration/` — real host, marked explicitly

`pytestmark = pytest.mark.integration` at the top of each file. Real
detection, real registries, real reads against whatever machine CI or you
are running on — but only ever read-only or `--dry-run` invocations of
mutating commands (`tool install`, `profile install`, `update system`,
...). **Never a real package install/remove/upgrade** — that would modify
the developer's workstation or the CI runner unpredictably (spec §70:
"Never run destructive integration tests against the developer's
workstation").

## `tests/fake_systems/` — spec §71's Fake System Layer

Simulated root filesystems (`etc/os-release`, `proc/`, `sys/`, fake
`usr/bin/{apt-get,dnf,pacman,sudo}` marker files) for `ubuntu`, `debian`,
`fedora`, `arch`, `wsl_ubuntu`, `docker_container`, `vm_qemu`,
`no_systemd` — lets detection/capability code be tested against every
target environment without needing every distribution physically. Empty
directories are given a `.gitkeep` since git doesn't track them — a
missing one silently breaks capability detection on a fresh checkout
even though it passes locally (this exact bug was Phase 14's CI failure).

## What's covered

Per spec §70: OS/distribution/WSL/container/capability/architecture
detection, package manager detection and mappings, tool/profile registry
validation, the Planner and every `ExecutionPlan` derived property,
`SafetyPolicy`, dry-run, `StateStore`/`HistoryStore` atomicity and crash
safety, version comparison, backup/rollback planning, log redaction, CLI
parsing and rendering. Current coverage: ~92% (`pytest --cov`).
