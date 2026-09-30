"""Reference MCP server over a fixture catalog."""

from __future__ import annotations

import os
from typing import Any

from fastmcp import FastMCP

from epienv.builder import DEFAULT_NOTICE
from epienv.enforce import InferencePolicy
from epienv.mcp import epistemic_tool
from epienv.models import AttributeValue, CertifiedFinding, Envelope, Observation, Subject
from examples.catalog_server.backends.fixture import Asset, CatalogBackend, FixtureBackend
from examples.catalog_server.inference.static import InferenceProvider, StaticInferenceProvider


def policy_from_env() -> InferencePolicy:
    """``EPIENV_INFERENCE=off`` withholds inferences."""
    flag = os.environ.get("EPIENV_INFERENCE", "").strip().lower()
    permitted = flag not in {"off", "false", "0"}
    return InferencePolicy(permitted=permitted)


def build_server(
    backend: CatalogBackend | None = None,
    provider: InferenceProvider | None = None,
    policy: InferencePolicy | None = None,
) -> FastMCP:
    """Build the catalog server. Defaults are the seed fixture and static inferences."""
    catalog = backend if backend is not None else FixtureBackend()
    inferences = provider if provider is not None else StaticInferenceProvider()
    active_policy = policy if policy is not None else policy_from_env()
    server: FastMCP = FastMCP("epistemic-catalog")

    def list_mapper(raw: dict[str, Any]) -> Envelope:
        del raw  # list_assets ignores the payload
        assets = catalog.list_assets()
        tables = sum(1 for asset in assets if asset.type == "table")
        columns = sum(1 for asset in assets if asset.type == "column")
        return Envelope(
            subject=Subject(type="catalog", id="seed", name="seed catalog"),
            attributes={"table_count": tables, "column_count": columns},
            inference_permitted=True,
            profiling_observations=[
                Observation(
                    id="po-1",
                    metric="asset_count",
                    value=float(len(assets)),
                    observed_at="2026-09-20T00:00:00Z",
                    profile_run_id="seed",
                )
            ],
        )

    def profile_mapper(raw: dict[str, Any]) -> Envelope:
        return _asset_envelope(
            catalog,
            inferences,
            str(raw["asset_id"]),
            quality=False,
            profile=True,
            inferred=True,
        )

    def describe_mapper(raw: dict[str, Any]) -> Envelope:
        return _asset_envelope(
            catalog,
            inferences,
            str(raw["asset_id"]),
            quality=True,
            profile=True,
            inferred=True,
        )

    def quality_mapper(raw: dict[str, Any]) -> Envelope:
        return _asset_envelope(
            catalog,
            inferences,
            str(raw["asset_id"]),
            quality=True,
            profile=False,
            inferred=False,
        )

    @epistemic_tool(server, mapper=list_mapper, policy=active_policy)
    def list_assets() -> dict[str, Any]:
        """List tables and columns in the seed catalog."""
        return {}

    @epistemic_tool(server, mapper=profile_mapper, policy=active_policy)
    def get_asset_profile(asset_id: str) -> dict[str, Any]:
        """Return profiling observations, and inferences when policy allows them."""
        return {"asset_id": asset_id}

    @epistemic_tool(server, mapper=describe_mapper, policy=active_policy)
    def describe_asset(asset_id: str) -> dict[str, Any]:
        """Return quality results, profile, and inferences for one asset."""
        return {"asset_id": asset_id}

    @epistemic_tool(server, mapper=quality_mapper, policy=active_policy)
    def get_quality(asset_id: str) -> dict[str, Any]:
        """Return certified data-quality findings for one asset."""
        return {"asset_id": asset_id}

    return server


def main() -> None:
    """Serve the catalog over stdio."""
    build_server().run()


def _asset_envelope(
    catalog: CatalogBackend,
    provider: InferenceProvider,
    asset_id: str,
    *,
    quality: bool,
    profile: bool,
    inferred: bool,
) -> Envelope:
    asset = catalog.get_asset(asset_id)
    findings = _findings(catalog, asset_id) if quality else []
    observations = _observations(catalog, asset_id) if profile else []
    produced = (
        provider.infer(
            asset_id,
            [item.id for item in observations],
            catalog.get_profile(asset_id) if profile else None,
            catalog.get_dq_results(asset_id) if quality else None,
        )
        if inferred
        else []
    )
    notice = DEFAULT_NOTICE if produced else None
    return Envelope(
        subject=_subject(asset),
        attributes=_attributes(asset),
        inference_permitted=True,
        governance_notice=notice,
        certified_findings=findings,
        profiling_observations=observations,
        ai_inferences=produced,
    )


def _subject(asset: Asset) -> Subject:
    return Subject(type=asset.type, id=asset.id, name=asset.name)


def _attributes(asset: Asset) -> dict[str, AttributeValue]:
    values: dict[str, AttributeValue] = {}
    if asset.table is not None:
        values["table"] = asset.table
    if asset.data_type is not None:
        values["data_type"] = asset.data_type
    return values


def _findings(catalog: CatalogBackend, asset_id: str) -> list[CertifiedFinding]:
    return [
        CertifiedFinding(
            id=f"cf-{index}",
            statement=item.statement,
            rule_id=item.rule_id,
            result=item.result,
            value=item.value,
            certified_by=item.certified_by,
            certified_at=item.certified_at,
        )
        for index, item in enumerate(catalog.get_dq_results(asset_id), start=1)
    ]


def _observations(catalog: CatalogBackend, asset_id: str) -> list[Observation]:
    profile = catalog.get_profile(asset_id)
    if profile is None:
        return []
    return [
        Observation(
            id=f"po-{index}",
            metric=item.metric,
            value=item.value,
            unit=item.unit,
            observed_at=profile.observed_at,
            profile_run_id=profile.profile_run_id,
        )
        for index, item in enumerate(profile.metrics, start=1)
    ]
