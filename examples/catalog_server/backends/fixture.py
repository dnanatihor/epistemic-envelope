"""In-process catalog loaded from seed.json."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Asset:
    """A table or column in the catalog."""

    id: str
    type: str
    name: str
    table: str | None = None
    data_type: str | None = None


@dataclass(frozen=True, slots=True)
class DqResult:
    """One approved data-quality rule result."""

    rule_id: str
    statement: str
    result: str
    certified_by: str
    certified_at: str
    value: float | None = None


@dataclass(frozen=True, slots=True)
class ProfileMetric:
    """One measured metric inside a profile run."""

    metric: str
    value: float
    unit: str | None = None


@dataclass(frozen=True, slots=True)
class Profile:
    """Metrics from one profiling run."""

    observed_at: str
    profile_run_id: str
    metrics: tuple[ProfileMetric, ...]


class CatalogBackend(Protocol):
    """Read assets, data-quality results, and profiles."""

    def list_assets(self) -> list[Asset]: ...

    def get_asset(self, asset_id: str) -> Asset: ...

    def get_dq_results(self, asset_id: str) -> list[DqResult]: ...

    def get_profile(self, asset_id: str) -> Profile | None: ...


class FixtureBackend:
    """Catalog stored in ``data/seed.json``. No network and no extra services."""

    def __init__(self, path: Path | None = None) -> None:
        seed_path = path or Path(__file__).resolve().parent.parent / "data" / "seed.json"
        with seed_path.open(encoding="utf-8") as handle:
            raw: dict[str, object] = json.load(handle)
        self._assets = [_asset(item) for item in _as_list(raw.get("assets"))]
        self._by_id = {asset.id: asset for asset in self._assets}
        self._dq = {
            key: [_dq(item) for item in _as_list(value)]
            for key, value in _as_dict(raw.get("dq_results")).items()
        }
        self._profiles = {
            key: _profile(value) for key, value in _as_dict(raw.get("profiles")).items()
        }

    def list_assets(self) -> list[Asset]:
        return list(self._assets)

    def get_asset(self, asset_id: str) -> Asset:
        try:
            return self._by_id[asset_id]
        except KeyError as exc:
            message = f"unknown asset {asset_id}"
            raise KeyError(message) from exc

    def get_dq_results(self, asset_id: str) -> list[DqResult]:
        self.get_asset(asset_id)
        return list(self._dq.get(asset_id, []))

    def get_profile(self, asset_id: str) -> Profile | None:
        self.get_asset(asset_id)
        return self._profiles.get(asset_id)


def _asset(item: object) -> Asset:
    body = _as_dict(item)
    table = body.get("table")
    data_type = body.get("data_type")
    return Asset(
        id=_text(body, "id"),
        type=_text(body, "type"),
        name=_text(body, "name"),
        table=table if isinstance(table, str) else None,
        data_type=data_type if isinstance(data_type, str) else None,
    )


def _dq(item: object) -> DqResult:
    body = _as_dict(item)
    value = body.get("value")
    return DqResult(
        rule_id=_text(body, "rule_id"),
        statement=_text(body, "statement"),
        result=_text(body, "result"),
        certified_by=_text(body, "certified_by"),
        certified_at=_text(body, "certified_at"),
        value=_number(value),
    )


def _profile(item: object) -> Profile:
    body = _as_dict(item)
    metrics = tuple(_metric(entry) for entry in _as_list(body.get("metrics")))
    return Profile(
        observed_at=_text(body, "observed_at"),
        profile_run_id=_text(body, "profile_run_id"),
        metrics=metrics,
    )


def _metric(item: object) -> ProfileMetric:
    body = _as_dict(item)
    unit = body.get("unit")
    value = body.get("value")
    if isinstance(value, bool) or not isinstance(value, int | float):
        message = "profile metric value must be a number"
        raise TypeError(message)
    return ProfileMetric(
        metric=_text(body, "metric"),
        value=float(value),
        unit=unit if isinstance(unit, str) else None,
    )


def _as_dict(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        message = "expected a JSON object"
        raise TypeError(message)
    return {str(key): item for key, item in value.items()}


def _as_list(value: object) -> list[object]:
    if not isinstance(value, list):
        message = "expected a JSON array"
        raise TypeError(message)
    return list(value)


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _text(body: dict[str, object], key: str) -> str:
    value = body.get(key)
    if not isinstance(value, str):
        message = f"{key} must be a string"
        raise TypeError(message)
    return value
