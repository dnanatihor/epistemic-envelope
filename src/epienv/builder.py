"""Build a Level 2 envelope and reject it when it does not conform."""

from __future__ import annotations

from epienv.models import (
    AttributeValue,
    CertifiedFinding,
    CuratedStatement,
    Envelope,
    Inference,
    Observation,
    ReviewStatus,
    Subject,
)
from epienv.validate import Violation, validate

DEFAULT_NOTICE = "AI-generated content is unverified and not certified."


class EnvelopeError(Exception):
    """Raised by ``EnvelopeBuilder.build`` when the envelope is not valid."""

    def __init__(self, violations: list[Violation]) -> None:
        self.violations = violations
        codes = ", ".join(item.code for item in violations)
        super().__init__(f"invalid envelope: {codes}")


class EnvelopeBuilder:
    """Chain together an envelope. ``build`` raises ``EnvelopeError`` if invalid."""

    def __init__(self, subject: Subject) -> None:
        self._subject = subject
        self._attributes: dict[str, AttributeValue] = {}
        self._permitted = True
        self._notice: str | None = None
        self._certified: list[CertifiedFinding] = []
        self._observed: list[Observation] = []
        self._inferred: list[Inference] = []
        self._curated: list[CuratedStatement] = []

    def attributes(self, **values: AttributeValue) -> EnvelopeBuilder:
        """Add descriptive structural attributes."""
        self._attributes.update(values)
        return self

    def permit_inference(self, permitted: bool, notice: str | None = None) -> EnvelopeBuilder:
        """Set whether inferred content may be included, and an optional notice."""
        self._permitted = permitted
        if notice is not None:
            self._notice = notice
        return self

    def certified(
        self,
        *,
        statement: str,
        rule_id: str,
        certified_by: str,
        certified_at: str,
        result: str | None = None,
        value: float | None = None,
        evidence_uri: str | None = None,
        id: str | None = None,
    ) -> EnvelopeBuilder:
        """Append a certified finding. ``id`` is ``cf-N`` when omitted."""
        item_id = id if id is not None else _next_id("cf", [item.id for item in self._certified])
        self._certified.append(
            CertifiedFinding(
                id=item_id,
                statement=statement,
                rule_id=rule_id,
                result=result,
                value=value,
                certified_by=certified_by,
                certified_at=certified_at,
                evidence_uri=evidence_uri,
            )
        )
        return self

    def observed(
        self,
        *,
        metric: str,
        value: float,
        observed_at: str,
        profile_run_id: str,
        unit: str | None = None,
        id: str | None = None,
    ) -> EnvelopeBuilder:
        """Append a profiling observation. ``id`` is ``po-N`` when omitted."""
        item_id = id if id is not None else _next_id("po", [item.id for item in self._observed])
        self._observed.append(
            Observation(
                id=item_id,
                metric=metric,
                value=value,
                unit=unit,
                observed_at=observed_at,
                profile_run_id=profile_run_id,
            )
        )
        return self

    def inferred(
        self,
        *,
        kind: str,
        statement: str,
        model: str,
        generated_at: str,
        reported_confidence: float | None = None,
        basis: list[str] | None = None,
        review_status: ReviewStatus | None = "unreviewed",
        id: str | None = None,
    ) -> EnvelopeBuilder:
        """Append an inference. ``id`` is ``ai-N`` when omitted."""
        item_id = id if id is not None else _next_id("ai", [item.id for item in self._inferred])
        self._inferred.append(
            Inference(
                id=item_id,
                kind=kind,
                statement=statement,
                reported_confidence=reported_confidence,
                model=model,
                generated_at=generated_at,
                basis=list(basis or []),
                review_status=review_status,
            )
        )
        return self

    def curated(
        self,
        *,
        statement: str,
        authored_by: str,
        authored_at: str,
        id: str | None = None,
    ) -> EnvelopeBuilder:
        """Append a curated statement. ``id`` is ``cm-N`` when omitted."""
        item_id = id if id is not None else _next_id("cm", [item.id for item in self._curated])
        self._curated.append(
            CuratedStatement(
                id=item_id,
                statement=statement,
                authored_by=authored_by,
                authored_at=authored_at,
            )
        )
        return self

    def build(self) -> Envelope:
        """Return the envelope, or raise ``EnvelopeError`` listing violations."""
        envelope = Envelope(
            subject=self._subject,
            attributes=dict(self._attributes),
            inference_permitted=self._permitted,
            governance_notice=self._notice,
            certified_findings=list(self._certified),
            profiling_observations=list(self._observed),
            ai_inferences=list(self._inferred),
            curated_metadata=list(self._curated),
        )
        violations = validate(envelope.model_dump(mode="json", exclude_none=True))
        if violations:
            raise EnvelopeError(violations)
        return envelope


def _next_id(prefix: str, used: list[str]) -> str:
    number = 1
    taken = set(used)
    while f"{prefix}-{number}" in taken:
        number += 1
    return f"{prefix}-{number}"
