"""The DATASUS-FTP dataset registry — single source of truth (spec §3).

One frozen row per dataset. The FTP path map, filename prefix map, CLI
choices and docs all derive from these rows. Adding a dataset is one row
here plus one ``data/dicionarios/<name>.yaml`` (spec §2, operational
contract).

The registry is a catalog, not a gate (spec §3.3, ADR 0002): the pipeline
takes ``Dataset`` *values*, so a ``Dataset`` built by a caller flows through
the same path as a registered one.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from omnisus_db.sources._base import ScopeKey

YM = tuple[int, int]
"""``(year, month)``, e.g. ``(2008, 1)``."""

Cadence = Literal["yearly", "monthly"]


@dataclass(frozen=True, kw_only=True)
class Dataset:
    """Identity and location of one DATASUS-FTP dataset.

    Holds *only* identity and location (spec I2). Anything behavioural
    belongs in an importer module, never as a flag here.
    """

    name: str
    """Registry key = lake table = YAML stem = CLI name (``sim_do``)."""

    prefix: str
    """DATASUS filename prefix: ``DO``, ``DN``, ``RD``, ``BI``, ``ATD``…"""

    ftp_dir: str
    """Directory on ``ftp.datasus.gov.br`` holding this dataset's files."""

    cadence: Cadence
    """How DATASUS publishes files. Decides filename shape (upstream fact)."""

    partition_by: tuple[str, ...]
    """How the lake table is laid out (our storage policy).

    Applied by ``Lake.ingest`` via ``SET PARTITIONED BY`` when the table is
    created, so files land under ``ano=…/uf=…/``. Each scope is already one
    ``(uf, ano[, mes])``, so partitioning costs nothing at write time and buys
    query pruning."""

    coverage: tuple[YM, YM | None]
    """``(first, last)`` published; ``last=None`` means ongoing.

    Provisional until the Tier 3 probe validates it against the server.
    """

    aliases: tuple[str, ...] = ()
    """Extra CLI names kept for back-compat (``"sim"`` -> ``sim_do``)."""

    dictionary: Path | None = None
    """Frictionless YAML. ``None`` -> packaged ``dicionarios/<name>.yaml``."""

    geography: Literal["state", "national"] = "state"
    """Source coverage. National SINAN filenames use PREFIX + BR + YY."""

    @property
    def monthly(self) -> bool:
        return self.cadence == "monthly"


_SIM = "/dissemin/publicos/SIM/CID10/DORES"
_SINASC = "/dissemin/publicos/SINASC/NOV/DNRES"
_SIH = "/dissemin/publicos/SIHSUS/200801_/Dados"
_SIA = "/dissemin/publicos/SIASUS/200801_/Dados"
_CNES_ST = "/dissemin/publicos/CNES/200508_/Dados/ST"

_YEARLY = ("ano", "uf")
_MONTHLY = ("ano", "uf", "mes")

# fmt: off
_ROWS: tuple[Dataset, ...] = (
    Dataset(name="sinan_chagas_prelim", prefix="CHAG", ftp_dir="/dissemin/publicos/SINAN/DADOS/PRELIM", cadence="yearly", partition_by=("_source_ano",), coverage=((2023, 1), None), geography="national"),
    Dataset(name="sim_do",    prefix="DO",  ftp_dir=_SIM,     cadence="yearly",  partition_by=_YEARLY,       coverage=((1996, 1), None), aliases=("sim",)),
    Dataset(name="sinasc_nv", prefix="DN",  ftp_dir=_SINASC,  cadence="yearly",  partition_by=_YEARLY,       coverage=((1996, 1), None), aliases=("sinasc",)),
    Dataset(name="sih_rd",    prefix="RD",  ftp_dir=_SIH,     cadence="monthly", partition_by=_MONTHLY,      coverage=((2008, 1), None), aliases=("sih",)),
    Dataset(name="sia_bi",    prefix="BI",  ftp_dir=_SIA,     cadence="monthly", partition_by=_MONTHLY,      coverage=((2008, 1), None)),
    Dataset(name="sia_am",    prefix="AM",  ftp_dir=_SIA,     cadence="monthly", partition_by=_MONTHLY,      coverage=((2008, 1), None)),
    Dataset(name="sia_aq",    prefix="AQ",  ftp_dir=_SIA,     cadence="monthly", partition_by=_MONTHLY,      coverage=((2008, 1), None)),
    Dataset(name="sia_atd",   prefix="ATD", ftp_dir=_SIA,     cadence="monthly", partition_by=_MONTHLY,      coverage=((2014, 8), None)),
    Dataset(name="sia_ad",    prefix="AD",  ftp_dir=_SIA,     cadence="monthly", partition_by=_MONTHLY,      coverage=((2008, 1), None)),
    Dataset(name="sia_abo",   prefix="ABO", ftp_dir=_SIA,     cadence="monthly", partition_by=_MONTHLY,      coverage=((2014, 1), None)),
    Dataset(name="sia_ps",    prefix="PS",  ftp_dir=_SIA,     cadence="monthly", partition_by=_MONTHLY,      coverage=((2012, 11), None)),
    Dataset(name="cnes_st",   prefix="ST",  ftp_dir=_CNES_ST, cadence="monthly", partition_by=("ano", "mes"), coverage=((2005, 8), None), aliases=("cnes-st",)),
)
# fmt: on

REGISTRY: dict[str, Dataset] = {d.name: d for d in _ROWS}

ALIASES: dict[str, str] = {alias: d.name for d in _ROWS for alias in d.aliases}


def resolve(dataset: str | Dataset) -> Dataset:
    """Return the ``Dataset`` for a registry key, an alias, or a value.

    Names at the edge, values inside (spec §3.3.1): a ``Dataset`` value
    passes through untouched — that is how an uncurated dataset reaches the
    pipeline.
    """
    if isinstance(dataset, Dataset):
        return dataset
    key = ALIASES.get(dataset, dataset)
    try:
        return REGISTRY[key]
    except KeyError:
        raise ValueError(f"unknown dataset: {dataset!r}") from None


def get_config(dataset: str) -> Dataset:
    """Registry lookup by key. Kept for callers that predate :func:`resolve`."""
    return resolve(dataset)


def in_coverage(dataset: str | Dataset, scope: ScopeKey) -> bool:
    """Whether ``scope`` falls inside the dataset's declared coverage window.

    The cheapest possible filter: a scope outside coverage cannot exist
    upstream, so rejecting it here saves a full FTP connect, login, CWD and
    PASV setup before the 550 that would have said the same thing.

    Yearly datasets carry no month, so their scopes are compared at month 1.
    A ``last`` of ``None`` means the dataset is ongoing and has no end bound.
    """
    d = resolve(dataset)
    first, last = d.coverage
    ym = (scope.ano, scope.mes if scope.mes is not None else 1)
    if ym < first:
        return False
    return not (last is not None and ym > last)
