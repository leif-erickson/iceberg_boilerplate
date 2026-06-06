"""Thin ingest: fetch source payload and write staging Parquet only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from scripts.env import ensure_lake_dirs, lake_root, partition_date


def fetch_orders(ds: str) -> list[dict[str, object]]:
    """Replace with real HTTP client; keep this layer free of transform logic."""
    return [
        {
            "order_id": "o-200",
            "customer_id": "c-9",
            "amount_usd": 88.0,
            "status": "paid",
            "event_ts": f"{ds}T12:30:00",
        },
        {
            "order_id": "o-201",
            "customer_id": "c-10",
            "amount_usd": 15.5,
            "status": "paid",
            "event_ts": f"{ds}T13:00:00",
        },
    ]


def write_staging(rows: list[dict[str, object]], lake_root_value: str, ds: str) -> Path:
    ensure_lake_dirs(lake_root_value)
    out_dir = Path(lake_root_value) / "staging" / "orders" / ds
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "orders_api.parquet"
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, out_path)

    manifest = out_dir / "manifest.json"
    manifest.write_text(json.dumps({"source": "orders_api", "rows": len(rows)}, indent=2))
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest orders API to staging")
    parser.add_argument("--lake-root", default=lake_root())
    parser.add_argument("--ds", default=partition_date())
    args = parser.parse_args()

    rows = fetch_orders(args.ds)
    out_path = write_staging(rows, args.lake_root, args.ds)
    print(f"Ingested {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
