"""Where the shared research lake lives for a notebook session."""

from __future__ import annotations

import os
from pathlib import Path


def data_root() -> Path:
    """Research-lake directory; `OMNISUS_NOTEBOOK_DATA` overrides.

    Relative to the process cwd so a molab or `--sandbox` session has one rule:
    `./data/lake/pesquisa`. Open the notebooks from the repository root (or set
    the environment variable) so SIM and IBGE share the same lake.
    """
    if env := os.environ.get("OMNISUS_NOTEBOOK_DATA"):
        return Path(env)
    return Path.cwd() / "data/lake/pesquisa"


def default_target() -> str:
    return f"ducklake:{data_root() / 'dados.ducklake'}"
