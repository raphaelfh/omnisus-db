"""Shared pytest fixtures for omnisus-db."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to tests/fixtures/."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def dbc_fixture(fixtures_dir: Path) -> Callable[[str], Path]:
    """Factory: dbc_fixture('sim_rr_2023_mini') -> Path."""

    def _resolve(name: str) -> Path:
        path = fixtures_dir / "dbc" / f"{name}.dbc"
        if not path.exists():
            pytest.skip(f"DBC fixture not present: {path}. Run scripts/build_fixtures.py")
        return path

    return _resolve


@pytest.fixture
def tmp_lake(tmp_path: Path) -> Iterator[Path]:
    """Temp directory for an ephemeral DuckLake."""
    lake_dir = tmp_path / "lake"
    lake_dir.mkdir()
    yield lake_dir
