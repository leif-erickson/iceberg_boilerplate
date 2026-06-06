"""Great Expectations suite for silver orders."""

from __future__ import annotations

from typing import Any

import pandas as pd

EXPECTATIONS: list[tuple[str, dict[str, Any]]] = [
    ("expect_table_row_count_to_be_between", {"min_value": 1}),
    ("expect_column_values_to_not_be_null", {"column": "order_id"}),
    ("expect_column_values_to_be_unique", {"column": "order_id"}),
    ("expect_column_values_to_be_in_set", {"column": "status", "value_set": ["paid"]}),
    ("expect_column_values_to_be_between", {"column": "amount_usd", "min_value": 0}),
]


def validate(df: pd.DataFrame) -> None:
    import great_expectations as gx

    context = gx.get_context(mode="ephemeral")
    validator = context.sources.pandas_default.read_dataframe(df)
    for expectation_type, kwargs in EXPECTATIONS:
        getattr(validator, expectation_type)(**kwargs)
    result = validator.validate()
    if not result["success"]:
        failed = [r.expectation_config.expectation_type for r in result.results if not r.success]
        raise ValueError(f"silver.orders GX failed: {failed}")
