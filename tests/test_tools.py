"""Invariants over the MCP tool surface.

These are cheap, offline, and catch the two failure modes that hurt most:

  * **A tool the LLM can see but the server can't run.** `TOOLS` and `_dispatch`
    are two hand-maintained lists that must stay in step. When they drift, the
    model calls a tool it was told about and gets `Unknown tool` back.

  * **A tool that asks the model for someone's user id.** 16 tools used to
    require a `user_id` argument, and the backend checked ownership against that
    same caller-supplied value. The fix moved identity to the API token; this
    file is what stops it coming back.
"""

from __future__ import annotations

import ast
import inspect
import pathlib

import pytest

from riskmanaged_mcp import mcp_server
from riskmanaged_mcp.client import RiskManagedClient

TOOLS = mcp_server.TOOLS
TOOL_NAMES = [t.name for t in TOOLS]
SERVER_SRC = pathlib.Path(inspect.getfile(mcp_server)).read_text()

# The only tools that may take a `user_id`: an admin naming the user they want a
# report *about*. Every other occurrence would be the caller naming themselves,
# which the token already answers.
ADMIN_TOOLS_WITH_TARGET_USER = {
    "admin_per_user_spend",
    "admin_per_user_spend_history",
}


def _dispatched_tool_names() -> set[str]:
    """Every string literal compared against `name` inside `_dispatch`."""
    found: set[str] = set()
    for node in ast.walk(ast.parse(SERVER_SRC)):
        if not isinstance(node, ast.Compare):
            continue
        if not (isinstance(node.left, ast.Name) and node.left.id == "name"):
            continue
        for comparator in node.comparators:
            if isinstance(comparator, ast.Constant) and isinstance(
                comparator.value, str
            ):
                found.add(comparator.value)
    return found


def _client_methods_called_by_dispatch() -> set[str]:
    """Every `client.<method>(...)` the dispatcher invokes."""
    return {
        node.func.attr
        for node in ast.walk(ast.parse(SERVER_SRC))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "client"
    }


class TestToolSchemas:
    @pytest.mark.parametrize("tool", TOOLS, ids=TOOL_NAMES)
    def test_schema_is_a_well_formed_object(self, tool):
        schema = tool.inputSchema
        assert schema.get("type") == "object", f"{tool.name}: not an object schema"
        assert isinstance(schema.get("properties", {}), dict)

    @pytest.mark.parametrize("tool", TOOLS, ids=TOOL_NAMES)
    def test_required_fields_are_declared_as_properties(self, tool):
        """A `required` entry with no matching property is unfillable — the
        model is told a field is mandatory and given no schema for it."""
        schema = tool.inputSchema
        properties = set(schema.get("properties", {}))
        missing = set(schema.get("required", [])) - properties
        assert not missing, f"{tool.name}: required but undeclared: {sorted(missing)}"

    @pytest.mark.parametrize("tool", TOOLS, ids=TOOL_NAMES)
    def test_description_is_useful(self, tool):
        """The description is the only thing the model reads when choosing."""
        assert tool.description, f"{tool.name}: no description"
        assert len(tool.description) > 20, f"{tool.name}: description too thin"

    def test_names_are_unique(self):
        duplicates = {n for n in TOOL_NAMES if TOOL_NAMES.count(n) > 1}
        assert not duplicates, f"duplicate tool names: {sorted(duplicates)}"


class TestIdentityComesFromTheToken:
    """Regression net for the impersonation hole."""

    @pytest.mark.parametrize("tool", TOOLS, ids=TOOL_NAMES)
    def test_no_tool_asks_the_model_for_an_acting_user_id(self, tool):
        if tool.name in ADMIN_TOOLS_WITH_TARGET_USER:
            pytest.skip("admin tools name a target user, not the actor")

        properties = set(tool.inputSchema.get("properties", {}))
        offenders = {p for p in properties if p in ("user_id", "actor_user_id")}
        assert not offenders, (
            f"{tool.name} takes {sorted(offenders)}. Identity must come from the "
            f"API token — a caller-supplied user id is an impersonation hole, "
            f"because the backend checks ownership against the value it was given."
        )

    def test_the_admin_exemption_stays_small(self):
        """Guard the allowlist itself: a new tool must not quietly join it."""
        actual = {
            t.name
            for t in TOOLS
            if "user_id" in t.inputSchema.get("properties", {})
        }
        assert actual == ADMIN_TOOLS_WITH_TARGET_USER, (
            "the set of tools taking a user_id changed; if this is a new admin "
            "report endpoint, add it deliberately — otherwise it is a regression"
        )


class TestDispatchCoverage:
    def test_every_declared_tool_is_dispatchable(self):
        """Otherwise the model calls it and gets `Unknown tool`."""
        undispatched = set(TOOL_NAMES) - _dispatched_tool_names()
        assert not undispatched, (
            f"declared in TOOLS but unreachable in _dispatch: {sorted(undispatched)}"
        )

    def test_every_dispatch_branch_is_a_declared_tool(self):
        """A dispatch branch with no `Tool()` is dead code the model can never
        reach — usually a rename that only got applied on one side."""
        orphaned = _dispatched_tool_names() - set(TOOL_NAMES)
        assert not orphaned, (
            f"dispatched but not declared in TOOLS: {sorted(orphaned)}"
        )

    def test_dispatch_only_calls_real_client_methods(self):
        """`_dispatch` is one long if-chain; a typo'd method name is invisible
        until that exact tool is called at runtime."""
        missing = sorted(
            m
            for m in _client_methods_called_by_dispatch()
            if not hasattr(RiskManagedClient, m)
        )
        assert not missing, f"_dispatch calls non-existent client methods: {missing}"

    def test_unknown_tool_is_rejected(self):
        with pytest.raises(ValueError, match="Unknown tool"):
            mcp_server._dispatch(object(), "no_such_tool", {})


class TestContextResource:
    """`context.md` is served straight into the model's context, so its
    absence would silently degrade every session."""

    def test_context_file_is_shipped_with_the_package(self):
        assert mcp_server.CONTEXT_FILE.exists(), (
            "context.md must be packaged — it is the agent's primary guide"
        )

    def test_context_is_not_empty(self):
        assert len(mcp_server.CONTEXT_FILE.read_text().strip()) > 500
