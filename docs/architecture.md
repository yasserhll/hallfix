# Architecture

Layered architecture; dependencies point downward only, and the CLI is not
allowed to contain business logic:

```text
CLI
  -> Application
       -> Diagnostics / Profiles / Tool Registry
            -> Planner -> ExecutionPlan -> SafetyPolicy -> Confirmation -> Executor
                 -> PackageManager / Services / Filesystem adapters
                      -> Verification -> StateStore -> History
```

## Layers

- `domain/` — pure Python: models, planning, safety rules, registries
  (parsing already-loaded data). No subprocess calls, no filesystem I/O
  beyond what's handed to it.
- `infrastructure/` — all I/O: command execution (`CommandRunner`),
  package manager adapters, service adapters, filesystem adapters,
  structured/redacted logging, state persistence.
- `detectors/` — read-only system introspection, returns domain models.
- `application/` — orchestrates domain + infrastructure; the only layer
  the CLI is allowed to call into.
- `cli/` — argument parsing, rendering, exit codes only.

## Phase 1 status

Implemented: project skeleton, configuration loading (`config/`),
structured JSON-lines logging with mandatory redaction
(`infrastructure/logging/`), the `CommandRunner` abstraction
(`infrastructure/commands/`), foundational domain models/enums/exceptions,
and the CLI skeleton (global options + `version` command).

## Phase 2 status

Implemented: `detectors/` (distribution, environment/virtualization,
capabilities, CPU, memory, disk, network basics, package manager, sudo)
and the `SystemDetector` orchestrator, plus `hallfix system info`. Every
detector reads from an injectable root path and injectable
command-runner/environment/connectivity-checker instead of hardcoding
`/etc`, `/proc`, or `subprocess` calls, so Phase 2's fake-system-layer
tests (`tests/fake_systems/`) never touch the real machine.

## Phase 3 status

Implemented: `infrastructure/package_managers/` — `AptManager`,
`DnfManager`, `PacmanManager`, `ZypperManager` behind one `PackageManager`
structural interface, with real (not existence-only-where-wrong) lock
detection and per-call dry-run on mutating operations. Selected via
`PackageManagerRegistry.create_package_manager(kind, ...)`.

## Phase 4 status

Implemented: `domain/registries/tool_registry.py` (validates already-loaded
tool data — the domain layer stays I/O-free; `infrastructure/registries/`
does the actual YAML reading) and `domain/registries/compatibility.py`
(resolves the trust-priority installation strategy and the
SUPPORTED/EXPERIMENTAL/DETECTED_ONLY/UNSUPPORTED verdict for a tool on the
detected system). `detectors/tool_verifier.py` checks whether a tool
actually works, not just whether a package transaction succeeded.
`hallfix tool list/search/info` — read-only. Tool/profile data now lives
under `src/hallfix/data/` (moved from a top-level `data/`, which wouldn't
have been bundled into a real wheel).

## Phase 5 status

Implemented: `domain/planning/` (`Action`/`ActionType`, `RiskEvaluator`,
`ExecutionPlan` with derived risk/root/network/reversibility properties),
`domain/safety/` (`SafetyPolicy`, the `ConfirmationPrompt` protocol added
per the Phase 0 review), and `application/planner.py` — the first real
content in `application/`, which exists precisely for components like this
one that must orchestrate domain logic with real infrastructure reads.
`hallfix plan install/remove/refresh` builds and displays a plan; there is
no Executor yet, so this is inherently dry-run — nothing in Phase 5 can
modify the system.

Note on layering in practice: `cli/commands/system.py` and `tool.py` call
`detectors/` and `domain/registries/` directly for simple read-only
queries — the strict "CLI only calls application/" rule stated in Phase 1
is aspirational for orchestration-heavy work (like the Planner) but isn't
worth the indirection for a plain lookup-and-render command.

## Phase 6 status

