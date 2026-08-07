"""Apache Iceberg IO via PyIceberg.

Locally this uses a SQLite catalog and a filesystem warehouse. In prod, set
`ICEBERG_CATALOG_URI`/`ICEBERG_WAREHOUSE` (or swap to the Glue catalog) without
changing the pipeline code. The Iceberg schema is derived from the data
contract, so schema drift is governed centrally.
"""

from __future__ import annotations

import polars as pl
import pyarrow as pa
from pyiceberg.catalog.sql import SqlCatalog
from pyiceberg.partitioning import PartitionField, PartitionSpec
from pyiceberg.schema import Schema
from pyiceberg.table import Table
from pyiceberg.transforms import IdentityTransform
from pyiceberg.types import (
    BooleanType,
    DateType,
    DoubleType,
    IntegerType,
    LongType,
    NestedField,
    StringType,
    TimestamptzType,
)

from lakehouse import settings
from lakehouse.registry import DataContract

_LOGICAL_TO_ICEBERG = {
    "string": StringType,
    "int": IntegerType,
    "long": LongType,
    "double": DoubleType,
    "decimal": DoubleType,
    "boolean": BooleanType,
    "date": DateType,
    "timestamp": TimestamptzType,
}

PARTITION_COLUMN = "dt"


def get_catalog() -> SqlCatalog:
    return SqlCatalog(
        settings.catalog_name(),
        uri=settings.catalog_uri(),
        warehouse=f"file://{settings.warehouse_path()}",
    )


def build_iceberg_schema(contract: DataContract) -> tuple[Schema, int]:
    """Return the Iceberg schema for the contract plus the `dt` partition field id."""
    fields: list[NestedField] = []
    field_id = 1
    for spec in contract.fields:
        fields.append(
            NestedField(
                field_id=field_id,
                name=spec.name,
                field_type=_LOGICAL_TO_ICEBERG[spec.type](),
                required=not spec.nullable,
            )
        )
        field_id += 1
    dt_field_id = field_id
    fields.append(NestedField(field_id=dt_field_id, name=PARTITION_COLUMN,
                              field_type=StringType(), required=True))
    return Schema(*fields), dt_field_id


def ensure_table(contract: DataContract) -> Table:
    catalog = get_catalog()
    namespace = settings.catalog_namespace()
    catalog.create_namespace_if_not_exists((namespace,))
    identifier = (namespace, contract.dataset)
    if catalog.table_exists(identifier):
        return catalog.load_table(identifier)

    schema, dt_field_id = build_iceberg_schema(contract)
    spec = PartitionSpec(
        PartitionField(source_id=dt_field_id, field_id=1000,
                       transform=IdentityTransform(), name=PARTITION_COLUMN)
    )
    return catalog.create_table(identifier=identifier, schema=schema, partition_spec=spec)


def _to_arrow(frame: pl.DataFrame, ds: str) -> pa.Table:
    return frame.with_columns(pl.lit(ds).alias(PARTITION_COLUMN)).to_arrow()


def write_partition(frame: pl.DataFrame, contract: DataContract, ds: str) -> int:
    """Overwrite the `dt=ds` partition of the contract's Iceberg table.

    Overwriting the partition keeps re-runs idempotent (no duplicate rows).
    Returns the number of rows written.
    """
    table = ensure_table(contract)
    arrow_table = _to_arrow(frame, ds).cast(table.schema().as_arrow())
    table.delete(f"{PARTITION_COLUMN} = '{ds}'")
    table.append(arrow_table)
    return frame.height


def read_table(contract: DataContract) -> pl.DataFrame:
    table = ensure_table(contract)
    return pl.from_arrow(table.scan().to_arrow())
