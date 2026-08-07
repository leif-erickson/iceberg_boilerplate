"""Tests for the declarative quality gates + SodaCL compilation."""

from __future__ import annotations

from datetime import datetime, timezone

import polars as pl

from lakehouse import quality
from lakehouse.registry import load_contract


def _silver(rows: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(rows)


def test_gates_pass_on_clean_frame() -> None:
    contract = load_contract("orders")
    frame = _silver(
        [
            {"order_id": "A", "customer_name": "Jose Garcia", "department": "Finance",
             "order_ts_utc": datetime(2026, 6, 5, tzinfo=timezone.utc), "amount_usd": 10.0},
            {"order_id": "B", "customer_name": "Zoe Muller", "department": "Sales",
             "order_ts_utc": datetime(2026, 6, 5, tzinfo=timezone.utc), "amount_usd": 20.0},
        ]
    )
    report = quality.run_quality_gates(frame, contract)
    assert report.passed, report.failures


def test_gates_flag_all_violations() -> None:
    contract = load_contract("orders")
    frame = _silver(
        [
            {"order_id": "A", "customer_name": "X", "department": "Finance",
             "order_ts_utc": datetime(2026, 6, 5, tzinfo=timezone.utc), "amount_usd": 1.0},
            {"order_id": "A", "customer_name": "Y", "department": "Bogus",
             "order_ts_utc": datetime(2026, 6, 5, tzinfo=timezone.utc), "amount_usd": -5.0},
            {"order_id": None, "customer_name": "Z", "department": "Sales",
             "order_ts_utc": datetime(2026, 6, 5, tzinfo=timezone.utc), "amount_usd": 2.0},
        ]
    )
    report = quality.run_quality_gates(frame, contract)
    failed = {r.name for r in report.failures}
    assert not report.passed
    assert {"keys_not_null", "unique_order_id", "amount_non_negative", "department_is_canonical"} <= failed


def test_to_sodacl_contains_expected_checks() -> None:
    contract = load_contract("orders")
    sodacl = quality.to_sodacl(contract)
    assert "checks for orders:" in sodacl
    assert "duplicate_count(order_id) = 0" in sodacl
    assert "min(amount_usd) >= 0" in sodacl
    assert "row_count >= 1" in sodacl
    assert "invalid_count(department) = 0" in sodacl
