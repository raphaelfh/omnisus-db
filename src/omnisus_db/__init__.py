"""omnisus-db — Brazilian public health database ingestion lib."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable, Sequence

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


def _import_dataset_ftp_monthly(
    dataset: str,
    *,
    years: Iterable[int],
    ufs: Sequence[str] | None,
    months: Iterable[int],
    target: str,
) -> list[ImportResult]:
    """Bulk import: every (uf, year, month) combo for a monthly DATASUS-FTP dataset."""
    if ufs is None:
        ufs = ALL_UFS

    async def run() -> list[ImportResult]:
        results: list[ImportResult] = []
        with Lake.local(target) as lake:
            for year in years:
                for uf in ufs:
                    for mes in months:
                        results.append(
                            await _import_scope_ftp(
                                dataset=dataset,
                                scope=ScopeKey(uf=uf, ano=year, mes=mes),
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


def import_sih(
    *,
    years: Iterable[int],
    ufs: Sequence[str] | None = None,
    months: Iterable[int] = range(1, 13),
    target: str = "ducklake:./omnisus.ducklake",
) -> list[ImportResult]:
    """Import SIH-RD (AIH reduzida) — monthly. (years x ufs x months)."""
    return _import_dataset_ftp_monthly(
        "sih_rd", years=years, ufs=ufs, months=months, target=target
    )


def import_sinasc(
    *,
    years: Iterable[int],
    ufs: Sequence[str] | None = None,
    target: str = "ducklake:./omnisus.ducklake",
) -> list[ImportResult]:
    """Import SINASC-NV (nascidos vivos) for the given years/UFs."""
    return _import_dataset_ftp("sinasc_nv", years=years, ufs=ufs, target=target)


def import_ibge_pop(
    *,
    years: Iterable[int] | None = None,
    target: str = "ducklake:./omnisus.ducklake",
) -> list[ImportResult]:
    """Import IBGE population estimates for the given years."""
    from omnisus_db.sources.ibge.importers.pop import import_pop_year

    if years is None:
        years = range(2010, 2026)

    async def run() -> list[ImportResult]:
        results: list[ImportResult] = []
        with Lake.local(target) as lake:
            for y in years:
                results.append(await import_pop_year(year=y, lake=lake))
        return results

    return asyncio.run(run())


def import_cnes_st(
    *,
    years: Iterable[int],
    months: Iterable[int] = range(1, 13),
    ufs: Sequence[str] | None = None,
    target: str = "ducklake:./omnisus.ducklake",
) -> list[ImportResult]:
    """Import CNES-ST (estabelecimentos) — monthly. (years x ufs x months).

    After the import succeeds, refreshes the ``aux_cnes`` view (latest snapshot
    per CNES) so downstream consumers can resolve CNES → name without picking
    a partition.
    """
    results = _import_dataset_ftp_monthly(
        "cnes_st",
        years=years,
        ufs=ufs,
        months=months,
        target=target,
    )
    with Lake.local(target) as lake:
        lake.ensure_aux_cnes_view()
    return results


def import_cnes_master(
    *,
    codes: Sequence[str] | None = None,
    target: str = "ducklake:./omnisus.ducklake",
    concurrency: int = 5,
    only_missing: bool = True,
    progress: Callable[[int, int], None] | None = None,
) -> int:
    """Fetch CNES establishment names from the public API → ``lake.cnes_master``.

    The DATASUS public CNES-ST DBF doesn't carry establishment names; this
    pulls them from ``apidadosabertos.saude.gov.br`` and joins them into
    ``aux_cnes`` so downstream tools (e.g. the Explorer) can resolve a CNES
    code to a human-readable name.

    With ``codes=None`` and ``only_missing=True`` (defaults), runs are
    incremental — only CNES codes present in ``cnes_st`` but absent from
    ``cnes_master`` are fetched. Pass ``progress=(done, total) -> None`` to
    stream job progress (e.g. from the backend admin UI).
    """
    from omnisus_db.sources.cnes.importers.master import (
        import_cnes_master as _impl,
    )

    return _impl(
        codes=codes,
        target=target,
        concurrency=concurrency,
        only_missing=only_missing,
        progress=progress,
    )


__all__ = [
    "ALL_UFS",
    "ImportResult",
    "Lake",
    "ScopeKey",
    "__version__",
    "import_cnes_master",
    "import_cnes_st",
    "import_ibge_pop",
    "import_sih",
    "import_sim",
    "import_sinasc",
]
