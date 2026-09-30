# 0001 — FastMCP integration

- Status: accepted
- Date: 2026-09-30

## Context

Phase 3 has to confirm two things against the installed FastMCP before the decorator and middleware are part of the SDK: whether middleware can replace a tool result's structured and text content, and whether a decorator can set `outputSchema` and annotations.

## Options considered

1. Spike against `fastmcp` 2.14.7 with an in-memory client, and ship both integrations if both capabilities work.
2. Ship only `shape_response` and the decorator if middleware cannot replace a result.

## Decision

Both capabilities work on `fastmcp` 2.14.7 (MCP SDK 1.30.0). The spike used `FastMCP`, `Client`, and `Middleware.on_call_tool`.

- A tool registered with `output_schema` and `annotations={"readOnlyHint": True}` lists `outputSchema` and `annotations.readOnlyHint` is true.
- `on_call_tool` receives a `ToolResult` and can return a new one. `Client.call_tool_mcp` then shows the replacement text content and `structuredContent`.

The SDK therefore ships `@epistemic_tool` and `EpistemicMiddleware`, both on top of `shape_response`.

`@epistemic_tool` takes the `FastMCP` server as its first argument. Registration has to happen on a server instance; there is no ambient server to decorate against.

`CallContext` carries the tool name, request headers when the framework exposes an HTTP request, and `client_id` when request metadata has one. An in-memory client has no HTTP request, so `headers` is empty in that mode.

An invalid shaped envelope is returned as a tool result with `isError` true and no structured envelope. `ToolResult.to_mcp_result` does not set `isError`, so error results use a small subclass that does.

## Consequences

Servers on this FastMCP version can retrofit existing tools with middleware and mark new tools with the decorator. A future FastMCP that stops returning `ToolResult` from `on_call_tool`, or that drops `output_schema` on `@tool`, would need this note revised.
