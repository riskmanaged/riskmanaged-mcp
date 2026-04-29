"""Risk management commands."""

import json

import typer
from rich import print as rprint
from riskmanaged_mcp.client import RiskManagedClient

app = typer.Typer(no_args_is_help=True)


@app.command("set-tp")
def set_tp(
    strategy_id: str = typer.Argument(help="Strategy ID"),
    tp_type: str = typer.Argument(help="Take-profit type name"),
    params: str = typer.Option("{}", help="JSON config"),
):
    """Set take-profit on a strategy."""
    client = RiskManagedClient()
    config = json.loads(params)
    result = client.set_take_profit(strategy_id, tp_type, config)
    rprint(f"[green]✓[/green] {result}")


@app.command("set-sl")
def set_sl(
    strategy_id: str = typer.Argument(help="Strategy ID"),
    sl_type: str = typer.Argument(help="Stop-loss type name"),
    params: str = typer.Option("{}", help="JSON config"),
):
    """Set stop-loss on a strategy."""
    client = RiskManagedClient()
    config = json.loads(params)
    result = client.set_stop_loss(strategy_id, sl_type, config)
    rprint(f"[green]✓[/green] {result}")


@app.command("remove-tp")
def remove_tp(strategy_id: str = typer.Argument(help="Strategy ID")):
    """Remove take-profit from a strategy."""
    client = RiskManagedClient()
    result = client.remove_take_profit(strategy_id)
    rprint(f"[green]✓[/green] {result}")


@app.command("remove-sl")
def remove_sl(strategy_id: str = typer.Argument(help="Strategy ID")):
    """Remove stop-loss from a strategy."""
    client = RiskManagedClient()
    result = client.remove_stop_loss(strategy_id)
    rprint(f"[green]✓[/green] {result}")


@app.command("tp-types")
def tp_types():
    """List available take-profit types."""
    client = RiskManagedClient()
    types = client.list_take_profit_types()
    for t in types:
        rprint(f"  {t['name']}")


@app.command("sl-types")
def sl_types():
    """List available stop-loss types."""
    client = RiskManagedClient()
    types = client.list_stop_loss_types()
    for t in types:
        rprint(f"  {t['name']}")


@app.command("tp-schema")
def tp_schema(name: str = typer.Argument(help="Take-profit type name")):
    """Get schema for a take-profit type."""
    client = RiskManagedClient()
    data = client.get_take_profit_schema(name)
    rprint(json.dumps(data, indent=2))


@app.command("sl-schema")
def sl_schema(name: str = typer.Argument(help="Stop-loss type name")):
    """Get schema for a stop-loss type."""
    client = RiskManagedClient()
    data = client.get_stop_loss_schema(name)
    rprint(json.dumps(data, indent=2))
