# Contributing

Hallfix is built in phases (see `CHANGELOG.md`). Before opening a PR:

1. `pytest`, `ruff check .`, `ruff format --check .`, `mypy` must all pass
   (CI enforces this on every push/PR — see `.github/workflows/ci.yml`).
2. New system-modifying behavior must go through `Planner` → `SafetyPolicy`
   → `Executor`, never call a package manager or write a file directly.
3. New external commands go through `CommandRunner` only.
4. Add unit tests using the fake command runner / fake filesystem — no test
   may touch the real system.
5. Update the relevant `docs/*.md` file if you changed behavior it describes.

See `docs/architecture.md` and `docs/security.md` for the constraints that
apply to any change.
