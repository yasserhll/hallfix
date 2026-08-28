# Changelog

## Unreleased — post-v0.1.0: Fedora live-verification

No source code changes. Live-verified Hallfix's detection, compatibility
classification, and plan-building against a genuine, unmodified Fedora
Linux 44 filesystem (pulled directly from Docker Hub's registry API and
run via an unprivileged `bwrap` sandbox, since this dev environment has
no real Fedora machine and no working privileged container runtime).
Confirmed correct: distribution/package-manager detection
(`family=REDHAT`, `DNF`), `resolve_installation_strategy`/
`assess_compatibility` (correctly `DETECTED_ONLY`, not `SUPPORTED`, for
DEBIAN-only-declared tools), `Planner.plan_tool_install`, and
`DnfManager.is_installed`/`get_version`/`check_lock` against the real
`rpm`/`dnf` binaries. Real package *installation* could not be completed —
confirmed to be a sandbox limitation (RPM's SELinux xattr writes are
refused under an unprivileged bind mount), not a Hallfix defect, by
reproducing the identical failure with a plain `dnf install`, no Hallfix
code involved. No tool's `supported_distributions` was changed as a
result, since the one thing that would justify that (real installation)
is still unverified. Full account: `docs/release-audit.md`'s Fedora
addendum. `README.md`'s "Supported systems"/"Known limitations" updated
to reflect the more precise state.

## Unreleased — Phase 15: Documentation & Release Audit

- Ran all six audits spec §Phase 15 requires (security, dependency, CLI,
  compatibility, documentation, test coverage) against the running code,
  not against what earlier phase notes claimed. Full write-up:
  `docs/release-audit.md`.
- Removed two dead exception classes (`CommandExecutionError`,
  `SafetyPolicyViolation`) found never raised or caught anywhere in
  `src/` or `tests/` — leftovers from before the codebase settled on
  structured results (`CommandResult`, `PolicyDecision`) instead of
  exceptions for these cases.
