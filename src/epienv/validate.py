"""Validate envelopes and labelled responses. Never raises on invalid input."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from rfc3339_validator import validate_rfc3339  # type: ignore[import-untyped]

from epienv.schema_check import LEVEL1_RESPONSE_SCHEMA

_PROVENANCE: dict[str, tuple[str, ...]] = {
    "certified": ("rule_id", "certified_by", "certified_at"),
    "observed": ("observed_at", "profile_run_id"),
    "inferred": ("model", "generated_at"),
    "curated": ("authored_by", "authored_at"),
}
_LAYER_KEYS: tuple[tuple[str, str], ...] = (
    ("certified_findings", "certified"),
    ("profiling_observations", "observed"),
    ("ai_inferences", "inferred"),
    ("curated_metadata", "curated"),
)
_TIMESTAMP_FIELDS = frozenset({"certified_at", "observed_at", "generated_at", "authored_at"})
_REVIEW_STATUSES = frozenset({"unreviewed", "accepted", "rejected"})
_INFERRED_KEYS = frozenset({"model", "generated_at"})
_REQUIRED_MESSAGE = re.compile(r"^'(.+)' is a required property$")
_UNEXPECTED_MESSAGE = re.compile(r"\('([^']+)' was unexpected\)")


@dataclass(frozen=True, slots=True)
class Violation:
    """One conformance failure.

    ``code`` is an envelope rule (E001-E010). Schema failures that the rules
    table does not name use ``schema``.
    """

    code: str
    path: str
    message: str


def validate(obj: dict[str, Any], level: Literal[1, 2] = 2) -> list[Violation]:
    """Validate ``obj`` at Level 1 or Level 2. Invalid input returns violations."""
    try:
        return _validate(obj, level)
    except Exception as exc:
        return [Violation(code="schema", path="", message=f"validation failed: {exc}")]


def _validate(obj: object, level: object) -> list[Violation]:
    if level not in (1, 2):
        return [Violation(code="schema", path="", message="level must be 1 or 2")]
    if not isinstance(obj, dict):
        return [
            Violation(
                code="E001",
                path="/inference_permitted",
                message="inference_permitted must be present and boolean",
            )
        ]
    document = cast(dict[str, Any], obj)
    semantic = _semantic(document, level)
    structural = _schema_violations(document, level)
    return _merge(semantic, structural)


def _semantic(obj: dict[str, Any], level: Literal[1, 2]) -> list[Violation]:
    if level == 1:
        return _semantic_level1(obj)
    return _semantic_level2(obj)


def _semantic_level2(obj: dict[str, Any]) -> list[Violation]:
    violations: list[Violation] = []
    violations.extend(_check_inference_permitted(obj))
    permitted = obj.get("inference_permitted")
    inferences = obj.get("ai_inferences")
    if permitted is False and inferences not in (None, []):
        violations.append(
            Violation(
                code="E002",
                path="/ai_inferences",
                message="ai_inferences must be absent or empty when inference is not permitted",
            )
        )
    if isinstance(inferences, list) and len(inferences) > 0 and not _notice_ok(obj):
        violations.append(
            Violation(
                code="E003",
                path="/governance_notice",
                message="governance_notice must be a non-empty string when inferences are present",
            )
        )
    items: list[tuple[str, str, dict[str, Any]]] = []
    for key, layer in _LAYER_KEYS:
        raw = obj.get(key, [])
        if raw is None:
            continue
        if not isinstance(raw, list):
            violations.append(
                Violation(code="E005", path=f"/{key}", message=f"{key} must be an array of items")
            )
            continue
        for index, item in enumerate(raw):
            path = f"/{key}/{index}"
            if not isinstance(item, dict):
                violations.append(
                    Violation(code="E005", path=path, message="item must be an object")
                )
                continue
            typed = cast(dict[str, Any], item)
            items.append((path, layer, typed))
            if layer == "certified":
                violations.extend(_forbidden_inferred_keys(typed, path))
            violations.extend(_provenance(typed, layer, path))
            violations.extend(_timestamps(typed, path))
            if "review_status" in typed and typed["review_status"] not in _REVIEW_STATUSES:
                violations.append(
                    Violation(
                        code="E010",
                        path=f"{path}/review_status",
                        message="review_status must be unreviewed, accepted, or rejected",
                    )
                )
    violations.extend(_unique_ids([(path, item) for path, _layer, item in items]))
    violations.extend(_basis([(path, item) for path, _layer, item in items]))
    attributes = obj.get("attributes")
    if attributes is not None:
        violations.extend(_attributes(attributes))
    return violations


def _semantic_level1(obj: dict[str, Any]) -> list[Violation]:
    violations: list[Violation] = []
    violations.extend(_check_inference_permitted(obj))
    labelled = _labelled(obj, [])
    inferred = [entry for entry in labelled if entry[1].get("epistemic_layer") == "inferred"]
    if obj.get("inference_permitted") is False and inferred:
        path = _pointer(inferred[0][0])
        violations.append(
            Violation(
                code="E002",
                path=path,
                message="inferred objects must be absent when inference is not permitted",
            )
        )
    if inferred and not _notice_ok(obj):
        violations.append(
            Violation(
                code="E003",
                path="/governance_notice",
                message=(
                    "governance_notice must be a non-empty string when inferred content is present"
                ),
            )
        )
    located: list[tuple[str, dict[str, Any]]] = []
    for parts, item in labelled:
        path = _pointer(parts)
        layer = item.get("epistemic_layer")
        if not isinstance(layer, str) or layer not in _PROVENANCE:
            continue
        if layer == "certified":
            violations.extend(_forbidden_inferred_keys(item, path))
        violations.extend(_provenance(item, layer, path))
        violations.extend(_timestamps(item, path))
        if "review_status" in item and item["review_status"] not in _REVIEW_STATUSES:
            violations.append(
                Violation(
                    code="E010",
                    path=f"{path}/review_status",
                    message="review_status must be unreviewed, accepted, or rejected",
                )
            )
        located.append((path, item))
    violations.extend(_unique_ids(located))
    violations.extend(_basis(located))
    return violations


def _check_inference_permitted(obj: dict[str, Any]) -> list[Violation]:
    value = obj.get("inference_permitted")
    if "inference_permitted" not in obj or not isinstance(value, bool):
        return [
            Violation(
                code="E001",
                path="/inference_permitted",
                message="inference_permitted must be present and boolean",
            )
        ]
    return []


def _notice_ok(obj: dict[str, Any]) -> bool:
    notice = obj.get("governance_notice")
    return isinstance(notice, str) and notice != ""


def _forbidden_inferred_keys(item: dict[str, Any], path: str) -> list[Violation]:
    found: list[Violation] = []
    for key in ("model", "generated_at"):
        if key in item:
            found.append(
                Violation(
                    code="E004",
                    path=f"{path}/{key}",
                    message=f"certified items must not carry {key}",
                )
            )
    return found


def _provenance(item: dict[str, Any], layer: str, path: str) -> list[Violation]:
    found: list[Violation] = []
    if "id" not in item or not isinstance(item.get("id"), str):
        found.append(Violation(code="E006", path=f"{path}/id", message="item id must be a string"))
    for key in _PROVENANCE[layer]:
        if key not in item:
            found.append(
                Violation(
                    code="E005",
                    path=f"{path}/{key}",
                    message=f"{layer} items must include {key}",
                )
            )
    return found


def _timestamps(item: dict[str, Any], path: str) -> list[Violation]:
    found: list[Violation] = []
    for key in _TIMESTAMP_FIELDS:
        if key not in item:
            continue
        value = item[key]
        if isinstance(value, str) and bool(validate_rfc3339(value.upper())):
            continue
        found.append(
            Violation(
                code="E009",
                path=f"{path}/{key}",
                message=f"{key} must be an RFC 3339 timestamp",
            )
        )
    return found


def _unique_ids(items: list[tuple[str, dict[str, Any]]]) -> list[Violation]:
    seen: dict[str, str] = {}
    found: list[Violation] = []
    for path, item in items:
        item_id = item.get("id")
        if not isinstance(item_id, str):
            continue
        if item_id in seen:
            found.append(
                Violation(
                    code="E006",
                    path=f"{path}/id",
                    message=f"duplicate item id {item_id}",
                )
            )
        else:
            seen[item_id] = path
    return found


def _basis(items: list[tuple[str, dict[str, Any]]]) -> list[Violation]:
    ids = {item["id"] for _path, item in items if isinstance(item.get("id"), str)}
    found: list[Violation] = []
    for path, item in items:
        basis = item.get("basis", None)
        if basis is None:
            continue
        if not isinstance(basis, list):
            found.append(
                Violation(code="E007", path=f"{path}/basis", message="basis must be an array")
            )
            continue
        for index, ref in enumerate(basis):
            if not isinstance(ref, str) or ref not in ids:
                target = ref if isinstance(ref, str) else index
                found.append(
                    Violation(
                        code="E007",
                        path=f"{path}/basis/{index}",
                        message=f"basis entry {target} does not reference an item id",
                    )
                )
    return found


def _attributes(attributes: object) -> list[Violation]:
    if not isinstance(attributes, dict):
        return [
            Violation(
                code="E008",
                path="/attributes",
                message="attributes must be an object of strings, numbers, and booleans",
            )
        ]
    found: list[Violation] = []
    typed = cast(dict[str, Any], attributes)
    for key, value in typed.items():
        if isinstance(value, bool | int | float | str):
            continue
        found.append(
            Violation(
                code="E008",
                path=f"/attributes/{_escape(key)}",
                message="attributes values must be strings, numbers, or booleans",
            )
        )
    return found


def _labelled(
    node: object, parts: list[str | int]
) -> list[tuple[tuple[str | int, ...], dict[str, Any]]]:
    found: list[tuple[tuple[str | int, ...], dict[str, Any]]] = []
    if isinstance(node, dict):
        typed = cast(dict[str, Any], node)
        if "epistemic_layer" in typed:
            found.append((tuple(parts), typed))
        for key, value in typed.items():
            found.extend(_labelled(value, [*parts, key]))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(_labelled(value, [*parts, index]))
    return found


def _schema_violations(obj: dict[str, Any], level: Literal[1, 2]) -> list[Violation]:
    envelope, labelled, level1_root = _validators()
    if level == 2:
        errors = envelope.iter_errors(obj)
        return [_map_schema_error(error) for error in errors]
    mapped = [_map_schema_error(error) for error in level1_root.iter_errors(obj)]
    for _parts, item in _labelled(obj, []):
        mapped.extend(_map_schema_error(error) for error in labelled.iter_errors(item))
    return mapped


def _map_schema_error(error: ValidationError) -> Violation:
    path = _pointer(error.absolute_path)
    name = _required_name(error) or _unexpected_name(error)
    if name and path:
        path = f"{path}/{_escape(name)}"
    elif name:
        path = f"/{_escape(name)}"
    code = _schema_code(error, name, path)
    return Violation(code=code, path=path, message=error.message)


def _schema_code(error: ValidationError, name: str | None, path: str) -> str:
    keyword = error.validator
    leaf = path.rsplit("/", 1)[-1]
    if keyword == "required":
        if name == "inference_permitted":
            return "E001"
        if name == "id":
            return "E006"
        if name in {key for keys in _PROVENANCE.values() for key in keys}:
            return "E005"
        return "schema"
    if keyword == "type":
        if leaf == "inference_permitted":
            return "E001"
        if path.startswith("/attributes"):
            return "E008"
        if leaf in _TIMESTAMP_FIELDS:
            return "E009"
        return "schema"
    if keyword == "format":
        return "E009"
    if keyword == "enum" and leaf == "review_status":
        return "E010"
    if keyword == "additionalProperties" and name in _INFERRED_KEYS:
        return "E004"
    if keyword == "not":
        return "E004"
    return "schema"


def _required_name(error: ValidationError) -> str | None:
    if error.validator != "required":
        return None
    match = _REQUIRED_MESSAGE.match(error.message)
    return match.group(1) if match else None


def _unexpected_name(error: ValidationError) -> str | None:
    if error.validator != "additionalProperties":
        return None
    match = _UNEXPECTED_MESSAGE.search(error.message)
    return match.group(1) if match else None


def _merge(semantic: list[Violation], structural: list[Violation]) -> list[Violation]:
    present = {item.code for item in semantic}
    merged = list(semantic)
    seen = {(item.code, item.path) for item in semantic}
    for item in structural:
        key = (item.code, item.path)
        if item.code in present or key in seen:
            continue
        merged.append(item)
        seen.add(key)
    return merged


def _pointer(parts: Iterable[object]) -> str:
    escaped = [_escape(str(part)) for part in parts]
    if not escaped:
        return ""
    return "/" + "/".join(escaped)


def _escape(part: str) -> str:
    return part.replace("~", "~0").replace("/", "~1")


def _schema_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "schema" / "envelope.v0.1.json"
        if candidate.is_file() and (parent / "pyproject.toml").is_file():
            return candidate.parent
    message = "normative schema directory was not found"
    raise FileNotFoundError(message)


@lru_cache(maxsize=1)
def _validators() -> tuple[Draft202012Validator, Draft202012Validator, Draft202012Validator]:
    schema_dir = _schema_dir()
    checker = Draft202012Validator.FORMAT_CHECKER

    def load(name: str) -> Draft202012Validator:
        with (schema_dir / name).open(encoding="utf-8") as handle:
            schema: dict[str, Any] = json.load(handle)
        return Draft202012Validator(schema, format_checker=checker)

    return (
        load("envelope.v0.1.json"),
        load("labelled-object.v0.1.json"),
        Draft202012Validator(LEVEL1_RESPONSE_SCHEMA, format_checker=checker),
    )
