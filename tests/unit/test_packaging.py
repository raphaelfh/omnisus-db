"""Packaging contract: a base install does not pull the notebook runtime."""

import re
import tomllib
from pathlib import Path

PYPROJECT = tomllib.loads(
    (Path(__file__).resolve().parents[2] / "pyproject.toml").read_text(encoding="utf-8")
)


def _names(requirements: list[str]) -> set[str]:
    return {re.split(r"[<>=!~;\[ ]", r, maxsplit=1)[0].strip().lower() for r in requirements}


def test_marimo_is_only_an_optional_extra():
    project = PYPROJECT["project"]
    assert "marimo" not in _names(project["dependencies"])
    assert "marimo" in _names(project["optional-dependencies"]["notebooks"])


def test_dev_installs_the_notebooks_extra():
    # CI syncs only --extra dev, and tests/unit/notebooks imports marimo.
    assert "omnisus-db[notebooks]" in PYPROJECT["project"]["optional-dependencies"]["dev"]
