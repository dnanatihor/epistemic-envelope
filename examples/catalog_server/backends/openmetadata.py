"""OpenMetadata REST backend. Paths match the v1.13 API reference.

This client was not checked against a running OpenMetadata server. See
docs/adr/0003-openmetadata-endpoints.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx

from examples.catalog_server.backends.fixture import Asset, DqResult, Profile, ProfileMetric

_PASS = {"Success", "success"}
_FAIL = {"Failed", "failed", "Aborted", "aborted"}


class OpenMetadataBackend:
    """Map OpenMetadata test cases to findings and column profiles to observations."""

    def __init__(
        self,
        base_url: str,
        token: str,
        client: httpx.Client | None = None,
    ) -> None:
        self._owns_client = client is None
        self._headers = {"Authorization": f"Bearer {token}"}
        self._client = client or httpx.Client(base_url=base_url.rstrip("/"))
        self._tables: list[dict[str, Any]] | None = None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def list_assets(self) -> list[Asset]:
        assets: list[Asset] = []
        for table in self._tables_data():
            table_fqn = str(table["fullyQualifiedName"])
            assets.append(Asset(id=table_fqn, type="table", name=str(table["name"])))
            for column in _columns(table):
                assets.append(_column_asset(table_fqn, table["name"], column))
        return assets

    def get_asset(self, asset_id: str) -> Asset:
        for asset in self.list_assets():
            if asset.id == asset_id:
                return asset
        message = f"unknown asset {asset_id}"
        raise KeyError(message)

    def get_dq_results(self, asset_id: str) -> list[DqResult]:
        asset = self.get_asset(asset_id)
        link = _entity_link(asset)
        response = self._client.get(
            "/api/v1/dataQuality/testCases",
            params={"entityLink": link, "fields": "testCaseResult", "limit": "100"},
            headers=self._headers,
        )
        response.raise_for_status()
        results: list[DqResult] = []
        for case in _data(response.json()):
            parsed = _dq_from_case(case)
            if parsed is not None:
                results.append(parsed)
        return results

    def get_profile(self, asset_id: str) -> Profile | None:
        asset = self.get_asset(asset_id)
        if asset.type != "column" or asset.table is None:
            return None
        table = self._table_for(asset.id[: -(len(asset.name) + 1)])
        response = self._client.get(
            f"/api/v1/tables/{quote(str(table['id']), safe='')}/columnProfile",
            params={"columnName": asset.name},
            headers=self._headers,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        rows = [row for row in _data(response.json()) if row.get("name") == asset.name]
        if not rows:
            return None
        latest = max(rows, key=lambda row: int(row.get("timestamp") or 0))
        return _profile_from_row(latest)

    def _tables_data(self) -> list[dict[str, Any]]:
        if self._tables is None:
            response = self._client.get(
                "/api/v1/tables",
                params={"limit": "100", "fields": "columns"},
                headers=self._headers,
            )
            response.raise_for_status()
            self._tables = _data(response.json())
        return self._tables

    def _table_for(self, name: str) -> dict[str, Any]:
        for table in self._tables_data():
            if table.get("name") == name or table.get("fullyQualifiedName") == name:
                return table
        message = f"unknown table {name}"
        raise KeyError(message)


def _columns(table: dict[str, Any]) -> list[dict[str, Any]]:
    raw = table.get("columns")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _column_asset(table_fqn: str, table_name: object, column: dict[str, Any]) -> Asset:
    name = str(column["name"])
    data_type = column.get("dataType")
    return Asset(
        id=f"{table_fqn}.{name}",
        type="column",
        name=name,
        table=str(table_name),
        data_type=str(data_type) if isinstance(data_type, str) else None,
    )


def _entity_link(asset: Asset) -> str:
    if asset.type == "column" and asset.table is not None:
        table_fqn = asset.id[: -(len(asset.name) + 1)]
        return f"<#E::table::{table_fqn}::columns::{asset.name}>"
    return f"<#E::table::{asset.id}>"


def _dq_from_case(case: dict[str, Any]) -> DqResult | None:
    result = case.get("testCaseResult")
    if not isinstance(result, dict):
        return None
    status = str(result.get("testCaseStatus", ""))
    if status in _PASS:
        outcome = "pass"
    elif status in _FAIL:
        outcome = "fail"
    else:
        outcome = status.lower() or "unknown"
    timestamp = result.get("timestamp")
    certified_at = _rfc3339(timestamp) if isinstance(timestamp, int) else "1970-01-01T00:00:00Z"
    statement = result.get("result")
    text = statement if isinstance(statement, str) and statement else str(case.get("name", "test"))
    updated_by = case.get("updatedBy")
    return DqResult(
        rule_id=str(case.get("name", "test")),
        statement=text,
        result=outcome,
        certified_by=updated_by if isinstance(updated_by, str) else "openmetadata",
        certified_at=certified_at,
    )


def _profile_from_row(row: dict[str, Any]) -> Profile:
    timestamp = row.get("timestamp")
    observed_at = _rfc3339(timestamp) if isinstance(timestamp, int) else "1970-01-01T00:00:00Z"
    metrics: list[ProfileMetric] = []
    proportion = row.get("nullProportion")
    if isinstance(proportion, int | float) and not isinstance(proportion, bool):
        metrics.append(ProfileMetric(metric="null_pct", value=float(proportion), unit="ratio"))
    return Profile(
        observed_at=observed_at,
        profile_run_id=str(timestamp if timestamp is not None else observed_at),
        metrics=tuple(metrics),
    )


def _data(payload: object) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        raw = payload.get("data", [])
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
    return []


def _rfc3339(epoch_ms: int) -> str:
    moment = datetime.fromtimestamp(epoch_ms / 1000, tz=UTC)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")