Implemented: `application/executor.py` (`Executor`, applying a plan
action-by-action with failure isolation and post-install verification),
`infrastructure/commands/runner.py`'s `PrivilegedCommandRunner` (the
per-command `sudo` escalation deferred since Phase 3), and
`cli/confirmation.py` (the concrete decision behind the `ConfirmationPrompt`
protocol). `hallfix tool install/remove` is the first system-modifying
command tree in Hallfix, and it cannot skip Planner/SafetyPolicy/Executor
to get there.

## Phase 7 status

Implemented: `infrastructure/state/store.py` (`StateStore`, atomic
single-snapshot JSON, ownership tracking) and
`infrastructure/state/history_store.py` (`HistoryStore`, append-only
JSONL, redacted, crash-tolerant on read). `Executor` records ownership
after real installs/removes only; `hallfix tool info` surfaces it,
`hallfix tool install/remove` write to history, `hallfix history[/show]`
reads it back.

## Phase 8 status

Implemented: `domain/registries/profile_registry.py` (`ProfileRegistry`),
`domain/registries/profile_diff.py` (pure diff computation),
`Planner.plan_profile_install` (multi-tool plans built by composing
`plan_tool_install` per tool, never a second install path), and
`Executor`'s `profile_id` threading into `StateStore.installed_for`.
`hallfix profile list/show/diff/install` — `install custom --tools ...`
goes through the identical execution path as a registry-defined profile.

## Phase 9 status

Implemented: `domain/diagnostics/` (pure check functions,
`DiagnosticEngine`/`DiagnosticRegistry`, deterministic `aggregate_health`),
`application/doctor.py` (the I/O assembly step — package manager lock,
dev-tool verification, DNS probe), and `detectors/dns_resolution.py` (a
second, DNS-specific connectivity probe distinct from Phase 2's raw-IP
check). `hallfix doctor`, `hallfix network info/doctor` — all read-only.

## Phase 10 status

Implemented: `domain/models/fix.py`/`domain/registries/fix_registry.py`
(`FixRegistry`, one entry — see `CHANGELOG.md` for why not more),
`ActionType.REPAIR_PACKAGE_MANAGER`/`RepairPackageManagerAction`
(reusing `RiskEvaluator`/`Executor`, not a separate execution path),
`Planner.plan_fix`, and `hallfix repair` / `hallfix fix <diagnostic-id>`.
A fix goes through the identical Planner -> SafetyPolicy -> confirmation
-> Executor -> History path as any other system change.

## Phase 11 status

Implemented: `Planner.plan_rollback` + `hallfix rollback [operation-id]`,
scoped honestly to what's actually reversible today (undoing a successful
install by removing the package — the only `Action` type ever marked
reversible with a real strategy). `HistoryStore` records now carry enough
detail to reconstruct that undo. `infrastructure/filesystem/backup.py`
(`BackupManager`) is real, tested, standalone infrastructure with no
caller yet — there's no `WRITE_FILE`/`MODIFY_FILE` action for it to serve.

## Phase 12 status

Implemented: `domain/models/report.py` (`Report`), `application/
report_generator.py` (`build_report` — aggregates `SystemContext`,
diagnostics, `StateStore`, `HistoryStore`; no new detection logic),
`cli/report_rendering.py` (TXT/HTML; JSON reuses the standard
`dataclasses.asdict` pattern), and `hallfix report
[--format txt|json|html] [--output path]`.

## Phase 13 status

Implemented: 5 additional profiles (Cybersecurity, Network Engineer,
System Administrator, Data/AI, Full Stack Developer) and their 17
supporting tool definitions under `src/hallfix/data/`. No new Python —
purely data, using the registry/Planner/Executor infrastructure already
built in Phases 4/8. 26 tools and 7 profiles total.

Not yet implemented: `profile remove` (needs "is this profile currently
installed" tracking); GPU detection (referenced by spec §33's Data/AI
profile vision, never built in Phase 2/9).

## Phase 14 status

