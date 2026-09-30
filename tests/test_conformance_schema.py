"""Phase 0 acceptance: the conformance suite is schema-checked."""

from __future__ import annotations

from pathlib import Path

from epienv.schema_check import RULE_CODES, check_suite

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SECTIONS = (
    "## Layers",
    "## Conformance levels",
    "## Envelope",
    "## Rules",
    "## Guidance",
    "## Versioning policy",
)


def test_conformance_suite_is_schema_checked() -> None:
    report = check_suite(ROOT)
    assert report.ok, "\n".join(report.problems)
    assert len(report.documents) >= 32


def test_suite_covers_every_rule_and_both_levels() -> None:
    report = check_suite(ROOT)
    assert report.ok, "\n".join(report.problems)
    codes = {item.code for item in report.documents if item.code is not None}
    assert set(RULE_CODES) <= codes
    levels = {item.level for item in report.documents}
    assert levels == {1, 2}


def test_valid_documents_pass_and_cross_item_rules_stay_out_of_schema() -> None:
    report = check_suite(ROOT)
    assert report.ok, "\n".join(report.problems)
    valid = [item for item in report.documents if item.code is None]
    assert len(valid) >= 12
    assert all(item.schema_valid for item in valid)
    invalid = [item for item in report.documents if item.code is not None]
    assert len(invalid) >= 20


def test_spec_has_required_sections_and_rules() -> None:
    text = (ROOT / "spec" / "SPEC-ENVELOPE.md").read_text(encoding="utf-8")
    for heading in REQUIRED_SECTIONS:
        assert heading in text
    for code in RULE_CODES:
        assert code in text
    changelog = (ROOT / "spec" / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "0.1" in changelog


def test_canonical_example_is_a_valid_level_2_document() -> None:
    report = check_suite(ROOT)
    canonical = next(
        item for item in report.documents if item.relative_path.endswith("l2-full.json")
    )
    assert canonical.level == 2
    assert canonical.schema_valid
    assert canonical.errors == ()
