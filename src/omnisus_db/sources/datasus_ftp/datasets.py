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

Release = Literal["final", "prelim"]
"""Which DATASUS directory a file was published in. ``prelim`` files are
revised and later moved to the final directory under the same name."""


@dataclass(frozen=True, kw_only=True)
class Dataset:
    """Identity and location of one DATASUS-FTP dataset.

    Holds *only* identity and location (spec I2). Anything behavioural
    belongs in an importer module, never as a flag here.
    """

    name: str
    """Registry key = lake table = YAML stem = CLI name (``sim_obitos``)."""

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

    dictionary: Path | None = None
    """Frictionless YAML. ``None`` -> packaged ``dicionarios/<name>.yaml``."""

    geography: Literal["state", "national"] = "state"
    """Source coverage. National SINAN filenames use PREFIX + BR + YY."""

    prelim_dir: str | None = None
    """Directory where DATASUS publishes this dataset's preliminary files,
    when it has one. Same filenames as ``ftp_dir``; a file is in one or the
    other, never both."""

    @property
    def monthly(self) -> bool:
        return self.cadence == "monthly"

    def directories(self) -> dict[Release, str]:
        """Every directory this row is published in, final first."""
        dirs: dict[Release, str] = {"final": self.ftp_dir}
        if self.prelim_dir is not None:
            dirs["prelim"] = self.prelim_dir
        return dirs


_SIM = "/dissemin/publicos/SIM/CID10/DORES"
_SINASC = "/dissemin/publicos/SINASC/NOV/DNRES"
_SIH = "/dissemin/publicos/SIHSUS/200801_/Dados"
_SIA = "/dissemin/publicos/SIASUS/200801_/Dados"
_CNES_ST = "/dissemin/publicos/CNES/200508_/Dados/ST"

_SINAN_FINAIS = "/dissemin/publicos/SINAN/DADOS/FINAIS"
_SINAN_PRELIM = "/dissemin/publicos/SINAN/DADOS/PRELIM"

_YEARLY = ("ano", "uf")
_MONTHLY = ("ano", "uf", "mes")

# fmt: off
_ROWS: tuple[Dataset, ...] = (
    Dataset(name="sinan_chagas",                  prefix="CHAG", ftp_dir=_SINAN_FINAIS, prelim_dir=_SINAN_PRELIM, cadence="yearly",  partition_by=("_source_ano",), coverage=((2000, 1), None), geography="national"),
    Dataset(name="sim_obitos",                    prefix="DO",   ftp_dir=_SIM,     prelim_dir="/dissemin/publicos/SIM/PRELIM/DORES",     cadence="yearly",  partition_by=_YEARLY,  coverage=((1996, 1), None)),
    Dataset(name="sinasc_nascidos_vivos",         prefix="DN",   ftp_dir=_SINASC,  prelim_dir="/dissemin/publicos/SINASC/PRELIM/DNRES",  cadence="yearly",  partition_by=_YEARLY,  coverage=((1996, 1), None)),
    Dataset(name="sih_aih_reduzida",              prefix="RD",   ftp_dir=_SIH,     cadence="monthly", partition_by=_MONTHLY, coverage=((2008, 1), None)),
    Dataset(name="sia_bpa_individualizado",       prefix="BI",   ftp_dir=_SIA,     cadence="monthly", partition_by=_MONTHLY, coverage=((2008, 1), None)),
    Dataset(name="sia_apac_medicamentos",         prefix="AM",   ftp_dir=_SIA,     cadence="monthly", partition_by=_MONTHLY, coverage=((2008, 1), None)),
    Dataset(name="sia_apac_quimioterapia",        prefix="AQ",   ftp_dir=_SIA,     cadence="monthly", partition_by=_MONTHLY, coverage=((2008, 1), None)),
    Dataset(name="sia_apac_tratamento_dialitico", prefix="ATD",  ftp_dir=_SIA,     cadence="monthly", partition_by=_MONTHLY, coverage=((2014, 8), None)),
    Dataset(name="sia_apac_laudos_diversos",      prefix="AD",   ftp_dir=_SIA,     cadence="monthly", partition_by=_MONTHLY, coverage=((2008, 1), None)),
    Dataset(name="sia_apac_cirurgia_bariatrica",  prefix="ABO",  ftp_dir=_SIA,     cadence="monthly", partition_by=_MONTHLY, coverage=((2014, 1), None)),
    Dataset(name="sia_psicossocial",              prefix="PS",   ftp_dir=_SIA,     cadence="monthly", partition_by=_MONTHLY, coverage=((2012, 11), None)),
    Dataset(name="cnes_estabelecimentos",         prefix="ST",   ftp_dir=_CNES_ST, cadence="monthly", partition_by=("ano", "mes"), coverage=((2005, 8), None)),
)
# fmt: on

REGISTRY: dict[str, Dataset] = {d.name: d for d in _ROWS}


def resolve(dataset: str | Dataset) -> Dataset:
    """Return the ``Dataset`` for a registry key or pass a value through.

    Names at the edge, values inside (spec §3.3.1): a ``Dataset`` value
    passes through untouched — that is how an uncurated dataset reaches the
    pipeline.
    """
    if isinstance(dataset, Dataset):
        return dataset
    try:
        return REGISTRY[dataset]
    except KeyError:
        raise ValueError(f"unknown dataset: {dataset!r}") from None


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


_FTP_URI_PREFIX = "ftp://ftp.datasus.gov.br"


def release_from_uri(dataset: str, source_uri: str | None) -> Release | None:
    """Which release a stored ``source_uri`` came from, or ``None`` when the
    dataset is not registered, the URI is unknown or its directory is not
    one this row declares."""
    d = REGISTRY.get(dataset)
    if d is None or source_uri is None or not source_uri.startswith(_FTP_URI_PREFIX):
        return None
    directory = source_uri.removeprefix(_FTP_URI_PREFIX).rsplit("/", 1)[0]
    for release, path in d.directories().items():
        if path == directory:
            return release
    return None
