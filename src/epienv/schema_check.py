"""Schema-check the conformance suite against the published JSON Schemas."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

VALID_NAME = re.compile(r"^l([12])-.+\.json$")
INVALID_NAME = re.compile(r"^(E0(?:0[1-9]|10))-l([12])-.+\.json$")
RULE_CODES = tuple(f"E0{number:02d}" for number in range(1, 11))
STRUCTURAL_CODES = frozenset({"E001", "E004", "E005", "E008", "E009", "E010"})
SEMANTIC_CODES = frozenset({"E002", "E003", "E006", "E007"})

# Root requirement for a Level 1 response. The labelled-object schema covers claims.
LEVEL1_RESPONSE_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["inference_permitted"],
    "properties": {
        "inference_permitted": {"type": "boolean"},
        "governance_notice": {"type": "string"},
    },
}


@dataclass(frozen=True)
class CheckedDocument:
    """Schema-check outcome for one conformance document."""

    relative_path: str
    level: int
    code: str | None
    schema_valid: bool
    errors: tuple[str, ...]


@dataclass(frozen=True)
class SuiteReport:
    """Schema-check outcome for the whole conformance suite."""

    documents: tuple[CheckedDocument, ...]
    problems: tuple[str, ...]

    @property
    def ok(self) -> bool:
        """True when every acceptance check on the suite passed."""
        return not self.problems


def check_suite(root: Path) -> SuiteReport:
    """Schema-check every conformance document under ``root``.

    Valid documents must satisfy the published schema for their level.
    Invalid documents are checked too. Structural codes (those the schema
    can express) must fail the schema. Cross-item codes must still pass the
    schema, because the standard leaves them to semantic validation.
    """
    schema_dir = root / "schema"
    conformance = root / "conformance"
    envelope = _validator(_load_json(schema_dir / "envelope.v0.1.json"))
    labelled = _validator(_load_json(schema_dir / "labelled-object.v0.1.json"))
    level1_root = _validator(LEVEL1_RESPONSE_SCHEMA)

    documents: list[CheckedDocument] = []
    problems: list[str] = []

    valid_dir = conformance / "valid"
    invalid_dir = conformance / "invalid"
    if not valid_dir.is_dir() or not invalid_dir.is_dir():
        problems.append("conformance/valid and conformance/invalid must both exist")
        return SuiteReport((), tuple(problems))

    for path in sorted(valid_dir.glob("*.json")):
        match = VALID_NAME.fullmatch(path.name)
        if match is None:
            problems.append(f"valid filename must be l1-*.json or l2-*.json: {path.name}")
            continue
        level = int(match.group(1))
        checked = _check_document(path, root, level, None, envelope, labelled, level1_root)
        documents.append(checked)
        if not checked.schema_valid:
            detail = "; ".join(checked.errors)
            problems.append(f"valid document failed schema: {checked.relative_path}: {detail}")

    seen_codes: set[str] = set()
    seen_invalid_levels: set[int] = set()
    for path in sorted(invalid_dir.glob("*.json")):
        match = INVALID_NAME.fullmatch(path.name)
        if match is None:
            problems.append(
                f"invalid filename must be E00N-l1-*.json or E00N-l2-*.json: {path.name}"
            )
            continue
        code, level_text = match.group(1), match.group(2)
        level = int(level_text)
        seen_codes.add(code)
        seen_invalid_levels.add(level)
        checked = _check_document(path, root, level, code, envelope, labelled, level1_root)
        documents.append(checked)
        if code in STRUCTURAL_CODES and checked.schema_valid:
            problems.append(f"structural invalid document passed schema: {checked.relative_path}")
        elif code in SEMANTIC_CODES and not checked.schema_valid:
            detail = "; ".join(checked.errors)
            problems.append(
                f"semantic-only invalid document failed schema: {checked.relative_path}: {detail}"
            )

    valid_docs = [item for item in documents if item.code is None]
    invalid_docs = [item for item in documents if item.code is not None]
    if len(valid_docs) < 12:
        problems.append(f"expected at least 12 valid documents, found {len(valid_docs)}")
    if len(invalid_docs) < 20:
        problems.append(f"expected at least 20 invalid documents, found {len(invalid_docs)}")
    missing_codes = [code for code in RULE_CODES if code not in seen_codes]
    if missing_codes:
        problems.append(f"invalid suite is missing codes: {', '.join(missing_codes)}")
    valid_levels = {item.level for item in valid_docs}
    if valid_levels != {1, 2}:
        problems.append(f"valid suite must include level 1 and level 2, found {valid_levels}")
    if seen_invalid_levels != {1, 2}:
        problems.append(
            f"invalid suite must include level 1 and level 2, found {seen_invalid_levels}"
        )
    return SuiteReport(tuple(documents), tuple(problems))


def _check_document(
    path: Path,
    root: Path,
    level: int,
    code: str | None,
    envelope: Draft202012Validator,
    labelled: Draft202012Validator,
    level1_root: Draft202012Validator,
) -> CheckedDocument:
    instance = _load_json(path)
    if level == 2:
        errors = _error_messages(envelope, instance)
    else:
        errors = _error_messages(level1_root, instance)
        if isinstance(instance, dict):
            for obj in _labelled_objects(instance):
                errors.extend(_error_messages(labelled, obj))
        else:
            errors.append("Level 1 document must be a JSON object")
    relative = path.relative_to(root).as_posix()
    return CheckedDocument(relative, level, code, not errors, tuple(errors))


def _labelled_objects(node: object) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(node, dict):
        if "epistemic_layer" in node:
            found.append(node)
        for value in node.values():
            found.extend(_labelled_objects(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_labelled_objects(item))
    return found


def _validator(schema: dict[str, Any]) -> Draft202012Validator:
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        message = f"published schema is not a valid Draft 2020-12 schema: {exc.message}"
        raise SystemExit(message) from exc
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def _error_messages(validator: Draft202012Validator, instance: Any) -> list[str]:
    return sorted(error.message for error in validator.iter_errors(instance))


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)
