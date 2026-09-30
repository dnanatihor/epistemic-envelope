# 0002 — How envelope rules apply to Level 1 responses

- Status: accepted
- Date: 2026-09-30

## Context

SPEC.md §4.3 states rules E001–E010 against the Level 2 envelope (`ai_inferences`, `certified_findings`, and so on). §4.2 describes Level 1 only as labelled objects plus a root `inference_permitted` and a `governance_notice` when inferred content is present. The conformance suite must cover Level 1 and Level 2, and Phase 1 `validate(obj, level=1)` needs a defined result for every code.

## Options considered

1. Leave Level 1 rules unspecified beyond §4.2 and cover only E001, E003, and E005 at Level 1. Pro: adds nothing. Con: `validate(level=1)` is undefined for the remaining codes, so Phase 1 would have to stop.
2. Restate every code for Level 1 by reading each container as the set of objects with that `epistemic_layer`. Pro: one rules table, both levels implementable, no new codes. Con: E002, E006, and E007 are applied to a shape SPEC.md does not spell out.

## Decision

Option 2, written into `spec/SPEC-ENVELOPE.md`. No new error codes. E008 stays Level 2 only, because Level 1 has no `attributes` member defined for this purpose. Level 1 objects may keep additional API fields; `model` and `generated_at` are still forbidden on certified objects.

## Consequences

The conformance fixtures and the later validator use this reading. If the curated layer is dropped (§11 of SPEC.md), both the Level 2 member and the `curated` label go with it.
