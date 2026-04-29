"""Auth commands — configure token, check identity."""

import typer
from rich import print as rprint
from riskmanaged_mcp import config

app = typer.Typer(no_args_is_help=True)


@app.command()
def configure(
    token: str = typer.Option(..., help="Your RiskManaged API token"),
    url: str = typer.Option("https://riskmanaged.io", help="Base URL of the platform"),
):
    """Save API token and base URL to ~/.riskmanaged/config.json."""
    config.set_credentials(token, url)
    rprint(f"[green]✓[/green] Credentials saved to {config.CONFIG_FILE}")


@app.command()
def whoami():
    """Check who you are authenticated as."""
    from riskmanaged_mcp.client import RiskManagedClient

    try:
        client = RiskManagedClient()
        me = client.get_me()
        rprint(f"[bold]Username:[/bold] {me['username']}")
        rprint(f"[bold]Plan:[/bold]     {me.get('current_plan', 'free')}")
        rprint(f"[bold]Tokens:[/bold]   {me.get('token_balance', 0)}")
    except Exception as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
