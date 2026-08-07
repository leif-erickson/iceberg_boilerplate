"""Declarative quality gates.

Quality gates are stored in the data contract (`quality_gates:`) so stewards can
manage them without code. This module runs them natively on Polars (fast, no
engine dependency) and can also compile them to SodaCL so the same gates run in
Soda Core / Soda Cloud. Great Expectations is a supported alternative; see
`governance/README.md`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import polars as pl

from lakehouse import registry
from lakehouse.registry import DataContract, QualityGate


@dataclass
class CheckResult:
    name: str
    check: str
    passed: bool
    detail: str = ""


@dataclass
class QualityReport:
    dataset: str
    results: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def failures(self) -> list[CheckResult]:
        return [r for r in self.results if not r.passed]


class QualityGateError(RuntimeError):
    """Raised when a strict quality-gate run has failures."""


def _allowed_values(gate: QualityGate) -> list[str]:
    if gate.from_canonical:
        return registry.load_canonical(gate.from_canonical).canonical_values
    return gate.values


def _run_gate(frame: pl.DataFrame, gate: QualityGate) -> CheckResult:
    if gate.check == "not_null":
        offenders = {c: frame[c].null_count() for c in gate.target_columns()}
        bad = {c: n for c, n in offenders.items() if n}
        return CheckResult(gate.name, gate.check, not bad, f"nulls={bad}" if bad else "")

    if gate.check == "unique":
        cols = gate.target_columns()
        n_unique = frame.select(cols).n_unique()
        passed = n_unique == frame.height
        return CheckResult(gate.name, gate.check, passed, f"unique={n_unique}/{frame.height}")

    if gate.check == "range":
        col = gate.column
        assert col is not None
        series = frame[col]
        observed_min, observed_max = series.min(), series.max()
        passed = True
        if gate.min is not None and observed_min is not None and observed_min < gate.min:
            passed = False
        if gate.max is not None and observed_max is not None and observed_max > gate.max:
            passed = False
        return CheckResult(gate.name, gate.check, passed, f"min={observed_min} max={observed_max}")

    if gate.check == "allowed_values":
        col = gate.column
        assert col is not None
        allowed = set(_allowed_values(gate))
        observed = set(frame[col].drop_nulls().unique().to_list())
        invalid = sorted(observed - allowed)
        return CheckResult(gate.name, gate.check, not invalid, f"invalid={invalid}" if invalid else "")

    if gate.check == "row_count":
        passed = True
        if gate.min is not None and frame.height < gate.min:
            passed = False
        if gate.max is not None and frame.height > gate.max:
            passed = False
        return CheckResult(gate.name, gate.check, passed, f"rows={frame.height}")

    raise ValueError(f"unknown quality check: {gate.check!r}")


def run_quality_gates(frame: pl.DataFrame, contract: DataContract) -> QualityReport:
    report = QualityReport(dataset=contract.dataset)
    for gate in contract.quality_gates:
        report.results.append(_run_gate(frame, gate))
    return report


def enforce(frame: pl.DataFrame, contract: DataContract) -> QualityReport:
    """Run gates and raise if any fail."""
    report = run_quality_gates(frame, contract)
    if not report.passed:
        failed = ", ".join(f"{r.name}({r.detail})" for r in report.failures)
        raise QualityGateError(f"{contract.dataset} quality gates failed: {failed}")
    return report


def _num(value: float) -> str:
    """Render whole floats as ints (0.0 -> 0) for clean SodaCL output."""
    return str(int(value)) if float(value).is_integer() else str(value)


def to_sodacl(contract: DataContract) -> str:
    """Compile the contract's quality gates to SodaCL for Soda Core / Soda Cloud."""
    lines: list[str] = [f"checks for {contract.dataset}:"]
    for gate in contract.quality_gates:
        if gate.check == "not_null":
            lines += [f"  - missing_count({c}) = 0" for c in gate.target_columns()]
        elif gate.check == "unique":
            lines += [f"  - duplicate_count({c}) = 0" for c in gate.target_columns()]
        elif gate.check == "range":
            if gate.min is not None:
                lines.append(f"  - min({gate.column}) >= {_num(gate.min)}")
            if gate.max is not None:
                lines.append(f"  - max({gate.column}) <= {_num(gate.max)}")
        elif gate.check == "allowed_values":
            lines.append(f"  - invalid_count({gate.column}) = 0:")
            lines.append("      valid values:")
            lines += [f'        - "{value}"' for value in _allowed_values(gate)]
        elif gate.check == "row_count":
            if gate.min is not None:
                lines.append(f"  - row_count >= {_num(gate.min)}")
            if gate.max is not None:
                lines.append(f"  - row_count <= {_num(gate.max)}")
    return "\n".join(lines) + "\n"
