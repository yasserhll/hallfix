# Changelog

## Unreleased — Phase 7: State & History

- `infrastructure/state/store.py`: `StateStore` — a single JSON snapshot
  under `~/.local/state/hallfix/state.json`, atomic on every save
  (temp-file write + `Path.replace`, same filesystem guaranteed). A
  corrupt/unreadable file is treated as "nothing recorded yet" rather than
  crashing Hallfix (spec §2: fail gracefully). `record_already_present`
  never overwrites an existing `installed_by_hallfix=True` fact — spec §8:
  "never assume that an installed package was installed by Hallfix" cuts
  both ways.
- `infrastructure/state/history_store.py`: `HistoryStore` — append-only
  JSON Lines (not one big JSON document): a single line write under
  `PIPE_BUF` is atomic on POSIX, and a crash mid-write only corrupts the
  last line, not the whole log (verified: `test_skips_corrupt_trailing_line`).
  Operation ids are sequential `HF-NNN`. Command/message text is redacted
  through the same redaction as structured logs before it ever touches
  disk (spec §9: never store secrets).
- `Executor` now takes an optional `state_store`; after a real (non-dry-run)
  successful install/remove it records ownership. Dry-run never touches
  the store — verified directly, not just inferred from the dry-run flag.
- `hallfix tool info <id>` now reports "Managed by Hallfix: yes/no/unknown".
  `hallfix tool install/remove` record every outcome (no-op, dry-run, or
  real) to history; `hallfix plan ...` (pure exploration) deliberately
  does not.
- `hallfix history` / `hallfix history show <id>` — read-only.
- `plan_reversible` is stored on each history record as descriptive
  metadata only — it is **not** presented as "rollback available"
  anywhere in the CLI, since there is no RollbackManager yet (Phase 11)
  and spec §11 is explicit: never claim rollback is available when it
  isn't.

## Unreleased — Phase 6: Executor

- `infrastructure/commands/runner.py`: `PrivilegedCommandRunner` — the
  privilege-escalation decision deferred since Phase 3. Wraps another
  `CommandRunner`, prepends `sudo` only to commands declaring
  `requires_root=True`, only when not already root. Never handles a
  password itself — `sudo`'s own prompt talks to the controlling terminal
  directly, same as if the user typed the command by hand. Elevates
  per-command, never the whole process (spec §48).
- `domain/planning/execution_result.py`: `ActionExecutionResult` /
  `PlanExecutionResult` — per-action outcomes, so one action failing in a
  multi-action plan doesn't collapse the result into an undifferentiated
  failure (spec §50 failure isolation, exercised by
  `test_failure_isolation_across_multiple_actions`).
- `application/executor.py`: `Executor` — applies a plan action by action;
  real exceptions are allowed to propagate rather than being caught and
  turned into a plausible-looking failure result (spec §78: no silent
  exception swallowing). Runs `ToolVerifier` after a successful, real
  install — a package transaction succeeding is not the same as the tool
  working (spec §26).
- `cli/confirmation.py`: `resolve_confirmation` — the concrete decision
  logic behind the `ConfirmationPrompt` protocol added in Phase 5.
  `--yes` bypasses confirmation for LOW/MEDIUM risk only; HIGH/CRITICAL
  always requires an interactive prompt, enforced via
  `SafetyPolicy.allows_auto_confirm`, not re-derived here.
- `hallfix tool install/remove <id>` — the first commands in Hallfix that
  can modify the system. Full path: Planner -> (no-op short-circuit for
  idempotence) -> SafetyPolicy -> confirmation -> Executor -> verification.
  `--dry-run` shows the plan and stops before any confirmation logic runs.
- Real, mutating install/remove is deliberately never exercised by the
  automated test suite (would modify whatever machine runs the tests) —
  covered by `Executor` unit tests against `FakeCommandRunner` instead;
  CLI integration tests only touch the no-op and `--dry-run` paths.

## Unreleased — Phase 5: Planning Engine

- `domain/planning/action.py`: `ActionType` + typed action dataclasses
  (`InstallPackageAction`, `RemovePackageAction`, `UpdatePackageIndexAction`)
  — only the 3 of spec §5's 18 action types Hallfix can actually construct
  and (eventually) execute right now; the rest get their own dataclass
  when the phase that implements their executor needs them.
