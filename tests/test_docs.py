"""The documentation must describe the software that exists.

These docs are not prose for humans to skim — `context.md` is served straight
into an LLM's context as an MCP resource, and `cron.md` is executed step by step
by an autonomous agent. A wrong field name in them is not a typo; it is a bug
with a delayed fuse.

And they had gone badly wrong. Every doc claimed an indicator's default name was
`{type}_{ticker}_{timeframe}`, so every worked example referenced lines like
`RSI_btcusdt_30m.rsi`. The real default is the bare class name, so the real line
is `RSI.rsi` — meaning every documented signal rule returned 422. Worse,
`StopLossSimple` was documented with a `stop_pct` key when the field is
`stoploss_pct`; because Pydantic ignored unknown keys, that produced a −5%
default stop reported as success.

Six rules, checked offline against the vendored snapshot. Between them they
would have caught every one of those errors on the day it was written.
"""

from __future__ import annotations

import json
import re

import pytest
import typer

from riskmanaged_mcp import config, mcp_server
from riskmanaged_mcp.cli import app as cli_app
from riskmanaged_mcp.client import RiskManagedClient

from .conftest import PACKAGE_ROOT, REPO_ROOT, SNAPSHOT_DIR

# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

DOCS = {
    "AGENTS.md": REPO_ROOT / "AGENTS.md",
    "AGENT.md": REPO_ROOT / "AGENT.md",
    "README.md": REPO_ROOT / "README.md",
    "cron.md": REPO_ROOT / "cron.md",
    "context.md": PACKAGE_ROOT / "context.md",
}
PRESENT = {name: path for name, path in DOCS.items() if path.exists()}

_REFERENCE = json.loads((SNAPSHOT_DIR / "reference.json").read_text())
INDICATORS: dict = _REFERENCE["indicators"]
RISK: dict = _REFERENCE["risk"]

TOOL_NAMES = {t.name for t in mcp_server.TOOLS}
CLIENT_METHODS = {m for m in dir(RiskManagedClient) if not m.startswith("_")}

# Lines that exist without an indicator — raw OHLCV columns are always valid.
OHLCV = {"open", "high", "low", "close", "volume"}

# A backticked identifier shaped like a tool name: verb_noun.
_TOOLISH = re.compile(
    r"^(get|list|create|update|delete|set|add|remove|run|share|approve|reject"
    r"|trigger|clone|commit|restore|check|archive|unarchive|test|reveal"
    r"|rollback|upsert|search)_[a-z0-9_]+$"
)
_BACKTICKED = re.compile(r"`([^`\n]+)`")
_FENCE = re.compile(r"```[a-zA-Z]*\n(.*?)```", re.S)
# Deliberately permissive on the prefix: `RSI_btcusdt_30m.rsi` must match so it
# can be rejected. Restricting to `[A-Z][A-Za-z0-9]*` would let the fictional
# forms slip past this rule entirely.
_LINE_REF = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)\.([a-z][a-z0-9_]*)\b")

# Real API field names that happen to look like verb_noun tool names.
_API_FIELD_NAMES = (
    {"trigger_line", "threshold_line", "threshold_value", "trigger_action",
     "trigger_direction", "trigger_line_shift", "threshold_line_shift",
     "set_published_mapping", "check_variations"}
    | {f for d in INDICATORS.values() for f in d["config_fields"]}
    | {ln for d in INDICATORS.values() for ln in d["lines"]}
    | {f for d in RISK.values() for f in d["config_fields"]}
)
_URL = re.compile(r"RISKMANAGED_URL[\"'\s:=]+[\"']?(https?://[^\s\"'`,]+)")


def _read(name: str) -> str:
    return PRESENT[name].read_text()


def _fences(text: str) -> list[str]:
    return _FENCE.findall(text)


DOC_IDS = sorted(PRESENT)


def _requires_docs():
    if not PRESENT:  # pragma: no cover
        pytest.skip("no docs found")


# ---------------------------------------------------------------------------
# Rule 1 — every tool named in the docs exists
# ---------------------------------------------------------------------------


