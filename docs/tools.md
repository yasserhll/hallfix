# Tools

A tool (spec §25) is a data-driven definition under
`src/hallfix/data/tools/` — never a hardcoded distro package name in
Python. Validated at startup by `ToolRegistry`
(`domain/registries/tool_registry.py`).

```yaml
id: git
name: Git
description: Distributed version control
category: essentials
installation_strategies: [APT, DNF, PACMAN, ZYPPER]
package_mappings:
  APT: git
  DNF: git
  PACMAN: git
  ZYPPER: git
verification:
  executable: git
  version_command: [git, --version]
supported_distributions: [DEBIAN]
risk_level: LOW
```

`ToolDefinition` fields: `id`, `name`, `description`, `category`,
`profiles`, `dependencies`, `installation_strategies`,
`package_mappings`, `verification`, `supported_distributions`,
`supported_architectures`, `minimum_version`, `recommended_version`,
`optional`, `risk_level`, `requires_root`, `documentation_url`.

## Installation strategies and trust priority

`InstallationStrategy` (spec §23): `APT`/`DNF`/`PACMAN`/`ZYPPER` (native —
the only strategies the Planner can currently build an executable plan
for), `PIP`/`PIPX`/`NPM`/`CARGO`/`COMPOSER` (language-ecosystem, declared
but not yet executable), `OFFICIAL_REPOSITORY`/`SIGNED_BINARY` (declared
for the trust-priority ranking, not yet executable). Trust priority is
resolved by `resolve_installation_strategy`
(`domain/registries/compatibility.py`): native package manager > official
repository > signed binary > language-ecosystem package.

## Compatibility levels

`assess_compatibility` never claims support merely because a package
manager is recognized (spec §84):

- `SUPPORTED` — distribution is in `supported_distributions` and a native
  strategy resolves.
- `EXPERIMENTAL` — a strategy resolves but the distribution isn't
  explicitly declared supported.
- `DETECTED_ONLY` — the system is recognized but nothing usable resolves.
- `UNSUPPORTED` — no usable strategy at all.

## Verification (spec §26)

A successful package transaction is not proof the tool works. After
install, `ToolVerifier` runs the tool's declared `version_command` for
real and reports `executable_found`/`installed_version` independently
from the package manager's own success/failure.

## Commands

```bash
hallfix tool list [--category X] [--profile developer]
hallfix tool search docker
hallfix tool info docker                    # compatibility, strategy, current install state
hallfix tool install docker                 # Planner -> SafetyPolicy -> confirmation -> Executor
hallfix tool remove docker
hallfix update tools                        # re-install every Hallfix-managed tool to pick up updates
```

`list`/`search`/`info` are read-only. `install`/`remove` support
`--dry-run` and `--yes`; `--yes` never bypasses HIGH/CRITICAL
confirmations.
