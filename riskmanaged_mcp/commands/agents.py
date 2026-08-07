"""Agent committee commands (W6.1 + W6.3 + W4.3 — the W6 surface).

The 8 logical groups exposed here mirror the MCP tool surface:
- `templates`         list / get the 3 day-1 hedge-fund templates (W6.1)
- `committees`        list / get / clone / messages / markets / cadence /
                      readings / decisions
- `routes`            list / upsert / delete per-user model routes (W3.5)
- `llm`               list / create / test / reveal / update / delete LLM connections (W3.7)
- `news`              list / get articles + list sources (W3.1)
- `macro`             list / get events (W3.2)
- `spend`             get / set your daily token cap (W6.3)
- `runs`              list recent committee runs with token counts
- `admin-spend`       platform / per-user LLM spend (requires the `admins` role)

Each command is a thin Typer wrapper over the corresponding
`RiskManagedClient` method, which hits /api/external/agent/*.

No command takes a `--user-id` for the acting user: the server reads identity
from the API token. The only exceptions are under `admin-spend`, where the id
names the user being reported *on*.
"""

import json

import typer
from rich import print as rprint
from rich.table import Table
from riskmanaged_mcp.client import RiskManagedClient

app = typer.Typer(no_args_is_help=True, help="Squads + W6 surface")


def _client():
    return RiskManagedClient()


# ---- Templates (W6.1) ----
templates_app = typer.Typer(help="Hedge-fund templates (W6.1)")
app.add_typer(templates_app, name="templates")


@templates_app.command("list")
def list_templates(enabled_only: bool = typer.Option(True)):
    """List the day-1 hedge-fund templates."""
    resp = _client().list_templates(enabled_only=enabled_only)
    table = Table(title="Templates")
    table.add_column("Slug", style="bold")
    table.add_column("Name")
    table.add_column("Cast")
    for t in resp.get("templates", []):
        table.add_row(
            t.get("slug", ""),
            t.get("name", ""),
            str(len(t.get("cast") or [])),
        )
    rprint(table)


@templates_app.command("get")
def get_template(slug: str = typer.Argument(...)):
    """Get one template by slug."""
    rprint(_client().get_template(slug))


# ---- Committees (W6.1) ----
committees_app = typer.Typer(help="Squads — config, markets, readings, decisions")
app.add_typer(committees_app, name="committees")


@committees_app.command("list")
def list_committees(
    enabled_only: bool = typer.Option(True, "--enabled-only/--all"),
):
    """List your squads."""
    rprint(_client().list_committees(enabled_only=enabled_only))


@committees_app.command("get")
def get_committee(instance_id: str = typer.Argument(...)):
    """Get one squad by id."""
    rprint(_client().get_committee(instance_id))


@committees_app.command("clone")
def clone_template(
    template_slug: str = typer.Option(..., "--template-slug"),
    name: str = typer.Option(..., "--name"),
    strategy_id: str = typer.Option("", "--strategy-id"),
    binding_type: str = typer.Option("strategy", "--binding-type"),
    autonomy_tier: str = typer.Option("suggest", "--tier"),
):
    """Clone a day-1 template into a working squad."""
    body = {
        "template_slug": template_slug,
        "name": name,
        "binding_type": binding_type,
        "strategy_id": strategy_id or None,
        "autonomy_tier": autonomy_tier,
    }
    rprint(_client().clone_template(body))


@committees_app.command("messages")
def committee_messages(
    instance_id: str = typer.Argument(...),
    since_id: int = typer.Option(0, "--since"),
    limit: int = typer.Option(200, "--limit"),
):
    """Replay the deliberation message bus for a squad."""
    rprint(_client().get_committee_messages(instance_id, since_id, limit))






# ---- Model routes (W3.5) ----
routes_app = typer.Typer(help="Per-user model routes (W3.5)")
app.add_typer(routes_app, name="routes")


@routes_app.command("list")
def list_routes():
    """List your per-task-class LLM routes."""
    rprint(_client().list_model_routes())


@routes_app.command("upsert")
def upsert_route(
    task_class: str = typer.Option(..., "--task-class"),
    provider: str = typer.Option(..., "--provider"),
    model: str = typer.Option(..., "--model"),
    connection_id: str = typer.Option("", "--connection-id"),
):
    """Create or update a route for one task class."""
    body = {
        "task_class": task_class,
        "provider": provider,
        "model": model,
        "connection_id": connection_id or None,
    }
    rprint(_client().upsert_model_route(body))


@routes_app.command("delete")
def delete_route(
    task_class: str = typer.Option(..., "--task-class"),
):
    """Delete the route for one task class."""
    rprint(_client().delete_model_route(task_class))


