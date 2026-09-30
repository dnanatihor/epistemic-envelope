"""Canned inferences for tests and demos. No model is called."""

from __future__ import annotations

from typing import Protocol

from epienv.models import Inference

_TS = "2026-09-20T00:00:00Z"


class InferenceProvider(Protocol):
    """Produce inferences for one asset from the ids of its observations."""

    def infer(self, asset_id: str, observation_ids: list[str]) -> list[Inference]: ...


class StaticInferenceProvider:
    """Return a fixed classification for columns that have one in the demo map."""

    def infer(self, asset_id: str, observation_ids: list[str]) -> list[Inference]:
        if asset_id != "col_email":
            return []
        basis = observation_ids[:1]
        return [
            Inference(
                id="ai-1",
                kind="classification",
                statement="Likely contains personal email addresses",
                model="static/canned",
                generated_at=_TS,
                reported_confidence=0.9,
                basis=basis,
                review_status="unreviewed",
            )
        ]
