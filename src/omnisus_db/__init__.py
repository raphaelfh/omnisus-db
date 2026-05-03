"""omnisus-db — Brazilian public health database ingestion lib."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Sequence

from omnisus_db._version import __version__
from omnisus_db.lake import Lake
from omnisus_db.sources._base import ImportResult, ScopeKey
from omnisus_db.sources.datasus_ftp._runner import import_scope as _import_scope_ftp

ALL_UFS: tuple[str, ...] = (
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
)


def _import_dataset_ftp(
    dataset: str,
    *,
    years: Iterable[int],
    ufs: Sequence[str] | None,
    target: str = "ducklake:./omnisus.ducklake",
) -> list[ImportResult]:
    """Bulk import: every (uf, year) combo for a DATASUS-FTP yearly dataset."""
    if ufs is None:
        ufs = ALL_UFS

    async def run() -> list[ImportResult]:
        results: list[ImportResult] = []
        with Lake.local(target) as lake:
            for year in years:
                for uf in ufs:
                    results.append(
                        await _import_scope_ftp(
                            dataset=dataset,
                            scope=ScopeKey(uf=uf, ano=year),
                            lake=lake,
                        )
                    )
        return results

    return asyncio.run(run())


def import_sim(
    *,
    years: Iterable[int],
    ufs: Sequence[str] | None = None,
    target: str = "ducklake:./omnisus.ducklake",
) -> list[ImportResult]:
    """Import SIM-DO (declarações de óbito) for the given years/UFs."""
    return _import_dataset_ftp("sim_do", years=years, ufs=ufs, target=target)


def import_sinasc(
    *,
    years: Iterable[int],
    ufs: Sequence[str] | None = None,
    target: str = "ducklake:./omnisus.ducklake",
) -> list[ImportResult]:
    """Import SINASC-NV (nascidos vivos) for the given years/UFs."""
    return _import_dataset_ftp("sinasc_nv", years=years, ufs=ufs, target=target)


__all__ = [
    "ALL_UFS",
    "ImportResult",
    "Lake",
    "ScopeKey",
    "__version__",
    "import_sim",
    "import_sinasc",
]