# ---- LLM connections (W3.7) ----
llm_app = typer.Typer(help="LLM connections (W3.7)")
app.add_typer(llm_app, name="llm")


@llm_app.command("list")
def list_connections():
    """List your LLM credentials (platform + direct + remote)."""
    rprint(_client().list_llm_connections())


@llm_app.command("create")
def create_connection(
    provider: str = typer.Option(..., "--provider"),
    label: str = typer.Option(..., "--label"),
    api_key: str = typer.Option(..., "--api-key"),
    endpoint: str = typer.Option("", "--endpoint"),
):
    """Create a direct (user-provided) LLM connection. Key is Fernet-encrypted server-side."""
    body = {
        "provider": provider,
        "label": label,
        "api_key": api_key,
        "endpoint": endpoint or None,
    }
    rprint(_client().create_llm_connection(body))


@llm_app.command("test")
def test_connection(connection_id: str = typer.Argument(...)):
    """Ping a connection to verify the credentials work."""
    rprint(_client().test_llm_connection(connection_id))


@llm_app.command("reveal")
def reveal_connection(connection_id: str = typer.Argument(...)):
    """Reveal the decrypted API key for a direct connection (sparingly)."""
    rprint(_client().reveal_llm_connection_key(connection_id))


@llm_app.command("update")
def update_connection(
    connection_id: str = typer.Argument(...),
    label: str = typer.Option("", "--label"),
    endpoint: str = typer.Option("", "--endpoint"),
):
    """Update a connection (label, endpoint, is_active)."""
    body = {}
    if label:
        body["label"] = label
    if endpoint:
        body["endpoint"] = endpoint
    rprint(_client().update_llm_connection(connection_id, body))


@llm_app.command("delete")
def delete_connection(connection_id: str = typer.Argument(...)):
    """Delete a direct or remote LLM connection."""
    rprint(_client().delete_llm_connection(connection_id))


# ---- News (W3.1) ----
news_app = typer.Typer(help="News articles + sources (W3.1)")
app.add_typer(news_app, name="news")


@news_app.command("list")
def list_news(
    symbol: str = typer.Option(None, "--symbol"),
    source_id: str = typer.Option(None, "--source"),
    since: str = typer.Option(None, "--since"),
    limit: int = typer.Option(50, "--limit"),
):
    """List recent news articles."""
    params = {"limit": limit}
    if symbol:
        params["symbol"] = symbol
    if source_id:
        params["source_id"] = source_id
    if since:
        params["since"] = since
    rprint(_client().list_news_articles(**params))


@news_app.command("get")
def get_news(article_id: str = typer.Argument(...)):
    """Get one news article by id."""
    rprint(_client().get_news_article(article_id))


@news_app.command("sources")
def news_sources():
    """List the user's news sources."""
    rprint(_client().list_news_sources())


# ---- Macro (W3.2) ----
macro_app = typer.Typer(help="Macro events (W3.2)")
app.add_typer(macro_app, name="macro")


@macro_app.command("list")
def list_macro(
    since: str = typer.Option(None, "--since"),
    until: str = typer.Option(None, "--until"),
    importance: str = typer.Option(None, "--importance"),
    limit: int = typer.Option(50, "--limit"),
):
    """List macro events (FOMC, CPI, etc.)."""
    params = {"limit": limit}
    if since:
        params["since"] = since
    if until:
        params["until"] = until
    if importance:
        params["importance"] = importance
    rprint(_client().list_macro_events(**params))


@macro_app.command("get")
def get_macro(event_id: str = typer.Argument(...)):
    """Get one macro event by id."""
    rprint(_client().get_macro_event(event_id))


# ---- User settings (W6.3) ----
spend_app = typer.Typer(help="User settings + daily spend cap (W6.3)")
app.add_typer(spend_app, name="spend")


@spend_app.command("get")
def get_spend_cap():
    """Get your daily token cap + today's spend so far."""
    rprint(_client().get_user_settings())


@spend_app.command("set")
def set_spend_cap(
    cap: int = typer.Option(
        -1, "--cap",
        help="Daily token cap (int >= 0). Use 0 to clear.",
    ),
):
    """Set or clear your daily token cap."""
    rprint(_client().set_daily_token_cap(cap if cap >= 0 else None))


# ---- Cadence, markets, readings and decisions ----


@committees_app.command("board")
def committee_board(instance_id: str = typer.Argument(...)):
    """One row per covered market: current call, standing, next wake."""
    rprint(_client().get_committee_cadence_board(instance_id))


