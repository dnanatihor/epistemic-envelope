"""Reference catalog server: fixture data, static inference, and startup."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest
from examples.catalog_server.backends.fixture import FixtureBackend
from examples.catalog_server.server import build_server
from fastmcp import Client

from epienv.models import Envelope
from epienv.render import to_llm_context
from epienv.validate import validate

ROOT = Path(__file__).resolve().parents[1]


def test_seed_has_three_tables_twelve_columns_failing_rule_and_stale_profile() -> None:
    backend = FixtureBackend()
    assets = backend.list_assets()
    tables = [asset for asset in assets if asset.type == "table"]
    columns = [asset for asset in assets if asset.type == "column"]
    assert len(tables) == 3
    assert len(columns) == 12
    amount = backend.get_dq_results("col_amount")
    assert amount[0].result == "fail"
    method = backend.get_profile("col_method")
    assert method is not None
    assert method.observed_at.startswith("2024-")
    email = backend.get_profile("col_email")
    assert email is not None
    assert email.observed_at.startswith("2026-")


async def test_tools_return_valid_envelopes_and_static_inference() -> None:
    async with Client(build_server()) as client:
        listed = await client.call_tool_mcp("list_assets", {})
        profile = await client.call_tool_mcp("get_asset_profile", {"asset_id": "col_email"})
        described = await client.call_tool_mcp("describe_asset", {"asset_id": "col_email"})
        quality = await client.call_tool_mcp("get_quality", {"asset_id": "col_amount"})
        for result in (listed, profile, described, quality):
            assert result.isError is False
            assert result.structuredContent is not None
            assert validate(result.structuredContent) == []
            envelope = Envelope.model_validate(result.structuredContent)
            assert result.content[0].text == to_llm_context(envelope)

        tools = {tool.name: tool for tool in await client.list_tools()}
        for name in ("list_assets", "get_asset_profile", "describe_asset", "get_quality"):
            assert tools[name].annotations is not None
            assert tools[name].annotations.readOnlyHint is True
            assert tools[name].outputSchema is not None

        described_env = Envelope.model_validate(described.structuredContent)
        assert [item.id for item in described_env.ai_inferences] == ["ai-1"]
        assert described_env.certified_findings[0].result == "pass"
        quality_env = Envelope.model_validate(quality.structuredContent)
        assert quality_env.certified_findings[0].result == "fail"
        assert quality_env.ai_inferences == []

        missing = await client.call_tool_mcp("describe_asset", {"asset_id": "missing"})
        assert missing.isError is True


async def test_inference_off_strips_inferences(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EPIENV_INFERENCE", "off")
    async with Client(build_server()) as client:
        for name, arguments in (
            ("list_assets", {}),
            ("get_asset_profile", {"asset_id": "col_email"}),
            ("describe_asset", {"asset_id": "col_email"}),
            ("get_quality", {"asset_id": "col_amount"}),
        ):
            result = await client.call_tool_mcp(name, arguments)
            assert result.structuredContent is not None
            envelope = Envelope.model_validate(result.structuredContent)
            assert envelope.ai_inferences == []
            assert envelope.inference_permitted is False


def test_module_starts() -> None:
    process = subprocess.Popen(
        [sys.executable, "-m", "examples.catalog_server"],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        time.sleep(1.5)
        assert process.poll() is None, process.stderr.read().decode() if process.stderr else ""
    finally:
        process.terminate()
        process.wait(timeout=5)
