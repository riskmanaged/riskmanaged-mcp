"""Bias generator and rule commands."""

import json

import typer
from rich import print as rprint
from riskmanaged_mcp.client import RiskManagedClient

app = typer.Typer(no_args_is_help=True)


@app.command("add")
def add(
    strategy_id: str = typer.Argument(help="Strategy ID"),
    name: str = typer.Argument(help="Bias generator name"),
):
    """Add a bias generator to a strategy."""
    client = RiskManagedClient()
    result = client.add_bias_generator(strategy_id, {"name": name})
    rprint(f"[green]✓[/green] {result}")


@app.command("remove")
def remove(
    strategy_id: str = typer.Argument(help="Strategy ID"),
    name: str = typer.Argument(help="Bias generator name"),
):
    """Remove a bias generator from a strategy."""
    client = RiskManagedClient()
    result = client.delete_bias_generator(strategy_id, name)
    rprint(f"[green]✓[/green] {result}")


@app.command("add-rule")
def add_rule(
    strategy_id: str = typer.Argument(help="Strategy ID"),
    name: str = typer.Argument(help="Bias generator name"),
    direction: str = typer.Option("long", help="Bias direction: long|short|neutral"),
    conditions: str = typer.Option("[]", help="JSON array of conditions"),
):
    """Add a rule to a bias generator."""
    client = RiskManagedClient()
    parsed = json.loads(conditions)
    result = client.add_bias_rule(strategy_id, name, direction, parsed)
    rprint(f"[green]✓[/green] {result}")


@app.command("edit-rule")
def edit_rule(
    strategy_id: str = typer.Argument(help="Strategy ID"),
    name: str = typer.Argument(help="Bias generator name"),
    index: int = typer.Argument(help="Rule index"),
    direction: str = typer.Option("long", help="Bias direction"),
    conditions: str = typer.Option("[]", help="JSON array of conditions"),
):
    """Edit a bias rule."""
    client = RiskManagedClient()
    parsed = json.loads(conditions)
    result = client.edit_bias_rule(strategy_id, name, index, direction, parsed)
    rprint(f"[green]✓[/green] {result}")


@app.command("remove-rule")
def remove_rule(
    strategy_id: str = typer.Argument(help="Strategy ID"),
    name: str = typer.Argument(help="Bias generator name"),
    index: int = typer.Argument(help="Rule index"),
):
    """Remove a bias rule."""
    client = RiskManagedClient()
    result = client.delete_bias_rule(strategy_id, name, index)
    rprint(f"[green]✓[/green] {result}")
