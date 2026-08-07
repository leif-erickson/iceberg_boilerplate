"""Governance registry: typed models + loaders for the version-controlled
metadata store (the "Collibra-lite" layer).

The registry holds three kinds of declarative metadata under `governance/`:

* data contracts   -> `contracts/*.yaml`   (schema, cleansing, quality gates)
* canonical maps   -> `canonical/*.yaml`    (alias -> approved value + code)
* cleansing rules  -> `cleansing_rules.yaml` (documented rule library)

Everything downstream (Polars cleansing, Pandera validation, Soda/GX checks and
the Iceberg schema) is derived from these files, so the YAML is the single
source of truth.
"""

from __future__ import annotations

import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from lakehouse import settings

LogicalType = Literal["string", "int", "long", "double", "decimal", "boolean", "date", "timestamp"]
CheckType = Literal["not_null", "unique", "range", "allowed_values", "row_count"]


class CleansingStep(BaseModel):
    """A single cleansing rule reference with optional parameters."""

    model_config = ConfigDict(extra="forbid")

    rule: str
    params: dict[str, object] = Field(default_factory=dict)

    @classmethod
    def coerce(cls, value: Union[str, dict, "CleansingStep"]) -> "CleansingStep":
        if isinstance(value, CleansingStep):
            return value
        if isinstance(value, str):
            return cls(rule=value)
        return cls(**value)


class FieldSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: LogicalType
    nullable: bool = True
    description: str = ""
    source_name: str | None = None
    canonical: str | None = None
    cleansing: list[CleansingStep] = Field(default_factory=list)

    @field_validator("cleansing", mode="before")
    @classmethod
    def _coerce_cleansing(cls, value: object) -> list[CleansingStep]:
        if not value:
            return []
        return [CleansingStep.coerce(v) for v in value]  # type: ignore[union-attr]

    @property
    def raw_name(self) -> str:
        """Column name in the raw/bronze input."""
        return self.source_name or self.name


class QualityGate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    check: CheckType
    column: str | None = None
    columns: list[str] = Field(default_factory=list)
    min: float | None = None
    max: float | None = None
    values: list[str] = Field(default_factory=list)
    from_canonical: str | None = None

    def target_columns(self) -> list[str]:
        if self.columns:
            return self.columns
        if self.column:
            return [self.column]
        return []


class DataContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset: str
    layer: str = "silver"
    owner: str = ""
    description: str = ""
    partition_by: list[str] = Field(default_factory=list)
    fields: list[FieldSpec]
    quality_gates: list[QualityGate] = Field(default_factory=list)

    def field(self, name: str) -> FieldSpec:
        for spec in self.fields:
            if spec.name == name:
                return spec
        raise KeyError(f"field {name!r} not in contract {self.dataset!r}")


class CanonicalEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical: str
    code: str
    aliases: list[str] = Field(default_factory=list)


class CanonicalMap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = ""
    unmatched: str = "__UNMAPPED__"
    entries: list[CanonicalEntry]

    @staticmethod
    def _normalize_key(value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", value)
        without_marks = "".join(c for c in decomposed if not unicodedata.combining(c))
        return " ".join(without_marks.lower().split())

    @property
    def lookup(self) -> dict[str, CanonicalEntry]:
        """Normalized alias/canonical -> entry, for case/diacritic-insensitive matching."""
        table: dict[str, CanonicalEntry] = {}
        for entry in self.entries:
            keys = [entry.canonical, entry.code, *entry.aliases]
            for key in keys:
                table[self._normalize_key(key)] = entry
        return table

    def resolve(self, value: str | None) -> str:
        if value is None:
            return self.unmatched
        entry = self.lookup.get(self._normalize_key(value))
        return entry.canonical if entry else self.unmatched

    @property
    def canonical_values(self) -> list[str]:
        return [entry.canonical for entry in self.entries]


def _read_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@lru_cache(maxsize=None)
def load_contract(dataset: str) -> DataContract:
    path = settings.CONTRACTS_DIR / f"{dataset}.yaml"
    return DataContract(**_read_yaml(path))


@lru_cache(maxsize=None)
def load_canonical(name: str) -> CanonicalMap:
    path = settings.CANONICAL_DIR / f"{name}.yaml"
    return CanonicalMap(**_read_yaml(path))


@lru_cache(maxsize=None)
def load_cleansing_rules() -> dict[str, dict]:
    return _read_yaml(settings.CLEANSING_RULES_FILE).get("rules", {})


def list_contracts() -> list[str]:
    return sorted(p.stem for p in settings.CONTRACTS_DIR.glob("*.yaml"))
