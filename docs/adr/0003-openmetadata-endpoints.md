# 0003 — OpenMetadata endpoint paths checked on 1.13.4

- Status: accepted
- Date: 2026-10-01

## Context

Phase 5 needs an optional backend that turns OpenMetadata data-quality
results into certified findings and column profiles into observations.
The v1.13 reference and the running server do not describe the column
profile route the same way.

## Options considered

1. Call `GET /api/v1/tables/{tableId}/columnProfile?columnName=`. That is the shape in older notes. Server 1.13.4 rejects it: `startTs` and `endTs` are required, and the path value must be a column's fully qualified name.
2. Call the routes the running server publishes in its OpenAPI document.

## Decision

Follow option 2. Checked against the official 1.13.4 Docker quickstart
(`docker-compose.yml` from the `1.13.4-release` GitHub assets) after
creating one synthetic table. The client calls:

- `GET /api/v1/tables?fields=columns` to list tables and columns
- `GET /api/v1/dataQuality/testCases?entityLink=...&fields=testCaseResult` for quality results
- `GET /api/v1/tables/{columnFqn}/columnProfile?startTs=...&endTs=...` for observations

`Success` maps to `pass`. `Failed` and `Aborted` map to `fail`. Timestamps
are Unix milliseconds, converted to UTC RFC 3339. Column profiles still
have no run id, so the raw timestamp string is `profile_run_id`.

## Consequences

`tests/fixtures/openmetadata/` holds the responses recorded from that
server. Tests replay them and do not open a network connection. The
Docker quickstart is heavy (MySQL, Elasticsearch, and the server) and
optional. Install the client with `epistemic-envelope[openmetadata]`.
On this machine Elasticsearch's host port was published as `19200`
because `9200` was already in use; the server itself stayed on `8585`.
