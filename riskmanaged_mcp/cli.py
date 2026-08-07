"""RiskManaged CLI — main entry point."""

import typer
from riskmanaged_mcp.commands import (
    agents,
    auth,
    backtest,
    bias,
    dev,
    grids,
    indicators,
    reference,
    risk,
    signals,
    strategies,
)

app = typer.Typer(
    name="riskmanaged",
    help="CLI for the RiskManaged trading platform. Manage strategies, indicators, backtests, and grids.",
    no_args_is_help=True,
)

app.add_typer(auth.app, name="auth", help="Configure API token and check identity")
app.add_typer(strategies.app, name="strategies", help="Strategy CRUD and management")
app.add_typer(
    indicators.app, name="indicators", help="Indicator types, schemas, and management"
)
app.add_typer(signals.app, name="signals", help="Signal group and rule management")
app.add_typer(bias.app, name="bias", help="Bias generator and rule management")
app.add_typer(risk.app, name="risk", help="Risk management (take-profit, stop-loss)")
app.add_typer(
    backtest.app, name="backtest", help="Backtesting and Monte Carlo simulations"
)
app.add_typer(grids.app, name="grids", help="Grid templates and grid searches")
app.add_typer(
    reference.app, name="reference", help="Reference data: tickers, patterns, constants"
)
app.add_typer(
    agents.app, name="agents", help="Squads + W6 surface (templates, LLM, news, macro, spend, proposals)"
)
app.add_typer(
    dev.app, name="dev", help="Maintainer utilities: regenerate docs and API snapshots"
)


if __name__ == "__main__":
    app()
