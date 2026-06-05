"""Orchestrate medallion layers with one entrypoint (local and ECS)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from scripts.env import duckdb_path, lake_root, partition_date
from scripts.lineage import lineage_enabled
from scripts.run_bronze import run_bronze
from scripts.run_gx import run_gx
from scripts.seed_fixtures import write_fixture

ROOT = Path(__file__).resolve().parents[1]


def pipeline_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env.setdefault("DBT_PROFILES_DIR", str(ROOT / "dbt"))
    env.setdefault("DBT_DUCKDB_PATH", str(duckdb_path()))
    env.setdefault("OPENLINEAGE_NAMESPACE", "datalake-etl")
    if lineage_enabled() and not env.get("OPENLINEAGE_CONFIG") and not env.get("OPENLINEAGE_URL"):
        env["OPENLINEAGE_CONFIG"] = str(ROOT / "quality" / "openlineage" / "openlineage.local.yml")
    return env


def _dbt_executable() -> str:
    if lineage_enabled():
        dbt_ol = Path.home() / ".local" / "bin" / "dbt-ol"
        if dbt_ol.exists():
            return str(dbt_ol)
    local_dbt = Path.home() / ".local" / "bin" / "dbt"
    return str(local_dbt) if local_dbt.exists() else "dbt"


def run_dbt(step: str, ds: str, lake_root_value: str, *, select: str | None = None) -> None:
    cmd = [
        _dbt_executable(),
        step,
        "--project-dir",
        str(ROOT / "dbt"),
        "--profiles-dir",
        str(ROOT / "dbt"),
        "--vars",
        f'{{"ds": "{ds}", "lake_root": "{lake_root_value}"}}',
    ]
    if select:
        cmd.extend(["--select", select])
    subprocess.run(cmd, check=True, env=pipeline_env())


def main() -> None:
    parser = argparse.ArgumentParser(description="Run medallion ETL pipeline")
    parser.add_argument(
        "stage",
        choices=[
            "fixtures",
            "ingest",
            "bronze",
            "gx-bronze",
            "silver",
            "gx-silver",
            "gold",
            "gold-dimensional",
            "gold-denormalized",
            "test",
            "all",
        ],
        nargs="?",
        default="all",
    )
    parser.add_argument("--lake-root", default=lake_root())
    parser.add_argument("--ds", default=partition_date())
    args = parser.parse_args()

    if args.stage in {"fixtures", "all"}:
        write_fixture(args.lake_root, args.ds)

    if args.stage in {"ingest", "all"}:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "ingest" / "orders_api.py"),
                "--ds",
                args.ds,
                "--lake-root",
                args.lake_root,
            ],
            check=True,
            env=pipeline_env(),
        )

    if args.stage in {"bronze", "all"}:
        run_bronze(lake_root_value=args.lake_root, ds=args.ds)

    if args.stage in {"gx-bronze", "all"}:
        run_gx("bronze", lake_root_value=args.lake_root, ds=args.ds)

    if args.stage in {"silver", "all"}:
        run_dbt("run", args.ds, args.lake_root, select="silver.*")

    if args.stage in {"gx-silver", "all"}:
        run_gx("silver", lake_root_value=args.lake_root, ds=args.ds)

    if args.stage in {"gold", "gold-dimensional", "all"}:
        run_dbt("run", args.ds, args.lake_root, select="tag:dimensional")

    if args.stage in {"gold", "gold-denormalized", "all"}:
        run_dbt("run", args.ds, args.lake_root, select="tag:denormalized")

    if args.stage in {"test", "all"}:
        subprocess.run(
            [sys.executable, "-m", "pytest", str(ROOT / "tests"), "-q"],
            check=True,
            env=pipeline_env(),
        )
        run_dbt("test", args.ds, args.lake_root)

    print(f"Pipeline stage '{args.stage}' completed for ds={args.ds}")


if __name__ == "__main__":
    main()