- `domain/planning/risk_evaluator.py`: `RiskEvaluator` — pure, derives
  `ActionRisk` (risk level, root/network requirements, reversibility,
  rollback strategy) from the action itself; never hand-set and stored
  redundantly.
- `domain/planning/execution_plan.py`: `ExecutionPlan` — `risk_level`,
  `requires_root`, `requires_network`, `reversible`, `estimated_changes`
  are all derived properties computed from `planned_actions`, per the
  Phase 0 review's one non-negotiable change (prevents plan metadata from
  drifting out of sync with what the actions actually do).
- `domain/safety/policy.py`: `SafetyPolicy` — MEDIUM/HIGH/CRITICAL risk
  always requires confirmation, not configurable; `allows_auto_confirm`
  enforces that `--yes` can never bypass HIGH/CRITICAL (spec §60).
- `domain/safety/confirmation.py`: `ConfirmationPrompt` protocol — the
  component recommended in the Phase 0 review; concrete implementations
  (interactive prompt, `--yes` bypass) arrive with the Executor in Phase 6,
  the first component that actually needs to ask.
- `application/planner.py`: `Planner` — the first real content in
  `application/`, orchestrating domain planning logic with real
  infrastructure reads (`PackageManager.is_installed`/`get_version`) to
  decide idempotence. Lives outside `domain/` specifically because it does
  I/O; a plan is still never a system modification — there's no Executor
  yet, so building a plan *is* dry-run right now, by construction, not by
  a flag.
- `hallfix plan install/remove/refresh <tool>` — builds and displays a
  plan in the spec §6 format (including whether SafetyPolicy would require
  confirmation), never applies it.
- Real bug caught in unit testing (not smoke testing this time): a no-op
  plan's `reversible` property was hardcoded to `False` instead of the
  vacuously-true `all()` over zero actions — "nothing happened" is
  trivially reversible, not the opposite.

## Unreleased — Phase 4: Tool Registry

