# Hallfix

**Hallfix — Safe, cross-distribution Linux system doctor and professional environment manager.**

> Status: early development (Phase 1 — Foundation). Not yet functional beyond
> `hallfix version`; see [Development Phases](#development-phases) below.

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

## Installation (development)

```bash
git clone <repo-url> hallfix
cd hallfix
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quick start

```bash
hallfix version
hallfix --help
```

(Diagnostics, profiles, and tool management land in later development phases.)

## Safety

See [`docs/security.md`](docs/security.md). In short: nothing is installed,
removed, or modified without an explicit execution plan, a risk assessment,
and — for MEDIUM risk and above — your confirmation. Dry-run
(`--dry-run`) always uses the same planning path as real execution.

## Supported systems (target)

Ubuntu LTS, Debian stable, Fedora current, Arch Linux, Ubuntu under WSL2.
Support level per distribution/tool combination is tracked explicitly
(`SUPPORTED` / `EXPERIMENTAL` / `DETECTED_ONLY` / `UNSUPPORTED`) — Hallfix
never claims support it hasn't actually implemented and tested.

## Architecture overview

Layered: CLI → Application → {Diagnostics, Profiles, ToolRegistry} → Planner
→ SafetyPolicy → Executor → system adapters → Verification → StateStore →
History. See [`docs/architecture.md`](docs/architecture.md).

## Development

See [`docs/development.md`](docs/development.md) and
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## Development Phases

Hallfix is built incrementally; each phase is implemented, tested, linted,
and type-checked before the next begins. Currently: **Phase 1 — Foundation**.
