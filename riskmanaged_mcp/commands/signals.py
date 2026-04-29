"""Signal group and rule commands."""

import json

import typer
from rich import print as rprint
from riskmanaged_mcp.client import RiskManagedClient

app = typer.Typer(no_args_is_help=True)


@app.command("add-group")
def add_group(
    strategy_id: str = typer.Argument(help="Strategy ID"),
    name: str = typer.Argument(help="Signal group name"),
):
    """Add a signal group to a strategy."""
    client = RiskManagedClient()
    result = client.add_signal_group(strategy_id, {"name": name})
    rprint(f"[green]✓[/green] {result}")


@app.command("remove-group")
def remove_group(
    strategy_id: str = typer.Argument(help="Strategy ID"),
    name: str = typer.Argument(help="Signal group name"),
):
    """Remove a signal group from a strategy."""
    client = RiskManagedClient()
    result = client.delete_signal_group(strategy_id, name)
    rprint(f"[green]✓[/green] {result}")


@app.command("add-rule")
def add_rule(
    strategy_id: str = typer.Argument(help="Strategy ID"),
    group: str = typer.Argument(help="Signal group name"),
    action: str = typer.Option(
        "enter_position", help="Trigger action: enter_position|exit_position"
    ),
    direction: str = typer.Option("long", help="Trigger direction: long|short"),
    conditions: str = typer.Option("[]", help="JSON array of conditions"),
):
    """Add a rule to a signal group."""
    client = RiskManagedClient()
    parsed = json.loads(conditions)
    result = client.add_signal_rule(strategy_id, group, action, direction, parsed)
    rprint(f"[green]✓[/green] {result}")


@app.command("edit-rule")
def edit_rule(
    strategy_id: str = typer.Argument(help="Strategy ID"),
    group: str = typer.Argument(help="Signal group name"),
    index: int = typer.Argument(help="Rule index"),
    action: str = typer.Option("enter_position", help="Trigger action"),
    direction: str = typer.Option("long", help="Trigger direction"),
    conditions: str = typer.Option("[]", help="JSON array of conditions"),
):
    """Edit a signal rule."""
    client = RiskManagedClient()
    parsed = json.loads(conditions)
    result = client.edit_signal_rule(
        strategy_id, group, index, action, direction, parsed
    )
    rprint(f"[green]✓[/green] {result}")


@app.command("remove-rule")
def remove_rule(
    strategy_id: str = typer.Argument(help="Strategy ID"),
    group: str = typer.Argument(help="Signal group name"),
    index: int = typer.Argument(help="Rule index"),
):
    """Remove a signal rule."""
    client = RiskManagedClient()
    result = client.delete_signal_rule(strategy_id, group, index)
    rprint(f"[green]✓[/green] {result}")