class TestToolNames:
    @pytest.mark.docs
    @pytest.mark.parametrize("doc", DOC_IDS)
    def test_named_tools_are_real(self, doc):
        """Catches the three tool tables that disagreed with each other and
        with the code (30 / "30+" / 66 against an actual 71)."""
        text = _read(doc)
        mentioned = {
            token
            for token in _BACKTICKED.findall(text)
            if _TOOLISH.match(token)
        }
        # A doc may legitimately name a CLI-only client method in prose, and
        # some real request/config fields are shaped like tool names.
        unknown = sorted(mentioned - TOOL_NAMES - CLIENT_METHODS - _API_FIELD_NAMES)
        assert not unknown, (
            f"{doc} refers to tools that do not exist: {unknown}"
        )


# ---------------------------------------------------------------------------
# Rule 2 — every CLI example is runnable
# ---------------------------------------------------------------------------


def _cli_examples() -> list[tuple[str, str]]:
    """`(doc, command)` for every `riskmanaged …` line in a fenced block."""
    found = []
    for doc in PRESENT:
        for block in _fences(_read(doc)):
            for raw in block.splitlines():
                line = raw.strip().lstrip("$").strip()
                if line.startswith("riskmanaged ") and not line.startswith(
                    "riskmanaged-mcp"
                ):
                    found.append((doc, line))
    return found


CLI_EXAMPLES = _cli_examples()


def _resolve(argv: list[str]) -> tuple[bool, str]:
    """Walk the click tree, validating each group/command and its flags."""
    command = typer.main.get_command(cli_app)
    consumed: list[str] = []

    index = 0
    while index < len(argv):
        token = argv[index]
        if token.startswith("-"):
            break
        if not hasattr(command, "commands"):
            break
        child = command.commands.get(token)
        if child is None:
            return False, (
                f"`{' '.join(['riskmanaged'] + consumed)}` has no subcommand "
                f"{token!r} (available: {sorted(command.commands)})"
            )
        command, consumed = child, consumed + [token]
        index += 1

    flags = {
        opt
        for param in getattr(command, "params", [])
        for opt in getattr(param, "opts", []) + getattr(param, "secondary_opts", [])
    }
    for token in argv[index:]:
        if not token.startswith("--"):
            continue
        name = token.split("=", 1)[0]
        if name in {"--help"}:
            continue
        if name not in flags:
            return False, (
                f"`riskmanaged {' '.join(consumed)}` has no option {name} "
                f"(available: {sorted(f for f in flags if f.startswith('--'))})"
            )
    return True, ""


class TestCliExamples:
    @pytest.mark.docs
    @pytest.mark.parametrize(
        "doc,command",
        CLI_EXAMPLES,
        ids=[f"{d}:{c[:60]}" for d, c in CLI_EXAMPLES] or None,
    )
    def test_example_resolves(self, doc, command):
        """A documented command that does not exist wastes an agent's turn and
        teaches it a false capability."""
        import shlex

        try:
            argv = shlex.split(command)[1:]
        except ValueError:
            pytest.skip(f"unparseable shell line: {command}")

        ok, reason = _resolve(argv)
        assert ok, f"{doc}: {reason}\n  example: {command}"


# ---------------------------------------------------------------------------
# Rules 3 + 4 — indicator names and their output lines
# ---------------------------------------------------------------------------


_TRIGGER_LINE_VALUE = re.compile(
    r'"(?:trigger_line|threshold_line|atr_line)"\s*:\s*"([^"]+)"'
)


def _line_references() -> list[tuple[str, str, str]]:
    """`(doc, prefix, line)` for every indicator-line reference.

    Extraction is deliberately narrow — only the two places a line can
    genuinely appear — because a loose scan for `word.word` also matches
    `github.com`, `install.sh` and `claude_desktop_config.json`.
    """
    found = []
    for doc in PRESENT:
        text = _read(doc)
        candidates = set(_TRIGGER_LINE_VALUE.findall(text))
        # Backticked references, e.g. `RSI.rsi`.
        candidates |= {
            token for token in _BACKTICKED.findall(text) if _LINE_REF.fullmatch(token)
        }
        for candidate in candidates:
            match = _LINE_REF.fullmatch(candidate.strip())
            if match and match.group(2) not in _FILE_SUFFIXES:
                found.append((doc, match.group(1), match.group(2)))
    return found


