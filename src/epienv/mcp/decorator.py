"""Register a FastMCP tool whose return value is an epistemic envelope."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, cast

from fastmcp import FastMCP

from epienv.enforce import InferencePolicy
from epienv.mcp.results import to_tool_result
from epienv.schema_check import load_schema
from epienv.shaping import Mapper, ShapedResult, shape_response


def epistemic_tool(
    server: FastMCP,
    *,
    mapper: Mapper,
    policy: InferencePolicy,
    read_only: bool = True,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Wrap a tool so it returns an envelope and the LLM rendering of it.

    FastMCP registers tools on a server instance, so ``server`` is required.
    ``read_only`` sets ``readOnlyHint`` and defaults to true.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(fn):

            @wraps(fn)
            async def wrapped(*args: Any, **kwargs: Any) -> Any:
                raw = await fn(*args, **kwargs)
                return _shape_raw(raw, mapper, policy)

        else:

            @wraps(fn)
            def wrapped(*args: Any, **kwargs: Any) -> Any:
                raw = fn(*args, **kwargs)
                return _shape_raw(raw, mapper, policy)

        wrapped.__annotations__ = {
            key: value
            for key, value in getattr(fn, "__annotations__", {}).items()
            if key != "return"
        }
        server.tool(
            wrapped,
            output_schema=load_schema("envelope.v0.1.json"),
            annotations={"readOnlyHint": read_only, "title": fn.__name__},
        )
        return wrapped

    return decorator


def _shape_raw(raw: object, mapper: Mapper, policy: InferencePolicy) -> Any:
    if not isinstance(raw, dict):
        return to_tool_result(
            ShapedResult(
                structured=None,
                text="invalid envelope: tool payload must be an object",
                violations=(),
            )
        )
    return to_tool_result(shape_response(cast(dict[str, Any], raw), mapper, policy))
