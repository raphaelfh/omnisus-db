"""DATASUS DBC filename codec: (dataset, ScopeKey) <-> filename.

Pure — no network, no cache. Decoding is always *for one row*: a directory
holds files of many datasets (SIASUS/200801_/Dados carries PA*, SAD* and the
APAC family), and the same prefix may be registered by an ad-hoc ``Dataset``,
so there is no global "which dataset owns this name" map.
"""

from __future__ import annotations

import re

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.datasets import Dataset, resolve


def _yy_to_year(yy: int) -> int:
    return 2000 + yy if yy < 80 else 1900 + yy


def scope_to_filename(dataset: str | Dataset, scope: ScopeKey) -> str:
    """Build the DATASUS DBC filename for a given (dataset, scope)."""
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


def decode_for(d: Dataset, name: str) -> ScopeKey | None:
    """Inverse of :func:`scope_to_filename` for one row.

    ``None`` when ``name`` is not one of this row's files. Case-insensitive,
    like the server. A shorter prefix never swallows a longer family's file:
    ``AD`` does not even reach ``ATDRR2401.dbc``'s groups (the literal prefix
    differs at the second letter), and a prefix that *is* a head of the name
    is still rejected by the fixed-width groups — matching ``ATDRR2401.dbc``
    as a two-letter ``AT`` row takes ``DR`` as the UF and then needs two
    digits where ``R2`` stands.
    """
    prefix = re.escape(d.prefix)
    if d.geography == "national":
        m = re.fullmatch(prefix + r"BR(\d{2})\.dbc", name, re.IGNORECASE)
        return ScopeKey(uf=None, ano=_yy_to_year(int(m[1]))) if m else None
    if d.monthly:
        m = re.fullmatch(prefix + r"([A-Z]{2})(\d{2})(\d{2})\.dbc", name, re.IGNORECASE)
        if m is None or not 1 <= int(m[3]) <= 12:
            return None
        return ScopeKey(uf=m[1].upper(), ano=_yy_to_year(int(m[2])), mes=int(m[3]))
    m = re.fullmatch(prefix + r"([A-Z]{2})(\d{4})\.dbc", name, re.IGNORECASE)
    return ScopeKey(uf=m[1].upper(), ano=int(m[2])) if m else None
