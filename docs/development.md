# Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

pytest
ruff check .
ruff format --check .
mypy
```

`pytest` runs the full suite, including `tests/integration/` (real
detection/reads against your machine — every test in it is read-only or
`--dry-run` only, never a real mutation, so it's safe to run locally and
in CI). Use `pytest -m "not integration"` to skip it, e.g. for a faster
inner loop.

## CI

`.github/workflows/ci.yml` runs on every push/PR: lint, format check,
strict type check, the full test suite across Python 3.11–3.13, then a
package build with a real install-and-run smoke test (build the wheel,
install it into a *fresh* venv, run `hallfix version` and `hallfix tool
list` — this is what actually catches packaging regressions like data
files not shipping, not just "the source imports"). `release.yml` runs
the same gate on a version tag push and attaches the built wheel/sdist to
a GitHub Release — see `docs/installation.md` for why that's the only
publish target for now.

## Rules (spec §77/§78)

- Implement one phase at a time; run tests/lint/typecheck before moving on.
- Never comment out a failing test to get CI green.
- No `shell=True`, no hardcoded distro assumptions, no god classes.
- Unit tests never touch the real system: inject `CommandRunner`,
  filesystem roots, and config/state paths rather than using real ones.
