"""Dagster code location for the lakehouse."""

from __future__ import annotations

from dagster import Definitions, load_assets_from_modules

from dagster_project import assets

defs = Definitions(
    assets=load_assets_from_modules([assets]),
    asset_checks=[assets.orders_quality_gates],
)
