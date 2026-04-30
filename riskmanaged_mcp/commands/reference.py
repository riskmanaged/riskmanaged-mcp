"""Reference data commands — tickers, patterns, constants."""

import json

import typer
from rich import print as rprint
from riskmanaged_mcp.client import RiskManagedClient

app = typer.Typer(no_args_is_help=True)


@app.command("tickers")
def tickers(
    search: str = typer.Option("", help="Search by name or symbol"),
    exchange: str = typer.Option("binance", help="Exchange: binance|bittensor"),
):
    """Search available tickers."""
    client = RiskManagedClient()
    results = client.search_tickers(search=search, exchange=exchange)
    for t in results:
        if isinstance(t, dict):
            rprint(f"  {t.get('symbol', t.get('name', str(t)))}")
        else:
            rprint(f"  {t}")


@app.command("patterns")
def patterns():
    """List available candlestick patterns."""
    client = RiskManagedClient()
    results = client.list_patterns()
    for p in results:
        rprint(f"  {p.get('pattern', '')}: {p.get('public_name', '')}")


@app.command("constants")
def constants():
    """Show platform constants (timeframes, exchanges, trigger types)."""
    client = RiskManagedClient()
    data = client.get_constants()
    rprint(json.dumps(data, indent=2))
