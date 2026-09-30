"""Policy matrix for enforce() and labelled enforcement."""

from __future__ import annotations

import pytest

from epienv.enforce import InferencePolicy, enforce, enforce_labelled
from epienv.models import Envelope, Inference, Subject
from epienv.validate import validate

TS = "2026-09-20T00:00:00Z"


def _envelope() -> Envelope:
    return Envelope(
        subject=Subject(type="column", id="col_email", name="email"),
        inference_permitted=True,
        governance_notice="AI-generated content is unverified and not certified.",
        ai_inferences=[
            Inference(
                id="ai-1",
                kind="classification",
                model="m",
                generated_at=TS,
                review_status="unreviewed",
            ),
            Inference(
                id="ai-2",
                kind="classification",
                model="m",
                generated_at=TS,
                review_status="accepted",
            ),
            Inference(
                id="ai-3",
                kind="description",
                model="m",
                generated_at=TS,
                review_status="unreviewed",
            ),
            Inference(
                id="ai-4",
                kind="description",
                model="m",
                generated_at=TS,
                review_status="accepted",
            ),
        ],
    )


@pytest.mark.parametrize(
    ("policy", "expected"),
    [
        (InferencePolicy(), ["ai-1", "ai-2", "ai-3", "ai-4"]),
        (InferencePolicy(permitted=False), []),
        (InferencePolicy(allowed_kinds={"classification"}), ["ai-1", "ai-2"]),
        (InferencePolicy(allowed_kinds={"description"}), ["ai-3", "ai-4"]),
        (InferencePolicy(allowed_kinds=set()), []),
        (InferencePolicy(require_review_accepted=True), ["ai-2", "ai-4"]),
        (
            InferencePolicy(allowed_kinds={"classification"}, require_review_accepted=True),
            ["ai-2"],
        ),
        (
            InferencePolicy(
                permitted=False,
                allowed_kinds={"classification"},
                require_review_accepted=True,
            ),
            [],
        ),
    ],
)
def test_policy_matrix_keeps_expected_inference_ids(
    policy: InferencePolicy, expected: list[str]
) -> None:
    original = _envelope()
    result = enforce(original, policy)
    assert [item.id for item in result.ai_inferences] == expected
    assert [item.id for item in original.ai_inferences] == ["ai-1", "ai-2", "ai-3", "ai-4"]
    dumped = result.model_dump(mode="json", exclude_none=True)
    assert validate(dumped) == []
    if not policy.permitted:
        assert result.inference_permitted is False
        assert result.governance_notice == policy.withheld_notice
    else:
        assert result.inference_permitted is True


def test_enforce_labelled_removes_disallowed_inferences() -> None:
    raw = {
        "inference_permitted": True,
        "governance_notice": "AI-generated content is unverified and not certified.",
        "asset": {
            "claims": [
                {"epistemic_layer": "certified", "id": "cf-1", "rule_id": "DQ-1"},
                {"epistemic_layer": "inferred", "id": "ai-1", "kind": "classification"},
                {"epistemic_layer": "inferred", "id": "ai-2", "kind": "description"},
            ]
        },
    }
    withheld = enforce_labelled(raw, InferencePolicy(permitted=False))
    assert raw["asset"]["claims"][1]["id"] == "ai-1"
    assert [item["id"] for item in withheld["asset"]["claims"]] == ["cf-1"]
    assert withheld["inference_permitted"] is False
    assert withheld["governance_notice"] == "AI inferences were withheld by policy."

    classified = enforce_labelled(raw, InferencePolicy(allowed_kinds={"classification"}))
    assert [item["id"] for item in classified["asset"]["claims"]] == ["cf-1", "ai-1"]