@committees_app.command("decisions")
def committee_decisions(
    instance_id: str = typer.Argument(...),
    symbol: str = typer.Option("", "--symbol"),
    limit: int = typer.Option(50, "--limit"),
):
    """A squad's recent decisions, newest first. The newest is unscored —
    it is graded when the next one supplies a closing price."""
    rprint(_client().list_committee_decisions(instance_id, symbol=symbol, limit=limit))


@committees_app.command("standing")
def committee_standing(
    instance_id: str = typer.Argument(...),
    symbol: str = typer.Option("", "--symbol"),
):
    """Cumulative points, recent form, accuracy and streak."""
    rprint(_client().get_committee_decision_summary(instance_id, symbol=symbol))


@committees_app.command("cadence")
def committee_cadence(
    instance_id: str = typer.Argument(...),
    enabled: bool = typer.Option(None, "--enabled/--disabled"),
    interval_seconds: int = typer.Option(None, "--interval-seconds"),
    context_bars: int = typer.Option(None, "--context-bars"),
    deadband_pct: float = typer.Option(None, "--deadband-pct"),
):
    """Configure how a squad wakes. Interval has a 30-minute floor."""
    body = {}
    if enabled is not None:
        body["cadence_enabled"] = enabled
    if interval_seconds is not None:
        body["cadence_interval_seconds"] = interval_seconds
    if context_bars is not None:
        body["context_bars"] = context_bars
    if deadband_pct is not None:
        body["score_deadband_pct"] = deadband_pct
    rprint(_client().set_committee_cadence(instance_id, body))


@committees_app.command("markets")
def committee_markets(instance_id: str = typer.Argument(...)):
    """The markets a squad covers."""
    rprint(_client().list_committee_markets(instance_id))


@committees_app.command("add-market")
def committee_add_market(
    instance_id: str = typer.Argument(...),
    symbol: str = typer.Argument(..., help="e.g. BTCUSDT"),
):
    """Cover a market. Idempotent — re-adding re-enables a paused one."""
    rprint(_client().add_committee_market(instance_id, symbol))


@committees_app.command("remove-market")
def committee_remove_market(
    instance_id: str = typer.Argument(...),
    symbol: str = typer.Argument(...),
):
    """Stop covering a market. Its past decisions are kept."""
    rprint(_client().remove_committee_market(instance_id, symbol))


@committees_app.command("readings")
def committee_readings(instance_id: str = typer.Argument(...)):
    """The indicator readings fed to the specialists."""
    rprint(_client().get_committee_readings(instance_id))


@committees_app.command("set-readings")
def committee_set_readings(
    instance_id: str = typer.Argument(...),
    indicators: str = typer.Option(..., "--indicators", help="JSON map"),
):
    """Replace the whole reading map. Omit `ticker` — a reading is computed
    per covered market."""
    import json as _json

    rprint(_client().set_committee_readings(instance_id, _json.loads(indicators)))


# ---- W6.5 — Observability (runs + spend) ----

runs_app = typer.Typer(help="Per-instance run history (W6.5)")

@runs_app.command("list")
def list_instance_runs(
    instance_id: str = typer.Argument(...),
    limit: int = typer.Option(50, "--limit"),
):
    """List the last N runs for an instance, with token counts."""
    rprint(_client().list_instance_runs(instance_id, limit=limit))


# NB: a distinct name from the W6.3 `spend_app` above. Both used to be
# bound to `spend_app` and registered as "spend", so this group silently
# shadowed the daily-cap commands and `agents spend get|set` were
# unreachable.
admin_spend_app = typer.Typer(help="LLM spend observability (W6.5 — admin-only)")

@admin_spend_app.command("user")
def spend_user(user_id: str = typer.Option(..., "--user-id")):
    """Per-user LLM spend for today UTC. ADMIN-ONLY."""
    rprint(_client().admin_per_user_spend(user_id))


@admin_spend_app.command("user-history")
def spend_user_history(
    user_id: str = typer.Option(..., "--user-id"),
    days: int = typer.Option(30, "--days"),
):
    """Per-user daily spend for the last N days. ADMIN-ONLY."""
    rprint(_client().admin_per_user_spend_history(user_id, days=days))


@admin_spend_app.command("platform")
def spend_platform():
    """Platform-wide spend for today UTC. ADMIN-ONLY."""
    rprint(_client().admin_platform_spend_today())


# Register the new subcommand groups on the parent `app`.
app.add_typer(runs_app, name="runs")
app.add_typer(admin_spend_app, name="admin-spend")


# ---- W6.5 — Rollback (tier flip via the audit log) ----

rollback_app = typer.Typer(help="Tier rollback via the audit log (W6.5)")






app.add_typer(rollback_app, name="rollback")
