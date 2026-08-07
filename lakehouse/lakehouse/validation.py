"""Pandera schema validation derived from a data contract.

Pandera enforces the *structural* contract (columns present, logical dtype,
nullability). Value-level rules live in `quality.py` as quality gates. Both are
generated from the same contract YAML.
"""

from __future__ import annotations

import pandera.polars as pa
import polars as pl

from lakehouse.registry import DataContract

_LOGICAL_TO_POLARS: dict[str, pl.DataType] = {
    "string": pl.Utf8,
    "int": pl.Int32,
    "long": pl.Int64,
    "double": pl.Float64,
    "decimal": pl.Float64,
    "boolean": pl.Boolean,
    "date": pl.Date,
    "timestamp": pl.Datetime(time_unit="us", time_zone="UTC"),
}


def build_schema(contract: DataContract) -> pa.DataFrameSchema:
    columns = {
        spec.name: pa.Column(
            _LOGICAL_TO_POLARS[spec.type],
            nullable=spec.nullable,
            coerce=True,
        )
        for spec in contract.fields
    }
    return pa.DataFrameSchema(columns, strict=True, coerce=True)


def validate_schema(frame: pl.DataFrame, contract: DataContract) -> pl.DataFrame:
    """Validate `frame` against the contract schema; raises on violation."""
    return build_schema(contract).validate(frame)
