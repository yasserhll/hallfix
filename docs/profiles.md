# Profiles

A profile (spec §27) is a data-driven bundle of tool ids — no distribution
package names, no Python code. Defined as YAML under
`src/hallfix/data/profiles/`:

```yaml
name: developer
description: Development workstation
categories:
  - essentials
  - programming
  - containers
tools:
  - git
  - python3
  - nodejs
  - docker
```

Loaded and validated at startup by `ProfileRegistry`
(`domain/registries/profile_registry.py`) — a malformed profile file fails
immediately, not whenever it happens to be looked up.

## Shipped profiles

`developer`, `devops`, `cybersecurity`, `network-engineer`,
`system-administrator`, `data-ai`, `full-stack-developer`. `custom` is not
a YAML file — it's built on the fly from `--tools` (spec §35: custom
profiles reuse the exact same `ProfileDefinition` type and go through the
exact same Planner, never a second installation system).

## Commands

```bash
hallfix profile list                        # every profile, tool count
hallfix profile show developer              # tools + per-tool compatibility
hallfix profile diff developer              # installed / missing / version-mismatched, read-only
hallfix profile install developer           # Planner -> SafetyPolicy -> confirmation -> Executor
hallfix profile remove developer            # same path, in reverse
hallfix profile install custom --tools git,htop
```

`diff` never modifies the system (spec §36). `install`/`remove` support
`--dry-run` and `--yes` like every other mutating command.

## Ownership and shared dependencies

`profile install` records which profile requested each tool in
`StateStore`'s `installed_for` list (see [state.md](state.md)).
`profile remove` (`Planner.plan_profile_remove`) only ever plans removing
a tool when Hallfix installed it *and* no other profile still claims it —
otherwise the tool is skipped with a note:

```text
Docker is also used by: devops. Removal skipped.
```

A tool that was already present before Hallfix touched it, or that
Hallfix merely observed rather than installed, is never removed by
`profile remove` — spec §37: "Never remove shared dependencies blindly."
