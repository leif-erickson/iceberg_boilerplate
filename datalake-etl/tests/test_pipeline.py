from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]


def test_full_local_pipeline(tmp_path: Path) -> None:
    lake = tmp_path / "lake"
    ds = "2026-06-05"
    env = {
        **dict(__import__("os").environ),
        "LAKE_ROOT": str(lake),
        "DS": ds,
        "PYTHONPATH": str(ROOT),
        "DBT_DUCKDB_PATH": str(tmp_path / "pipeline.duckdb"),
        "DBT_PROFILES_DIR": str(ROOT / "dbt"),
        "PATH": f"{Path.home() / '.local' / 'bin'}:{__import__('os').environ.get('PATH', '')}",
    }

    for stage in ("fixtures", "ingest", "bronze", "silver", "gold"):
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "run_pipeline.py"), stage],
            check=True,
            cwd=ROOT,
            env=env,
        )

    gold_path = lake / "gold" / "mart_revenue_daily" / f"dt={ds}" / "data.parquet"
    assert gold_path.exists()

    con = duckdb.connect()
    row = con.execute(
        f"SELECT order_count, revenue_usd FROM read_parquet('{gold_path}')"
    ).fetchone()
    con.close()
    assert row is not None
    assert row[0] >= 1
    assert row[1] > 0
