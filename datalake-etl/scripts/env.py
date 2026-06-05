"""Shared environment helpers for local and prod parity."""

from __future__ import annotations

import os
from pathlib import Path


def lake_root() -> str:
    return os.environ.get("LAKE_ROOT", "./lake")


def partition_date() -> str:
    return os.environ.get("DS", "2026-06-05")


def dbt_target() -> str:
    return os.environ.get("DBT_TARGET", "local")


def duckdb_path() -> Path:
    root = Path(__file__).resolve().parents[1] / "duckdb"
    root.mkdir(exist_ok=True)
    return root / f"{dbt_target()}.duckdb"


def ensure_lake_dirs(base: str | Path, ds: str | None = None) -> None:
    base_path = Path(base)
    for layer in ("staging/orders", "bronze/orders", "silver/orders", "gold/mart_revenue_daily"):
        (base_path / layer).mkdir(parents=True, exist_ok=True)
    if ds:
        for layer in ("bronze/orders", "silver/orders", "gold/mart_revenue_daily"):
            (base_path / layer / f"dt={ds}").mkdir(parents=True, exist_ok=True)
        (base_path / "staging" / "orders" / ds).mkdir(parents=True, exist_ok=True)
