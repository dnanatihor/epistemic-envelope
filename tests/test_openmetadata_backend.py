"""OpenMetadata backend against recorded HTTP responses. No network."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
from examples.catalog_server.backends.openmetadata import OpenMetadataBackend

_FIXTURES = Path(__file__).parent / "fixtures" / "openmetadata"
_COLUMN = "sample.shop.public.customers.email"


def _load(name: str) -> object:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.host != "openmetadata.test":
        message = f"unexpected host {request.url.host}"
        raise AssertionError(message)
    if request.headers.get("authorization") != "Bearer recorded-token":
        message = "missing bearer token"
        raise AssertionError(message)
    path = request.url.path
    if path == "/api/v1/tables":
        return httpx.Response(200, json=_load("tables.json"))
    if path == "/api/v1/dataQuality/testCases":
        return httpx.Response(200, json=_load("test-cases.json"))
    if path.endswith("/columnProfile"):
        if "startTs" not in request.url.params or "endTs" not in request.url.params:
            message = "column profiles require startTs and endTs"
            raise AssertionError(message)
        return httpx.Response(200, json=_load("column-profile.json"))
    return httpx.Response(404)


def _backend() -> OpenMetadataBackend:
    client = httpx.Client(
        base_url="https://openmetadata.test",
        transport=httpx.MockTransport(_handler),
    )
    return OpenMetadataBackend("https://openmetadata.test", "recorded-token", client=client)


def test_maps_recorded_quality_and_profile() -> None:
    backend = _backend()
    assets = backend.list_assets()
    assert any(asset.id == _COLUMN for asset in assets)
    findings = backend.get_dq_results(_COLUMN)
    assert findings[0].result == "pass"
    assert findings[0].certified_by == "admin"
    assert findings[0].certified_at == "2026-09-20T00:00:00Z"
    profile = backend.get_profile(_COLUMN)
    assert profile is not None
    assert profile.metrics[0].metric == "null_pct"
    assert profile.metrics[0].value == 0.02
    assert profile.profile_run_id == "1789862400000"
    assert profile.observed_at == "2026-09-20T00:00:00Z"


def test_unknown_asset_raises() -> None:
    backend = _backend()
    try:
        backend.get_asset("missing.column")
    except KeyError:
        return
    raise AssertionError("expected KeyError")
