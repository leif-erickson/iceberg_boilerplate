"""Generate tiny staging Parquet fixtures for local development."""

from __future__ import annotations

import argparse
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from scripts.env import ensure_lake_dirs, lake_root, partition_date


def build_orders_table() -> pa.Table:
    return pa.table(
        {
            "order_id": ["o-100", "o-101", "o-101", "o-102"],
            "customer_id": ["c-1", "c-2", "c-2", "c-3"],
            "amount_usd": [120.5, 45.0, 45.0, 310.25],
            "status": ["paid", "paid", "paid", "pending"],
            "event_ts": [
                "2026-06-05T08:00:00",
                "2026-06-05T09:15:00",
                "2026-06-05T09:16:00",
                "2026-06-05T11:00:00",
            ],
        }
    )


def write_fixture(lake_root_value: str, ds: str) -> Path:
    ensure_lake_dirs(lake_root_value)
    out_dir = Path(lake_root_value) / "staging" / "orders" / ds
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "orders.parquet"
    pq.write_table(build_orders_table(), out_path)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed local staging fixtures")
    parser.add_argument("--lake-root", default=lake_root())
    parser.add_argument("--ds", default=partition_date())
    args = parser.parse_args()
    out_path = write_fixture(args.lake_root, args.ds)
    print(f"Wrote fixture: {out_path}")


if __name__ == "__main__":
    main()