Implemented: `.github/workflows/ci.yml` (lint/format/type-check/full test
suite across Python 3.11–3.13/package build with an install smoke test)
and `.github/workflows/release.yml` (tag-triggered, GitHub Release only —
no PyPI publish yet, see `docs/installation.md`). Package build verified
by hand (built a wheel, installed it into a fresh non-editable venv,
confirmed it runs) before trusting the CI job to do the same automatically.
`docs/installation.md` added; `README.md` brought current after being
stale since Phase 1.

Not yet implemented: PyPI/`.deb`/`.rpm`/AUR/Homebrew distribution (spec
§74 explicitly defers these — each needs real, human-provisioned
accounts/credentials); `profile remove`; GPU detection.

## Phase 15 status

The final phase: no new features, six audits (security, dependency, CLI,
compatibility, documentation, test coverage) against the actual code, not
against what the docs claimed. Full findings in
[`docs/release-audit.md`](release-audit.md). Net effect: two dead
exception classes removed (`CommandExecutionError`, `SafetyPolicyViolation`
— declared, never raised anywhere); 24 new unit/integration tests closing
real coverage gaps (`cli/rendering.py`, `cli/commands/plan.py`,
`cli/commands/history.py`, `cli/commands/network.py` — which had no
dedicated test file at all before this phase — and
`infrastructure/package_managers/zypper.py`), raising overall coverage
90% → 92%; `docs/security.md` item 4 clarified to state plainly that no
non-native installation strategy is executable yet, so there's no live
code path needing its own checksum/signature verification beyond what
`apt`/`dnf`/`pacman`/`zypper` already do; a "Known limitations" section
added to `README.md` collecting every honestly-scoped gap in one place
instead of leaving them scattered across phase notes.

## Post-release: spec completeness pass

A full line-by-line cross-check of the master spec against the running
code (post-`v0.1.2`) found six CLI-tree commands (spec §60) that were
either explicitly documented as deferred or missing outright, with no
functionality behind them at all. Closed all six, each through the
existing architecture rather than a parallel path:

- `hallfix recommend` (§41): reuses `compute_profile_diff` per profile
  (domain/registries/recommendation.py), never a second installed/missing
  algorithm.
- `hallfix profile remove` (§37): `Planner.plan_profile_remove` reuses
  `plan_tool_remove` per tool, gated on `StateStore`'s `installed_for`
  ownership record — a tool is only planned for removal when Hallfix
  installed it *and* no other profile still claims it.
- `hallfix snapshot` (§10): new `domain/models/snapshot.py` +
  `infrastructure/state/snapshot_store.py` (atomic JSON-per-snapshot,
  same temp-file+replace pattern as `StateStore`/`HistoryStore`) +
  `application/snapshot.py` to build one from real reads. Records
  "relevant Hallfix state" (OS info, Hallfix-managed tools and their
  versions, requesting profiles) — explicitly not a full filesystem
  snapshot, per spec.
- `hallfix update system`/`tools`/`hallfix` (§54): required adding
  `PackageManager.upgrade()` to the interface itself (spec §19 listed it;
  no adapter had implemented it) across all four adapters, a new
  `UpgradeSystemAction`/`ActionType.UPGRADE_SYSTEM_PACKAGES` wired through
  `RiskEvaluator` (MEDIUM, not reversible) and `Executor`, and
  `Planner.plan_tool_update`/`plan_tools_update` (like install, but skips
  the "already meets minimum" idempotence short-circuit — an update must
  still re-run to pick up a newer version). `update hallfix` reports
  self-update as honestly unavailable (no distribution channel exists
  yet) rather than fabricating support, per spec §84.
- `hallfix config`/`hallfix logs` (§57/§58): read-only views over
  infrastructure that already existed (`ConfigurationManager`, the
  structured JSON-lines logger) but had no command surface.

Deliberately left out: the interactive menu on a bare `hallfix` invocation
and the first-run wizard (spec §61/§63) — the spec's own wording for both
is "may display", not a hard requirement, unlike every item above.
