# Epistemic Envelope — Normative Standard

| | |
|---|---|
| Version | 0.1 |
| Status | Draft |
| Licence | Specification text: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). |

## Keywords

The key words MUST, MUST NOT, REQUIRED, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

This document is the normative standard. The JSON Schema files `schema/envelope.v0.1.json` (Level 2) and `schema/labelled-object.v0.1.json` (Level 1) are normative. Implementations MUST conform to this standard. This standard is not changed to match an implementation.

## Layers

An epistemic envelope separates four kinds of statement. Each item belongs to exactly one layer.

| Layer | Container key | Meaning | Required provenance |
|---|---|---|---|
| Certified | `certified_findings` | Outcome of an approved, rule-based check | `rule_id`, `certified_by`, `certified_at` |
| Observed | `profiling_observations` | Measurement from automated profiling or scanning | `observed_at`, `profile_run_id` |
| Inferred | `ai_inferences` | Content generated or judged by an AI/ML model | `model`, `generated_at` |
| Curated | `curated_metadata` | Statement authored by a human steward | `authored_by`, `authored_at` |

The curated layer is OPTIONAL in version 0.1. A conformant document MAY omit `curated_metadata`.

## Conformance levels

### Level 1 — Labelled

Level 1 is for existing APIs that cannot be restructured into an envelope. A Level 1 response is a JSON object. The response root MUST include `inference_permitted` (E001). Whenever the response contains inferred content, the response root MUST include a non-empty `governance_notice` (E003).

Every object that carries a claim MUST include `epistemic_layer`, whose value MUST be one of `certified`, `observed`, `inferred`, or `curated`, and MUST include that layer's required provenance keys (E005).

The same rules apply to a Level 1 response as to a Level 2 envelope, with these readings:

- `certified_findings`, `profiling_observations`, `ai_inferences`, and `curated_metadata` are read as the objects in the response whose `epistemic_layer` is `certified`, `observed`, `inferred`, and `curated` respectively.
- If `inference_permitted` is false, the response MUST NOT contain an object whose `epistemic_layer` is `inferred` (E002).
- Item `id`s MUST be unique among labelled objects in the response (E006). A labelled object that has an `id` MUST use a string.
- Every `basis` entry MUST reference the `id` of an object in the same response (E007).
- E008 applies to Level 2 `attributes` only.
- Timestamp members and `review_status` follow E009 and E010 wherever they appear.

A Level 1 claim object MAY contain additional members from the existing API. Those members MUST NOT be used to smuggle a claim that belongs in a different layer.

### Level 2 — Enveloped

