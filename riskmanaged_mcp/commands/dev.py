"""Maintainer commands: keep the generated docs and the vendored snapshot fresh.

Not part of the user-facing surface — these exist so the two things that must
track the platform can be refreshed with one command each:

  * `sync-docs`     — regenerate the tool tables in AGENTS.md / README.md
  * `sync-snapshot` — re-vendor the API schema the offline tests check against

`tests/test_docs.py` and `tests/test_api_contract.py` fail when either is stale,
so this is the fix, not the check.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import print as rprint

from riskmanaged_mcp import docgen
from riskmanaged_mcp.client import RiskManagedClient

app = typer.Typer(no_args_is_help=True, help="Maintainer utilities")

REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DIR = REPO_ROOT / "tests" / "snapshots"
GENERATED_DOCS = ("AGENTS.md", "README.md")


@app.command("sync-docs")
def sync_docs():
    """Regenerate the tool tables embedded in the docs."""
    changed = []
    for name in GENERATED_DOCS:
        path = REPO_ROOT / name
        if path.exists() and docgen.update_doc(path):
            changed.append(name)

    if changed:
        rprint(f"[green]✓[/green] Updated: {', '.join(changed)}")
    else:
        rprint("[dim]Already up to date.[/dim]")


@app.command("sync-snapshot")
def sync_snapshot(
    base_url: str = typer.Option(
        None, "--base-url", help="Override the configured API base URL"
    ),
):
    """Re-vendor the API schema the offline contract tests run against.

    Needs a reachable backend and a valid token — this is the one command here
    that talks to the network. The tests never do.
    """
    client = RiskManagedClient(base_url=base_url) if base_url else RiskManagedClient()
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    spec = client._request("GET", "/openapi.json")
    (SNAPSHOT_DIR / "openapi.json").write_text(
        json.dumps(spec, indent=2, sort_keys=True)
    )
    route_count = sum(len(ops) for ops in spec["paths"].values())
    rprint(f"[green]✓[/green] openapi.json — {len(spec['paths'])} paths, "
           f"{route_count} operations")

    indicators = {}
    for category in client.list_indicator_types() or []:
        for name in _indicator_names(category):
            schema = client.get_indicator_schema(name)
            indicators[name] = {
                "default_name": (
                    schema.get("required_input", {})
                    .get("name", {})
                    .get("default", name)
                ),
                "lines": sorted(schema.get("lines", [])),
                "config_fields": sorted(schema.get("required_input", {})),
            }

    risk = {}
    for kind, lister, schema_getter in (
        ("stoploss", client.list_stop_loss_types, client.get_stop_loss_schema),
        ("takeprofit", client.list_take_profit_types, client.get_take_profit_schema),
    ):
        for name in _flatten(lister()):
            schema = schema_getter(name)
            risk[name] = {
                "kind": kind,
                "config_fields": sorted(schema.get("properties", {})),
            }

    (SNAPSHOT_DIR / "reference.json").write_text(
        json.dumps(
            {
                "indicators": indicators,
                "risk": risk,
                "constants": client.get_constants(),
            },
            indent=2,
            sort_keys=True,
        )
    )
    rprint(
        f"[green]✓[/green] reference.json — {len(indicators)} indicators, "
        f"{len(risk)} risk types"
    )


def _indicator_names(category) -> list[str]:
    """`/reference/indicators` groups by category; shapes vary, so be liberal."""
    if isinstance(category, str):
        return [category]
    if isinstance(category, dict):
        items = category.get("indicators") or category.get("items") or []
        return [i if isinstance(i, str) else i.get("name") for i in items]
    return []


def _flatten(listing) -> list[str]:
    if isinstance(listing, dict):
        return [k for k in listing]
    return [i if isinstance(i, str) else i.get("name") for i in listing or []]
