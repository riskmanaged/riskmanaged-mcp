"""Auth commands — OAuth login, manual token, whoami, logout.

W6.4: the primary flow is `riskmanaged auth login` — opens a
browser, walks the user through the /mcp-authorize page, and
saves the minted API token to ~/.riskmanaged/config.json with
chmod 600. The legacy `configure --token ...` flow is kept for
automation + CI use.
"""

import typer
from rich import print as rprint
from riskmanaged_mcp import config

app = typer.Typer(no_args_is_help=True)


@app.command()
def login(
    url: str = typer.Option(
        "https://agent.riskmanaged.io",
        "--url",
        "-u",
        help="Base URL of the RiskManaged platform",
    ),
):
    """Open the browser, walk through the /mcp-authorize flow, save the token.

    The CLI binds a localhost listener on a random port, opens
    the browser to the authorize page, waits up to 60s for the
    user to click "Authorize", and saves the resulting API token
    to ~/.riskmanaged/config.json (chmod 600).
    """
    from riskmanaged_mcp.oauth import oauth_login, save_credentials

    rprint(f"[bold]Logging in to {url}...[/bold]")
    try:
        token, base_url = oauth_login(url)
    except TimeoutError as e:
        rprint(f"[red]Timeout:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]Login failed:[/red] {e}")
        raise typer.Exit(1)
    save_credentials(token, base_url)
    rprint(f"[green]✓[/green] Logged in. Token saved to {config.CONFIG_FILE}")


@app.command()
def configure(
    token: str = typer.Option(..., help="Your RiskManaged API token"),
    url: str = typer.Option(
        "https://agent.riskmanaged.io",
        "--url",
        help="Base URL of the platform",
    ),
):
    """Save an API token directly (no browser). For automation + CI use.

    For interactive use, prefer `riskmanaged auth login` (the OAuth
    browser flow).
    """
    config.set_credentials(token, url)
    rprint(f"[green]✓[/green] Credentials saved to {config.CONFIG_FILE}")


@app.command()
def logout():
    """Remove the locally-saved token. Does NOT revoke the server-side token."""
    cfg = config.load_config()
    if "token" not in cfg:
        rprint("No token configured.")
        return
    cfg.pop("token", None)
    config.save_config(cfg)
    rprint("[green]✓[/green] Local token removed.")
    rprint(
        "[yellow]Note:[/yellow] the server-side token is still active. "
        "Revoke it from your profile page to invalidate it."
    )


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
