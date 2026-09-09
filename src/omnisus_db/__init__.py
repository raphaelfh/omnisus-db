"""omnisus-db — Brazilian public health database ingestion lib."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable, Sequence

from omnisus_db._version import __version__
from omnisus_db.lake import DEFAULT_TARGET, Lake
from omnisus_db.sources._base import (
    ImportReport,
    ImportResult,
    ScopeKey,
    ScopeOutcome,
)
from omnisus_db.sources.datasus_ftp._runner import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CONCURRENCY,
)
from omnisus_db.sources.datasus_ftp._runner import run_scopes as _run_scopes_ftp
from omnisus_db.sources.datasus_ftp.datasets import Dataset, resolve
from omnisus_db.sources.datasus_ftp.inventory import (
    FtpEntry,
    FtpPathNotFound,
    FtpUnavailable,
    available,
)
from omnisus_db.sources.datasus_ftp.inventory import crawl as _crawl

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


def scopes_for(
    dataset: str | Dataset,
    *,
    years: Iterable[int],
    ufs: Sequence[str] | None = None,
    months: Iterable[int] | None = None,
) -> list[ScopeKey]:
    """The product planner: every (uf, year[, month]) for a dataset.

    ``months`` is ignored for yearly datasets and defaults to 1..12 for
    monthly ones. Order is year -> uf -> month. Planning is composition
    (spec §5.1): pass the result — or any other ``list[ScopeKey]`` — to
    :func:`import_dataset`.
    """
    d = resolve(dataset)
    uf_list = tuple(ufs) if ufs is not None else ALL_UFS
    month_list = tuple(months) if months is not None else tuple(range(1, 13))
    scopes: list[ScopeKey] = []
    for year in years:
        for uf in uf_list:
            if d.monthly:
                scopes.extend(ScopeKey(uf=uf, ano=year, mes=m) for m in month_list)
            else:
                scopes.append(ScopeKey(uf=uf, ano=year))
    return scopes


def browse(path: str, *, depth: int = 1, refresh: bool = False) -> list[FtpEntry]:
    """List any DATASUS FTP path — the open-world counterpart to :func:`available`.

    Reaches subsystems this package does not model (SINAN, CIHA, PCE).
    ``depth=1`` lists ``path`` only; recursion is bounded (spec §4.1).

    Deliberately eager — a CLI table needs the whole result before it can be
    rendered — so :func:`~omnisus_db.sources.datasus_ftp.inventory.crawl`'s
    laziness (a huge tree can be interrupted, spec I7) is not reachable
    through this public function. In-process callers who need that should
    call ``crawl`` directly instead of ``browse``.
    """
    return list(_crawl(path, depth=depth, refresh=refresh))


def import_dataset(
    dataset: str | Dataset,
    *,
    scopes: Sequence[ScopeKey],
    target: str = DEFAULT_TARGET,
    concurrency: int = DEFAULT_CONCURRENCY,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> ImportReport:
    """Import the given scopes of any DATASUS-FTP dataset into the lake.

    ``dataset`` is a registry key (``"sia_bi"``), an alias (``"sim"``) or a
    ``Dataset`` value. The loop iterates ``scopes`` and never asks where they
    came from — planning is composition:

        odb.import_dataset("sim_do", scopes=odb.scopes_for("sim_do", years=...))
        odb.import_dataset("sim_do", scopes=odb.available("sim_do", years=...))

    The first plans blindly and lets tolerance absorb the gaps; the second
    asks the server first and plans only what exists. There is no flag —
    the difference is which function fills ``scopes``.

    Returns an :class:`~omnisus_db.sources._base.ImportReport`: a scope
    DATASUS never published is ``skipped``, a scope that exists but could not
    be ingested is ``failed``, and neither aborts the run. Inspect
    ``report.failed``, never the report's truthiness.

    ``concurrency`` bounds fetches in flight; parse and sink stay on a single
    consumer because the lake holds one DuckDB connection. ``batch_size``
    scopes share one DuckLake transaction, and therefore one snapshot.
    DATASUS FTP is a shared public resource — raise ``concurrency`` only with
    reason.
    """
    d = resolve(dataset)

    async def run() -> ImportReport:
        with Lake.local(target) as lake:
            return await _run_scopes_ftp(
                d,
                scopes=scopes,
                lake=lake,
                concurrency=concurrency,
                batch_size=batch_size,
            )

    return asyncio.run(run())


def import_sim(
    *,
    years: Iterable[int],
    ufs: Sequence[str] | None = None,
    target: str = DEFAULT_TARGET,
) -> ImportReport:
    """Import SIM-DO (declarações de óbito). Alias for ``import_dataset("sim_do", ...)``."""
    return import_dataset(
        "sim_do", scopes=scopes_for("sim_do", years=years, ufs=ufs), target=target
    )


def import_sinasc(
    *,
    years: Iterable[int],
    ufs: Sequence[str] | None = None,
    target: str = DEFAULT_TARGET,
) -> ImportReport:
    """Import SINASC-NV (nascidos vivos). Alias for ``import_dataset("sinasc_nv", ...)``."""
    return import_dataset(
        "sinasc_nv", scopes=scopes_for("sinasc_nv", years=years, ufs=ufs), target=target
    )


def import_sih(
    *,
    years: Iterable[int],
    ufs: Sequence[str] | None = None,
    months: Iterable[int] = range(1, 13),
    target: str = DEFAULT_TARGET,
) -> ImportReport:
    """Import SIH-RD (AIH reduzida), monthly. Alias for ``import_dataset("sih_rd", ...)``."""
    return import_dataset(
        "sih_rd",
        scopes=scopes_for("sih_rd", years=years, ufs=ufs, months=months),
        target=target,
    )


def import_ibge_pop(
    *,
    years: Iterable[int] | None = None,
    target: str = DEFAULT_TARGET,
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
    years: Iterable[int] | None = None,
    months: Iterable[int] = range(1, 13),
    ufs: Sequence[str] | None = None,
    scopes: Sequence[ScopeKey] | None = None,
    target: str = DEFAULT_TARGET,
) -> ImportReport:
    """Import CNES-ST (estabelecimentos), monthly, then refresh ``aux_cnes``.

    This stays a named function rather than a bare alias because the view
    refresh is *behaviour*, and behaviour lives in importers, not in the
    registry row (spec I2). ``import_dataset("cnes_st", ...)`` loads the
    table but does not refresh the view; call
    ``Lake.ensure_aux_cnes_view()`` afterwards if you use that path.

    Pass ``scopes`` to supply a scope list built any way you like — including
    by :func:`available` — or ``years``/``ufs``/``months`` to have
    :func:`scopes_for` build the product. Exactly one of the two.
    """
    if (scopes is None) == (years is None):
        raise ValueError("provide exactly one of `scopes` or `years`")
    if scopes is None:
        assert years is not None, "the check above guarantees this"
        scopes = scopes_for("cnes_st", years=years, ufs=ufs, months=months)
    report = import_dataset("cnes_st", scopes=scopes, target=target)
    with Lake.local(target) as lake:
        lake.ensure_aux_cnes_view()
    return report


def import_cnes_master(
    *,
    codes: Sequence[str] | None = None,
    target: str = DEFAULT_TARGET,
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
    "DEFAULT_TARGET",
    "Dataset",
    "FtpEntry",
    "FtpPathNotFound",
    "FtpUnavailable",
    "ImportReport",
    "ImportResult",
    "Lake",
    "ScopeKey",
    "ScopeOutcome",
    "__version__",
    "available",
    "browse",
    "import_cnes_master",
    "import_cnes_st",
    "import_dataset",
    "import_ibge_pop",
    "import_sih",
    "import_sim",
    "import_sinasc",
    "scopes_for",
]
