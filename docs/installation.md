# Installation

There is no published release yet (no PyPI package, `.deb`, `.rpm`, or AUR
package) — spec §74 deliberately scopes the MVP to source installation and
explicitly says not to promote a `curl | sh` one-liner until there's a
mature, secure installation mechanism. Every method below installs from
source you can read first.

## Prerequisites

- Linux (Hallfix is Linux-only by design — it detects and manages Linux
  systems specifically).
- Python 3.11 or newer.
- `python3-venv` (or your distro's equivalent) if it isn't already part of
  your Python install — Debian/Ubuntu split it into a separate package;
  Fedora/Arch/openSUSE normally don't.

## Option 1: Editable install for development (recommended for now)

This is what every phase of Hallfix's own development has used.

```bash
git clone https://github.com/yasserhll/hallfix.git
cd hallfix
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

`-e` (editable) means changes to the source under `src/hallfix/` take
effect immediately without reinstalling. `[dev]` pulls in pytest, ruff,
and mypy — omit it (`pip install -e .`) for a runtime-only install.

Verify it worked:

```bash
hallfix version
hallfix doctor
```

## Option 2: Build and install a wheel

If you want a normal (non-editable) install — e.g. to test packaging
itself, or to install into a different environment:

```bash
git clone https://github.com/yasserhll/hallfix.git
cd hallfix
python -m venv .venv && source .venv/bin/activate
pip install build
python -m build                 # produces dist/hallfix-*.whl and dist/hallfix-*.tar.gz
pip install dist/hallfix-*.whl
```

This is exactly what `.github/workflows/ci.yml` and `release.yml` do —
build the wheel, then install it into a *fresh* venv and run `hallfix
version` — as a real smoke test that packaging still works, not just that
the source imports cleanly.

## Uninstalling

```bash
pip uninstall hallfix
```

State/history/config Hallfix wrote are not touched by this — see below.

## Where Hallfix keeps its own data

None of this is removed by uninstalling the package:

- `~/.config/hallfix/config.toml` — your configuration (optional; sane
  defaults apply if absent).
- `~/.local/state/hallfix/state.json` — what Hallfix has installed
  (ownership tracking).
- `~/.local/state/hallfix/history.jsonl` — the operation log
  (`hallfix history`).
- `~/.local/state/hallfix/logs/hallfix.log` — structured, secret-redacted
  logs.

Delete these manually if you want a completely clean slate.

## Future packaging (not yet available)

Spec §74 names PyPI, a standalone binary, `.deb`, `.rpm`, AUR, and
Homebrew/Linuxbrew as future distribution targets — none are implemented
yet, and this file will be updated when any of them are. The project
structure (a normal `pyproject.toml`/hatchling build already producing a
correct wheel — verified by hand and by CI) doesn't block any of them; it's
a matter of setting up the actual publishing pipeline for each, which
needs real accounts/credentials a human has to provision, not something
to wire up speculatively.

## Troubleshooting

**`ensurepip is not available` / `No module named venv`** — install your
distro's Python venv package (`sudo apt install python3-venv` on Debian/
Ubuntu; usually unnecessary elsewhere).

**A command needs administrator privileges and nothing happens** —
Hallfix elevates individual commands via `sudo`, which needs a real
controlling terminal to prompt for a password. It will not work through
a fully non-interactive/no-TTY environment (some containers, some CI
runners, some IDE-embedded terminals) — run it from a normal terminal.

**`hallfix tool list` shows an empty/short list** — this usually means
the package's `data/` directory (tool/profile YAML definitions) didn't
ship with your install. Confirm with
`python -c "import hallfix, pathlib; print(pathlib.Path(hallfix.__file__).parent / 'data')"`
and check that path actually contains `tools/*.yaml` and
`profiles/*.yaml`. If you hit this, please open an issue — it would be a
packaging regression, and `hallfix tool list` returning fewer tools than
expected is exactly the kind of thing CI's install smoke test exists to
catch before a release ships.