- Moved `data/` under `src/hallfix/data/` (was a top-level sibling of
  `src/`, per the spec's suggested tree) — a top-level `data/` wouldn't be
  bundled into a real wheel build (spec §74's PyPI goal), so tool/profile
  YAML now ships as proper package data. Empty at the time, zero-risk move.
- `domain/models/tool.py`: `InstallationStrategy` (spec §23: APT/DNF/
  PACMAN/ZYPPER/PIP/PIPX/NPM/CARGO/COMPOSER/OFFICIAL_REPOSITORY/
  SIGNED_BINARY), `VerificationSpec`, `ToolDefinition`, `ToolVerificationResult`.
- `domain/registries/tool_registry.py`: parses and validates already-loaded
  dicts into `ToolDefinition`s — every declared `installation_strategy`
  must have a `package_mappings` entry, enum values are checked, ids must
  be unique — fails loudly at load time (spec §25), never at first use.
  `infrastructure/registries/` does the actual YAML I/O, kept out of the
  (I/O-free) domain layer.
- `domain/registries/compatibility.py`: `resolve_installation_strategy`
  picks the highest-trust usable strategy (native manager > official
  vendor repo > signed binary > language ecosystem, spec §24), rejecting a
  native strategy that doesn't match the system's actual detected package
  manager. `assess_compatibility` never returns SUPPORTED unless the tool
  explicitly declares this distribution family supported (spec §84) — an
  unresolvable strategy is EXPERIMENTAL at best, not SUPPORTED.
- `detectors/tool_verifier.py`: `ToolVerifier` — runs a tool's
  `version_command`, reads exit code 127 as "not found" (not a generic
  error), extracts the version, and checks it against
  `minimum_version`/`recommended_version` via `utils/version.py`'s
  dotted-numeric comparator.
- Six starter tools (`src/hallfix/data/tools/*.yaml`): git, curl, python3,
  htop, docker, black — deliberately only `supported_distributions:
  [DEBIAN]` for the native ones (only apt has been live-verified, in
  Phase 3's smoke test), demonstrating SUPPORTED vs DETECTED_ONLY vs
  EXPERIMENTAL vs UNSUPPORTED are all real, reachable outcomes, not
  decorative enum values.
- `hallfix tool list [--category/--profile]`, `tool search`, `tool info`
  — read-only; `install`/`remove` deliberately don't exist yet (need
  Planner/SafetyPolicy/Executor, Phase 5/6).
- Fixed a real UX bug caught in CLI smoke testing: `CommandRunner` was
  logging a missing executable at ERROR level unconditionally, so checking
  an *optional, not-yet-installed* tool printed a scary `ERROR: command
  not found` line for a completely normal outcome. Downgraded to DEBUG —
  the returned `exit_code=127` already tells the caller what happened.

## Unreleased — Phase 3: Package Managers

- `infrastructure/package_managers/`: `AptManager`, `DnfManager`,
  `PacmanManager`, `ZypperManager`, each implementing the `PackageManager`
  structural interface (`detect`, `check_lock`, `refresh_metadata`,
  `install`, `remove`, `is_installed`, `get_version`, `search`, `repair`)
  and returning structured results (`PackageOperationResult`,
  `PackageManagerOperationResult`, `PackageSearchResult`) — never raw
  strings.
- Lock handling (spec §20): two real probes, not a placeholder —
  flock-based for apt/dpkg (the lock file exists permanently; only the
  flock itself is transient) and existence-based for dnf/pacman/zypper
  (pidfile/lockfile created only for the duration of an active run, a
  documented best-effort heuristic). Never deletes a lock file. Verified
  against a real held `flock(2)` in a child process, not just mocked.
  `install`/`remove`/`refresh_metadata`/`repair` check the lock first and
  skip cleanly (`skipped_due_to_lock=True`) rather than forcing through.
- Dry-run applies per mutating call (`install(..., dry_run=True)` etc.);
  read-only calls (`is_installed`, `get_version`, `search`, `detect`,
  `check_lock`) always execute for real, since dry-run has no meaning for
  a read and they're what an accurate plan is built from.
- `PackageManagerRegistry.create_package_manager(kind, ...)` — the one
  place that maps a detected `PackageManagerKind` to its adapter.
- Idempotence handled explicitly per manager (e.g. apt's "already the
  newest version", pacman's "target not found" on remove) rather than
  treating any non-zero exit as failure.
- Verified read-only (`detect`/`is_installed`/`get_version`/`search`)
  against the real host's `apt-get`/`dpkg-query`, not just fakes.

## Unreleased — Phase 2: Detection

- `detectors/`: distribution (`/etc/os-release`, `ID_LIKE` fallback for
  derivatives), environment (bare metal / VM / WSL1 / WSL2 / Docker /
  Podman / LXC / systemd-nspawn), capabilities (systemd, sudo, SELinux,
  AppArmor, network manager, container runtime, immutable OS, graphical
  session, filesystem write access, internet/ipv4/ipv6), CPU, memory,
  disk (`/proc/mounts`, pseudo-fs filtered), network basics (interfaces,
  addresses, default gateway, DNS via `ip -j` + `/etc/resolv.conf`),
  native package manager, sudo availability.
- Every detector takes an injectable root path (and, where relevant, an
  injectable `CommandRunner`/environment/connectivity-checker) so unit
  tests never touch the real filesystem, network, or subprocess.
- `SystemDetector` orchestrates all of the above into one `SystemContext`.
- `hallfix system info` (with `--json`) — thin CLI rendering layer only.
- Fake system fixtures (`tests/fake_systems/`): ubuntu, debian, fedora,
  arch, wsl_ubuntu, docker_container, vm_qemu, no_systemd.
- `FakeCommandRunner` test double; `tests/integration/` split out for the
  handful of tests that deliberately exercise the real host.

## Unreleased — Phase 1: Foundation

- Project structure and `pyproject.toml` (Typer + Rich, pytest/ruff/mypy dev tooling).
- CLI skeleton: global options (`--dry-run`, `--yes`, `--verbose`, `--quiet`,
  `--no-color`, `--json`, `--language`) and `hallfix version`.
- Foundational domain models/enums/exceptions.
- Configuration loading from `~/.config/hallfix/config.toml` (TOML, stdlib
  `tomllib`), validated, defaults-on-missing-file.
- Structured JSON-lines logging to `~/.local/state/hallfix/logs/` with
  mandatory secret redaction.
- `CommandRunner` abstraction (`SubprocessCommandRunner` /
  `DryRunCommandRunner`) — no `shell=True`, argv always a list.
- Unit tests, Ruff config (incl. bandit security rules), strict mypy config.