# `config.json`, `install.sh`, `cron.md` are backticked filenames, not lines.
_FILE_SUFFIXES = {
    "json", "sh", "md", "py", "toml", "yaml", "yml", "txt", "lock",
    "git", "com", "io", "org", "net", "html", "js", "cfg", "ini",
}


# Every line name any indicator publishes — used to sanity-check references
# through a *custom* indicator name, where the type is not recoverable.
ALL_LINE_NAMES = {ln for d in INDICATORS.values() for ln in d["lines"]}


LINE_REFS = sorted(set(_line_references()))

# Prefixes that look like `Name.line` but are not indicator references.
_NOT_INDICATORS = {
    "README",
    "AGENT",
    "AGENTS",
    "OpenClaw",
    "Claude",
    "Cursor",
    "Hermes",
    "MCP",
    "RiskManaged",
    "US",
    "Python",
    "JSON",
    "API",
    "CLI",
    "GitHub",
    "PyPI",
    "riskmanaged",
    "riskmanaged_mcp",
    "config",
    "auth",
    "e",
    "g",
    "i",
    # Prose object references, e.g. `strategy.mode`, `stats.sharpe`. These name
    # response fields, not indicator lines.
    "strategy",
    "mapping",
    "instance",
    "position",
    "variation",
    "response",
    "template",
    "stats",
    "backtest",
    "summary",
}


class TestIndicatorLineReferences:
    @pytest.mark.docs
    @pytest.mark.parametrize(
        "doc,indicator,line",
        LINE_REFS,
        ids=[f"{d}:{i}.{ln}" for d, i, ln in LINE_REFS] or None,
    )
    def test_line_exists(self, doc, indicator, line):
        """The rule that would have caught `RSI_btcusdt_30m.rsi`,
        `MACD.macd_signal` and `BollingerBands…upper` — all fictional.

        Two cases. If the prefix is a known indicator type, the line must be
        one of *its* lines. If it is not, the reference is presumed to use a
        custom `name` (which the API genuinely supports, e.g. `fast_rsi.rsi`),
        and all we can check is that the suffix is a real line name somewhere —
        which is still enough to reject `macd_hist`.
        """
        if indicator in _NOT_INDICATORS or line in OHLCV:
            pytest.skip(f"{indicator}.{line} is not an indicator line reference")

        if indicator in INDICATORS:
            valid = set(INDICATORS[indicator]["lines"])
            assert line in valid, (
                f"{doc}: `{indicator}` has no line {line!r}. "
                f"Valid lines: {sorted(valid)}"
            )
            return

        assert line in ALL_LINE_NAMES, (
            f"{doc}: `{indicator}.{line}` — no indicator publishes a line "
            f"called {line!r}. If `{indicator}` is a custom indicator name, the "
            f"suffix must still be a real output line of its type."
        )

    def test_default_indicator_names_are_documented_correctly(self):
        """No doc may reassert the retired `{type}_{ticker}_{timeframe}` shape."""
        offenders = []
        for doc in PRESENT:
            for match in re.finditer(
                r"\b[A-Za-z]+_[a-z]+usdt?_\d+[mhd]\b", _read(doc)
            ):
                offenders.append(f"{doc}: {match.group(0)}")
        assert not offenders, (
            "docs still use the fictional {type}_{ticker}_{timeframe} naming: "
            f"{offenders}"
        )


# ---------------------------------------------------------------------------
# Rule 5 — risk-management config keys
# ---------------------------------------------------------------------------


def _risk_configs() -> list[tuple[str, str, str]]:
    """`(doc, risk_type, key)` for keys documented against a risk type.

    Matches a risk type name followed on the same line by a JSON object, which
    is how every example in these docs is written.
    """
    found = []
    pattern = re.compile(
        r"\b(" + "|".join(sorted(RISK)) + r")\b[^\n{]*(\{[^\n]*\})"
    )
    for doc in PRESENT:
        for risk_type, blob in pattern.findall(_read(doc)):
            for key in re.findall(r'"([a-z_]+)"\s*:', blob):
                found.append((doc, risk_type, key))
    return found


