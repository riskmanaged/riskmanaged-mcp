"""Strategy CRUD commands."""

import json

import typer
from rich import print as rprint
from rich.table import Table
from riskmanaged_mcp.client import RiskManagedClient

app = typer.Typer(no_args_is_help=True)


def _client():
    return RiskManagedClient()


@app.command("list")
def list_strategies(
    search: str = typer.Option(None, help="Search by name or ticker"),
    timeframe: str = typer.Option(None, help="Filter by timeframe"),
    mode: str = typer.Option(None, help="Filter by mode: paper|live|backtest"),
    limit: int = typer.Option(50, help="Max results"),
):
    """List your strategies."""
    params = {"limit": limit}
    if search:
        params["search"] = search
    if timeframe:
        params["root_timeframe"] = timeframe
    if mode:
        params["mode"] = mode

    strategies = _client().list_strategies(**params)

    table = Table(title="Strategies")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Ticker")
    table.add_column("TF")
    table.add_column("Mode")

    for s in strategies:
        table.add_row(
            s.get("id", ""),
            s.get("name", ""),
            s.get("root_ticker", ""),
            s.get("root_timeframe", ""),
            s.get("mode", ""),
        )
    rprint(table)


@app.command("get")
def get_strategy(strategy_id: str = typer.Argument(help="Strategy ID")):
    """Get full details of a strategy."""
    data = _client().get_strategy(strategy_id)
    rprint(json.dumps(data, indent=2, default=str))


@app.command("create")
def create_strategy(
    name: str = typer.Option(..., help="Strategy name"),
    exchange: str = typer.Option("binance", help="Exchange"),
    timeframe: str = typer.Option("30m", help="Root timeframe"),
    ticker: str = typer.Option("BTCUSDT", help="Root ticker"),
    mode: str = typer.Option("backtest", help="Mode: paper|live|backtest"),
):
    """Create a new strategy."""
    data = {
        "name": name,
        "root_exchange": exchange,
        "root_timeframe": timeframe,
        "root_ticker": ticker,
        "mode": mode,
    }
    result = _client().create_strategy(data)
    rprint(
        f"[green]✓[/green] Strategy created: {json.dumps(result, indent=2, default=str)}"
    )


@app.command("delete")
def delete_strategy(strategy_id: str = typer.Argument(help="Strategy ID")):
    """Delete a strategy."""
    _client().delete_strategy(strategy_id)
    rprint(f"[green]✓[/green] Strategy {strategy_id} deleted")


@app.command("archive")
def archive_strategy(strategy_id: str = typer.Argument(help="Strategy ID")):
    """Archive a strategy."""
    _client().archive_strategy(strategy_id)
    rprint(f"[green]✓[/green] Strategy archived")


@app.command("unarchive")
def unarchive_strategy(strategy_id: str = typer.Argument(help="Strategy ID")):
    """Unarchive a strategy."""
    _client().unarchive_strategy(strategy_id)
    rprint(f"[green]✓[/green] Strategy restored")


@app.command("clone")
def clone_strategy(strategy_id: str = typer.Argument(help="Strategy ID")):
    """Clone a strategy to live mode."""
    result = _client().clone_strategy(strategy_id)
    rprint(f"[green]✓[/green] Cloned: {result}")
