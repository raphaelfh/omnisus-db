"""DATASUS DBC filename codec: (dataset, ScopeKey) <-> filename.

Split out of the old ``inventory.py`` so that name could be used for the
actual inventory (spec §4). This module is pure — no network, no cache.
"""

from __future__ import annotations

import re

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.datasets import REGISTRY, Dataset, resolve

# Derived from the registry (spec §3.1) — never hand-maintained here.
PREFIX_TO_DATASET: dict[str, str] = {d.prefix: d.name for d in REGISTRY.values()}

_YEARLY_PATTERN = re.compile(r"^([A-Z]{2})([A-Z]{2})(\d{4})\.dbc$", re.IGNORECASE)
# Prefixes are 2 OR 3 letters (ATD, ABO); greedy {2,3} + backtracking resolves
# the ambiguity because UF must be exactly 2 letters and the date 4 digits
# (ATDRR2401 -> ATD+RR, never AT+DR; AMRR2401 backtracks AMR -> AM+RR).
_MONTHLY_PATTERN = re.compile(r"^([A-Z]{2,3})([A-Z]{2})(\d{2})(\d{2})\.dbc$", re.IGNORECASE)


def _yy_to_year(yy: int) -> int:
    return 2000 + yy if yy < 80 else 1900 + yy


def parse_filename(name: str) -> tuple[ScopeKey, str]:
    """Parse a DATASUS DBC filename into (ScopeKey, dataset_name).

    Examples:
        DOSP2024.dbc -> (ScopeKey('SP', 2024), 'sim_do')
        RDSP2401.dbc -> (ScopeKey('SP', 2024, 1), 'sih_rd')
    """
    for d in REGISTRY.values():
        if d.geography == "national":
            match = re.fullmatch(re.escape(d.prefix) + r"BR(\d{2})\.dbc", name, re.IGNORECASE)
            if match:
                return ScopeKey(uf=None, ano=_yy_to_year(int(match[1]))), d.name
    # Try yearly first to extract prefix and decide based on dataset registry.
    yearly = _YEARLY_PATTERN.match(name)
    monthly = _MONTHLY_PATTERN.match(name)

    # Prefix length varies (2 or 3 letters) and cadence isn't encoded in the
    # filename, so try both patterns and disambiguate by looking the matched
    # prefix up in PREFIX_TO_DATASET. This is unambiguous: the UF is a fixed
    # 2 letters and a digit can never be a UF letter, so the greedy `{2,3}`
    # prefix group in _MONTHLY_PATTERN backtracks to the correct split
    # (ATDRR2401 -> ATD+RR, never AT+DR; AMRR2401 backtracks AMR -> AM+RR).
    candidate = monthly or yearly
    if not candidate:
        raise ValueError(f"unrecognized filename: {name}")
    prefix = candidate.group(1).upper()
    if prefix not in PREFIX_TO_DATASET:
        raise ValueError(f"unknown dataset prefix: {prefix}")
    dataset = PREFIX_TO_DATASET[prefix]
    if REGISTRY[dataset].monthly:
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


def scope_to_filename(dataset: str | Dataset, scope: ScopeKey) -> str:
    """Build the DATASUS DBC filename for a given (dataset, scope).

    Accepts a registry key, an alias, or a ``Dataset`` value (spec §3.3.1),
    so an ad-hoc dataset can name its files without being registered.
    """
    d = resolve(dataset)
    if d.geography == "national":
        if scope.uf is not None or scope.mes is not None:
            raise ValueError("national yearly dataset requires uf=None and mes=None")
        if not 1980 <= scope.ano <= 2079:
            raise ValueError("year cannot be represented by the national filename codec")
        return f"{d.prefix}BR{scope.ano % 100:02d}.dbc"
    if scope.uf is None:
        raise ValueError("state dataset requires UF")
    yy = scope.ano % 100
    if d.monthly:
        if scope.mes is None:
            raise ValueError(f"{d.name} requires mes; got: {scope}")
        return f"{d.prefix}{scope.uf}{yy:02d}{scope.mes:02d}.dbc"
    return f"{d.prefix}{scope.uf}{scope.ano:04d}.dbc"


def decode(name: str) -> tuple[ScopeKey, str] | None:
    """Best-effort :func:`parse_filename`: ``None`` instead of raising.

    A DATASUS directory holds files from many datasets, most of which this
    package does not model (SIASUS/200801_/Dados carries ``PA*`` and ``SAD*``
    alongside the APAC family). Callers that scan a directory need to skip
    those, not fail on them.
    """
    try:
        return parse_filename(name)
    except ValueError:
        return None
