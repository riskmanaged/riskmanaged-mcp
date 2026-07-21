"""Every CLI command loads and can describe itself.

Typer builds its command tree from function signatures at import time, so a
malformed default or an unsupported annotation raises when the group is
*rendered*, not when the module is imported. That makes such breakage invisible
to a smoke test that only imports — and invisible to every other command, since
each group fails independently.

The other thing pinned here is group uniqueness. `commands/agents.py` once bound
two different Typer apps to the same variable and registered both under the name
`spend`; the second silently shadowed the first, and `agents spend get|set`
became unreachable while every import still succeeded and every other command
still worked.
"""

from __future__ import annotations

import ast
import inspect
import pathlib

import pytest
import typer
from typer.testing import CliRunner

from riskmanaged_mcp import cli as cli_module
from riskmanaged_mcp.client import RiskManagedClient

runner = CliRunner()

COMMANDS_DIR = pathlib.Path(inspect.getfile(cli_module)).parent / "commands"


def _walk(app: typer.Typer, prefix: tuple[str, ...] = ()):
    """Yield the argv path of every group and leaf command in the tree."""
    for command in app.registered_commands:
        name = command.name or command.callback.__name__.replace("_", "-")
        yield prefix + (name,)
    for group in app.registered_groups:
        group_path = prefix + (group.name,)
        yield group_path
        yield from _walk(group.typer_instance, group_path)


ALL_PATHS = sorted(_walk(cli_module.app))
GROUP_PATHS = sorted(
    prefix + (g.name,)
    for prefix, app in [((), cli_module.app)]
    for g in app.registered_groups
)
LEAF_PATHS = [p for p in ALL_PATHS if p not in set(GROUP_PATHS)]


class TestCommandTreeRenders:
    def test_root_help(self):
        result = runner.invoke(cli_module.app, ["--help"])
        assert result.exit_code == 0, result.output

    @pytest.mark.parametrize("path", ALL_PATHS, ids=[" ".join(p) for p in ALL_PATHS])
    def test_help_renders(self, path):
        """Exit 0 means Typer successfully built this command's signature."""
        result = runner.invoke(cli_module.app, [*path, "--help"])
        assert result.exit_code == 0, (
            f"`riskmanaged {' '.join(path)} --help` failed:\n{result.output}"
        )

    def test_the_tree_is_not_accidentally_empty(self):
        """Guard the guard: if `_walk` stopped finding commands, every
        parametrised test above would vacuously pass."""
        assert len(ALL_PATHS) > 80, f"only found {len(ALL_PATHS)} commands"


class TestGroupRegistration:
    def test_group_names_are_unique(self):
        """Two groups sharing a name means one is unreachable."""

        def _check(app: typer.Typer, where: str):
            names = [g.name for g in app.registered_groups]
            dupes = {n for n in names if names.count(n) > 1}
            assert not dupes, f"{where}: duplicate sub-group names {sorted(dupes)}"
            for group in app.registered_groups:
                _check(group.typer_instance, f"{where} {group.name}")

        _check(cli_module.app, "riskmanaged")

    def test_command_names_are_unique_within_a_group(self):
        def _check(app: typer.Typer, where: str):
            names = [
                c.name or c.callback.__name__ for c in app.registered_commands
            ]
            dupes = {n for n in names if names.count(n) > 1}
            assert not dupes, f"{where}: duplicate command names {sorted(dupes)}"
            for group in app.registered_groups:
                _check(group.typer_instance, f"{where} {group.name}")

        _check(cli_module.app, "riskmanaged")

    def test_daily_spend_cap_commands_are_reachable(self):
        """The exact regression: the W6.5 admin spend group shadowed the W6.3
        daily-cap group, so these two commands could not be invoked."""
        for sub in ("get", "set"):
            result = runner.invoke(cli_module.app, ["agents", "spend", sub, "--help"])
            assert result.exit_code == 0, (
                f"`agents spend {sub}` unreachable:\n{result.output}"
            )


class TestCommandsCallRealClientMethods:
    def test_no_command_calls_a_nonexistent_client_method(self):
        """Command bodies call `_client().something()`. A typo or a renamed
        client method only surfaces when a user runs that exact command."""
        missing: dict[str, set[str]] = {}

        for path in sorted(COMMANDS_DIR.glob("*.py")):
            called = {
                node.func.attr
                for node in ast.walk(ast.parse(path.read_text()))
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                # Specifically `_client().method(...)`. Matching any `x().y()`
                # also catches dict `.get()` chains and `Path(...).resolve()`.
                and isinstance(node.func.value, ast.Call)
                and isinstance(node.func.value.func, ast.Name)
                and node.func.value.func.id == "_client"
            }
            bad = {m for m in called if not hasattr(RiskManagedClient, m)}
            if bad:
                missing[path.name] = bad

        assert not missing, f"commands calling non-existent client methods: {missing}"


class TestCliIsOffline:
    def test_help_never_needs_credentials(self, monkeypatch):
        """`--help` must work before `auth login`. Constructing the client at
        import or decoration time would break first-run UX."""
        monkeypatch.delenv("RISKMANAGED_TOKEN", raising=False)
        monkeypatch.delenv("RISKMANAGED_URL", raising=False)

        result = runner.invoke(cli_module.app, ["--help"])
        assert result.exit_code == 0, result.output
