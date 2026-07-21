"""Every client call must address a route the platform actually publishes.

`test_client_contract.py` proves the client sends the request *it intends to*.
This file proves that request corresponds to something real — the two are
different failures, and only this one catches a backend rename.

It runs against `snapshots/openapi.json`, a vendored copy of the external API's
OpenAPI document, so the open-source repo stays testable with no backend and no
credentials. Refresh it with `riskmanaged dev sync-snapshot`; a test in the
platform repo fails when the vendored copy falls behind, which is the half of
the loop that has to live over there.

The bug that motivated this: the client pointed two of its three HTTP clients at
`/api/internal/*`, which the API token cannot authenticate. It produced a
plausible-looking client that talked to nothing, and no behavioural test noticed
because the paths were wrong rather than the logic.
"""

from __future__ import annotations

import json
import re

import pytest

from .conftest import SNAPSHOT_DIR
from .test_client_contract import CASE_IDS, CASES

OPENAPI_FILE = SNAPSHOT_DIR / "openapi.json"


def _load_spec() -> dict:
    if not OPENAPI_FILE.exists():  # pragma: no cover
        pytest.skip(f"missing snapshot {OPENAPI_FILE}; run `riskmanaged dev sync-snapshot`")
    return json.loads(OPENAPI_FILE.read_text())


SPEC = _load_spec()


def _published_routes() -> set[tuple[str, str]]:
    """`(VERB, templated path)` for everything the external API publishes."""
    routes = set()
    for path, operations in SPEC["paths"].items():
        for verb in operations:
            if verb.lower() in {"get", "post", "put", "patch", "delete"}:
                routes.add((verb.upper(), path))
    return routes


PUBLISHED = _published_routes()

# `/strategies/{strategy_id}` in the spec vs `/strategies/STRAT1` in a call.
_PARAM = re.compile(r"\{[^}]+\}")


def _templates_for(verb: str, concrete_path: str) -> bool:
    """Does any published route match this concrete path?

    Path params are the only wildcard, and ids here never contain a slash, so
    `{param}` → `[^/]+` is an exact enough match to distinguish
    `/strategies/{id}` from `/strategies/{id}/clone`.
    """
    for published_verb, template in PUBLISHED:
        if published_verb != verb:
            continue
        pattern = "^" + _PARAM.sub("[^/]+", template) + "$"
        if re.match(pattern, concrete_path):
            return True
    return False


class TestSnapshotIsUsable:
    def test_snapshot_exists_and_parses(self):
        assert SPEC.get("openapi"), "not an OpenAPI document"
        assert SPEC.get("paths"), "snapshot has no paths"

    def test_snapshot_covers_the_expected_surface(self):
        """Guard against a truncated or half-written snapshot silently making
        every assertion below vacuous."""
        assert len(PUBLISHED) > 80, f"only {len(PUBLISHED)} routes in the snapshot"

    def test_snapshot_is_the_external_api(self):
        """A snapshot of the *internal* app would let the old bug back in."""
        assert not any(
            path.startswith("/api/internal") for path in SPEC["paths"]
        ), "snapshot appears to include internal routes"


class TestEveryClientCallIsPublished:
    @pytest.mark.contract
    @pytest.mark.parametrize("method,kwargs,verb,path", CASES, ids=CASE_IDS)
    def test_route_exists(self, method, kwargs, verb, path):
        assert _templates_for(verb, path), (
            f"{method}: {verb} {path} is not published by the external API. "
            f"Either the backend moved it or the client has a typo — both are "
            f"invisible at runtime until a user calls this tool."
        )


class TestNoInternalRoutes:
    def test_client_source_has_no_internal_prefix(self):
        """The base URL is `/api/external`, so an internal path could only
        appear as a hand-written absolute escape hatch."""
        import inspect

        from riskmanaged_mcp import client as client_module

        source = inspect.getsource(client_module)
        offenders = [
            line.strip()
            for line in source.splitlines()
            if "/api/internal" in line
            and not line.lstrip().startswith("#")
            and "`" not in line  # prose in the module docstring
        ]
        assert not offenders, f"client addresses internal routes: {offenders}"

    def test_base_url_is_the_external_api(self):
        from riskmanaged_mcp.client import RiskManagedClient

        instance = RiskManagedClient(token="t", base_url="https://x.invalid")
        assert str(instance._client.base_url).rstrip("/").endswith("/api/external")
