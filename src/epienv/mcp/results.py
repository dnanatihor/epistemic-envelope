"""Turn a shaped result into a FastMCP tool result."""

from __future__ import annotations

from fastmcp.tools.tool import ToolResult
from mcp.types import CallToolResult

from epienv.shaping import ShapedResult


class _ErrorToolResult(ToolResult):
    """Tool result that the MCP client reports as an error."""

    def to_mcp_result(self) -> CallToolResult:
        return CallToolResult(content=self.content, isError=True)


def to_tool_result(shaped: ShapedResult) -> ToolResult:
    """Return structured content plus the LLM text, or an error result."""
    if shaped.ok and shaped.structured is not None:
        return ToolResult(content=shaped.text, structured_content=shaped.structured)
    return _ErrorToolResult(content=shaped.text)
