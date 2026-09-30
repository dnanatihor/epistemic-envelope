# 0003 — OpenMetadata endpoint paths from the v1.13 reference

- Status: accepted
- Date: 2026-09-30

## Context

Phase 5 needs an optional backend that turns OpenMetadata data-quality
results into certified findings and column profiles into observations.
No OpenMetadata server is running in this environment, so the paths
could not be checked against a live instance.

## Options considered

1. Wait for a local Docker quickstart and record live responses. Accurate, and heavier than this phase can run here.
2. Use the published v1.13 REST reference and recorded fixtures. Tests stay offline. A path that drifted in a later release will not be caught until someone runs the client.

## Decision

Follow option 2. The client calls:

- `GET /api/v1/tables?fields=columns` to list tables and columns
- `GET /api/v1/dataQuality/testCases?entityLink=...&fields=testCaseResult` for quality results
- `GET /api/v1/tables/{id}/columnProfile?columnName=...` for observations

`Success` maps to `pass` and `Failed` maps to `fail`. Column-profile
timestamps are Unix milliseconds, converted to UTC RFC 3339. The v1.13
column-profile reference does not name a profile-run id, so the raw
timestamp string is stored as `profile_run_id`.

## Consequences

Tests prove the mapping against fixtures in `tests/fixtures/openmetadata/`.
They do not prove that a deployed OpenMetadata answers these paths.
Re-record the fixtures against a running server before relying on the
backend in production. Setup remains the official Docker quickstart,
which is heavy and optional (`pip install 'epistemic-envelope[openmetadata]'`).
