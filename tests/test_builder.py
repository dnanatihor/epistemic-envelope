"""Builder round-trip and error listing."""

from __future__ import annotations

import pytest

from epienv.builder import DEFAULT_NOTICE, EnvelopeBuilder, EnvelopeError
from epienv.models import Envelope, Subject
from epienv.validate import validate

TS = "2026-09-20T00:00:00Z"


def _subject() -> Subject:
    return Subject(type="column", id="col_email", name="email")


def _full_builder() -> EnvelopeBuilder:
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


def test_build_round_trip_validates_and_reloads() -> None:
    built = _full_builder().build()
    dumped = built.model_dump(mode="json", exclude_none=True)
    assert validate(dumped) == []
    assert Envelope.model_validate(dumped) == built
    assert built.certified_findings[0].id == "cf-1"
    assert built.profiling_observations[0].id == "po-1"
    assert built.ai_inferences[0].id == "ai-1"


def test_supplied_id_is_kept_and_auto_ids_skip_it() -> None:
    built = (
        EnvelopeBuilder(subject=_subject())
        .permit_inference(False)
        .certified(
            id="cf-2",
            statement="First",
            rule_id="DQ-1",
            certified_by="steward_a",
            certified_at=TS,
        )
        .certified(
            statement="Second",
            rule_id="DQ-2",
            certified_by="steward_a",
            certified_at=TS,
        )
        .build()
    )
    assert [item.id for item in built.certified_findings] == ["cf-2", "cf-1"]


def test_build_lists_violations() -> None:
    builder = (
        EnvelopeBuilder(subject=_subject())
        .permit_inference(False, notice=DEFAULT_NOTICE)
        .inferred(
            kind="classification",
            statement="Not allowed",
            model="provider/model-id",
            generated_at=TS,
        )
    )
    with pytest.raises(EnvelopeError) as raised:
        builder.build()
    assert [item.code for item in raised.value.violations] == ["E002"]
