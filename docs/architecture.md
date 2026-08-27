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

Not yet implemented (later phases, see `CHANGELOG.md`): profile registry,
the executor, `StateStore`/`HistoryStore`, diagnostics, fixes,
backup/rollback, reports.
