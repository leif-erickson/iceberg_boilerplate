"""Render Jinja-templated SQL and execute in DuckDB."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
from jinja2 import Template

from scripts.env import duckdb_path, ensure_lake_dirs, lake_root, partition_date


def render_sql(sql_path: Path, context: dict[str, str]) -> str:
    template = Template(sql_path.read_text())
    return template.render(**context)


def run_sql_file(
    sql_path: Path,
    *,
    lake_root_value: str,
    ds: str,
    database: Path | None = None,
) -> None:
    ensure_lake_dirs(lake_root_value, ds)
    context = {
        "lake_root": lake_root_value.rstrip("/"),
        "ds": ds,
        "source_uri": f"staging/orders/{ds}",
    }
    sql = render_sql(sql_path, context)
    db_path = database or duckdb_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(db_path))
    try:
        for statement in _split_statements(sql):
            con.execute(statement)
    finally:
        con.close()


def _split_statements(sql: str) -> list[str]:
    parts = [part.strip() for part in sql.split(";")]
    return [part for part in parts if part]


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute templated SQL with DuckDB")
    parser.add_argument("sql_file", type=Path)
    parser.add_argument("--lake-root", default=lake_root())
    parser.add_argument("--ds", default=partition_date())
    args = parser.parse_args()
    run_sql_file(args.sql_file, lake_root_value=args.lake_root, ds=args.ds)
    print(f"Executed {args.sql_file} for ds={args.ds}")


if __name__ == "__main__":
    main()
