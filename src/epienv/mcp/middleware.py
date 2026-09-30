"""Apply envelope shaping to tools on an existing FastMCP server."""

from __future__ import annotations

from collections.abc import Mapping

from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools.tool import ToolResult
from mcp.types import CallToolRequestParams

from epienv.mcp.results import to_tool_result
from epienv.shaping import CallContext, Mapper, PolicyResolver, shape_response


class EpistemicMiddleware(Middleware):
    """Shape listed tools. Tools without a mapper pass through unchanged."""

    def __init__(self, mappers: dict[str, Mapper], policy_resolver: PolicyResolver) -> None:
        self._mappers = mappers
        self._policy_resolver = policy_resolver

    async def on_call_tool(
        self,
        context: MiddlewareContext[CallToolRequestParams],
        call_next: CallNext[CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        result = await call_next(context)
        name = context.message.name
        mapper = self._mappers.get(name)
        if mapper is None:
            return result
        raw = result.structured_content if isinstance(result.structured_content, dict) else {}
        policy = self._policy_resolver(_call_context(context, name))
        return to_tool_result(shape_response(raw, mapper, policy))


def _call_context(context: MiddlewareContext[CallToolRequestParams], name: str) -> CallContext:
    headers: dict[str, str] = {}
    client_info: str | None = None
    fastmcp_context = context.fastmcp_context
    if fastmcp_context is not None:
        request_context = fastmcp_context.request_context
        if request_context is not None:
            request = getattr(request_context, "request", None)
            raw_headers = getattr(request, "headers", None)
            if isinstance(raw_headers, Mapping):
                headers = {str(key).lower(): str(value) for key, value in raw_headers.items()}
            client_info = fastmcp_context.client_id
    return CallContext(tool_name=name, headers=headers, client_info=client_info)
