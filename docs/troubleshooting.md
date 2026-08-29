# Troubleshooting

For install-time problems (missing `venv`, empty `tool list`, no-TTY
`sudo`), see [installation.md](installation.md)'s own Troubleshooting
section. This covers problems while actually *running* Hallfix.

## "Package manager is currently busy"

Another `apt`/`dnf`/`pacman`/`zypper` process (or an unattended-upgrades
job) holds the lock. Hallfix **never deletes a lock file** or forces
through it (spec §20) — wait for the other process to finish and retry.

## A plan says a tool needs confirmation and nothing happens non-interactively

`--yes` auto-confirms LOW/MEDIUM risk, but never HIGH/CRITICAL (spec §60:
"`--yes` must NOT bypass HIGH/CRITICAL mandatory safety confirmations").
If a script needs to run unattended, check the plan's risk level first
(`hallfix plan install <tool>` or `--dry-run`) — a HIGH/CRITICAL action is
not automatable by design, not a bug.

## Installed, but Hallfix still reports the tool as missing/broken

`hallfix tool install`'s post-install verification (spec §26) is
independent of the package manager's own success — it actually runs the
tool's version command. A package can report "installed" while the
binary isn't on `PATH`, is a stub, or is missing a shared library. Run
`hallfix tool info <id>` to see exactly what verification found.

## "This tool isn't supported here" but it clearly works

Check `hallfix tool info <id>` for the compatibility level:
`SUPPORTED` / `EXPERIMENTAL` / `DETECTED_ONLY` / `UNSUPPORTED` (spec
§84). Hallfix deliberately under-claims rather than over-claims —
`DETECTED_ONLY` means the distribution is recognized but not yet
verified for that tool, not that installation will fail. See
[tools.md](tools.md).

## Offline / no Internet

Local diagnostics (`hallfix doctor`, `hallfix system info`) work fully
offline (spec §51) — only actions that actually need network access
(refreshing package metadata, installing) are affected, and those fail
with a clear reason rather than hanging silently.

## Where to look for detail

```bash
hallfix logs                 # tail Hallfix's own structured (redacted) log
hallfix logs --lines 200 --json
hallfix history show HF-004  # exactly what one past operation did/failed
hallfix --verbose <command>  # full detail on stderr, no stack trace unless --verbose
hallfix config                # confirm which config file (if any) is actually loaded
```

## Config file won't load

`hallfix config` shows the exact path Hallfix looked for
(`~/.config/hallfix/config.toml` by default, or `$XDG_CONFIG_HOME`) and
whether it exists. A malformed TOML file is a hard error at startup
(never silently ignored) — the error message includes the parse
position. Configuration can never disable a mandatory safety rule (spec
§58); there's no field for that.