Level 2 is the envelope defined in [Envelope](#envelope). A Level 2 document MUST NOT use `epistemic_layer` on items; the container key is the layer.

## Envelope

A Level 2 envelope is a JSON object with the following members.

| Member | Required | Type | Meaning |
|---|---|---|---|
| `envelope_version` | MUST | string, equal to `0.1` | Version of this standard |
| `subject` | MUST | object | The thing the claims are about |
| `attributes` | MAY | object | Descriptive structural facts about the subject |
| `inference_permitted` | MUST | boolean | Whether inferred content may be present (E001) |
| `governance_notice` | conditional | string | Required by E003 when `ai_inferences` is non-empty |
| `certified_findings` | MAY | array | Certified items |
| `profiling_observations` | MAY | array | Observed items |
| `ai_inferences` | MAY | array | Inferred items. Constrained by E002 and E003 |
| `curated_metadata` | MAY | array | Curated items |

`subject` MUST contain string members `type`, `id`, and `name`.

`attributes` MUST contain only descriptive structural values (JSON strings, numbers, or booleans). It MUST NOT contain arrays, objects, or nulls, and MUST NOT contain objects that carry layer or provenance keys (E008).

Item objects use the members below. Each item MUST include a string `id` (E006). Provenance members listed for the layer are REQUIRED (E005). Other members are the defined claim content and MAY be omitted, except where a rule says otherwise. Item objects MUST NOT contain members that are not defined for that layer. In particular, an item in `certified_findings` MUST NOT include `model` or `generated_at` (E004).

### Certified finding

| Member | Required | Type |
|---|---|---|
| `id` | MUST | string |
| `statement` | MAY | string |
| `rule_id` | MUST | string |
| `result` | MAY | string |
| `value` | MAY | number |
| `certified_by` | MUST | string |
| `certified_at` | MUST | RFC 3339 timestamp (E009) |
| `evidence_uri` | MAY | string or null |

### Profiling observation

| Member | Required | Type |
|---|---|---|
| `id` | MUST | string |
| `metric` | MAY | string |
| `value` | MAY | number |
| `unit` | MAY | string |
| `observed_at` | MUST | RFC 3339 timestamp (E009) |
| `profile_run_id` | MUST | string |

### AI inference

| Member | Required | Type |
|---|---|---|
| `id` | MUST | string |
| `kind` | MAY | string |
| `statement` | MAY | string |
| `reported_confidence` | MAY | number |
| `model` | MUST | string |
| `generated_at` | MUST | RFC 3339 timestamp (E009) |
| `basis` | MAY | array of strings |
| `review_status` | MAY | `unreviewed`, `accepted`, or `rejected` (E010) |

### Curated statement

| Member | Required | Type |
|---|---|---|
| `id` | MUST | string |
| `statement` | MAY | string |
| `authored_by` | MUST | string |
| `authored_at` | MUST | RFC 3339 timestamp (E009) |

### Example

```json
{
  "envelope_version": "0.1",
  "subject": {"type": "column", "id": "col_email", "name": "email"},
  "attributes": {"data_type": "varchar", "table": "customers"},
  "inference_permitted": true,
  "governance_notice": "AI-generated content is unverified and not certified.",
  "certified_findings": [
    {"id": "cf-1", "statement": "Email format rule passed", "rule_id": "DQ-17",
     "result": "pass", "value": 0.998, "certified_by": "steward_a",
     "certified_at": "2026-09-20T00:00:00Z", "evidence_uri": null}
  ],
  "profiling_observations": [
    {"id": "po-1", "metric": "null_pct", "value": 0.02, "unit": "ratio",
     "observed_at": "2026-09-20T00:00:00Z", "profile_run_id": "pr_9"}
  ],
  "ai_inferences": [
    {"id": "ai-1", "kind": "classification", "statement": "Likely contains personal email addresses",
     "reported_confidence": 0.9, "model": "provider/model-id", "generated_at": "2026-09-20T00:00:00Z",
     "basis": ["po-1"], "review_status": "unreviewed"}
  ],
  "curated_metadata": []
}
```

## Rules

A validator MUST report every failing rule below. `validate` in the Python SDK returns one `Violation` per failing rule instance and MUST NOT raise on invalid input. Codes are stable.

| Code | Rule |
|---|---|
| E001 | `inference_permitted` MUST be present and boolean. |
| E002 | If `inference_permitted` is false, `ai_inferences` MUST be absent or empty. |
| E003 | If `ai_inferences` is non-empty, `governance_notice` MUST be a non-empty string. |
| E004 | Items in `certified_findings` MUST NOT carry inferred provenance keys (`model`, `generated_at`). |
| E005 | Every item MUST carry its layer's required provenance keys ([Layers](#layers)). |
| E006 | Item `id`s MUST be unique within an envelope. Every item MUST have a string `id`. |
| E007 | Every `basis` entry MUST reference an existing item `id`. |
| E008 | `attributes` MUST contain only descriptive structural values (strings, numbers, booleans), never objects that carry layer or provenance keys. |
| E009 | Timestamps MUST be RFC 3339 strings. |
| E010 | `review_status` MUST be one of `unreviewed`, `accepted`, `rejected`. |

Timestamp members are `certified_at`, `observed_at`, `generated_at`, and `authored_at`. An RFC 3339 timestamp MUST be a complete date-time with a timezone offset or the suffix `Z`. A date alone is not sufficient.

E010 applies when `review_status` is present. Omitting `review_status` does not violate E010.

The JSON Schemas enforce the structural subset of these rules: types, required members (E001 and E005), the closed item shapes that reject `model` and `generated_at` on certified findings (E004), primitive `attributes` (E008), `format: date-time` (E009), and the `review_status` enumeration (E010). The cross-item rules E002, E003, E006, and E007 are not expressed by the schemas. A validator MUST still check them and MUST return the rule code.

When a document fails both a schema constraint and the rule that constraint encodes, a validator MUST report that code once for that defect.

### Conformance documents

The conformance suite in `conformance/` is normative input for implementations of this version.

- `conformance/valid/l1-*.json` and `conformance/valid/l2-*.json` MUST be accepted at the level named in the filename.
- `conformance/invalid/E00N-l1-*.json` and `conformance/invalid/E00N-l2-*.json` MUST each produce exactly one violation, whose code is the `E00N` prefix, at the level named in the filename.

Schema checking of this suite is defined as follows. A Level 2 document is checked against `schema/envelope.v0.1.json`. A Level 1 document is checked by validating its root object for the presence of a boolean `inference_permitted`, and by validating every nested object that contains `epistemic_layer` against `schema/labelled-object.v0.1.json`. Format assertions for `date-time` are part of that check.

## Guidance

These recommendations are SHOULD, not conformance rules.

- `reported_confidence` is the model's own estimate and is not calibrated. Consumers SHOULD NOT treat it as a probability of correctness. The name is deliberate.
- Inferences SHOULD list their `basis` so consumers can trace a claim to the measurements it rests on.
- Consumers presenting envelopes to an LLM SHOULD keep layers visibly separate.
- When inference is permitted and inferred content is present, producers SHOULD set `governance_notice` to a sentence that states the content is unverified and not certified. The example in [Envelope](#envelope) uses `AI-generated content is unverified and not certified.`

## Versioning policy

This standard is version 0.1. The member `envelope_version` MUST be the string `0.1` for documents that conform to this version.

Changes to this document MUST be versioned edits. Each published edit MUST be recorded in `spec/CHANGELOG.md`.

A JSON Schema file published for a released version of this standard MUST NOT be edited in place. A later version MUST be published as a new schema file. Until version 0.1 is released, these files MAY still change, and each change MUST be recorded in `spec/CHANGELOG.md`.

## Mapping to MCP Governance Auditor rules

| Envelope code | Auditor rule |
|---|---|
| E001 | EPI-001 |
| E002 | EPI-008 |
| E003 | EPI-009 |
| E004 | EPI-004 |
| E005 | EPI-005 (certified) / EPI-006 (observed timestamp) |