RISK_CONFIGS = sorted(set(_risk_configs()))


class TestRiskConfigKeys:
    @pytest.mark.docs
    @pytest.mark.parametrize(
        "doc,risk_type,key",
        RISK_CONFIGS,
        ids=[f"{d}:{t}.{k}" for d, t, k in RISK_CONFIGS] or None,
    )
    def test_key_exists(self, doc, risk_type, key):
        """The `stop_pct` rule. An unknown key used to be dropped in silence,
        applying the default — a documented 3% stop became −5%, with a ✓."""
        valid = set(RISK[risk_type]["config_fields"])
        # `profit_target` etc. live on nested items, not the top-level model.
        nested = {"profit_target", "amount", "level_name", "value"}
        if key in nested:
            pytest.skip(f"{key} belongs to a nested item, not {risk_type}")
        assert key in valid, (
            f"{doc}: `{risk_type}` has no config field {key!r}. "
            f"Valid fields: {sorted(valid)}"
        )


# ---------------------------------------------------------------------------
# Rule 6 — the base URL
# ---------------------------------------------------------------------------


class TestBaseUrl:
    @pytest.mark.docs
    @pytest.mark.parametrize("doc", DOC_IDS)
    def test_documented_url_matches_the_default(self, doc):
        """`riskmanaged.io` is the marketing site; the API is at
        `agent.riskmanaged.io`. Pointing a client at the former returns HTML
        where JSON is expected, and every tool call fails inscrutably."""
        wrong = [
            url
            for url in _URL.findall(_read(doc))
            if url.rstrip("/") != config.DEFAULT_BASE_URL.rstrip("/")
        ]
        assert not wrong, (
            f"{doc}: RISKMANAGED_URL documented as {wrong}, but the API is at "
            f"{config.DEFAULT_BASE_URL}"
        )


# ---------------------------------------------------------------------------
# Structural: the docs exist and cover the surface
# ---------------------------------------------------------------------------


class TestDocsExist:
    def test_agents_md_is_present(self):
        """`AGENTS.md` is the filename agent tooling discovers by convention."""
        assert DOCS["AGENTS.md"].exists(), "AGENTS.md is missing"

    def test_agent_md_points_at_agents_md(self):
        """The old name stays as a pointer so existing links keep working."""
        if not DOCS["AGENT.md"].exists():
            pytest.skip("AGENT.md removed entirely")
        assert "AGENTS.md" in DOCS["AGENT.md"].read_text()

    @pytest.mark.parametrize("doc", ["AGENTS.md", "README.md"])
    def test_tool_count_claims_are_accurate(self, doc):
        """Three docs previously claimed three different counts."""
        if doc not in PRESENT:
            pytest.skip(f"{doc} not present")
        claims = re.findall(r"\b(\d+)\s+tools\b", _read(doc))
        wrong = [c for c in claims if int(c) != len(TOOL_NAMES)]
        assert not wrong, (
            f"{doc} claims {wrong} tools; there are {len(TOOL_NAMES)}"
        )


class TestGeneratedBlocks:
    """The tool tables are generated, so they cannot silently rot."""

    @pytest.mark.docs
    @pytest.mark.parametrize("doc", ["AGENTS.md", "README.md"])
    def test_generated_block_is_current(self, doc):
        from riskmanaged_mcp import docgen

        if doc not in PRESENT:
            pytest.skip(f"{doc} not present")
        assert docgen.block_is_current(PRESENT[doc]), (
            f"{doc}'s tool table is out of date — run `riskmanaged dev sync-docs`"
        )

    def test_every_tool_is_categorised(self):
        """A new tool must be placed deliberately, not dumped into 'Other'."""
        from riskmanaged_mcp import docgen

        categorised = {n for _, names in docgen.CATEGORIES for n in names}
        uncategorised = sorted(TOOL_NAMES - categorised)
        assert not uncategorised, (
            f"tools missing from docgen.CATEGORIES: {uncategorised}"
        )
