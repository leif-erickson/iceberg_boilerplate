"""Command-line entrypoint for the lakehouse.

Examples:
    python -m lakehouse.cli run orders data/raw/orders.csv --ds 2026-06-05
    python -m lakehouse.cli sodacl orders --out governance/soda/orders.yml
"""

from __future__ import annotations

import argparse
from pathlib import Path

from lakehouse import quality, settings
from lakehouse.pipeline import run_dataset
from lakehouse.registry import load_contract


def _run(args: argparse.Namespace) -> None:
    result = run_dataset(args.dataset, args.raw, ds=args.ds)
    print(
        f"[{result.dataset}] bronze={result.bronze_rows} silver={result.silver_rows} "
        f"gold={result.gold_rows} quality_passed={result.quality.passed}"
    )
    for check in result.quality.results:
        print(f"  - {check.name}: {'PASS' if check.passed else 'FAIL'} {check.detail}".rstrip())


def _sodacl(args: argparse.Namespace) -> None:
    sodacl = quality.to_sodacl(load_contract(args.dataset))
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(sodacl, encoding="utf-8")
        print(f"wrote {out}")
    else:
        print(sodacl, end="")


def main() -> None:
    parser = argparse.ArgumentParser(description="Governance-driven lakehouse pipeline")
    sub = parser.add_subparsers(required=True)

    run_p = sub.add_parser("run", help="Run bronze -> silver -> Iceberg for a dataset")
    run_p.add_argument("dataset")
    run_p.add_argument("raw")
    run_p.add_argument("--ds", default=settings.partition_date())
    run_p.set_defaults(func=_run)

    soda_p = sub.add_parser("sodacl", help="Compile a contract's quality gates to SodaCL")
    soda_p.add_argument("dataset")
    soda_p.add_argument("--out", default=None)
    soda_p.set_defaults(func=_sodacl)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
