"""dbt CLI helpers."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from scripts.env import duckdb_path
from scripts.lineage import lineage_enabled

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
