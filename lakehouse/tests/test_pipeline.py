"""End-to-end pipeline tests (bronze -> silver -> Iceberg)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lakehouse import iceberg_io, quality, settings
from lakehouse.pipeline import run_dataset
from lakehouse.registry import load_contract

RAW = settings.PROJECT_ROOT / "data" / "raw" / "orders.csv"


def test_run_dataset_writes_iceberg(lake_env: Path) -> None:
    result = run_dataset("orders", RAW, ds="2026-06-05")
    assert result.bronze_rows == 6
    assert result.silver_rows == 6
    assert result.gold_rows == 6
    assert result.quality.passed

    table = iceberg_io.read_table(load_contract("orders"))
    assert table.height == 6
    # Departments are canonicalised and every order maps to an approved value.
    assert set(table["department"].unique().to_list()) <= {
        "People & Culture", "Finance", "Engineering", "Sales", "Marketing",
    }
    # Re-running the same partition is idempotent (overwrite, not append).
    run_dataset("orders", RAW, ds="2026-06-05")
    assert iceberg_io.read_table(load_contract("orders")).height == 6


def test_run_dataset_fails_quality_gate(lake_env: Path, tmp_path: Path) -> None:
    bad = tmp_path / "bad_orders.csv"
    bad.write_text(
        "order_id,customer_name,department,order_timestamp,amount\n"
        "ord-001,Jane Doe,wizardry,2026-06-05 09:30:00,\"1,000.00\"\n"
        "ord-001,John Roe,Finance,2026-06-05 10:30:00,\"-50,00\"\n",
        encoding="utf-8",
    )
    with pytest.raises(quality.QualityGateError):
        run_dataset("orders", bad, ds="2026-06-05")
