"""Indicator management commands."""

import json

import typer
from rich import print as rprint
from riskmanaged_mcp.client import RiskManagedClient

app = typer.Typer(no_args_is_help=True)


@app.command("list-types")
def list_types():
    """List all available indicator types."""
    client = RiskManagedClient()
    groups = client.list_indicator_types()
    for group in groups:
        rprint(f"\n[bold cyan]{group['category']}[/bold cyan]")
        for ind in group["indicators"]:
            rprint(f"  {ind['name']:30s} {ind.get('public_name', '')}")


@app.command("schema")
def schema(indicator_name: str = typer.Argument(help="Indicator type name")):
    """Get the parameter schema and output lines for an indicator."""
    client = RiskManagedClient()
    data = client.get_indicator_schema(indicator_name)
    rprint(json.dumps(data, indent=2))


@app.command("add")
def add(
    strategy_id: str = typer.Argument(help="Strategy ID"),
    indicator_name: str = typer.Argument(help="Indicator type name"),
    params: str = typer.Option("{}", help="JSON config for the indicator"),
):
    """Add an indicator to a strategy."""
    client = RiskManagedClient()
    config = json.loads(params)
    result = client.add_indicator(strategy_id, indicator_name, config)
    rprint(f"[green]✓[/green] {result}")


@app.command("remove")
def remove(
    strategy_id: str = typer.Argument(help="Strategy ID"),
    indicator_name: str = typer.Argument(help="Indicator instance name"),
):
    """Remove an indicator from a strategy."""
    client = RiskManagedClient()
    result = client.delete_indicator(strategy_id, indicator_name)
    rprint(f"[green]✓[/green] {result}")
