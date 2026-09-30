"""Pydantic mirror of the normative JSON Schemas.

The schemas in ``schema/`` are authoritative. These models exist so callers can
build and dump envelopes; ``validate`` remains the conformance check.
"""

from __future__ import annotations

from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

AttributeValue: TypeAlias = str | int | float | bool
ReviewStatus: TypeAlias = Literal["unreviewed", "accepted", "rejected"]


class Subject(BaseModel):
    """The thing an envelope's claims are about."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: str
    id: str
    name: str


class CertifiedFinding(BaseModel):
    """Outcome of an approved, rule-based check."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    rule_id: str
    certified_by: str
    certified_at: str
    statement: str | None = None
    result: str | None = None
    value: float | None = None
    evidence_uri: str | None = None


class Observation(BaseModel):
    """Measurement from automated profiling or scanning."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    observed_at: str
    profile_run_id: str
    metric: str | None = None
    value: float | None = None
    unit: str | None = None


class Inference(BaseModel):
    """Content generated or judged by a model."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    model: str
    generated_at: str
    kind: str | None = None
    statement: str | None = None
    reported_confidence: float | None = None
    basis: list[str] = Field(default_factory=list)
    review_status: ReviewStatus | None = None


class CuratedStatement(BaseModel):
    """Statement authored by a human steward."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    authored_by: str
    authored_at: str
    statement: str | None = None


class Envelope(BaseModel):
    """Level 2 epistemic envelope, version 0.1."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    subject: Subject
    inference_permitted: bool
    envelope_version: Literal["0.1"] = "0.1"
    attributes: dict[str, AttributeValue] = Field(default_factory=dict)
    governance_notice: str | None = None
    certified_findings: list[CertifiedFinding] = Field(default_factory=list)
    profiling_observations: list[Observation] = Field(default_factory=list)
    ai_inferences: list[Inference] = Field(default_factory=list)
    curated_metadata: list[CuratedStatement] = Field(default_factory=list)
