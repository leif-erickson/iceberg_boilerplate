"""Unit tests for the cleansing / normalization rules."""

from __future__ import annotations

import pytest

from lakehouse.cleansing import normalize_us_number, strip_diacritics, to_utc_iso8601


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("José", "Jose"),
        ("Renée Dubois", "Renee Dubois"),
        ("Åsa Lindström", "Asa Lindstrom"),
        ("Bjørk", "Bjork"),
        ("Æsir", "AEsir"),
        ("Größe", "Grosse"),
        ("łódź", "lodz"),
    ],
)
def test_strip_diacritics(raw: str, expected: str) -> None:
    assert strip_diacritics(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1.234,56", 1234.56),   # EU: dot thousands, comma decimal
        ("1,234.56", 1234.56),   # US: comma thousands, dot decimal
        ("999,99", 999.99),      # EU comma decimal only
        ("3 000,50", 3000.50),   # space thousands + comma decimal
        ("1,000.00", 1000.0),
        ("$3,000.99", 3000.99),  # currency symbol stripped
        ("-2.500,00", -2500.0),  # negative EU
        ("42", 42.0),
        ("", None),
    ],
)
def test_normalize_us_number(raw: str, expected: float | None) -> None:
    assert normalize_us_number(raw) == expected


def test_normalize_us_number_explicit_format() -> None:
    # "1.000" is ambiguous; explicit EU treats the dot as a thousands separator.
    assert normalize_us_number("1.000", source_format="eu") == 1000.0
    assert normalize_us_number("1.000", source_format="us") == 1.0


def test_to_utc_iso8601_naive_is_localized() -> None:
    # 09:30 US/Eastern (EDT, -04:00) -> 13:30 UTC.
    dt = to_utc_iso8601("2026-06-05 09:30:00", assume_timezone="America/New_York")
    assert dt is not None
    assert dt.hour == 13 and dt.minute == 30
    assert dt.utcoffset().total_seconds() == 0
    assert dt.isoformat() == "2026-06-05T13:30:00+00:00"


def test_to_utc_iso8601_respects_offset() -> None:
    dt = to_utc_iso8601("2026-06-05T11:00:00-04:00", assume_timezone="UTC")
    assert dt is not None and dt.hour == 15
