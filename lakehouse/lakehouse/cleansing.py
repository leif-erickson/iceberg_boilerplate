"""Contract-driven cleansing + normalization built on Polars.

Each cleansing rule named in a data contract maps to a scalar helper here and is
composed into a Polars expression per field. `apply_contract` runs the full set:
rename raw columns, apply cleansing, resolve canonical mappings, and cast to the
contract's logical types.
"""

from __future__ import annotations

import unicodedata
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import polars as pl
from dateutil import parser as dateutil_parser

from lakehouse import registry
from lakehouse.registry import CleansingStep, DataContract, FieldSpec

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


# Letters that do NOT decompose under NFKD (stroke/ligature letters) need an
# explicit transliteration so "scrub diacritics" also folds them to ASCII.
_TRANSLITERATION = str.maketrans(
    {
        "ø": "o", "Ø": "O",
        "ł": "l", "Ł": "L",
        "đ": "d", "Đ": "D",
        "ð": "d", "Ð": "D",
        "æ": "ae", "Æ": "AE",
        "œ": "oe", "Œ": "OE",
        "ß": "ss",
    }
)


def strip_diacritics(text: str) -> str:
    """"José" -> "Jose", "Bjørk" -> "Bjork". NFKD decompose, drop combining
    marks, and transliterate non-decomposable stroke/ligature letters."""
    pre = text.translate(_TRANSLITERATION)
    decomposed = unicodedata.normalize("NFKD", pre)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def to_utc_iso8601(value: str, assume_timezone: str = "UTC") -> datetime | None:
    """Parse a timestamp string and return a tz-aware UTC datetime.

    Naive inputs are interpreted in `assume_timezone`. The value is stored as a
    real UTC timestamp; any ISO-8601 rendering is a serialization detail.
    """
    text = (value or "").strip()
    if not text:
        return None
    parsed = dateutil_parser.parse(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(assume_timezone))
    return parsed.astimezone(timezone.utc)


def normalize_us_number(value: str, source_format: str = "auto") -> float | None:
    """Normalize a numeric string with mixed EU/US separators to a float.

    Examples: "1.234,56" -> 1234.56, "1,234.56" -> 1234.56, "1 234,56" -> 1234.56.
    """
    text = (value or "").strip()
    if not text:
        return None
    # Drop currency symbols, spaces, and non-breaking spaces; keep sign/digits/.,
    cleaned = "".join(c for c in text if c.isdigit() or c in ".,-")
    if not cleaned:
        return None

    has_dot = "." in cleaned
    has_comma = "," in cleaned

    if source_format == "us":
        cleaned = cleaned.replace(",", "")
    elif source_format == "eu":
        cleaned = cleaned.replace(".", "").replace(",", ".")
    else:  # auto
        if has_dot and has_comma:
            # The right-most separator is the decimal point.
            decimal_sep = "," if cleaned.rfind(",") > cleaned.rfind(".") else "."
            thousands_sep = "." if decimal_sep == "," else ","
            cleaned = cleaned.replace(thousands_sep, "").replace(decimal_sep, ".")
        elif has_comma:
            cleaned = cleaned.replace(",", ".")
        # only a dot (or plain integer): already US-style
    try:
        return float(cleaned)
    except ValueError:
        return None


def _apply_step(expr: pl.Expr, step: CleansingStep) -> pl.Expr:
    rule = step.rule
    if rule == "trim":
        return expr.str.strip_chars().str.replace_all(r"\s+", " ")
    if rule == "upper":
        return expr.str.to_uppercase()
    if rule == "lower":
        return expr.str.to_lowercase()
    if rule == "title_case":
        return expr.str.to_titlecase()
    if rule == "scrub_diacritics":
        return expr.map_elements(strip_diacritics, return_dtype=pl.Utf8)
    if rule == "utc_iso8601":
        assume_tz = str(step.params.get("assume_timezone", "UTC"))
        return expr.map_elements(
            lambda s: to_utc_iso8601(s, assume_tz),
            return_dtype=pl.Datetime(time_unit="us", time_zone="UTC"),
        )
    if rule == "us_number_format":
        source_format = str(step.params.get("source_format", "auto"))
        return expr.map_elements(
            lambda s: normalize_us_number(s, source_format),
            return_dtype=pl.Float64,
        )
    raise ValueError(f"unknown cleansing rule: {rule!r}")


def _field_expr(spec: FieldSpec) -> pl.Expr:
    expr = pl.col(spec.raw_name).cast(pl.Utf8, strict=False)
    for step in spec.cleansing:
        expr = _apply_step(expr, step)
    # If cleansing already produced a non-string dtype (timestamp/number), don't
    # force a Utf8 round-trip; otherwise cast to the logical target type.
    produces_typed = any(s.rule in {"utc_iso8601", "us_number_format"} for s in spec.cleansing)
    if not produces_typed:
        expr = expr.cast(_LOGICAL_TO_POLARS[spec.type], strict=False)
    return expr.alias(spec.name)


def apply_contract(frame: pl.DataFrame, contract: DataContract) -> pl.DataFrame:
    """Produce the cleansed, canonicalised, typed frame described by `contract`."""
    cleansed = frame.select([_field_expr(spec) for spec in contract.fields])

    # Resolve canonical mappings (alias -> approved value) after cleansing.
    for spec in contract.fields:
        if spec.canonical:
            cmap = registry.load_canonical(spec.canonical)
            cleansed = cleansed.with_columns(
                pl.col(spec.name).map_elements(cmap.resolve, return_dtype=pl.Utf8)
            )
    return cleansed
