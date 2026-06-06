from __future__ import annotations

from pathlib import Path

import duckdb

from scripts.run_bronze import run_bronze
from scripts.seed_fixtures import write_fixture


def test_bronze_land_deduplicates_sources(tmp_path: Path) -> None:
    lake = tmp_path / "lake"
    ds = "2026-06-05"
    write_fixture(str(lake), ds)

    con = duckdb.connect()
    con.execute(
        f"""
        COPY (
            SELECT 'o-300' AS order_id, 'c-1' AS customer_id, 10.0 AS amount_usd,
                   'paid' AS status, '{ds}T14:00:00' AS event_ts
        ) TO '{lake}/staging/orders/{ds}/extra.parquet' (FORMAT PARQUET)
        """
    )
    con.close()

    run_bronze(lake_root_value=str(lake), ds=ds)

    bronze_path = lake / "bronze" / "orders" / f"dt={ds}" / "orders.parquet"
    assert bronze_path.exists()

    con = duckdb.connect()
    row = con.execute(
        f"""
        SELECT count(*) AS n,
               count(*) FILTER (WHERE _ingested_at IS NOT NULL) AS with_ingested
        FROM read_parquet('{bronze_path}')
        """
    ).fetchone()
    con.close()
    assert row[0] == 5
    assert row[1] == 5
