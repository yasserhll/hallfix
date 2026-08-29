# Diagnostics

Every diagnostic returns a structured `DiagnosticResult`
(`domain/models/diagnostic.py`, spec §39) — never a printed string:

```text
id            stable dotted namespace, e.g. "system.disk", "network.dns_resolution"
category      e.g. "system", "network", "package"
severity      INFO | OK | WARNING | ERROR | CRITICAL
title
description
evidence      tuple of supporting facts
recommendation
fix_available fix_id
```

`fix_available`/`fix_id` are always `False`/`None` today — nothing in
Hallfix auto-fixes a diagnostic yet beyond the small `FixRegistry` set
(see below); `id` stays stable across added/removed checks so it can
later be safely referenced by a fix.

## Diagnostic categories (`domain/diagnostics/`)

`system_checks.py` (OS, kernel, CPU, RAM, disk, filesystem),
`network_checks.py` (interfaces, DNS, connectivity — same read-only
administrative tests as `network doctor`, never external scans or
port-scanning per spec §18), `package_checks.py` (package manager health,
lock state), `development_checks.py` (git, docker, SSH, dev environment
variables).

`DiagnosticEngine`/`DiagnosticRegistry` (`domain/diagnostics/engine.py`,
`registry.py`) run every registered check and aggregate an overall
`HealthState`: `HEALTHY` / `DEGRADED` / `UNHEALTHY` / `CRITICAL` —
categorical, not a numeric score (spec §40), and missing *optional*
software is never treated as a failure.

## Commands

```bash
hallfix doctor              # every category, aggregated health
hallfix doctor --json
hallfix network doctor      # network category only
hallfix network info        # raw network facts, no health judgement
hallfix recommend           # evidence-based profile suggestion from what's installed
```

All read-only. `doctor` exits non-zero when overall health is `UNHEALTHY`
or `CRITICAL`, for scripting.