- Added 24 tests closing real coverage gaps found during the audit:
  `cli/rendering.py` (62% → 100%, was never exercised with a non-noop
  plan or a failed/verified action), `cli/commands/plan.py` (78% → 100%,
  the MEDIUM+-risk confirmation notice was host-state-dependent and
  untested), `cli/commands/history.py` (85% → 98%, no test ever seeded a
  failed outcome), `cli/commands/network.py` (89% → 98% — this command
  group had **no dedicated test file at all** before this phase), and
  `infrastructure/package_managers/zypper.py` (67% → 88%, thinner test
  file than the other three adapters). Overall line coverage: 90% → 92%.
  Documented, rather than papered over, the one coverage gap left
  deliberately open: `cli/commands/fix.py`/`rollback.py`'s real-execution
  branches, which are only reachable by a real system mutation (forbidden
  in this project's tests) or a cross-module DI refactor out of scope for
  an audit phase — every component those branches call is independently
  tested at 95–100%, so the gap is in argument plumbing, not logic.
- Clarified `docs/security.md` item 4: the trust-priority install-strategy
  order is implemented, but the Planner refuses to execute any non-native
  strategy, so there's currently no live code path needing its own
  checksum/signature verification — real installs already go through
  `apt`/`dnf`/`pacman`/`zypper`, which verify signatures themselves.
- Added a "Known limitations" section to `README.md` collecting every
  honestly-scoped gap (the `--language fr` no-op, unverified DNF/Pacman/
  Zypper, missing `profile remove`, unexecutable `OFFICIAL_REPOSITORY`/
  `SIGNED_BINARY` strategies, no dependency-vulnerability scan run) in one
  place instead of leaving them scattered across per-phase notes.
- Cross-checked spec §80's Definition of Done item by item against the
  actual implementation — no unmet item found.

## Unreleased — Phase 14: Packaging & CI

- Fixed a real bug the CI run itself caught on its first execution: 9
  tests across `test_capabilities.py`/`test_system_detector.py` asserted
  `systemd`/`selinux` capability detection against fixture directories
  under `tests/fake_systems/` (e.g. `ubuntu/run/systemd/system/`,
  `fedora/sys/fs/selinux/`) that were empty on disk — and git does not
  track empty directories, so they silently didn't exist after a fresh
  checkout. Passed locally (447/447) only because this sandbox's working
  tree still had those directories from when they were first created;
  failed on all three CI Python versions against a real clone. Added
  `.gitkeep` to all 46 empty fixture directories and verified the fix
  against an actual fresh `git worktree` checkout (not just re-running
  locally, which wouldn't have caught the same class of gap again) before
  re-pushing.
- Actually built the package and verified it, rather than trusting the
  `pyproject.toml` config: `python -m build`, inspected the wheel's
  contents, then installed it into a completely fresh (non-editable) venv
  and confirmed `hallfix version`/`hallfix tool list` work — the tool/
  profile YAML data does ship correctly via hatchling's default
  git-tracked-file inclusion. (A first verification pass wrongly
  suggested otherwise — a bug in my own check command, a `grep -E
  "\.yaml$"` anchor that could never match `zipfile -l`'s
  filename-then-columns output — corrected by testing further rather
  than trusting the first result or leaving a needless `force-include`
  behind.)
- Found and fixed a real CI-fragility bug while auditing for exactly this
  class of issue: three integration tests assumed `docker` was *not*
  pre-installed (true on this dev sandbox, false on GitHub Actions'
  `ubuntu-latest`, which ships Docker pre-installed for container
  actions). Made all three robust to either real host state, matching
  the pattern already established in Phase 10 for the same class of
  problem — caught by review before CI ever ran, not by a failed run.
- `.github/workflows/ci.yml`: lint, format check, strict type check, full
  test suite (unit + integration — every integration test is read-only or
  `--dry-run` only, so running the real suite in CI is safe) across Python
  3.11/3.12/3.13, then a package build with a real install-and-run smoke
  test (fresh venv, not editable — the same check that verified the wheel
  above). Runs as the unprivileged `runner` user throughout (spec §72: CI
  must not require root).
- `.github/workflows/release.yml`: triggered by a version tag, re-runs
  the full quality gate, builds, verifies the wheel installs and runs,
  then publishes to a GitHub Release using only the built-in
  `GITHUB_TOKEN`. Deliberately does not publish to PyPI — that needs a
  human to provision an account/trusted-publisher config, not something
  to wire up unasked (spec §74: don't implement every packaging format
  in the MVP, don't promote `curl | sh` before there's a mature
  mechanism).
- Added `classifiers`/`[project.urls]` to `pyproject.toml`; `build` as a
  dev dependency.
- Rewrote `README.md`, which had been stale since Phase 1 (still said
  "not yet functional beyond `hallfix version`" through 13 completed
  phases) — a real problem to catch before any release, not just
  cosmetic. Added `docs/installation.md` (spec §73, never written until
  now).

## Unreleased — Phase 13: Remaining Profiles

- Purely data-driven: no new Python — the registry/Planner/Executor
  infrastructure from Phases 4/8 already handles this. 17 new tool
  definitions (`wireshark`, `tcpdump`, `lsof`, `strace`, `binutils`,
  `iproute2`, `traceroute`, `mtr`, `ethtool`, `dig`, `wget`, `rsync`,
  `nodejs`, `php`, `composer`, `postgresql-client`, `jupyter`) and 5
  profiles: Cybersecurity, Network Engineer, System Administrator,
  Data/AI, Full Stack Developer.
- Cybersecurity: tools only, no automation of scanning/exploitation/
  brute-force/credential-collection/remote-attacks — Hallfix prepares
  tools, never performs offensive actions (spec §30).
- Data/AI: GPU detection/CUDA guidance from the full spec vision (§33)
  isn't implemented — there's no GPU detector (never built in Phase 2/9)
  — documented honestly in the profile file rather than silently omitted.
- Handled real per-manager package-name differences rather than assuming
  uniform naming: Fedora's `iproute2` package is actually named
  `iproute`; Debian/Ubuntu's CLI-only `mtr` build is packaged as
  `mtr-tiny`; `dig` comes from a different package on every single
  manager (`dnsutils`/`bind-utils`/`bind`/`bind-utils`). All three
  verified with targeted regression tests, not just "loads without
  error."
- Renamed the Full Stack profile's id from an initial `full-stack` to
  `full-stack-developer` mid-implementation — `python3.yaml` (Phase 4)
  had already anticipated that exact name in its informational
  `profiles:` metadata; matched it rather than leaving an inconsistency.
- Verified against the real host, not just fixtures: `profile diff
  network-engineer` correctly found 7 of 8 tools already present with
  accurate versions and correctly flagged `traceroute` as the one
  missing tool; `--dry-run profile install cybersecurity` correctly
  planned to install only `wireshark`, the one genuinely absent tool.

## Unreleased — Phase 12: Reports

- Mostly an aggregation phase, not new detection: `domain/models/report.py`
  (`Report`, `ManagedToolSummary`) assembles what already exists —
  `SystemContext` (Phase 2), diagnostics (Phase 9, whose `recommendation`
  field directly populates the report's Recommendations section — no
  separate recommendation engine invented), `StateStore` (Phase 7), and
  `HistoryStore` (Phase 7/11).
- `application/report_generator.py`: `build_report`. "Never include
  secrets" (spec §55) holds structurally, not via an extra redaction pass
  — every source it draws from is already secret-safe by construction
  from earlier phases.
- Real bug caught before it shipped (unit test, not smoke test): the
  first version called both `run_doctor()` and `build_diagnostic_context()`
  separately to get the diagnostics and the underlying `SystemContext`,
  which would have silently run *every* detection I/O call twice
  (detection, package-lock check, `dpkg --audit`, dev-tool verification,
  DNS probe) on every `hallfix report`. Fixed by building the context
  once and running `DiagnosticEngine` directly; verified with a
  regression test asserting each stubbed command is called exactly once.
- `cli/report_rendering.py`: `render_txt`/`render_html` — JSON needs no
  dedicated renderer (`dataclasses.asdict` + `json.dumps`, the same
  pattern every other `--json` command already uses). HTML escapes all
  content (verified against a deliberately hostile description
  containing `<script>`).
- `hallfix report [--format txt|json|html] [--output <path>]` — entirely
  read-only. The global `--json` flag is also honored as `--format json`,
  for consistency with every other command.

## Unreleased — Phase 11: Backup & Rollback

- Scope check against our actual `Action` types: only `InstallPackageAction`
  is ever `reversible=True` with a real `rollback_strategy`
  (`"remove_package"`) — removes, refreshes, and repairs are all already
  correctly marked non-reversible. Rollback is therefore genuinely scoped
  to "undo a successful install by removing the package," not a general
  undo system.
- `domain/models/history.py`: `ActionOutcome` extended with
  `reversible`/`rollback_strategy`/`tool_id`/`package`/`strategy`/
  `risk_level` — enough detail to reconstruct the one rollback strategy
  that exists, without guessing from free-text `message`.
  `rollback_eligible` (per outcome) and `is_rollback_eligible`/
  `rollback_eligible_outcomes` (per record) are the actual eligibility
  checks — spec §11: never claim rollback is available when it is not,
  so eligibility is checked per action, never assumed from the aggregate
  `plan_reversible` flag. Old history lines (pre-Phase-11) still parse,
  correctly coming back as not rollback-eligible.
- `cli/history_recording.py`: `build_action_outcomes` — the one place
  that extracts this detail from a real `Action`, replacing near-identical
  inline construction that had been duplicated across `tool.py`/
  `profile.py`/`fix.py`.
- `Planner.plan_rollback(record)` reconstructs an `ExecutionPlan` from a
  `HistoryStore` record's eligible outcomes — reuses `RiskEvaluator`,
  `RemovePackageAction`, and the existing `Executor`, exactly like
  `plan_fix` before it (spec §84: never a separate mechanism). Rollback
  creates a *new* history operation; the record being rolled back is
  never edited.
- `hallfix rollback [operation-id]` — no argument rolls back the most
  recent eligible operation (excluding prior rollbacks themselves, so
  "undo the undo" requires an explicit id).
- `infrastructure/filesystem/backup.py`: `BackupManager` (spec §46) —
  atomic backup/restore via temp-file + `Path.replace`, naming matches
  spec's `*.hallfix-backup-YYYYMMDD-HHMMSS` example exactly, ownership
  preservation is best-effort ("when applicable" per spec's own wording).
  No `Action` calls this yet (no `WRITE_FILE`/`MODIFY_FILE` action type
  exists) — built as real, tested, standalone infrastructure the same way
  Phase 1's `CommandRunner` predated Phase 2's detectors being its first
  caller, not left unimplemented or faked.
- Process note, not a code bug: while smoke-testing, ran `hallfix rollback
  <id>` without `--dry-run` against a self-seeded history entry — a real
  (if harmless, since it failed on the sandbox's missing sudo TTY)
  mutating command run without checking first. Flagged directly rather
  than silently corrected.

## Unreleased — Phase 10: Safe Fixes

- Deliberately only **one** fix exists: cross-referencing spec §43's
  forbidden repair categories (bootloader/partitions/firewall/SSH/network
  config/filesystem repair/kernel/drivers) against Phase 9's actual
  diagnostics leaves exactly one genuinely safe, well-understood
  candidate — repairing broken/half-configured dpkg package state, which
  is what `PackageManager.repair()` already did since Phase 3. Disk
  space, package locks, and DNS/network config are all diagnosed but
  deliberately have no automated fix, rather than padding the registry
  with unsafe or fake entries (spec §84).
- Key architectural decision: a fix is **not** a separate execution
  system. Added one new `ActionType` (`REPAIR_PACKAGE_MANAGER`) and
  `RepairPackageManagerAction`, handled by the existing `RiskEvaluator`/
  `Executor`; `Planner.plan_fix` reuses `ExecutionPlan` exactly like tool/
  profile installs. `hallfix repair`/`hallfix fix <id>` go through the
  identical Planner -> SafetyPolicy -> confirmation -> Executor -> History
  path — spec §84's "never bypass the Planner" applies to fixes too, not
  just installs.
- `domain/models/fix.py` + `domain/registries/fix_registry.py`:
  `FixDefinition`/`FixRegistry` — hardcoded in Python, not YAML (one
  entry doesn't justify a data-loading pipeline; revisit if this grows).
- `detectors/package_health.py` (`check_dpkg_broken_state`) + a new
  `package.broken_state` diagnostic (APT-only; other managers report "not
  checked", never a false claim).
- `Planner.plan_fix` re-checks `check_dpkg_broken_state` itself before
  building an action (mirroring `plan_tool_install`'s `is_installed`
  check) — running a repair when nothing is actually broken would be
  needless, even though the underlying `dpkg --configure -a` is harmless.
- Real bug caught in CLI smoke testing (not unit tests): `hallfix fix
  <id>` on a diagnostic that's currently OK printed "No automated fix
  available for this issue" — technically true but misleading, since it
  reads as "Hallfix can't fix this category of problem" (true for DNS)
  rather than "nothing is wrong right now" (the actual case). Split into
  a distinct "Nothing to fix." message (exit 0, a success state) versus
  the genuine no-fix-exists message (exit 1) — verified with a regression
  test that doesn't depend on the live host's actual network state.

## Unreleased — Phase 9: Doctor

- `domain/models/diagnostic.py`: `DiagnosticResult` — stable dotted `id`
  (`"system.disk"`, `"network.dns_resolution"`), never a sequential
  number, so it stays meaningful as checks change and can be safely
  referenced by a future `fix_id`. `fix_available`/`fix_id` are always
  `False`/`None` — there is no FixRegistry yet (Phase 10).
- `domain/diagnostics/`: ~19 pure check functions across system/network/
  package/development categories, all operating on an already-assembled
  `DiagnosticContext` (zero I/O in the check functions themselves).
  `DiagnosticEngine`/`DiagnosticRegistry` run them; `aggregate_health` is
  a small, documented, deterministic rule (CRITICAL > ERROR > WARNING >
  else HEALTHY) — categorical, not a numeric score, per spec §40.
- `detectors/dns_resolution.py`: a *second* connectivity probe, distinct
  from Phase 2's `check_internet_connectivity` (which deliberately
  connects to a raw IP, bypassing DNS). Together they let a diagnostic
  distinguish spec §18's exact example: raw connectivity fine, DNS
  resolution failing — verified directly
  (`test_the_spec_example_scenario_dns_failure_with_raw_connectivity`).
- `application/doctor.py`: `build_diagnostic_context`/`run_doctor` — the
  only place the extra I/O (package manager lock check, git/docker/ssh
  verification, the DNS probe gated on raw connectivity already being up)
  gets gathered before handing off to the pure engine.
- Git/Docker/SSH absence is always INFO, never WARNING/ERROR — spec §40:
  "Do not penalize a machine because optional software is absent,"
  verified directly (`test_doctor_never_penalizes_absent_optional_tools`).
- Added an `ssh` tool definition (needed for the SSH dev-environment check).
- `hallfix doctor [--json]`, `hallfix network info`, `hallfix network
  doctor [--json]` — all read-only.
- Real bug caught in CLI smoke testing (not unit tests): `check_disk`
  picked up squashfs mounts (snap packages — fixed-size, always ~100%
  "used" by design) when computing worst-case usage, which reported this
  actual development machine as CRITICAL. Same root cause as the Phase 2
  `system info` display bug, this time in diagnostic logic that drives
  the exit code, not just a rendering filter — fixed with a regression
  test (`test_check_disk_ignores_squashfs_always_full_by_design`).

## Unreleased — Phase 8: Profiles

- `domain/models/profile.py` + `domain/registries/profile_registry.py`:
  `ProfileDefinition`/`ProfileRegistry`, same validate-at-load-time
  pattern as tools. Deliberately does not cross-validate tool references
  against `ToolRegistry` at load time (would couple load order) — an
  unresolvable tool id is reported clearly wherever the profile is
  actually used instead.
- `ExecutionPlan` gained a `notes: tuple[str, ...]` field for informational
  per-tool status in a multi-tool plan (already-satisfied, unknown tool) —
  purely descriptive, never affects risk/execution.
- `Planner.plan_profile_install` builds one plan covering every tool in a
  profile by calling `plan_tool_install` per tool and merging the
  results — spec §35: custom profiles (and every profile, by the same
  reasoning) must reuse the same Planner, never a second install system.
  `Executor.execute_plan` gained `profile_id`, threaded to
  `StateStore.record_installed` so `installed_for` (built in Phase 7) is
  finally populated.
- `domain/registries/profile_diff.py`: pure `compute_profile_diff` —
  installed/missing/version-mismatch, computed from an already-run
  `{tool_id: ToolVerificationResult}` mapping. No "configuration" section
  (spec's "Docker installed but service disabled" example) since service
  detection doesn't exist yet.
- `hallfix profile list/show/diff/install` — `diff` never modifies the
  system (spec §36); `install custom --tools a,b,c` builds an ad-hoc
  `ProfileDefinition` on the fly and goes through the identical
  Planner -> SafetyPolicy -> confirmation -> Executor path as a real
  profile. `profile remove` deliberately does not exist yet — spec §37's
  shared-dependency safety check needs "is this profile currently
  installed" tracking Hallfix doesn't have.
- Two more tools added (`jq`, `tmux`) so Developer/DevOps profiles have
  something real to install; both profiles are explicitly scoped to only
  the tools Hallfix's registry actually defines (no kubectl/Terraform/
  Node.js/etc. references to tools that don't exist).
- Extracted `cli/rendering.py` (`render_plan_human`/`render_execution_result`)
  out of `tool.py` — `profile.py` needed the identical rendering, so this
  was the third call site, not a hypothetical one.
- Real bug caught before it shipped (unit test, not smoke test): the CLI's
  `_require_profile`-equivalent originally called `ProfileRegistry.require()`
  directly, which raises `RegistryError` uncaught for an unknown profile —
  inconsistent with `tool.py`'s clean `get()` + typer.Exit(1) pattern.
  Fixed with a `_require_profile` helper before any test caught it in CI;
  caught while writing the integration tests.

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
