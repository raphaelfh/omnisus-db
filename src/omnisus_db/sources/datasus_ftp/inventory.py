"""DATASUS FTP filename conventions and inventory helpers."""

from __future__ import annotations

import re

from omnisus_db.sources._base import ScopeKey

# Dataset name -> (filename prefix, monthly?)
DATASET_PREFIX: dict[str, tuple[str, bool]] = {
    "sim_do": ("DO", False),
    "sinasc_nv": ("DN", False),
    "sih_rd": ("RD", True),
    "cnes_st": ("ST", True),
}

# Reverse map: prefix -> dataset
PREFIX_TO_DATASET: dict[str, str] = {p: name for name, (p, _) in DATASET_PREFIX.items()}

_YEARLY_PATTERN = re.compile(r"^([A-Z]{2})([A-Z]{2})(\d{4})\.dbc$", re.IGNORECASE)
_MONTHLY_PATTERN = re.compile(r"^([A-Z]{2})([A-Z]{2})(\d{2})(\d{2})\.dbc$", re.IGNORECASE)


def _yy_to_year(yy: int) -> int:
    return 2000 + yy if yy < 80 else 1900 + yy


def parse_filename(name: str) -> tuple[ScopeKey, str]:
    """Parse a DATASUS DBC filename into (ScopeKey, dataset_name).

    Examples:
        DOSP2024.dbc -> (ScopeKey('SP', 2024), 'sim_do')
        RDSP2401.dbc -> (ScopeKey('SP', 2024, 1), 'sih_rd')
    """
    # Try yearly first to extract prefix and decide based on dataset registry.
    yearly = _YEARLY_PATTERN.match(name)
    monthly = _MONTHLY_PATTERN.match(name)

    # Use the shape of the file (post-prefix digits) plus dataset registry:
    # - yearly datasets have prefix + UF + YYYY (8 chars before .dbc)
    # - monthly datasets have prefix + UF + YYMM (8 chars before .dbc) — same length!
    # Distinguish by prefix lookup against DATASET_PREFIX.
    candidate = monthly or yearly
    if not candidate:
        raise ValueError(f"unrecognized filename: {name}")
    prefix = candidate.group(1).upper()
    if prefix not in PREFIX_TO_DATASET:
        raise ValueError(f"unknown dataset prefix: {prefix}")
    dataset = PREFIX_TO_DATASET[prefix]
    _, is_monthly = DATASET_PREFIX[dataset]
    if is_monthly:
        m = _MONTHLY_PATTERN.match(name)
        if not m:
            raise ValueError(f"expected monthly filename: {name}")
        _, uf, yy, mm = m.groups()
        return ScopeKey(uf=uf.upper(), ano=_yy_to_year(int(yy)), mes=int(mm)), dataset
    m = _YEARLY_PATTERN.match(name)
    if not m:
        raise ValueError(f"expected yearly filename: {name}")
    _, uf, yyyy = m.groups()
    return ScopeKey(uf=uf.upper(), ano=int(yyyy)), dataset


def scope_to_filename(dataset: str, scope: ScopeKey) -> str:
    """Build the DATASUS DBC filename for a given (dataset, scope)."""
    if dataset not in DATASET_PREFIX:
        raise ValueError(f"unknown dataset: {dataset}")
    prefix, monthly = DATASET_PREFIX[dataset]
    yy = scope.ano % 100
    if monthly:
        if scope.mes is None:
            raise ValueError(f"{dataset} requires mes; got: {scope}")
        return f"{prefix}{scope.uf}{yy:02d}{scope.mes:02d}.dbc"
    return f"{prefix}{scope.uf}{scope.ano:04d}.dbc"
