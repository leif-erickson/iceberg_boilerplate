"""Tests for canonical department mapping."""

from __future__ import annotations

from lakehouse.registry import load_canonical


def test_aliases_resolve_case_and_diacritic_insensitive() -> None:
    depts = load_canonical("departments")
    assert depts.resolve("hr") == "People & Culture"
    assert depts.resolve("Recursos Humanos") == "People & Culture"
    assert depts.resolve("PEOPLE OPS") == "People & Culture"
    assert depts.resolve("mktg") == "Marketing"
    assert depts.resolve("ingeniería") == "Engineering"


def test_code_lookup_and_unmatched() -> None:
    depts = load_canonical("departments")
    assert depts.resolve("FI") == "Finance"
    assert depts.resolve("does-not-exist") == depts.unmatched
    assert depts.resolve(None) == depts.unmatched


def test_canonical_values() -> None:
    depts = load_canonical("departments")
    assert set(depts.canonical_values) == {
        "People & Culture",
        "Finance",
        "Engineering",
        "Sales",
        "Marketing",
    }
