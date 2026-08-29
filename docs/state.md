# State

Hallfix tracks what *it* changed — never assumes an installed package was
installed by Hallfix (spec §8). Three stores, all under
`~/.local/state/hallfix/` (`XDG_STATE_HOME` respected), all atomic
(temp-file write + `Path.replace`, so a crash mid-write never leaves a
half-written file under its final name):

## StateStore (`infrastructure/state/store.py`)

One JSON file, `state.json`, rewritten in full on every save. Per tool:

```json
{
  "tools": {
    "docker": {
      "present_before_hallfix": false,
      "installed_by_hallfix": true,
      "installed_for": ["developer", "devops"]
    }
  }
}
```

`installed_for` is how `profile remove` decides whether a tool is still
shared (see [profiles.md](profiles.md)). A corrupt/unreadable state file
is treated as "nothing recorded yet", not a fatal error — losing
ownership tracking is recoverable; refusing to start over a file only
Hallfix itself writes is not (spec §2: "fail gracefully").

## HistoryStore (`infrastructure/state/history_store.py`)

Append-only JSON Lines, `history.jsonl` — one line per operation, so a
crash mid-write can only corrupt the last line (skipped on read), never
the whole history. Every `hallfix ... install/remove/update/repair`
invocation appends an `OperationRecord`: id, timestamp, command, plan,
dry-run flag, and per-action `ActionOutcome`s (succeeded, message,
reversible, rollback strategy). Free-text fields go through the same
redaction as logs before being written (spec §9: never store secrets).

```bash
hallfix history                 # most recent first
hallfix history show HF-004
```

## SnapshotStore (`infrastructure/state/snapshot_store.py`)

One JSON file per snapshot under `state_home()/snapshots/`. Not a full
filesystem snapshot (spec §10 explicitly doesn't require one) — records
OS info, every Hallfix-managed tool and its current version, and the
profiles that requested them, built from real reads by
`application/snapshot.py`.

```bash
hallfix snapshot
```

All three are read-only from the CLI's perspective except `snapshot`
(which only ever writes to its own store) — none of them are ever
modified as a side effect of an unrelated command.
