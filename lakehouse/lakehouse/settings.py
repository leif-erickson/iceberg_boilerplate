"""Environment + path helpers for local/prod parity.

Local development uses a filesystem warehouse and a SQLite Iceberg catalog. In
production the same code targets S3 + AWS Glue by overriding a few env vars, so
nothing here hardcodes prod locations.
"""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent

GOVERNANCE_DIR = PROJECT_ROOT / "governance"
CONTRACTS_DIR = GOVERNANCE_DIR / "contracts"
CANONICAL_DIR = GOVERNANCE_DIR / "canonical"
CLEANSING_RULES_FILE = GOVERNANCE_DIR / "cleansing_rules.yaml"


def lake_root() -> Path:
    """Root of the local lake / warehouse (S3 URI prefix in prod)."""
    return Path(os.environ.get("LAKE_ROOT", str(PROJECT_ROOT / "lake")))


def warehouse_path() -> Path:
    """Iceberg warehouse directory."""
    path = Path(os.environ.get("ICEBERG_WAREHOUSE", str(lake_root() / "warehouse")))
    path.mkdir(parents=True, exist_ok=True)
    return path


def catalog_uri() -> str:
    """SQLAlchemy URI for the local Iceberg SQL catalog (Glue in prod)."""
    default = f"sqlite:///{lake_root() / 'catalog.db'}"
    lake_root().mkdir(parents=True, exist_ok=True)
    return os.environ.get("ICEBERG_CATALOG_URI", default)


def catalog_name() -> str:
    return os.environ.get("ICEBERG_CATALOG_NAME", "lakehouse")


def catalog_namespace() -> str:
    return os.environ.get("ICEBERG_NAMESPACE", "silver")


def partition_date() -> str:
    return os.environ.get("DS", "2026-06-05")
