"""In-memory FastMCP client tests for the decorator and middleware."""

from __future__ import annotations

from typing import Any

import pytest
from fastmcp import Client, FastMCP

from epienv.enforce import InferencePolicy
from epienv.mcp import EpistemicMiddleware, epistemic_tool
from epienv.models import CertifiedFinding, Envelope, Subject
from epienv.render import to_llm_context
from epienv.shaping import CallContext, shape_response
from epienv.validate import validate

TS = "2026-09-20T00:00:00Z"


def _mapper(raw: dict[str, Any]) -> Envelope:
    return Envelope(
        subject=Subject(type="column", id=str(raw["id"]), name=str(raw["name"])),
        inference_permitted=True,
        governance_notice="AI-generated content is unverified and not certified.",
        certified_findings=[],
        profiling_observations=[],
        ai_inferences=[],
    )


def _broken_mapper(raw: dict[str, Any]) -> Envelope:
    envelope = _mapper(raw)
    return envelope.model_copy(
        update={
            "certified_findings": [
                CertifiedFinding(
                    id="cf-1",
                    rule_id="DQ-17",
                    certified_by="steward_a",
                    certified_at="yesterday",
                )
            ]
        }
    )


def _policy(context: CallContext) -> InferencePolicy:
    assert context.tool_name == "profile_column"
    return InferencePolicy()


def _server() -> FastMCP:
    server = FastMCP("epistemic-test")

    @epistemic_tool(server, mapper=_mapper, policy=InferencePolicy())
    def describe_column(column_id: str) -> dict[str, Any]:
        """Decorated tool."""
        return {"id": column_id, "name": "email"}

    @server.tool
    def profile_column(column_id: str) -> dict[str, Any]:
        """Middleware-shaped tool."""
        return {"id": column_id, "name": "email"}

    @server.tool
    def echo(text: str) -> str:
        """Passes through unchanged."""
        return text

    @epistemic_tool(server, mapper=_mapper, policy=InferencePolicy(), read_only=False)
    def editable(column_id: str) -> dict[str, Any]:
        return {"id": column_id, "name": "email"}

    @epistemic_tool(server, mapper=_broken_mapper, policy=InferencePolicy())
    def broken(column_id: str) -> dict[str, Any]:
        return {"id": column_id, "name": "email"}

    server.add_middleware(EpistemicMiddleware({"profile_column": _mapper}, _policy))
    return server


def test_shape_response_logs_and_withholds_invalid_envelopes(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level("ERROR"):
        shaped = shape_response(
            {"id": "col_email", "name": "email"},
            _broken_mapper,
            InferencePolicy(),
        )
    assert shaped.structured is None
    assert shaped.ok is False
    assert shaped.violations[0].code == "E009"
    assert "E009" in shaped.text
    assert "E009" in caplog.text


async def test_decorator_and_middleware_return_envelopes() -> None:
    async with Client(_server()) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}

        described = tools["describe_column"]
        assert described.outputSchema is not None
        assert described.outputSchema["properties"]["envelope_version"]["const"] == "0.1"
        assert described.annotations is not None
        assert described.annotations.readOnlyHint is True

        editable = tools["editable"]
        assert editable.annotations is not None
        assert editable.annotations.readOnlyHint is False

        for name in ("describe_column", "profile_column"):
            result = await client.call_tool_mcp(name, {"column_id": "col_email"})
            assert result.isError is False
            assert result.structuredContent is not None
            assert validate(result.structuredContent) == []
            envelope = Envelope.model_validate(result.structuredContent)
            assert result.content[0].text == to_llm_context(envelope)

        echoed = await client.call_tool_mcp("echo", {"text": "hello"})
        assert echoed.isError is False
        assert echoed.content[0].text == "hello"
        assert echoed.structuredContent == {"result": "hello"}

        broken = await client.call_tool_mcp("broken", {"column_id": "col_email"})
        assert broken.isError is True
        assert broken.structuredContent is None
        assert "E009" in broken.content[0].text
