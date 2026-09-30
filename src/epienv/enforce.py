"""Apply an inference policy to a Level 2 envelope or a Level 1 response."""

from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel, ConfigDict

from epienv.builder import DEFAULT_NOTICE
from epienv.models import Envelope, Inference


class InferencePolicy(BaseModel):
    """Which inferences a caller is allowed to receive."""

    model_config = ConfigDict(frozen=True)

    permitted: bool = True
    allowed_kinds: set[str] | None = None
    require_review_accepted: bool = False
    notice: str = DEFAULT_NOTICE
    withheld_notice: str = "AI inferences were withheld by policy."


def enforce(env: Envelope, policy: InferencePolicy) -> Envelope:
    """Return a copy of ``env`` with inferences filtered by ``policy``."""
    if not policy.permitted:
        return env.model_copy(
            update={
                "ai_inferences": [],
                "inference_permitted": False,
                "governance_notice": policy.withheld_notice,
            }
        )
    kept = [item for item in env.ai_inferences if _keep_inference(item, policy)]
    notice = env.governance_notice
    if kept and not notice:
        notice = policy.notice
    return env.model_copy(
        update={
            "ai_inferences": kept,
            "inference_permitted": True,
            "governance_notice": notice,
        }
    )


def enforce_labelled(obj: dict[str, Any], policy: InferencePolicy) -> dict[str, Any]:
    """Return a copy of a Level 1 response with disallowed inferred objects removed."""
    filtered = _filter_node(obj, policy)
    result = cast(dict[str, Any], filtered)
    if not policy.permitted:
        result["inference_permitted"] = False
        result["governance_notice"] = policy.withheld_notice
    return result


def _keep_inference(item: Inference, policy: InferencePolicy) -> bool:
    if policy.allowed_kinds is not None and item.kind not in policy.allowed_kinds:
        return False
    return not (policy.require_review_accepted and item.review_status != "accepted")


def _keep_labelled(item: dict[str, Any], policy: InferencePolicy) -> bool:
    if item.get("epistemic_layer") != "inferred":
        return True
    if not policy.permitted:
        return False
    kind = item.get("kind")
    if policy.allowed_kinds is not None and kind not in policy.allowed_kinds:
        return False
    return not (policy.require_review_accepted and item.get("review_status") != "accepted")


def _filter_node(node: object, policy: InferencePolicy) -> object:
    if isinstance(node, list):
        kept: list[object] = []
        for item in node:
            if isinstance(item, dict) and not _keep_labelled(cast(dict[str, Any], item), policy):
                continue
            kept.append(_filter_node(item, policy))
        return kept
    if isinstance(node, dict):
        typed = cast(dict[str, Any], node)
        copied: dict[str, Any] = {}
        for key, value in typed.items():
            if isinstance(value, dict) and not _keep_labelled(cast(dict[str, Any], value), policy):
                continue
            copied[key] = _filter_node(value, policy)
        return copied
    return node
