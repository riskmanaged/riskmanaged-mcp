"""Generate the tool tables that appear in the docs.

Three documents used to carry hand-maintained tool tables, and they disagreed
with each other and with the code: 30 tools, "30+" tools, and 66 tools, against
an actual 71. Hand-maintaining the same list in three places has exactly one
outcome.

So the tables are generated from `TOOLS` and spliced between markers:

    <!-- BEGIN GENERATED TOOLS -->
    ...
    <!-- END GENERATED TOOLS -->

`riskmanaged dev sync-docs` rewrites them; `tests/test_docs.py` fails when a
document's block is stale.
"""

from __future__ import annotations

import re
from pathlib import Path

from riskmanaged_mcp.mcp_server import TOOLS

BEGIN = "<!-- BEGIN GENERATED TOOLS -->"
END = "<!-- END GENERATED TOOLS -->"

_BLOCK = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)

# Ordered category → the tools it contains. Anything unlisted lands in "Other",
# which is itself a signal that a new tool was added without being placed.
CATEGORIES: list[tuple[str, tuple[str, ...]]] = [
    ("Account", ("get_me",)),
    (
        "Reference",
        (
            "list_indicator_types",
            "get_indicator_schema",
            "list_patterns",
            "search_tickers",
            "get_constants",
        ),
    ),
    (
        "Strategies",
        (
            "list_strategies",
            "get_strategy",
            "create_strategy",
            "update_strategy",
            "delete_strategy",
        ),
    ),
    ("Indicators", ("add_indicator", "delete_indicator", "remove_indicator")),
    ("Signals", ("add_signal_group", "add_signal_rule", "delete_signal_rule")),
    ("Bias", ("add_bias_generator", "add_bias_rule")),
    ("Risk", ("set_stop_loss", "set_take_profit")),
    (
        "Backtest",
        ("run_backtest", "get_reports", "get_backtest_results", "run_monte_carlo"),
    ),
    ("Versioning", ("commit_version", "get_versions", "list_versions", "restore_version")),
    (
        "Grids",
        (
            "create_grid_template",
            "update_grid_template",
            "check_variations",
            "create_grid",
            "get_grid",
        ),
    ),
    ("Community", ("share_strategy",)),
    ("Committee templates", ("list_templates", "get_template")),
    (
        "Committees",
        (
            "list_committees",
            "get_committee",
            "clone_template",
            "trigger_committee_run",
            "get_committee_messages",
            "get_committee_track_record",
            "set_committee_tier",
            "list_instance_runs",
        ),
    ),
    (
        "Promotion",
        (
            "get_committee_promotion_status",
            "get_committee_promotion_events",
            "list_rollback_candidates",
            "rollback_instance",
        ),
    ),
    (
        "Proposals",
        ("list_pending_proposals", "get_proposal", "approve_proposal", "reject_proposal"),
    ),
    ("Model routes", ("list_model_routes", "upsert_model_route", "delete_model_route")),
    (
        "LLM connections",
        (
            "list_llm_connections",
            "create_llm_connection",
            "test_llm_connection",
            "reveal_llm_connection_key",
            "update_llm_connection",
            "delete_llm_connection",
        ),
    ),
    ("News", ("list_news_articles", "get_news_article", "list_news_sources")),
    ("Macro", ("list_macro_events", "get_macro_event")),
    ("Spend caps", ("get_user_settings", "set_daily_token_cap")),
    (
        "Admin (requires the admins role)",
        (
            "admin_per_user_spend",
            "admin_per_user_spend_history",
            "admin_platform_spend_today",
        ),
    ),
]


def render_tool_table() -> str:
    """The generated block, markers included."""
    available = {t.name for t in TOOLS}
    placed: set[str] = set()

    rows = [
        f"_{len(TOOLS)} tools. This table is generated — "
        f"run `riskmanaged dev sync-docs` after changing them._",
        "",
        "| Category | Tools |",
        "|---|---|",
    ]

    for category, names in CATEGORIES:
        present = [n for n in names if n in available]
        placed.update(present)
        if present:
            rows.append(
                f"| **{category}** | " + ", ".join(f"`{n}`" for n in present) + " |"
            )

    leftover = sorted(available - placed)
    if leftover:
        rows.append(
            "| **Other** | " + ", ".join(f"`{n}`" for n in leftover) + " |"
        )

    return "\n".join([BEGIN, *rows, END])


def update_doc(path: Path) -> bool:
    """Rewrite the generated block in `path`. True if the file changed."""
    text = path.read_text()
    if BEGIN not in text:
        return False
    updated = _BLOCK.sub(lambda _: render_tool_table(), text)
    if updated == text:
        return False
    path.write_text(updated)
    return True


def block_is_current(path: Path) -> bool:
    """False when the file's generated block no longer matches `TOOLS`."""
    text = path.read_text()
    match = _BLOCK.search(text)
    if match is None:
        return True  # nothing generated in this file
    return match.group(0) == render_tool_table()
