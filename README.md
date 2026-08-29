# Hallfix

**Hallfix — Safe, cross-distribution Linux system doctor and professional environment manager.**

> Status: all 15 planned phases complete, including the Phase 15 release
> audit, plus a full spec cross-check that closed every remaining CLI
> gap (`recommend`, `profile remove`, `snapshot`, `update`, `config`,
> `logs`). See [Development Phases](#development-phases) below and
> [`docs/release-audit.md`](docs/release-audit.md) for the audit itself.

## What Hallfix is

Hallfix discovers your Linux system, diagnoses problems and missing
capabilities, recommends improvements, builds an explicit reviewable plan,
applies only approved changes, verifies the result, and records what it did
so it can be rolled back:

```text
DISCOVER → DIAGNOSE → RECOMMEND → PLAN → REVIEW → APPLY → VERIFY → RECORD → ROLLBACK
```

## What Hallfix is NOT

- Not a wrapper around `apt install package1 package2 ...`.
- Not a collection of hardcoded shell scripts.
- Not a tool that performs offensive security actions automatically.
- Not something that modifies your system without an explicit, reviewable plan.

## Installation

See [`docs/installation.md`](docs/installation.md). Short version — there's
no packaged release yet, so install from source:

```bash
git clone https://github.com/yasserhll/hallfix.git
cd hallfix
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quick start

```bash
hallfix system info                    # detected hardware/network/environment
hallfix doctor                         # full system health check
hallfix recommend                      # evidence-based profile suggestion, read-only
hallfix tool list                      # browse the tool registry
hallfix tool install git               # plan -> confirm -> install (dry-run: add --dry-run)
hallfix profile list                   # developer, devops, cybersecurity, ...
hallfix profile diff developer         # what's installed vs. missing, read-only
hallfix profile install developer      # install a whole profile
hallfix profile remove developer       # remove it (skips tools shared with other profiles)
hallfix update system                  # full native package-manager upgrade
hallfix update tools                   # update every Hallfix-managed tool
hallfix snapshot                       # record a point-in-time Hallfix state snapshot
hallfix history                        # what Hallfix has done
hallfix logs                           # tail Hallfix's own structured log
hallfix config                         # show the effective configuration
hallfix rollback                       # undo the most recent reversible install
hallfix repair                         # diagnose, then apply safe LOW-risk fixes
hallfix report --format html --output report.html
hallfix --help                         # full command tree
```

Every command that can modify the system supports `--dry-run` (shows the
plan, changes nothing) and requires explicit confirmation for MEDIUM+ risk
actions — `--yes` cannot bypass HIGH/CRITICAL confirmations.

## Safety

See [`docs/security.md`](docs/security.md). In short: nothing is installed,
removed, or modified without an explicit execution plan, a risk assessment,
and — for MEDIUM risk and above — your confirmation. Dry-run
(`--dry-run`) always uses the same planning path as real execution.

## Supported systems

Actually verified so far: **Debian-family** (Ubuntu, Debian) via `apt`/`dpkg`,
real installs included.

**Fedora**: detection, compatibility classification, and plan-building are
live-verified against a real, unmodified Fedora Linux 44 filesystem
(correct `family=REDHAT`, correct `DNF` resolution, correct real
`is_installed`/`get_version`/`check_lock` via the genuine `rpm`/`dnf`
binaries) — see `docs/release-audit.md`'s Fedora addendum. Real *package
installation* on Fedora is still unverified (the dev sandbox used for this
couldn't complete an actual `dnf install`, for reasons confirmed to be a
sandbox limitation, not a Hallfix bug), so tool definitions still
correctly declare `supported_distributions: [DEBIAN]` only — Hallfix
never claims support for the one thing that's still actually unverified.

Pacman/Zypper adapters exist and are unit-tested against fakes, but have
had no live verification at all yet (real or containerized). Support
level per tool is reported explicitly (`SUPPORTED` / `EXPERIMENTAL` /
`DETECTED_ONLY` / `UNSUPPORTED`, via `hallfix tool info <id>`).

## Known limitations

Honestly scoped gaps, collected in one place (see
[`docs/release-audit.md`](docs/release-audit.md) for the full audit that
found/confirmed each of these):

- `--language fr` is accepted and validated but nothing is actually
  translated yet — spec-compliant ("prepare architecture for English/
  French... do not over-engineer translation in the MVP"), not a bug.
- Pacman/Zypper package manager adapters are implemented and unit-tested
  against fakes, but have never run against real hardware or a container
  — see [Supported systems](#supported-systems). DNF is partially
  live-verified (detection/compatibility/planning, not installation).
- The `OFFICIAL_REPOSITORY`/`SIGNED_BINARY` installation strategies are
  declared in the domain model (for the trust-priority ranking) but the
  Planner refuses to build an executable plan for them — every real
  install currently goes through a native package manager only.
- `hallfix update hallfix` (self-update) honestly reports itself as
  unavailable rather than faking it — Hallfix has no packaging/
  distribution channel yet (source install only). Update from source
  with `git pull` + `pip install -e .`.
- No automated dependency-vulnerability scan (e.g. `pip-audit`) has been
  run against the three runtime dependencies.

## Documentation

[`docs/installation.md`](docs/installation.md) ·
[`docs/architecture.md`](docs/architecture.md) ·
[`docs/security.md`](docs/security.md) ·
[`docs/development.md`](docs/development.md) ·
[`docs/profiles.md`](docs/profiles.md) ·
[`docs/tools.md`](docs/tools.md) ·
[`docs/diagnostics.md`](docs/diagnostics.md) ·
[`docs/state.md`](docs/state.md) ·
[`docs/rollback.md`](docs/rollback.md) ·
[`docs/testing.md`](docs/testing.md) ·
[`docs/troubleshooting.md`](docs/troubleshooting.md) ·
[`CONTRIBUTING.md`](CONTRIBUTING.md)

## Architecture overview

Layered: CLI → Application (Planner/Executor/Doctor/ReportGenerator) →
Domain (planning, diagnostics, registries, safety) → Infrastructure
(package managers, command execution, state/history) → Linux. See
[`docs/architecture.md`](docs/architecture.md) for the full breakdown and
per-phase status.

## Development

See [`docs/development.md`](docs/development.md) and
[`CONTRIBUTING.md`](CONTRIBUTING.md). CI runs lint, format check, strict
type check, the full test suite (Python 3.11–3.13), and a package build
with an install smoke test on every push — see
[`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Development Phases

Hallfix is built incrementally; each phase is implemented, tested, linted,
and type-checked before the next begins (see `CHANGELOG.md` for what
shipped in each). All 15 complete: Foundation, Detection, Package
Managers, Tool Registry, Planning Engine, Executor, State & History,
Profiles, Doctor, Safe Fixes, Backup & Rollback, Reports, Remaining
Profiles, Packaging & CI, Documentation & Release Audit.
