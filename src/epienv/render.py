"""Render an envelope for an LLM with layers kept visibly separate."""

from __future__ import annotations

from epienv.models import CertifiedFinding, CuratedStatement, Envelope, Inference, Observation

_CERTIFIED = "Certified findings (authoritative)"
_OBSERVED = "Profiling observations (measured; may be stale)"
_INFERRED = "AI inferences (unverified; do not present as fact)"
_CURATED = "Curated metadata (human-authored)"
_DASH = "\u2014"


def to_llm_context(env: Envelope, style: str = "markdown") -> str:
    """Render ``env``. ``style`` must be ``markdown``. The text is deterministic."""
    if style != "markdown":
        message = "style must be markdown"
        raise ValueError(message)
    sections = [
        _section(_CERTIFIED, [_certified_line(item) for item in env.certified_findings]),
        _section(_OBSERVED, [_observed_line(item) for item in env.profiling_observations]),
        _section(_INFERRED, [_inferred_line(item) for item in env.ai_inferences]),
    ]
    if env.curated_metadata:
        sections.append(_section(_CURATED, [_curated_line(item) for item in env.curated_metadata]))
    lines = ["\n".join(sections)]
    if env.governance_notice:
        lines.append(f"Governance notice: {env.governance_notice}")
    return "\n".join(lines) + "\n"


def _section(title: str, rows: list[str]) -> str:
    body = "\n".join(f"- {row}" for row in rows) if rows else "- none"
    return f"## {title}\n{body}"


def _certified_line(item: CertifiedFinding) -> str:
    statement = item.statement or ""
    result = item.result or ""
    date = _date(item.certified_at)
    return (
        f"[{item.id}] {statement} {_DASH} rule {item.rule_id}, {result}, "
        f"certified by {item.certified_by} on {date}"
    )


def _observed_line(item: Observation) -> str:
    metric = item.metric or ""
    value = _number(item.value) if item.value is not None else ""
    date = _date(item.observed_at)
    return f"[{item.id}] {metric} = {value} (observed {date}, run {item.profile_run_id})"


def _inferred_line(item: Inference) -> str:
    statement = item.statement or ""
    based = "[" + ", ".join(item.basis) + "]" if item.basis else "none"
    review = item.review_status or "unreviewed"
    return f"[{item.id}] {statement} {_DASH} model {item.model}, based on {based}, review: {review}"


def _curated_line(item: CuratedStatement) -> str:
    statement = item.statement or ""
    return (
        f"[{item.id}] {statement} {_DASH} authored by {item.authored_by} "
        f"on {_date(item.authored_at)}"
    )


def _date(timestamp: str) -> str:
    return timestamp.split("T", 1)[0]


def _number(value: float) -> str:
    text = format(value, "f").rstrip("0").rstrip(".")
    return text or "0"
