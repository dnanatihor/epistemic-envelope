"""Golden renders for to_llm_context()."""

from __future__ import annotations

from pathlib import Path

import pytest

from epienv.builder import DEFAULT_NOTICE, EnvelopeBuilder
from epienv.enforce import InferencePolicy, enforce
from epienv.models import Subject
from epienv.render import to_llm_context

GOLDEN = Path(__file__).resolve().parent / "golden"
TS = "2026-09-20T00:00:00Z"


def _subject() -> Subject:
    return Subject(type="column", id="col_email", name="email")


def _full() -> EnvelopeBuilder:
    return (
        EnvelopeBuilder(subject=_subject())
        .attributes(data_type="varchar", table="customers")
        .permit_inference(True, notice=DEFAULT_NOTICE)
        .certified(
            statement="Email format rule passed",
            rule_id="DQ-17",
            result="pass",
            certified_by="steward_a",
            certified_at=TS,
        )
        .observed(metric="null_pct", value=0.02, observed_at=TS, profile_run_id="pr_9")
        .inferred(
            kind="classification",
            statement="Likely contains personal emails",
            model="provider/model-id",
            generated_at=TS,
            reported_confidence=0.9,
            basis=["po-1"],
        )
    )


def _without_inferences() -> EnvelopeBuilder:
    return (
        EnvelopeBuilder(subject=_subject())
        .certified(
            statement="Email format rule passed",
            rule_id="DQ-17",
            result="pass",
            certified_by="steward_a",
            certified_at=TS,
        )
        .observed(metric="null_pct", value=0.02, observed_at=TS, profile_run_id="pr_9")
    )


def _read(name: str) -> str:
    return (GOLDEN / name).read_text(encoding="utf-8")


def test_golden_renders_match() -> None:
    full = _full().build()
    no_inferences = _without_inferences().build()
    withheld = enforce(full, InferencePolicy(permitted=False))
    empty = EnvelopeBuilder(subject=_subject()).permit_inference(False).build()

    cases = {
        "full.txt": full,
        "no_inferences.txt": no_inferences,
        "withheld.txt": withheld,
        "all_empty.txt": empty,
    }
    for name, envelope in cases.items():
        rendered = to_llm_context(envelope)
        assert rendered == to_llm_context(envelope, style="markdown")
        assert rendered == _read(name)


def test_unknown_style_is_rejected() -> None:
    envelope = EnvelopeBuilder(subject=_subject()).permit_inference(False).build()
    with pytest.raises(ValueError, match="markdown"):
        to_llm_context(envelope, style="html")
