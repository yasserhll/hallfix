"""``hallfix recommend`` (spec §41). Read-only — never installs anything.

Verifies each tool referenced by any known profile exactly once (not once
per profile) since ``ToolVerifier.verify`` shells out; profiles commonly
share tools (e.g. ``git``), and re-verifying the same tool per profile
would be wasted I/O for no extra signal.
"""

from __future__ import annotations

import dataclasses
import json

import typer
from rich.console import Console

from hallfix.detectors.tool_verifier import ToolVerifier
from hallfix.domain.exceptions import RegistryError
from hallfix.domain.models.profile import ProfileDefinition
from hallfix.domain.models.tool import ToolVerificationResult
from hallfix.domain.registries.profile_registry import ProfileRegistry
from hallfix.domain.registries.recommendation import (
    RecommendationResult,
    compute_recommendation,
)
from hallfix.domain.registries.tool_registry import ToolRegistry
from hallfix.infrastructure.commands.runner import SubprocessCommandRunner
from hallfix.infrastructure.registries.profile_registry_loader import load_profile_registry
from hallfix.infrastructure.registries.tool_registry_loader import load_tool_registry


def _load_profile_registry() -> ProfileRegistry:
    try:
        return load_profile_registry()
    except RegistryError as exc:
        typer.secho(f"Profile registry error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc


def _load_tool_registry() -> ToolRegistry:
    try:
        return load_tool_registry()
    except RegistryError as exc:
        typer.secho(f"Tool registry error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc


def _verify_all_profile_tools(
    profiles: tuple[ProfileDefinition, ...], tool_registry: ToolRegistry
) -> dict[str, ToolVerificationResult]:
    verifier = ToolVerifier(command_runner=SubprocessCommandRunner())
    tool_ids: set[str] = set()
    for profile in profiles:
        tool_ids.update(profile.tools)

    verifications: dict[str, ToolVerificationResult] = {}
    for tool_id in tool_ids:
        tool = tool_registry.get(tool_id)
        if tool is not None:
            verifications[tool_id] = verifier.verify(tool)
    return verifications


def _render(console: Console, result: RecommendationResult) -> None:
    best = result.best_match
    if best is None:
        console.print("No installed tools matched any known profile yet.")
        console.print("Run `hallfix profile list` to explore available profiles.")
        console.print("\nNo changes have been made.")
        return

    console.print("Detected:\n")
    for entry in best.diff.installed:
        console.print(f"✓ {entry.tool_name}")
    for entry in best.diff.missing:
        console.print(f"✗ {entry.tool_name}")

    console.print(f"\nPotential profile:\n{best.profile_name}")

    if best.diff.missing:
        console.print("\nMissing tools:")
        for entry in best.diff.missing:
            console.print(entry.tool_name)

    console.print("\nNo changes have been made.")


def recommend(ctx: typer.Context) -> None:
    """Recommend a professional profile based on what's already installed."""
    cli_ctx = ctx.obj
    profile_registry = _load_profile_registry()
    tool_registry = _load_tool_registry()
    profiles = profile_registry.list_all()

    verifications = _verify_all_profile_tools(profiles, tool_registry)
    result = compute_recommendation(profiles, tool_registry, verifications)

    if cli_ctx is not None and cli_ctx.json_output:
        best = result.best_match
        payload = {
            "best_match": dataclasses.asdict(best) if best else None,
            "matches": [dataclasses.asdict(m) for m in result.matches],
        }
        typer.echo(json.dumps(payload, default=str, indent=2))
        return

    console = Console(no_color=cli_ctx.no_color if cli_ctx else False)
    _render(console, result)
