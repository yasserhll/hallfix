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

## Rules (spec §77/§78)

- Implement one phase at a time; run tests/lint/typecheck before moving on.
- Never comment out a failing test to get CI green.
- No `shell=True`, no hardcoded distro assumptions, no god classes.
- Unit tests never touch the real system: inject `CommandRunner`,
  filesystem roots, and config/state paths rather than using real ones.
