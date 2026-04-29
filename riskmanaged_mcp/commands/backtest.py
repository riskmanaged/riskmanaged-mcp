"""Backtest and Monte Carlo commands."""

import json

import typer
from rich import print as rprint
from riskmanaged_mcp.client import RiskManagedClient

app = typer.Typer(no_args_is_help=True)


@app.command("run")
def run(strategy_id: str = typer.Argument(help="Strategy ID")):
    """Run a backtest on a strategy."""
    client = RiskManagedClient()
    rprint("[dim]Running backtest... this may take a minute.[/dim]")
    result = client.run_backtest(strategy_id)
    rprint(f"[green]✓[/green] Backtest complete")
    rprint(json.dumps(result, indent=2, default=str))


@app.command("reports")
def reports(strategy_id: str = typer.Argument(help="Strategy ID")):
    """Get backtest report data."""
    client = RiskManagedClient()
    data = client.get_reports(strategy_id)
    rprint(json.dumps(data, indent=2, default=str))


@app.command("montecarlo")
def montecarlo(
    strategy_id: str = typer.Argument(help="Strategy ID"),
    sims: int = typer.Option(1000, help="Number of simulations"),
    bust: float = typer.Option(-0.20, help="Bust threshold"),
    goal: float = typer.Option(0.50, help="Goal threshold"),
):
    """Run a Monte Carlo simulation."""
    client = RiskManagedClient()
    rprint("[dim]Running Monte Carlo simulation...[/dim]")
    result = client.run_monte_carlo(strategy_id, sims=sims, bust=bust, goal=goal)
    rprint(f"[green]✓[/green] Monte Carlo complete")
    rprint(json.dumps(result, indent=2, default=str))


@app.command("montecarlo-results")
def montecarlo_results(strategy_id: str = typer.Argument(help="Strategy ID")):
    """Get stored Monte Carlo results."""
    client = RiskManagedClient()
    data = client.get_monte_carlo(strategy_id)
    rprint(json.dumps(data, indent=2, default=str))
