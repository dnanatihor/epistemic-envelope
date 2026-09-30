"""Phase 1 acceptance: validate() passes the conformance suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from epienv.models import Envelope
from epienv.schema_check import INVALID_NAME, VALID_NAME
from epienv.validate import validate

ROOT = Path(__file__).resolve().parents[1]
VALID = ROOT / "conformance" / "valid"
INVALID = ROOT / "conformance" / "invalid"


def _load(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_valid_conformance_documents_have_no_violations() -> None:
    paths = sorted(VALID.glob("*.json"))
    assert len(paths) >= 12
    for path in paths:
        match = VALID_NAME.fullmatch(path.name)
        assert match is not None
        level = int(match.group(1))
        assert validate(_load(path), level=level) == []  # type: ignore[arg-type]


def test_invalid_conformance_documents_return_exactly_one_coded_violation() -> None:
    paths = sorted(INVALID.glob("*.json"))
    assert len(paths) >= 20
    seen: set[str] = set()
    levels: set[int] = set()
    for path in paths:
        match = INVALID_NAME.fullmatch(path.name)
        assert match is not None
        code = match.group(1)
        level = int(match.group(2))
        seen.add(code)
        levels.add(level)
        violations = validate(_load(path), level=level)  # type: ignore[arg-type]
        assert [item.code for item in violations] == [code], path.name
    assert seen == {f"E0{number:02d}" for number in range(1, 11)}
    assert levels == {1, 2}


def test_validate_never_raises_on_invalid_input() -> None:
    bad_inputs: list[Any] = [None, [], "envelope", 1, {"envelope_version": "nope"}]
    for obj in bad_inputs:
        violations = validate(obj)
        assert isinstance(violations, list)


def test_sdk_envelopes_validate_against_the_schema() -> None:
    schema = _load(ROOT / "schema" / "envelope.v0.1.json")
    checker = Draft202012Validator.FORMAT_CHECKER
    validator = Draft202012Validator(schema, format_checker=checker)
    documents = [
        Envelope.model_validate(_load(VALID / "l2-full.json")),
        Envelope.model_validate(_load(VALID / "l2-attribute-primitives.json")),
        Envelope.model_validate(_load(VALID / "l2-all-layers-empty.json")),
    ]
    for envelope in documents:
        dumped = envelope.model_dump(mode="json", exclude_none=True)
        errors = sorted(validator.iter_errors(dumped), key=lambda err: list(err.path))
        assert errors == []
        assert validate(dumped) == []
