# Security Model

Hallfix is secure by default (spec §68). Rules enforced from Phase 1 onward:

1. No arbitrary shell commands built from user input — `CommandRunner`
   never uses `shell=True` and always takes argv as a list
   (`infrastructure/commands/runner.py`).
2. Structured logs are redacted before they ever reach disk — the
   redaction filter is attached to the log handler itself, not left as
   something call sites must remember to invoke
   (`infrastructure/logging/redaction.py`, `logger.py`).
3. No secret can be smuggled in through configuration — the config schema
   (`config/schema.py`) has no field that widens what any future
   `SafetyPolicy` allows.

Rules that apply once the corresponding component exists (tracked here so
later phases are held to them):

4. Prefer official repositories over third-party installers; verify
   checksums/signatures when available (Planner/installation strategies,
   Phase 4+). As of Phase 15: the trust-priority order (native package
   manager > official repository > signed binary > language-ecosystem
   package) is implemented in `resolve_installation_strategy`, but the
   Planner only ever builds an executable plan for a *native* package
   manager strategy — it explicitly refuses (raises `PlanningError`) for
   any tool that would require `OFFICIAL_REPOSITORY` or `SIGNED_BINARY`,
   since no Executor code implements either yet. So there is currently no
   live code path that needs its own checksum/signature verification:
   every real install goes through `apt`/`dnf`/`pacman`/`zypper`, which
   already verify package signatures themselves. This rule stays recorded
   for when (if) a non-native strategy becomes executable.
5. Confirm sensitive (MEDIUM+ risk) operations explicitly; `--yes` does not
   bypass HIGH/CRITICAL confirmations (SafetyPolicy, Phase 5).
6. Back up sensitive files before modifying them; only claim rollback where
   it is technically real (BackupManager/RollbackManager, Phase 11).
7. Least privilege: Hallfix runs as a normal user; only individual
   operations are elevated, explicitly (Executor, Phase 6).
8. No automatic reboot, firewall change, SSH change, partition change,
   driver replacement, or destructive package removal, ever, by default.
9. No automatic offensive security actions (scanning, exploitation, brute
   force, credential collection) under any profile.
