# Rollback

Rollback is only ever offered when Hallfix can *actually* reverse an
operation — never claimed as available when it isn't (spec §11).

## Reversibility is computed per action, not assumed

Every action's `RiskEvaluator`-computed `ActionRisk` carries its own
`reversible`/`rollback_strategy`:

| Action | Reversible | Strategy |
|---|---|---|
| `InstallPackageAction` | yes | `remove_package` |
| `RemovePackageAction` | **no** | — Hallfix doesn't record the exact prior version/config to restore |
| `UpdatePackageIndexAction` | yes | — (nothing to undo) |
| `RepairPackageManagerAction` | **no** | — "un-configuring" isn't a real rollback |
| `UpgradeSystemAction` | **no** | — Hallfix doesn't record prior package versions |

These flags are recorded per `ActionOutcome` in `HistoryStore` at the
moment an operation runs (`domain/models/history.py`) — never
reconstructed later from a message string.

## What `hallfix rollback` actually does

```bash
hallfix rollback              # most recent rollback-eligible operation
hallfix rollback HF-004       # a specific one
```

`OperationRecord.rollback_eligible_outcomes` filters to outcomes that
succeeded, weren't already-satisfied no-ops, and are individually marked
reversible with a known strategy. `Planner.plan_rollback` builds a real
`ExecutionPlan` from exactly those — an install becomes a
`RemovePackageAction` — and it goes through the same
SafetyPolicy -> confirmation -> Executor path as any other plan.
**Rollback itself creates a new `HistoryStore` operation** (spec §11) —
it is not a special, unrecorded code path.

If nothing in a record is rollback-eligible, `hallfix rollback` says so
and does nothing; it never guesses at an undo strategy Hallfix doesn't
actually have.
