"""Agent committee commands (W6.1 + W6.3 + W4.3 — the W6 surface).

The 8 logical groups exposed here mirror the MCP tool surface:
- `templates`         list / get the 3 day-1 hedge-fund templates (W6.1)
- `committees`        list / get / clone / trigger / messages / track-record / set-tier (W6.1)
- `routes`            list / upsert / delete per-user model routes (W3.5)
- `llm`               list / create / test / reveal / update / delete LLM connections (W3.7)
- `news`              list / get articles + list sources (W3.1)
- `macro`             list / get events (W3.2)
- `spend`             get / set your daily token cap (W6.3)
- `proposals`         list pending / get / approve / reject + committee promotion status / events (W4.3)
- `runs`              list recent committee runs with token counts
- `admin-spend`       platform / per-user LLM spend (requires the `admins` role)
- `rollback`          tier rollback via the audit log

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

app = typer.Typer(no_args_is_help=True, help="Agent committees + W6 surface")


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
committees_app = typer.Typer(help="Agent committees (W6.1)")
app.add_typer(committees_app, name="committees")


@committees_app.command("list")
def list_committees(
    enabled_only: bool = typer.Option(True, "--enabled-only/--all"),
):
    """List your committees."""
    rprint(_client().list_committees(enabled_only=enabled_only))


@committees_app.command("get")
def get_committee(instance_id: str = typer.Argument(...)):
    """Get one committee by id."""
    rprint(_client().get_committee(instance_id))


@committees_app.command("clone")
def clone_template(
    template_slug: str = typer.Option(..., "--template-slug"),
    name: str = typer.Option(..., "--name"),
    strategy_id: str = typer.Option("", "--strategy-id"),
    binding_type: str = typer.Option("strategy", "--binding-type"),
    autonomy_tier: str = typer.Option("suggest", "--tier"),
):
    """Clone a day-1 template into a working committee."""
    body = {
        "template_slug": template_slug,
        "name": name,
        "binding_type": binding_type,
        "strategy_id": strategy_id or None,
        "autonomy_tier": autonomy_tier,
    }
    rprint(_client().clone_template(body))


@committees_app.command("trigger")
def trigger_committee(
    instance_id: str = typer.Argument(...),
    symbol: str = typer.Option("BTCUSDT", "--symbol"),
):
    """Run one deliberation cycle. Blocks until {awaiting_user, completed}."""
    rprint(_client().trigger_committee_run(instance_id, {"symbol": symbol}))


@committees_app.command("messages")
def committee_messages(
    instance_id: str = typer.Argument(...),
    since_id: int = typer.Option(0, "--since"),
    limit: int = typer.Option(200, "--limit"),
):
    """Replay the deliberation message bus for a committee."""
    rprint(_client().get_committee_messages(instance_id, since_id, limit))


@committees_app.command("track-record")
def committee_track_record(instance_id: str = typer.Argument(...)):
    """Get the cheap track-record summary for a committee."""
    rprint(_client().get_committee_track_record(instance_id))


@committees_app.command("set-tier")
def set_committee_tier(
    instance_id: str = typer.Argument(...),
    to_tier: str = typer.Option(..., "--to-tier"),
    reason: str = typer.Option("", "--reason"),
):
    """Direct, non-gated tier flip (bypasses evaluate_promotion)."""
    rprint(
        _client().set_committee_tier(
            instance_id,
            {"to_tier": to_tier, "reason": reason or None},
        )
    )


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


# ---- Proposals (W4.3) ----
proposals_app = typer.Typer(help="Proposals + committee promotion (W4.3)")
app.add_typer(proposals_app, name="proposals")


@proposals_app.command("list")
def list_proposals(
    instance_id: str = typer.Option("", "--instance-id"),
):
    """List trade proposals awaiting approval, for one committee
    or across all of yours."""
    rprint(_client().list_pending_proposals(instance_id))


@proposals_app.command("get")
def get_proposal(proposal_id: str = typer.Argument(...)):
    """Get one proposal by id."""
    rprint(_client().get_proposal(proposal_id))


@proposals_app.command("approve")
def approve_proposal(proposal_id: str = typer.Argument(...)):
    """Approve a pending proposal."""
    rprint(_client().approve_proposal(proposal_id))


@proposals_app.command("reject")
def reject_proposal(
    proposal_id: str = typer.Argument(...),
    reason: str = typer.Option("", "--reason"),
):
    """Reject a pending proposal with an optional reason."""
    rprint(
        _client().reject_proposal(
            proposal_id, {"reason": reason}
        )
    )


@proposals_app.command("promotion-status")
def committee_promotion_status(
    instance_id: str = typer.Argument(...),
    to_tier: str = typer.Option("auto_live", "--to-tier"),
):
    """Get the eligibility status of a committee for promotion."""
    rprint(
        _client().get_committee_promotion_status(instance_id, to_tier=to_tier)
    )


@proposals_app.command("promotion-events")
def committee_promotion_events(
    instance_id: str = typer.Argument(...),
    limit: int = typer.Option(5, "--limit"),
):
    """List recent promotion events for a committee (audit log)."""
    rprint(_client().get_committee_promotion_events(instance_id, limit=limit))


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


@rollback_app.command("list")
def list_rollback_candidates(
    instance_id: str = typer.Argument(...),
    limit: int = typer.Option(20, "--limit"),
):
    """List the last N promotion events for the instance, with
    `can_rollback` flags. Only the most recent event can be
    rolled back."""
    rprint(_client().list_rollback_candidates(instance_id, limit=limit))


@rollback_app.command("perform")
def rollback_instance(
    instance_id: str = typer.Argument(...),
    event_id: str = typer.Option(..., "--event-id"),
):
    """Roll the instance's autonomy_tier back to the value it held
    BEFORE the named event was applied. Only the most recent event
    is rollbackable. Writes a new AgentPromotionEvent with
    trigger='rollback'."""
    rprint(
        _client().rollback_instance(instance_id, event_id)
    )


app.add_typer(rollback_app, name="rollback")
