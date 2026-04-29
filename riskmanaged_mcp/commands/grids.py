"""Grid template and grid search commands."""

import json

import typer
from rich import print as rprint
from rich.table import Table
from riskmanaged_mcp.client import RiskManagedClient

app = typer.Typer(no_args_is_help=True)


@app.command("create-template")
def create_template(strategy_id: str = typer.Argument(help="Strategy ID")):
    """Create a grid template from a strategy."""
    client = RiskManagedClient()
    result = client.create_grid_template(strategy_id)
    rprint(f"[green]✓[/green] Template created")
    rprint(json.dumps(result, indent=2, default=str))


@app.command("list-templates")
def list_templates():
    """List your grid templates."""
    client = RiskManagedClient()
    templates = client.list_grid_templates()
    table = Table(title="Grid Templates")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="bold")
    for t in templates:
        table.add_row(str(t.get("id", "")), t.get("name", ""))
    rprint(table)


@app.command("get-template")
def get_template(template_id: str = typer.Argument(help="Template ID")):
    """Get a grid template's details."""
    client = RiskManagedClient()
    data = client.get_grid_template(template_id)
    rprint(json.dumps(data, indent=2, default=str))


@app.command("update-template")
def update_template(
    template_id: str = typer.Argument(help="Template ID"),
    data: str = typer.Option("{}", help="JSON body: {template_data: {...}, name: ...}"),
):
    """Update a grid template."""
    client = RiskManagedClient()
    body = json.loads(data)
    result = client.update_grid_template(template_id, body)
    rprint(f"[green]✓[/green] Template updated")


@app.command("variations")
def variations(template_id: str = typer.Argument(help="Template ID")):
    """Check the number of variations for a template."""
    client = RiskManagedClient()
    result = client.check_variations(template_id)
    rprint(json.dumps(result, indent=2))


@app.command("create")
def create(template_id: str = typer.Argument(help="Template ID")):
    """Create a grid search from a template (costs tokens)."""
    client = RiskManagedClient()
    rprint("[dim]Creating grid search...[/dim]")
    result = client.create_grid(template_id)
    rprint(f"[green]✓[/green] Grid created")
    rprint(json.dumps(result, indent=2, default=str))


@app.command("list")
def list_grids():
    """List your grid searches."""
    client = RiskManagedClient()
    grids = client.list_grids()
    table = Table(title="Grids")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Variations")
    for g in grids:
        table.add_row(
            str(g.get("id", ""))[:8],
            g.get("name", ""),
            str(g.get("variation_count", "")),
        )
    rprint(table)


@app.command("get")
def get_grid(grid_id: str = typer.Argument(help="Grid ID")):
    """Get grid search results."""
    client = RiskManagedClient()
    data = client.get_grid(grid_id)
    rprint(json.dumps(data, indent=2, default=str))


@app.command("archive")
def archive(grid_id: str = typer.Argument(help="Grid ID")):
    """Archive all variations in a grid."""
    client = RiskManagedClient()
    result = client.archive_grid(grid_id)
    rprint(f"[green]✓[/green] {result}")
