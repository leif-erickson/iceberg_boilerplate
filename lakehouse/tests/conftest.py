"""Shared pytest fixtures."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Keep tests hermetic: no lineage emission, no metric pushes.
os.environ.setdefault("OPENLINEAGE_DISABLED", "true")
os.environ.setdefault("METRICS_DISABLED", "true")


@pytest.fixture()
def lake_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the Iceberg catalog + warehouse at an isolated temp directory."""
    monkeypatch.setenv("LAKE_ROOT", str(tmp_path))
    monkeypatch.setenv("DS", "2026-06-05")
    return tmp_path
