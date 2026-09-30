"""Map a raw payload to an envelope, enforce policy, and validate."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from epienv.enforce import InferencePolicy, enforce
from epienv.models import Envelope
from epienv.render import to_llm_context
from epienv.validate import Violation, validate

logger = logging.getLogger("epienv.shaping")


class Mapper(Protocol):
    """Turn one raw tool payload into an envelope."""

    def __call__(self, raw: dict[str, Any]) -> Envelope: ...


@dataclass(frozen=True, slots=True)
class ShapedResult:
    """Structured envelope, LLM text, and any violations found after shaping."""

    structured: dict[str, Any] | None
    text: str
    violations: tuple[Violation, ...]

    @property
    def ok(self) -> bool:
        """True when the shaped envelope conformed."""
        return not self.violations and self.structured is not None


def shape_response(
    raw: dict[str, Any],
    mapper: Mapper,
    policy: InferencePolicy,
) -> ShapedResult:
    """Map, enforce, then validate.

    An invalid envelope is a server bug. Violations are logged and the return
    value is an error result, not the invalid envelope.
    """
    try:
        envelope = mapper(raw)
        enforced = enforce(envelope, policy)
    except Exception as exc:
        logger.exception("mapper failed while shaping a response")
        return ShapedResult(
            structured=None,
            text=f"invalid envelope: mapper failed: {exc}",
            violations=(),
        )
    dumped = enforced.model_dump(mode="json", exclude_none=True)
    violations = tuple(validate(dumped))
    if violations:
        codes = ", ".join(item.code for item in violations)
        logger.error("shaped envelope is invalid: %s", codes)
        return ShapedResult(
            structured=None,
            text=f"invalid envelope: {codes}",
            violations=violations,
        )
    return ShapedResult(
        structured=dumped,
        text=to_llm_context(enforced),
        violations=(),
    )


PolicyResolver = Callable[["CallContext"], InferencePolicy]


@dataclass(frozen=True, slots=True)
class CallContext:
    """What the policy resolver can see for one tool call.

    In-memory clients often have no HTTP request, so ``headers`` may be empty.
    """

    tool_name: str
    headers: dict[str, str]
    client_info: str | None
