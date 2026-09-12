# DATASUS Release Directories Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One structure for DATASUS final and preliminary files across every FTP row, readable row names with no aliases, identity validation declared in the dictionary, and `outdated()` for the yearly move to final — proven by a `sinan_hanseniase` pilot.

**Architecture:** The registry row gains `prelim_dir`; discovery decodes filenames against the requested `Dataset` and records which directory each scope came from; the runner resolves releases once per run, fetches from the listed directory, stamps `_source_release` on every row and validates identity from an `x-identity` block in the YAML. Every existing row is renamed to DATASUS's own file-type wording; `ALIASES` and `get_config()` are deleted.

**Tech Stack:** Python 3.12+, `uv`, pytest + hypothesis, polars, pyarrow, DuckLake, typer/rich CLI, mkdocs (strict), pre-commit (ruff, mypy, frictionless, generated-docs check).

**Spec:** `docs/superpowers/specs/2026-09-12-datasus-release-directories-design.md`

## Global Constraints

- Run everything with `uv run --locked …` from the checkout root; never `pip`.
- Offline suite: `uv run --locked pytest tests -m 'not e2e and not perf' -q`. Unit tests never touch the network: patch `_blocking_list` / `fetch_dbc_bytes` / `available_releases` as shown.
- Lint gates before every commit: `uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked mypy src && uv run --locked python scripts/gen_datasets_doc.py --check`.
- **Falsify every new test once:** after it passes, break the implementation (comment out the line it guards), see it fail, restore. Record nothing; just do it.
- **No dead code:** no aliases, no compatibility shims, no "kept for old callers". Delete, don't deprecate.
- Names: `<sistema>_<conteúdo>` in full Portuguese words (spec §3.7). Reserved lake columns start with `_source_`.
- DATASUS FTP is shared: live steps download the named file once; nothing loops over directories.
- Historical documents (`reports/*`, `docs/superpowers/specs|plans/*` older than this one, `docs/decisions/0001`) are records: never rewrite them. Amend ADR 0002 by appending.
- Commit messages end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

---

## File map

| File | Responsibility after this plan |
|---|---|
| `src/omnisus_db/sources/datasus_ftp/datasets.py` | `Release`, `Dataset` (+`prelim_dir`, `directories()`, no `aliases`), `REGISTRY`, `resolve`, `in_coverage`, `release_from_uri`. No `ALIASES`, no `get_config`. |
| `src/omnisus_db/sources/datasus_ftp/filenames.py` | `scope_to_filename`, `decode_for(d, name)`. No global prefix map. |
| `src/omnisus_db/sources/datasus_ftp/inventory.py` | `list_dir`, `list_dir_cached`, `crawl`, `available_releases`, `available`. |
| `src/omnisus_db/sources/datasus_ftp/fetch.py` | `ftp_path_for(d, scope, release)`, `fetch_dbc_bytes(..., release=)`. |
| `src/omnisus_db/sources/datasus_ftp/identity.py` (new) | `validate_identity(staging, dicionario, scope)` — the `x-identity` mode rule. |
| `src/omnisus_db/sources/datasus_ftp/staging.py` | injects `_source_release`. |
| `src/omnisus_db/sources/datasus_ftp/_runner.py` | resolves releases once per run; passes release to fetch, staging, `source_uri`; calls `validate_identity`. |
| `src/omnisus_db/lake/publication.py` | `publications()` rows carry `release`. |
| `src/omnisus_db/__init__.py` | exports `available_releases`, `outdated`, `import_cnes_estabelecimentos`. |
| `src/omnisus_db/cli/main.py` | `inventory` shows `Release`; no alias choices; `ibge_populacao`. |
| `src/omnisus_db/sources/sinan/` | deleted. |
| `src/omnisus_db/data/dicionarios/*.yaml` | renamed stems; `sinan_chagas.yaml` and `sinan_hanseniase.yaml` carry `x-identity`. |
| `scripts/gen_dicionario.py` (new) | physical-inventory YAML from one DBC file (used for every new agravo). |
| `tests/integration/test_registry_probe.py` | probes the union of a row's directories. |

---

### Task 1: Rename every row to its readable name; delete aliases and `get_config`

**Files:**
- Modify: `src/omnisus_db/sources/datasus_ftp/datasets.py`, `src/omnisus_db/__init__.py`, `src/omnisus_db/cli/main.py`, `src/omnisus_db/sources/cnes/importers/st.py`, `src/omnisus_db/products.py` (docstring), `src/omnisus_db/lake/operations.py` (docstrings), `scripts/gen_datasets_doc.py`, `scripts/build_fixtures.py`, `mkdocs.yml`, `tests/**`, `notebooks/*.py`, `notebooks/README.md`, `docs/*.md`, `docs/guides/*.md`, `docs/dicionario/**` (where a row name appears), `README.md`
- Rename (git mv): `src/omnisus_db/data/dicionarios/{sim_do→sim_obitos, sinasc_nv→sinasc_nascidos_vivos, sih_rd→sih_aih_reduzida, sia_bi→sia_bpa_individualizado, sia_am→sia_apac_medicamentos, sia_aq→sia_apac_quimioterapia, sia_atd→sia_apac_tratamento_dialitico, sia_ad→sia_apac_laudos_diversos, sia_abo→sia_apac_cirurgia_bariatrica, sia_ps→sia_psicossocial, cnes_st→cnes_estabelecimentos, sinan_chagas_prelim→sinan_chagas, ibge_pop→ibge_populacao}.yaml`; same for `docs/sources/*.md`.
- Test: `tests/unit/sources/datasus_ftp/test_datasets.py`, `tests/unit/test_registry_consistency.py`, `tests/unit/cli/test_main.py`

**Interfaces:**
- Produces: registry keys `sim_obitos`, `sinasc_nascidos_vivos`, `sih_aih_reduzida`, `sia_bpa_individualizado`, `sia_apac_medicamentos`, `sia_apac_quimioterapia`, `sia_apac_tratamento_dialitico`, `sia_apac_laudos_diversos`, `sia_apac_cirurgia_bariatrica`, `sia_psicossocial`, `cnes_estabelecimentos`, `sinan_chagas`; public `import_cnes_estabelecimentos(...)` (same signature as the old `import_cnes_st`); CLI non-FTP name `ibge_populacao`. `Dataset` has no `aliases` field; module has no `ALIASES`, no `get_config`.

- [ ] **Step 1: Write the failing registry test**

Replace the `ELEVEN` set and the alias tests in `tests/unit/sources/datasus_ftp/test_datasets.py`:

```python
ROWS = {
    "sim_obitos",
    "sinasc_nascidos_vivos",
    "sih_aih_reduzida",
    "sia_bpa_individualizado",
    "sia_apac_medicamentos",
    "sia_apac_quimioterapia",
    "sia_apac_tratamento_dialitico",
    "sia_apac_laudos_diversos",
    "sia_apac_cirurgia_bariatrica",
    "sia_psicossocial",
    "cnes_estabelecimentos",
    "sinan_chagas",
}


def test_registry_has_exactly_the_supported_ftp_datasets() -> None:
    assert set(REGISTRY) == ROWS


def test_names_are_full_readable_words() -> None:
    """Spec §3.7: <sistema>_<conteúdo>, never a two-letter file prefix or a release."""
    for name, d in REGISTRY.items():
        system, _, content = name.partition("_")
        assert content, name
        assert content.lower() != d.prefix.lower(), name
        assert not name.endswith(("_prelim", "_final")), name


def test_module_has_no_alias_surface() -> None:
    import omnisus_db.sources.datasus_ftp.datasets as m

    assert not hasattr(m, "ALIASES")
    assert not hasattr(m, "get_config")
    assert "aliases" not in Dataset.__dataclass_fields__
```

Delete `test_aliases_resolve_to_keys`-style tests that import `ALIASES` (in this file, `test_registry_consistency.py`, `test_main.py`).

- [ ] **Step 2: Run it to see it fail**

Run: `uv run --locked pytest tests/unit/sources/datasus_ftp/test_datasets.py -q`
Expected: FAIL (`sim_do` still registered; `ALIASES` exists).

- [ ] **Step 3: Rename the rows and delete the alias surface**

In `datasets.py`, the row block becomes:

```python
# fmt: off
_ROWS: tuple[Dataset, ...] = (
    Dataset(name="sinan_chagas",                  prefix="CHAG", ftp_dir="/dissemin/publicos/SINAN/DADOS/PRELIM", cadence="yearly",  partition_by=("_source_ano",), coverage=((2023, 1), None), geography="national"),
    Dataset(name="sim_obitos",                    prefix="DO",   ftp_dir=_SIM,     cadence="yearly",  partition_by=_YEARLY,  coverage=((1996, 1), None)),
    Dataset(name="sinasc_nascidos_vivos",         prefix="DN",   ftp_dir=_SINASC,  cadence="yearly",  partition_by=_YEARLY,  coverage=((1996, 1), None)),
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
```

Delete the `aliases` field from `Dataset`, the `ALIASES` dict and `get_config`. (`sinan_chagas` keeps `ftp_dir=PRELIM` only until Task 2 gives it the final directory.)

- [ ] **Step 4: Rename every other occurrence**

Run this from the checkout root and review the diff file by file (`git diff --stat`):

```bash
for pair in sinan_chagas_prelim:sinan_chagas sim_do:sim_obitos sinasc_nv:sinasc_nascidos_vivos sih_rd:sih_aih_reduzida sia_bi:sia_bpa_individualizado sia_am:sia_apac_medicamentos sia_aq:sia_apac_quimioterapia sia_atd:sia_apac_tratamento_dialitico sia_ad:sia_apac_laudos_diversos sia_abo:sia_apac_cirurgia_bariatrica sia_ps:sia_psicossocial cnes_st:cnes_estabelecimentos ibge_pop:ibge_populacao import_cnes_st:import_cnes_estabelecimentos; do
  old=${pair%%:*}; new=${pair##*:}
  git grep -l -w "$old" -- src tests scripts notebooks docs/*.md docs/sources docs/guides docs/dicionario mkdocs.yml README.md \
    | xargs perl -pi -e "s/\\b${old}\\b/${new}/g"
done
for pair in sim_do:sim_obitos sinasc_nv:sinasc_nascidos_vivos sih_rd:sih_aih_reduzida sia_bi:sia_bpa_individualizado sia_am:sia_apac_medicamentos sia_aq:sia_apac_quimioterapia sia_atd:sia_apac_tratamento_dialitico sia_ad:sia_apac_laudos_diversos sia_abo:sia_apac_cirurgia_bariatrica sia_ps:sia_psicossocial cnes_st:cnes_estabelecimentos sinan_chagas_prelim:sinan_chagas ibge_pop:ibge_populacao; do
  old=${pair%%:*}; new=${pair##*:}
  [ -f src/omnisus_db/data/dicionarios/$old.yaml ] && git mv src/omnisus_db/data/dicionarios/$old.yaml src/omnisus_db/data/dicionarios/$new.yaml
  [ -f docs/sources/$old.md ] && git mv docs/sources/$old.md docs/sources/$new.md
done
```

Then by hand:
- `cli/main.py`: `_NON_FTP = {"ibge_populacao": "ibge_populacao"}`; `dataset_choices()` returns `sorted({*REGISTRY, *_NON_FTP})`; `ftp_dataset_choices()` returns `sorted(REGISTRY)`; remove the `ALIASES` import and the `cnes-st`/`ibge-pop` hyphenated names.
- `scripts/gen_datasets_doc.py`: drop the `Aliases` column (table header becomes `| Dataset | Prefix | Cadence | Partitioned by | Coverage | FTP directory |`), then `uv run --locked python scripts/gen_datasets_doc.py`.
- `mkdocs.yml` nav lines 44–49: `SIM óbitos: sources/sim_obitos.md`, `SINASC nascidos vivos: sources/sinasc_nascidos_vivos.md`, `SIH AIH reduzida: sources/sih_aih_reduzida.md`, `IBGE população: sources/ibge_populacao.md`, `CNES estabelecimentos: sources/cnes_estabelecimentos.md`, `SINAN Chagas: sources/sinan_chagas.md`.
- Every renamed YAML: set `name:` to the new stem (`load_dicionario` reads `raw["name"]`).
- `tests/unit/test_registry_consistency.py`: `test_b_cli_accepts_every_row_and_alias` → asserts `set(dataset_choices()) == set(REGISTRY) | set(cli_main._NON_FTP)`; `test_d_inventory_advertises…` → `== set(REGISTRY)`; `test_keys_equal_names_and_aliases_point_at_keys` keeps only the key==name loop; `test_c_available_accepts_exactly_the_registry` loops `REGISTRY` only and asserts on `available("sim_obitos")`.
- `docs/sources/sinan_chagas.md` first line: rename the product; the contract text is rewritten in Task 11.
- The fixture `.dbc` files keep their names (they encode prefix/UF); only the keys of `_FIXTURE_FOR`, `DBC_CASES` and `build_fixtures.TARGETS` change.

- [ ] **Step 5: Run the whole offline suite and the gates**

Run: `uv run --locked pytest tests -m 'not e2e and not perf' -q && uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked mypy src && uv run --locked python scripts/gen_datasets_doc.py --check && uv run --locked mkdocs build --strict`
Expected: all PASS. Then `git grep -n -w -e sim_do -e sinasc_nv -e sih_rd -e sia_bi -e cnes_st -e sinan_chagas_prelim -e ibge_pop -e ALIASES -e get_config -- src tests scripts notebooks docs/*.md docs/sources docs/guides mkdocs.yml README.md` prints nothing.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "Rename every dataset to its readable DATASUS name and delete aliases

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: `prelim_dir`, `Release` and `directories()` on the registry row

**Files:**
- Modify: `src/omnisus_db/sources/datasus_ftp/datasets.py`, `scripts/gen_datasets_doc.py`, `docs/datasets.md` (regenerated)
- Test: `tests/unit/sources/datasus_ftp/test_datasets.py`, `tests/unit/test_registry_consistency.py`

**Interfaces:**
- Produces: `Release = Literal["final", "prelim"]`; `Dataset.prelim_dir: str | None = None`; `Dataset.directories() -> dict[Release, str]`; `release_from_uri(dataset_name: str, source_uri: str | None) -> Release | None`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/sources/datasus_ftp/test_datasets.py`:

```python
from omnisus_db.sources.datasus_ftp.datasets import release_from_uri


def test_directories_is_final_only_without_prelim_dir() -> None:
    assert _adhoc().directories() == {"final": "/dissemin/publicos/X"}


def test_directories_lists_prelim_after_final() -> None:
    d = _adhoc(prelim_dir="/dissemin/publicos/X/PRELIM")
    assert list(d.directories().items()) == [
        ("final", "/dissemin/publicos/X"),
        ("prelim", "/dissemin/publicos/X/PRELIM"),
    ]


def test_rows_with_a_preliminary_directory_declare_it() -> None:
    assert REGISTRY["sim_obitos"].prelim_dir == "/dissemin/publicos/SIM/PRELIM/DORES"
    assert REGISTRY["sinasc_nascidos_vivos"].prelim_dir == "/dissemin/publicos/SINASC/PRELIM/DNRES"
    chagas = REGISTRY["sinan_chagas"]
    assert chagas.ftp_dir == "/dissemin/publicos/SINAN/DADOS/FINAIS"
    assert chagas.prelim_dir == "/dissemin/publicos/SINAN/DADOS/PRELIM"
    assert chagas.coverage[0] == (2000, 1)


def test_release_from_uri_recognises_both_directories() -> None:
    assert release_from_uri("sim_obitos", "ftp://ftp.datasus.gov.br/dissemin/publicos/SIM/PRELIM/DORES/DOSP2025.dbc") == "prelim"
    assert release_from_uri("sim_obitos", "ftp://ftp.datasus.gov.br/dissemin/publicos/SIM/CID10/DORES/DOSP2024.dbc") == "final"
    assert release_from_uri("sim_obitos", None) is None
    assert release_from_uri("not_a_row", "ftp://ftp.datasus.gov.br/x/y.dbc") is None
    assert release_from_uri("sim_obitos", "ftp://ftp.datasus.gov.br/elsewhere/DOSP2024.dbc") is None
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run --locked pytest tests/unit/sources/datasus_ftp/test_datasets.py -q`
Expected: FAIL with `TypeError: unexpected keyword 'prelim_dir'` / `ImportError`.

- [ ] **Step 3: Implement**

In `datasets.py`:

```python
Release = Literal["final", "prelim"]
"""Which DATASUS directory a file was published in. ``prelim`` files are
revised and later moved to the final directory under the same name."""
```

Add to `Dataset` after `geography`:

```python
    prelim_dir: str | None = None
    """Directory where DATASUS publishes this dataset's preliminary files,
    when it has one. Same filenames as ``ftp_dir``; a file is in one or the
    other, never both."""

    def directories(self) -> dict[Release, str]:
        """Every directory this row is published in, final first."""
        dirs: dict[Release, str] = {"final": self.ftp_dir}
        if self.prelim_dir is not None:
            dirs["prelim"] = self.prelim_dir
        return dirs
```

Rows:

```python
_SINAN_FINAIS = "/dissemin/publicos/SINAN/DADOS/FINAIS"
_SINAN_PRELIM = "/dissemin/publicos/SINAN/DADOS/PRELIM"
# ...
    Dataset(name="sinan_chagas", prefix="CHAG", ftp_dir=_SINAN_FINAIS, prelim_dir=_SINAN_PRELIM, cadence="yearly", partition_by=("_source_ano",), coverage=((2000, 1), None), geography="national"),
    Dataset(name="sim_obitos", prefix="DO", ftp_dir=_SIM, prelim_dir="/dissemin/publicos/SIM/PRELIM/DORES", cadence="yearly", partition_by=_YEARLY, coverage=((1996, 1), None)),
    Dataset(name="sinasc_nascidos_vivos", prefix="DN", ftp_dir=_SINASC, prelim_dir="/dissemin/publicos/SINASC/PRELIM/DNRES", cadence="yearly", partition_by=_YEARLY, coverage=((1996, 1), None)),
```

Module-level function:

```python
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
```

`gen_datasets_doc.py`: add a `Preliminary directory` column rendering `` `d.prelim_dir` `` or `—`; regenerate.

- [ ] **Step 4: Run tests and gates**

Run: `uv run --locked pytest tests/unit -q && uv run --locked python scripts/gen_datasets_doc.py && uv run --locked python scripts/gen_datasets_doc.py --check`
Expected: PASS. (Golden filename tests for `sinan_chagas` still pass: the filename codec does not read directories.)

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Declare preliminary directories on the registry row

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: Decode filenames against the requested dataset

**Files:**
- Modify: `src/omnisus_db/sources/datasus_ftp/filenames.py`, `src/omnisus_db/sources/datasus_ftp/inventory.py` (import only), `tests/integration/test_registry_probe.py` (import only; body rewritten in Task 7), `notebooks/inventario_dados_reais.py`
- Test: `tests/unit/sources/datasus_ftp/test_filenames.py`, `tests/unit/sources/datasus_ftp/test_filenames_golden.py`, `tests/unit/sources/datasus_ftp/test_sia_apac.py`, `tests/unit/sources/datasus_ftp/test_sia_bi.py`, `tests/unit/sources/datasus_ftp/test_sinan_chagas.py`

**Interfaces:**
- Produces: `decode_for(d: Dataset, name: str) -> ScopeKey | None`. Removes `parse_filename`, `decode`, `PREFIX_TO_DATASET`.

- [ ] **Step 1: Write the failing tests**

In `test_filenames_golden.py`, replace the `parse_filename` round-trip with:

```python
from omnisus_db.sources.datasus_ftp.filenames import decode_for, scope_to_filename


@pytest.mark.parametrize(("dataset", "scope", "filename"), GOLDEN, ids=_IDS)
def test_decode_for_inverts_scope_to_filename(dataset: str, scope: ScopeKey, filename: str) -> None:
    assert decode_for(REGISTRY[dataset], filename) == scope


@pytest.mark.parametrize(("dataset", "scope", "filename"), GOLDEN, ids=_IDS)
def test_no_other_row_claims_the_name(dataset: str, scope: ScopeKey, filename: str) -> None:
    """ATDRR2401 must decode for the ATD row only, never for AD; ADAC2401 for AD only."""
    claimants = {name for name, d in REGISTRY.items() if decode_for(d, filename) is not None}
    assert claimants == {dataset}


@settings(max_examples=300)
@given(
    dataset=st.sampled_from(sorted(REGISTRY)),
    uf=st.sampled_from(ALL_UFS),
    ano=st.integers(min_value=1980, max_value=2079),
    mes=st.integers(min_value=1, max_value=12),
)
def test_round_trip_property(dataset: str, uf: str, ano: int, mes: int) -> None:
    d = REGISTRY[dataset]
    scope = (
        ScopeKey(uf=None, ano=ano)
        if d.geography == "national"
        else ScopeKey(uf=uf, ano=ano, mes=mes if d.monthly else None)
    )
    assert decode_for(d, scope_to_filename(d, scope)) == scope


def test_decode_for_rejects_foreign_and_malformed_names() -> None:
    d = REGISTRY["sim_obitos"]
    assert decode_for(d, "DNSP2024.dbc") is None
    assert decode_for(d, "DOSP24.dbc") is None
    assert decode_for(d, "DOSP2024.DBC") == ScopeKey(uf="SP", ano=2024)
    assert decode_for(REGISTRY["sih_aih_reduzida"], "RDSP2413.dbc") is None
```

Update `test_sinan_chagas.py::test_national_filename_and_planner` to `assert decode_for(d, "CHAGBR23.dbc") == scopes[0]` and `assert decode_for(d, "CHAGSP23.dbc") is None`. In `test_filenames.py`, `test_sia_apac.py`, `test_sia_bi.py` replace each `parse_filename(name)` / `decode(name)` assertion with `decode_for(REGISTRY[<row>], name)`; assertions that expected `(scope, dataset_name)` now expect `scope`.

- [ ] **Step 2: Run to see them fail**

Run: `uv run --locked pytest tests/unit/sources/datasus_ftp -q`
Expected: FAIL with `ImportError: cannot import name 'decode_for'`.

- [ ] **Step 3: Implement `decode_for`; delete the global map**

`filenames.py` becomes:

```python
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
    like the server. A 2-letter prefix never swallows a 3-letter one
    (``AD`` on ``ATDRR2401.dbc`` fails because ``TR`` is not two digits).
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
```

Temporarily make `inventory.available` and `test_registry_probe.py` compile by replacing `decode(entry.name)` with `decode_for(d, entry.name)` and `decoded[1] == d.name` filters with `is not None` (both files are rewritten in Tasks 4 and 7). In `notebooks/inventario_dados_reais.py` replace `decode(name)` with `decode_for(resolve(<row>), name)`.

- [ ] **Step 4: Run tests**

Run: `uv run --locked pytest tests/unit -q && uv run --locked mypy src`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Decode DATASUS filenames against the requested dataset row

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: `available_releases()` over every directory; `Release` column in the CLI

**Files:**
- Modify: `src/omnisus_db/sources/datasus_ftp/inventory.py`, `src/omnisus_db/__init__.py` (export), `src/omnisus_db/cli/main.py` (`inventory` command)
- Test: `tests/unit/sources/datasus_ftp/test_available.py`, `tests/unit/cli/test_main.py`

**Interfaces:**
- Consumes: `Dataset.directories()`, `decode_for`.
- Produces: `available_releases(dataset, *, years=None, refresh=False) -> dict[ScopeKey, Release]` (sorted by year, uf, month); `available(...)` returns `list(available_releases(...))`. Exported as `omnisus_db.available_releases`.

- [ ] **Step 1: Write the failing tests**

Append to `test_available.py`:

```python
from omnisus_db.sources.datasus_ftp.inventory import available_releases

SIM_PRELIM_DIR = REGISTRY["sim_obitos"].prelim_dir


def _listing_by_path(paths: dict[str, list[str]]):
    def fake(path: str, _timeout: float) -> list[str]:
        return paths[path]

    return fake


def test_available_releases_reads_both_directories() -> None:
    fake = _listing_by_path({SIM_DIR: [_file("DOAC2024.dbc")], SIM_PRELIM_DIR: [_file("DOAC2025.dbc")]})
    with patch("omnisus_db.sources.datasus_ftp.inventory._blocking_list", side_effect=fake):
        releases = available_releases("sim_obitos")
    assert releases == {ScopeKey(uf="AC", ano=2024): "final", ScopeKey(uf="AC", ano=2025): "prelim"}
    assert list(releases) == [ScopeKey(uf="AC", ano=2024), ScopeKey(uf="AC", ano=2025)]


def test_available_is_the_keys_of_available_releases() -> None:
    fake = _listing_by_path({SIM_DIR: [_file("DOAC2024.dbc")], SIM_PRELIM_DIR: [_file("DOAC2025.dbc")]})
    with patch("omnisus_db.sources.datasus_ftp.inventory._blocking_list", side_effect=fake):
        assert available("sim_obitos", years=[2025]) == [ScopeKey(uf="AC", ano=2025)]


def test_same_scope_in_both_directories_is_an_error_not_a_preference() -> None:
    fake = _listing_by_path({SIM_DIR: [_file("DOAC2025.dbc")], SIM_PRELIM_DIR: [_file("DOAC2025.dbc")]})
    with patch("omnisus_db.sources.datasus_ftp.inventory._blocking_list", side_effect=fake):
        with pytest.raises(ValueError, match="both final and prelim"):
            available_releases("sim_obitos")


def test_row_without_prelim_dir_lists_one_directory_only() -> None:
    calls: list[str] = []

    def fake(path: str, _timeout: float) -> list[str]:
        calls.append(path)
        return [_file("BIRR2401.dbc")]

    with patch("omnisus_db.sources.datasus_ftp.inventory._blocking_list", side_effect=fake):
        assert available_releases("sia_bpa_individualizado") == {ScopeKey(uf="RR", ano=2024, mes=1): "final"}
    assert calls == [SIA_DIR]


def test_adhoc_dataset_is_discovered() -> None:
    """ADR 0002: an unregistered Dataset flows through the same path — including discovery."""
    from omnisus_db.sources.datasus_ftp.datasets import Dataset

    d = Dataset(name="pce", prefix="PCE", ftp_dir="/dissemin/publicos/PCE/DADOS", cadence="yearly",
                partition_by=("ano", "uf"), coverage=((2000, 1), None))
    with patch("omnisus_db.sources.datasus_ftp.inventory._blocking_list", return_value=[_file("PCEAL2023.dbc")]):
        assert available(d) == [ScopeKey(uf="AL", ano=2023)]
```

In `tests/unit/cli/test_main.py`, extend the inventory test so the stubbed `odb.available_releases` returns `{ScopeKey(uf="AC", ano=2025): "prelim"}` and assert `"prelim"` appears in the output and the header has `Release`.

- [ ] **Step 2: Run to see them fail**

Run: `uv run --locked pytest tests/unit/sources/datasus_ftp/test_available.py tests/unit/cli/test_main.py -q`
Expected: FAIL (`available_releases` missing; CLI table has 3 columns).

- [ ] **Step 3: Implement**

Replace `available` in `inventory.py`:

```python
def available_releases(
    dataset: str | Dataset,
    *,
    years: Iterable[int] | None = None,
    refresh: bool = False,
) -> dict[ScopeKey, Release]:
    """Scopes DATASUS actually publishes for ``dataset`` and the release each
    one is in, ordered by year, uf, month.

    One cached LIST per directory of the row (spec §4.1). Filenames are decoded
    for this row only, so other datasets sharing the directory are skipped and
    an ad-hoc ``Dataset`` is discovered like a registered one. A scope found
    in two directories is a server inconsistency and raises: it is never
    resolved by preference.
    """
    d = resolve(dataset)
    wanted = set(years) if years is not None else None
    found: dict[ScopeKey, Release] = {}
    for release, directory in d.directories().items():
        for entry in list_dir_cached(directory, refresh=refresh).files:
            scope = decode_for(d, entry.name)
            if scope is None or (wanted is not None and scope.ano not in wanted):
                continue
            if scope in found:
                raise ValueError(
                    f"{d.name}: {entry.name} is published as both {found[scope]} and {release}"
                )
            found[scope] = release
    ordered = sorted(found, key=lambda s: (s.ano, s.uf or "", s.mes or 0))
    logger.info("inventory.available", dataset=d.name, scopes=len(ordered))
    return {s: found[s] for s in ordered}


def available(
    dataset: str | Dataset,
    *,
    years: Iterable[int] | None = None,
    refresh: bool = False,
) -> list[ScopeKey]:
    """The scopes of :func:`available_releases`, without the release."""
    return list(available_releases(dataset, years=years, refresh=refresh))
```

Import `Release` from `datasets` and `decode_for` from `filenames`. Export `available_releases` in `omnisus_db/__init__.py` (`from …inventory import available, available_releases`; add to `__all__`).

CLI `inventory` command:

```python
        releases = odb.available_releases(d, refresh=refresh)
        table = RichTable("UF", "Ano", "Mês", "Release")
        for s, release in releases.items():
            table.add_row(s.uf or "Nacional", str(s.ano), "" if s.mes is None else f"{s.mes:02d}", release)
        console.print(table)
        console.print(f"[dim]{len(releases)} scope(s) available for {d.name}[/dim]")
```

- [ ] **Step 4: Run tests and gates**

Run: `uv run --locked pytest tests/unit -q && uv run --locked mypy src`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "List every release directory in available() and show it in inventory

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: Fetch from the listed directory; runner resolves releases once per run

**Files:**
- Modify: `src/omnisus_db/sources/datasus_ftp/fetch.py`, `src/omnisus_db/sources/datasus_ftp/_runner.py`, `src/omnisus_db/__init__.py` (`import_dataset` passes nothing new; docstring), `scripts/build_fixtures.py`
- Test: `tests/unit/sources/datasus_ftp/test_fetch.py`, `tests/unit/sources/datasus_ftp/test_runner.py`, `tests/unit/test_public_api.py`

**Interfaces:**
- Consumes: `available_releases`, `Dataset.directories()`.
- Produces: `ftp_path_for(dataset, scope, release: Release = "final") -> tuple[str, str]` (pure); `fetch_dbc_bytes(*, dataset, scope, release: Release = "final", …)`; `ingest_raw(d, scope, raw, lake, *, release: Release = "final", …)`; `run_scopes(…)` resolves `releases: dict[ScopeKey, Release]` once via `available_releases` **only when `d.prelim_dir is not None`**, otherwise `{}`; `_runner.release_map(d) -> dict[ScopeKey, Release]` is the patch seam.

- [ ] **Step 1: Write the failing tests**

Append to `test_fetch.py`:

```python
from omnisus_db.sources.datasus_ftp.fetch import ftp_path_for


def test_ftp_path_for_uses_the_release_directory() -> None:
    d = REGISTRY["sim_obitos"]
    scope = ScopeKey(uf="SP", ano=2025)
    assert ftp_path_for(d, scope) == (d.ftp_dir, "DOSP2025.dbc")
    assert ftp_path_for(d, scope, "prelim") == (d.prelim_dir, "DOSP2025.dbc")


def test_ftp_path_for_prelim_on_a_row_without_prelim_dir_is_a_caller_bug() -> None:
    with pytest.raises(ValueError, match="has no prelim directory"):
        ftp_path_for(REGISTRY["sia_bpa_individualizado"], ScopeKey(uf="RR", ano=2024, mes=1), "prelim")
```

Append to `test_runner.py`:

```python
def test_run_scopes_fetches_from_the_listed_release(monkeypatch, tmp_path) -> None:
    from omnisus_db.sources.datasus_ftp import _runner

    seen: list[tuple[ScopeKey, str]] = []

    async def fake_fetch(*, dataset, scope, release="final", **_):
        seen.append((scope, release))
        raise FtpFileNotFound("stop here")  # skipped: the release choice is what we test

    monkeypatch.setattr(_runner, "release_map", lambda d: {ScopeKey(uf="AC", ano=2025): "prelim"})
    monkeypatch.setattr(_runner, "fetch_dbc_bytes", fake_fetch)
    with Lake.local(f"ducklake:{tmp_path}/l.ducklake") as lake:
        asyncio.run(_runner.run_scopes("sim_obitos", scopes=[ScopeKey(uf="AC", ano=2024), ScopeKey(uf="AC", ano=2025)], lake=lake))
    assert seen == [(ScopeKey(uf="AC", ano=2024), "final"), (ScopeKey(uf="AC", ano=2025), "prelim")]


def test_release_map_lists_nothing_for_rows_without_prelim_dir(monkeypatch) -> None:
    from omnisus_db.sources.datasus_ftp import _runner

    monkeypatch.setattr(_runner, "available_releases", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not list")))
    assert _runner.release_map(REGISTRY["sia_bpa_individualizado"]) == {}
```

In `tests/unit/test_public_api.py::_fake_fetch_from`, also `monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.release_map", lambda d: {})` so rows with `prelim_dir` do not list.

- [ ] **Step 2: Run to see them fail**

Run: `uv run --locked pytest tests/unit/sources/datasus_ftp/test_fetch.py tests/unit/sources/datasus_ftp/test_runner.py -q`
Expected: FAIL (`ftp_path_for` takes 2 args; `release_map` missing).

- [ ] **Step 3: Implement**

`fetch.py`:

```python
def ftp_path_for(dataset: str | Dataset, scope: ScopeKey, release: Release = "final") -> tuple[str, str]:
    """Return (remote_dir, filename) for ``scope`` in ``release``.

    Pure: the release comes from the caller, who learned it from the listing
    (``available_releases``). Nothing here tries one directory then another.
    """
    d = resolve(dataset)
    directories = d.directories()
    if release not in directories:
        raise ValueError(f"{d.name} has no {release} directory")
    return directories[release], scope_to_filename(d, scope)
```

`fetch_dbc_bytes` gains `release: Release = "final"` and passes it to `ftp_path_for`.

`_runner.py`:

```python
from omnisus_db.sources.datasus_ftp.datasets import Dataset, Release, in_coverage, resolve
from omnisus_db.sources.datasus_ftp.inventory import available_releases


def release_map(d: Dataset) -> dict[ScopeKey, Release]:
    """Where each published scope currently lives. Rows with a single
    directory need no listing: everything is ``final``."""
    if d.prelim_dir is None:
        return {}
    return available_releases(d)
```

`import_scope`: `releases = await asyncio.to_thread(release_map, d)`; `raw = await fetch_dbc_bytes(dataset=d, scope=scope, release=releases.get(scope, "final"))`; `ingest_raw(d, scope, raw, lake, release=releases.get(scope, "final"))`.

`ingest_raw(..., release: Release = "final")`: `source_uri=f"ftp://ftp.datasus.gov.br{d.directories()[release]}/{scope_to_filename(d, scope)}"`. (Staging gets `release` in Task 6.)

`run_scopes`: after validating arguments, `releases = await asyncio.to_thread(release_map, d)`; in `produce`, `fetch_dbc_bytes(dataset=d, scope=scope, release=releases.get(scope, "final"))`; in the consumer, `ingest_raw(..., release=releases.get(scope, "final"))`.

`scripts/build_fixtures.py::fetch_via_ftp`: `release = odb.available_releases(dataset).get(scope, "final")` and `ftp_path = ftp_path_for(dataset, scope, release)[0]`.

- [ ] **Step 4: Run tests and gates**

Run: `uv run --locked pytest tests/unit -q && uv run --locked mypy src`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Fetch each scope from the directory the listing found it in

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: `_source_release` on every row; `release` in `publications()`

**Files:**
- Modify: `src/omnisus_db/sources/datasus_ftp/staging.py`, `src/omnisus_db/sources/datasus_ftp/_runner.py`, `src/omnisus_db/lake/publication.py`
- Test: `tests/unit/sources/datasus_ftp/test_staging.py` (create if absent), `tests/unit/sources/datasus_ftp/test_sinan_chagas.py`, `tests/unit/lake/test_publication.py` (or the existing publication test module)

**Interfaces:**
- Consumes: `Release`, `release_from_uri`.
- Produces: `dbc_bytes_to_parquet(..., release: Release | None = None)` writes column `_source_release` (`pa.string()`); `publications()` rows have `release: Release | None`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/sources/datasus_ftp/test_staging.py
import polars as pl
import pytest

from omnisus_db.sources.datasus_ftp import parse
from omnisus_db.sources.datasus_ftp.staging import dbc_bytes_to_parquet
from tests.support.dbf import make_dbf


def _dbf(fields, rows):
    return make_dbf(fields, [b" " + r for r in rows])


def test_staging_stamps_source_release(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(parse.datasus_dbc, "decompress_bytes", lambda raw: raw)
    raw = _dbf([("NU_ANO", "C", 4, 0)], [b"2025"])
    out = tmp_path / "s.parquet"
    dbc_bytes_to_parquet(raw, out, dataset="sinan_chagas", source_ano=2025, release="prelim")
    frame = pl.read_parquet(out)
    assert frame["_source_release"].to_list() == ["prelim"]
    assert frame["_source_ano"].to_list() == [2025]


def test_staging_rejects_a_dbf_that_already_has_the_reserved_column(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(parse.datasus_dbc, "decompress_bytes", lambda raw: raw)
    raw = _dbf([("_SOURCE_RE", "C", 5, 0)], [b"final"])  # DBF names are 10 chars; lowercased it collides
    with pytest.raises(ValueError, match="reserved"):
        dbc_bytes_to_parquet(raw, tmp_path / "s.parquet", dataset="sinan_chagas", source_ano=2025, release="final")
```

(The second test guards the rule; if a 10-char DBF name cannot collide with `_source_release`, keep the check and drop this test — say so in the commit body.)

Publication test:

```python
def test_publications_expose_release_from_source_uri(tmp_path) -> None:
    import polars as pl
    import omnisus_db as odb
    from omnisus_db.sources._base import ScopeKey

    with odb.Lake.local(f"ducklake:{tmp_path}/l.ducklake") as lake:
        p = tmp_path / "d.parquet"
        pl.DataFrame({"_source_ano": [2025], "_source_release": ["prelim"], "v": [1]}).write_parquet(p)
        lake.publish_scope("sinan_chagas", p, scope=ScopeKey(uf=None, ano=2025), source_sha256="a" * 64,
                           parser_version="v1", source_uri="ftp://ftp.datasus.gov.br/dissemin/publicos/SINAN/DADOS/PRELIM/CHAGBR25.dbc")
        pl.DataFrame({"_source_ano": [2024], "_source_release": ["final"], "v": [1]}).write_parquet(p)
        lake.publish_scope("sinan_chagas", p, scope=ScopeKey(uf=None, ano=2024), source_sha256="b" * 64,
                           parser_version="v1", source_uri="ftp://ftp.datasus.gov.br/dissemin/publicos/SINAN/DADOS/FINAIS/CHAGBR24.dbc")
        pl.DataFrame({"_source_ano": [2023], "v": [1]}).write_parquet(p)
        lake.publish_scope("sinan_chagas", p, scope=ScopeKey(uf=None, ano=2023), source_sha256="c" * 64, parser_version="v1")
        rows = {r["scope"].ano: r["release"] for r in lake.publications()}
    assert rows == {2025: "prelim", 2024: "final", 2023: None}
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run --locked pytest tests/unit/sources/datasus_ftp/test_staging.py tests/unit/lake -q`
Expected: FAIL (`release` kwarg unknown; no `release` key).

- [ ] **Step 3: Implement**

`staging.py`: add parameter `release: Release | None = None`; in `spool`, after the `_source_ano` reserved check add `if "_source_release" in lowered: raise ValueError("DBF uses reserved source column _source_release")`; extend both injection lists with `("_source_release", release, pa.string())`. `_runner.ingest_raw` passes `release=release`.

`publication.py::publications`:

```python
    from omnisus_db.sources.datasus_ftp.datasets import release_from_uri  # local: lake stays registry-free at import

    for row in rows:
        dimensions = json.loads(row["scope_json"])
        row["scope"] = scope_from_fields(dimensions) if isinstance(dimensions, dict) else None
        row["release"] = release_from_uri(row["dataset"], row.get("source_uri"))
```

- [ ] **Step 4: Run tests**

Run: `uv run --locked pytest tests/unit -q && uv run --locked mypy src`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Stamp every row with _source_release and expose release in publications()

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: Tier 3 probe over the union of a row's directories

**Files:**
- Modify: `tests/integration/test_registry_probe.py`

**Interfaces:**
- Consumes: `Dataset.directories()`, `decode_for`, `Listing`.

- [ ] **Step 1: Rewrite the probe**

```python
ROWS = [pytest.param(d, id=name) for name, d in sorted(REGISTRY.items())]


@pytest.fixture(scope="module")
def listings() -> dict[str, Listing]:
    """One live LIST per distinct directory — rows share directories (SIA) and
    a row may have two (final + preliminary)."""
    cache: dict[str, Listing] = {}
    for d in REGISTRY.values():
        for directory in d.directories().values():
            if directory not in cache:
                cache[directory] = list_dir(directory, timeout_seconds=120.0)
    return cache


def _scopes(d: Dataset, listings: dict[str, Listing]) -> list[ScopeKey]:
    return [
        scope
        for directory in d.directories().values()
        for e in listings[directory].files
        if (scope := decode_for(d, e.name)) is not None
    ]


@pytest.mark.parametrize("d", ROWS)
def test_every_directory_exists_and_parses_cleanly(d: Dataset, listings: dict[str, Listing]) -> None:
    for release, directory in d.directories().items():
        listing = listings[directory]
        assert listing.entries, f"{d.name}: {release} directory {directory} listed empty"
        assert listing.skipped == 0, f"{d.name}: {listing.skipped} unparseable LIST lines in {directory}"


@pytest.mark.parametrize("d", ROWS)
def test_some_directory_holds_files_with_this_prefix(d: Dataset, listings: dict[str, Listing]) -> None:
    assert _scopes(d, listings), f"{d.name}: no file in {list(d.directories().values())} decodes to this row"


@pytest.mark.parametrize("d", ROWS)
def test_no_scope_is_published_in_two_directories(d: Dataset, listings: dict[str, Listing]) -> None:
    scopes = _scopes(d, listings)
    assert len(scopes) == len(set(scopes)), f"{d.name}: a scope appears in more than one release directory"
```

Keep `test_coverage_matches_the_earliest_published_file` and `test_coverage_end_is_not_a_stale_claim` but compute `scopes = _scopes(d, listings)`.

- [ ] **Step 2: Compile-check offline, then run live once**

Run: `uv run --locked pytest tests/integration/test_registry_probe.py --collect-only -q` → collects without error.
Run: `uv run --locked pytest tests/integration/test_registry_probe.py -m integration -q`
Expected: PASS for all 12 rows (SIM/SINASC now list their PRELIM directories too). A failure is a finding about a row, not a reason to loosen an assertion.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_registry_probe.py
git commit -m "Probe the union of a row's release directories

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: `x-identity` validation from the dictionary; delete the Chagas module

**Files:**
- Create: `src/omnisus_db/sources/datasus_ftp/identity.py`
- Delete: `src/omnisus_db/sources/sinan/__init__.py`, `src/omnisus_db/sources/sinan/chagas.py`
- Modify: `src/omnisus_db/sources/datasus_ftp/_runner.py`, `src/omnisus_db/data/dicionarios/sinan_chagas.yaml`
- Test: `tests/unit/sources/datasus_ftp/test_identity.py` (new), `tests/unit/sources/datasus_ftp/test_sinan_chagas.py`

**Interfaces:**
- Consumes: `Dicionario.raw`, `load_dicionario`.
- Produces: `validate_identity(staging: Path, dicionario: Dicionario, scope: ScopeKey) -> None`; YAML block `x-identity: {year_column: str, code_column?: str, code?: str}`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/sources/datasus_ftp/test_identity.py
from pathlib import Path

import polars as pl
import pytest

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.identity import validate_identity
from omnisus_db.transforms.dictionaries import Dicionario


def _dic(**identity) -> Dicionario:
    raw = {"name": "t", "schema": {"fields": []}}
    if identity:
        raw["x-identity"] = identity
    return Dicionario(name="t", title="t", encoding="latin-1", fields=[], primary_key=[], partitions=[],
                      source_format="dbc", version="1", raw=raw)


def _staging(tmp_path: Path, **columns) -> Path:
    p = tmp_path / "s.parquet"
    pl.DataFrame(columns).write_parquet(p)
    return p


SCOPE = ScopeKey(uf=None, ano=2025)


def test_no_block_means_no_check(tmp_path) -> None:
    validate_identity(_staging(tmp_path, nu_ano=["1999"]), _dic(), SCOPE)


def test_mode_of_year_must_equal_the_scope_year(tmp_path) -> None:
    ok = _staging(tmp_path, nu_ano=["2025", "2025", "2026"])  # a few off-year records are normal (TB)
    validate_identity(ok, _dic(year_column="nu_ano"), SCOPE)
    bad = _staging(tmp_path, nu_ano=["2024", "2024", "2025"])
    with pytest.raises(ValueError, match="year"):
        validate_identity(bad, _dic(year_column="nu_ano"), SCOPE)


def test_missing_year_column_and_empty_file_are_rejected(tmp_path) -> None:
    with pytest.raises(ValueError, match="nu_ano"):
        validate_identity(_staging(tmp_path, other=["x"]), _dic(year_column="nu_ano"), SCOPE)
    with pytest.raises(ValueError, match="empty"):
        validate_identity(_staging(tmp_path, nu_ano=pl.Series([], dtype=pl.String)), _dic(year_column="nu_ano"), SCOPE)


def test_code_mode_must_match_when_the_column_exists(tmp_path) -> None:
    dic = _dic(year_column="nu_ano", code_column="id_agravo", code="A309")
    validate_identity(_staging(tmp_path, nu_ano=["2025"] * 3, id_agravo=["A309", "A309", "A30."]), dic, SCOPE)
    with pytest.raises(ValueError, match="A309"):
        validate_identity(_staging(tmp_path, nu_ano=["2025"] * 3, id_agravo=["", "", "A309"]), dic, SCOPE)  # AIDABR24 shape
    validate_identity(_staging(tmp_path, nu_ano=["2025"]), dic, SCOPE)  # pre-2007 layout: no code column


def test_values_are_trimmed_and_compared_as_text(tmp_path) -> None:
    validate_identity(_staging(tmp_path, nu_ano=[" 2025 "], id_agravo=[" A309"]),
                      _dic(year_column="nu_ano", code_column="id_agravo", code="A309"), SCOPE)
```

Replace `test_chagas_validator_rejects_wrong_source` in `test_sinan_chagas.py` with a test that runs `ingest_raw` on a synthetic DBF whose `NU_ANO` mode is wrong and asserts `ValueError` mentioning `year` — reuse the existing `test_synthetic_full_pipeline…` fixture-building code with `NU_ANO` set to `2022` for every record and scope 2023.

- [ ] **Step 2: Run to see them fail**

Run: `uv run --locked pytest tests/unit/sources/datasus_ftp/test_identity.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

```python
# src/omnisus_db/sources/datasus_ftp/identity.py
"""Source identity, declared in the dictionary and checked once per file.

A DATASUS file is identified by the *mode* of its year column (and, when the
layout has one, of its agravo code): the whole file is rejected when the
mode is wrong, while the few off-year or mis-typed records real files carry
(tuberculosis, zika) stay in the lake untouched. Which columns and which code
is a per-dataset fact, so it lives in the YAML's ``x-identity`` block, and
changing it changes ``parser_version`` for free.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from omnisus_db.sources._base import ScopeKey
from omnisus_db.transforms.dictionaries import Dicionario


def _mode(frame: pl.LazyFrame, column: str) -> str | None:
    """Most frequent trimmed text value; ties break on the value, so the answer is deterministic."""
    top = (
        frame.select(pl.col(column).cast(pl.String).str.strip_chars().alias("v"))
        .group_by("v")
        .len()
        .sort(["len", "v"], descending=[True, False])
        .limit(1)
        .collect()
    )
    return top["v"][0] if top.height else None


def validate_identity(staging: Path, dicionario: Dicionario, scope: ScopeKey) -> None:
    spec = dicionario.raw.get("x-identity")
    if not spec:
        return
    frame = pl.scan_parquet(staging)
    columns = set(frame.collect_schema().names())
    year_column = spec["year_column"]
    if year_column not in columns:
        raise ValueError(f"{dicionario.name}: identity column {year_column!r} is missing")
    year = _mode(frame, year_column)
    if year is None:
        raise ValueError(f"{dicionario.name}: empty source file")
    if year != str(scope.ano):
        raise ValueError(f"{dicionario.name}: most frequent {year_column} is {year}, not the scope year {scope.ano}")
    code_column = spec.get("code_column")
    if code_column and code_column in columns:
        code = _mode(frame, code_column)
        if code != spec["code"]:
            raise ValueError(f"{dicionario.name}: most frequent {code_column} is {code!r}, not {spec['code']!r}")
```

`_runner.ingest_raw`: replace the `if d.name == …` block with

```python
        validate_identity(staging, load_dicionario(d.dictionary if d.dictionary is not None else d.name), scope)
```

(import `validate_identity` and `load_dicionario` at module top). Delete `src/omnisus_db/sources/sinan/`.

`sinan_chagas.yaml`: after `x-partitions`, add

```yaml
x-identity:
  year_column: nu_ano
  code_column: id_agravo
  code: B571
```

and update `x-evidence.source_url` to the `FINAIS`-or-`PRELIM` file actually inventoried (keep the observed one).

- [ ] **Step 4: Run tests and gates**

Run: `uv run --locked pytest tests/unit -q && uv run --locked mypy src && uv run --locked frictionless validate src/omnisus_db/data/dicionarios/sinan_chagas.yaml`
Expected: PASS; `git grep -n "sources.sinan" src tests` prints nothing.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Validate source identity from the dictionary's x-identity block

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 9: `outdated()`

**Files:**
- Modify: `src/omnisus_db/__init__.py`
- Test: `tests/unit/test_public_api.py`

**Interfaces:**
- Consumes: `available_releases`, `Session.publications()` rows with `release` and `scope`.
- Produces: `outdated(dataset, *, lake: Lake | LakeReader, refresh: bool = False) -> list[ScopeKey]`, exported.

- [ ] **Step 1: Write the failing test**

```python
def test_outdated_lists_scopes_whose_release_moved(tmp_path, monkeypatch) -> None:
    import polars as pl

    target = f"ducklake:{tmp_path}/l.ducklake"
    with Lake.local(target) as lake:
        for year, release in ((2024, "FINAIS"), (2025, "PRELIM"), (2026, "PRELIM")):
            p = tmp_path / "d.parquet"
            pl.DataFrame({"_source_ano": [year], "v": [1]}).write_parquet(p)
            lake.publish_scope("sinan_chagas", p, scope=ScopeKey(uf=None, ano=year), source_sha256=str(year) * 16,
                               parser_version="v1", source_uri=f"ftp://ftp.datasus.gov.br/dissemin/publicos/SINAN/DADOS/{release}/CHAGBR{year % 100}.dbc")
    server = {ScopeKey(uf=None, ano=2024): "final", ScopeKey(uf=None, ano=2025): "final", ScopeKey(uf=None, ano=2027): "prelim"}
    monkeypatch.setattr("omnisus_db.available_releases", lambda *a, **k: server)
    with Lake.local(target) as lake:
        assert odb.outdated("sinan_chagas", lake=lake) == [ScopeKey(uf=None, ano=2025)]
        # 2026 is in the lake but no longer on the server: a withdrawal, not an outdated release
        assert odb.outdated("sia_bpa_individualizado", lake=lake) == []
```

- [ ] **Step 2: Run to see it fail**

Run: `uv run --locked pytest tests/unit/test_public_api.py -k outdated -q`
Expected: FAIL with `AttributeError: outdated`.

- [ ] **Step 3: Implement**

```python
def outdated(
    dataset: str | Dataset,
    *,
    lake: Lake | LakeReader,
    refresh: bool = False,
) -> list[ScopeKey]:
    """Scopes whose release in ``lake`` differs from the server's current one.

    The yearly operation: DATASUS moves a year from the preliminary to the
    final directory under the same name, and nothing in the lake changes by
    itself. Read-only; pass the result to :func:`import_dataset` with
    ``policy="replace"`` and a ``run_id``. Scopes in the lake that the server
    no longer lists are a withdrawal, a different fact, and are not returned.
    """
    d = resolve(dataset)
    current = available_releases(d, refresh=refresh)
    moved = {
        row["scope"]
        for row in lake.publications()
        if row["dataset"] == d.name
        and row["active"]
        and row["scope"] is not None
        and row["release"] is not None
        and current.get(row["scope"]) not in (None, row["release"])
    }
    return sorted(moved, key=lambda s: (s.ano, s.uf or "", s.mes or 0))
```

Add `"outdated"` and `"available_releases"` to `__all__`.

- [ ] **Step 4: Run tests and gates**

Run: `uv run --locked pytest tests/unit -q && uv run --locked mypy src`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Add outdated(), the scopes whose release moved on the server

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 10: `scripts/gen_dicionario.py` and the `sinan_hanseniase` pilot

**Files:**
- Create: `scripts/gen_dicionario.py`, `src/omnisus_db/data/dicionarios/sinan_hanseniase.yaml`, `tests/fixtures/dbc/sinan_hanseniase_br_2026.dbc` (+ `.json` sidecar), `docs/sources/sinan_hanseniase.md`, `tests/integration/test_sinan_hanseniase_e2e.py`
- Modify: `src/omnisus_db/sources/datasus_ftp/datasets.py`, `scripts/build_fixtures.py`, `tests/unit/test_public_api.py` (`_FIXTURE_FOR`), `tests/support/dbf.py` (`DBC_CASES`), `tests/fixtures/dbf/manifest.json` (if the conftest manifest lists fixtures), `docs/datasets.md`, `mkdocs.yml`

**Interfaces:**
- Produces: registry row `sinan_hanseniase` (prefix `HANS`, national, `FINAIS` 2001–, `prelim_dir` PRELIM); `scripts/gen_dicionario.py <name> <path.dbc> --title … --dictionary-url …` writing a physical-inventory YAML.

- [ ] **Step 1: Write the generator**

```python
"""Write a physical-inventory dictionary YAML from one DATASUS DBC file.

The YAML records what the file physically contains — field names, DBF types
mapped to Frictionless types — and says so in ``x-evidence``. It is the
starting point for every new dataset row; semantic curation is a later,
separate act (docs/dicionario/consumo.md).

    uv run --locked python scripts/gen_dicionario.py sinan_hanseniase HANSBR26.dbc \
        --title "SINAN — Hanseníase, notificações nacionais" \
        --source-url ftp://ftp.datasus.gov.br/dissemin/publicos/SINAN/DADOS/PRELIM/HANSBR26.dbc \
        --dictionary-url https://portalsinan.saude.gov.br/images/documentos/Agravos/Hanseniase/DIC_DADOS_Hanseniase_v5.pdf \
        --identity nu_ano id_agravo A309
"""

from __future__ import annotations

import argparse
import datetime as dt
import struct
from pathlib import Path

import datasus_dbc
import yaml

_TYPES = {"C": "string", "D": "date", "L": "boolean", "M": "string", "F": "number"}


def fields_of(dbf: bytes) -> list[dict[str, str]]:
    n, header_len, _ = struct.unpack("<IHH", dbf[4:12])
    out, pos = [], 32
    while dbf[pos] != 0x0D:
        name = dbf[pos : pos + 11].split(b"\0")[0].decode("latin-1").lower()
        kind, width, decimals = chr(dbf[pos + 11]), dbf[pos + 16], dbf[pos + 17]
        if kind == "N":
            ftype = "integer" if decimals == 0 else "number"
        else:
            ftype = _TYPES.get(kind, "string")
        out.append({"name": name, "type": ftype})
        pos += 32
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name")
    ap.add_argument("dbc", type=Path)
    ap.add_argument("--title", required=True)
    ap.add_argument("--source-url", required=True)
    ap.add_argument("--dictionary-url", required=True)
    ap.add_argument("--identity", nargs=3, metavar=("YEAR_COLUMN", "CODE_COLUMN", "CODE"))
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    dbf = datasus_dbc.decompress_bytes(args.dbc.read_bytes())
    fields = fields_of(dbf)
    doc: dict = {
        "name": args.name,
        "title": args.title,
        "profile": "tabular-data-resource",
        "encoding": "latin-1",
        "x-version": "1.0.0",
        "x-source-format": "dbc",
        "x-partitions": ["_source_ano"],
        "x-evidence": {
            "physical_schema": f"{args.dbc.name}, {len(fields)} fields; observed {dt.date.today().isoformat()}",
            "semantic_status": "Physical inventory; individual semantic fields not audited. No inferred category mappings.",
            "dictionary_url": args.dictionary_url,
            "source_url": args.source_url,
        },
        "schema": {"fields": fields},
    }
    if args.identity:
        year_column, code_column, code = args.identity
        doc["x-identity"] = {"year_column": year_column, "code_column": code_column, "code": code}
    out = args.out or Path("src/omnisus_db/data/dicionarios") / f"{args.name}.yaml"
    out.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"wrote {out} ({len(fields)} fields)")


if __name__ == "__main__":
    main()
```

Add a unit test `tests/unit/scripts/test_gen_dicionario.py` that builds a DBF with `make_dbf([("NU_ANO","C",4,0),("QT","N",5,0),("VL","N",6,2),("DT","D",8,0)], …)`, patches `datasus_dbc.decompress_bytes` to identity, runs `fields_of`, and asserts `[{"name":"nu_ano","type":"string"},{"name":"qt","type":"integer"},{"name":"vl","type":"number"},{"name":"dt","type":"date"}]`. Run it, see it pass, falsify (swap integer/number), restore.

- [ ] **Step 2: Register the row and generate the YAML from the real file**

Row (national, both directories):

```python
    Dataset(name="sinan_hanseniase", prefix="HANS", ftp_dir=_SINAN_FINAIS, prelim_dir=_SINAN_PRELIM, cadence="yearly", partition_by=("_source_ano",), coverage=((2001, 1), None), geography="national"),
```

Download once (610,149 bytes, preliminary 2026 — the smallest file, and it exercises the preliminary path): add to `build_fixtures.TARGETS` the entry `("sinan_hanseniase", ScopeKey(uf=None, ano=2026), "sinan_hanseniase_br_2026.dbc")` and run `uv run --locked python scripts/build_fixtures.py`. Then:

```bash
uv run --locked python scripts/gen_dicionario.py sinan_hanseniase tests/fixtures/dbc/sinan_hanseniase_br_2026.dbc \
  --title "SINAN — Hanseníase, notificações nacionais" \
  --source-url ftp://ftp.datasus.gov.br/dissemin/publicos/SINAN/DADOS/PRELIM/HANSBR26.dbc \
  --dictionary-url https://portalsinan.saude.gov.br/images/documentos/Agravos/Hanseniase/DIC_DADOS_Hanseniase_v5.pdf \
  --identity nu_ano id_agravo A309
```

Expected output: `wrote … (63 fields)`. Write the sidecar `tests/fixtures/dbc/sinan_hanseniase_br_2026.json` with `source_uri`, `acquired_at`, `sha256` (`shasum -a 256`), `bytes`, `scope: "national preliminary 2026"`, `records` (from the DBF header) and the same `note` as the Chagas sidecar. Add `"sinan_hanseniase": ("sinan_hanseniase_br_2026", ScopeKey(uf=None, ano=2026))` to `_FIXTURE_FOR`, and the pair to `DBC_CASES` if that list drives a parametrised test; update `tests/fixtures/dbf/manifest.json` the same way the Chagas fixture is listed.

- [ ] **Step 3: Run the offline suite, docs and probe**

Run: `uv run --locked pytest tests/unit -q` — `test_public_api` now imports the hanseníase fixture through the full pipeline; the identity check passes only if the mode of `nu_ano` is 2026 and of `id_agravo` is `A309` (the report's sample says so for 2023/2025; this proves it for 2026).
Run: `uv run --locked python scripts/gen_datasets_doc.py && uv run --locked frictionless validate src/omnisus_db/data/dicionarios/sinan_hanseniase.yaml`
Run: `uv run --locked pytest tests/integration/test_registry_probe.py -m integration -q -k hanseniase`
Expected: PASS.

- [ ] **Step 4: e2e test and docs page**

```python
# tests/integration/test_sinan_hanseniase_e2e.py
"""Live: one final and one preliminary year through the same row, then outdated() is empty."""

import pytest

import omnisus_db as odb

pytestmark = [pytest.mark.integration, pytest.mark.e2e]


def test_final_and_preliminary_years_share_one_table(tmp_path):
    releases = odb.available_releases("sinan_hanseniase", refresh=True)
    final = max(s for s, r in releases.items() if r == "final")
    prelim = max(s for s, r in releases.items() if r == "prelim")
    target = f"ducklake:{tmp_path}/hans.ducklake"
    report = odb.import_dataset("sinan_hanseniase", scopes=[final, prelim], target=target,
                                policy="skip_same", run_id="pilot", batch_size=1, concurrency=1)
    assert not report.failed and len(report.ok) == 2
    with odb.Lake.local(target) as lake:
        rows = {r["scope"].ano: r["release"] for r in lake.publications()}
        assert rows == {final.ano: "final", prelim.ano: "prelim"}
        by_release = dict(lake.connect().execute(
            "SELECT _source_release, count(*) FROM lake.sinan_hanseniase GROUP BY 1").fetchall())
        assert set(by_release) == {"final", "prelim"}
        assert odb.outdated("sinan_hanseniase", lake=lake) == []
```

Run it once: `uv run --locked pytest tests/integration/test_sinan_hanseniase_e2e.py -q` (two downloads, ~2.5 MB). Expected: PASS.

`docs/sources/sinan_hanseniase.md`: copy the structure of `docs/sources/sinan_chagas.md` as rewritten in Task 11 (discover with `available_releases`, import, `outdated`, interpretation caveats: notifications ≠ cases; final/preliminary meaning; official dictionary link). Add it to `mkdocs.yml` nav.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Add sinan_hanseniase, the first row published in two release directories

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 11: Documentation, ADR amendment, handoff and CHANGELOG

**Files:**
- Modify: `docs/decisions/0002-registry-as-catalog.md` (append), `docs/architecture.md`, `docs/sources/sinan_chagas.md`, `docs/sources/sim_obitos.md`, `docs/sources/sinasc_nascidos_vivos.md`, `docs/guides/inventory.md`, `docs/guides/reprocessing-and-maintenance.md`, `docs/api.md`, `docs/index.md`, `README.md`, `CHANGELOG.md`, `reports/2026-09-11-handoff-omnisus-app.md` (append a dated note only)

- [ ] **Step 1: ADR 0002 amendment (append)**

```markdown
## Amendment 2026-09-12 — release directories share a row; names are readable

DATASUS publishes preliminary files beside the final ones under the same
names (SIM, SINASC, SINAN, e-SUS Notifica; verified live 2026-09-11/12) and
the layout does not change at that boundary. Decision 2 splits rows on
*schema*, so a publication status is not a new row: the row declares
`prelim_dir`, discovery reads both directories, every lake row carries
`_source_release`, and `outdated()` names the scopes whose release moved.
Eras with different columns in different directories still split.

Row names are `<sistema>_<conteúdo>` in full Portuguese words matching the
DATASUS file-type description. `ALIASES` and `get_config()` were removed;
there is no compatibility surface. Spec:
`docs/superpowers/specs/2026-09-12-datasus-release-directories-design.md`.
```

- [ ] **Step 2: Source pages and guides**

`docs/sources/sinan_chagas.md`: rewrite the first section — the product covers `FINAIS` (2000–2022 today) and `PRELIM` (2023– today); the integrity contract paragraph replaces the per-record rule with the `x-identity` mode rule ("o `nu_ano` mais frequente deve ser o ano do arquivo e o `id_agravo` mais frequente deve ser `B571`; registros isolados fora do ano são preservados"); add the `outdated()` example:

```python
with odb.Lake.local("ducklake:./chagas.ducklake") as lake:
    moved = odb.outdated("sinan_chagas", lake=lake)
odb.import_dataset("sinan_chagas", scopes=moved, target="ducklake:./chagas.ducklake",
                   policy="replace", run_id="chagas-final-2026")
```

`docs/sources/sim_obitos.md` and `sinasc_nascidos_vivos.md`: add a "Dados preliminares" section stating the PRELIM directory, that `available_releases()` shows the release, that rows carry `_source_release`, and the `outdated()` recipe. `docs/guides/inventory.md`: the `Release` column. `docs/guides/reprocessing-and-maintenance.md`: "Quando um ano passa de preliminar a final" → `outdated` + `replace`. `docs/architecture.md`: replace the Chagas paragraph with the generic release structure and the `_source_release` reserved column. `docs/api.md`: `available_releases`, `outdated`, `import_cnes_estabelecimentos`.

- [ ] **Step 3: CHANGELOG and handoff note**

Under `## Unreleased`, add a `### Changed` block:

```markdown
### Changed

- **Every dataset is renamed to its readable DATASUS name** (`sim_do` → `sim_obitos`,
  `sinasc_nv` → `sinasc_nascidos_vivos`, `sih_rd` → `sih_aih_reduzida`,
  `sia_bi` → `sia_bpa_individualizado`, `sia_am` → `sia_apac_medicamentos`,
  `sia_aq` → `sia_apac_quimioterapia`, `sia_atd` → `sia_apac_tratamento_dialitico`,
  `sia_ad` → `sia_apac_laudos_diversos`, `sia_abo` → `sia_apac_cirurgia_bariatrica`,
  `sia_ps` → `sia_psicossocial`, `cnes_st` → `cnes_estabelecimentos`,
  `sinan_chagas_prelim` → `sinan_chagas`, `ibge_pop` → `ibge_populacao`;
  `import_cnes_st` → `import_cnes_estabelecimentos`). No aliases are kept.
  Lake tables carry the new names: rebuild existing lakes into a new target.
- Final and preliminary DATASUS directories are one dataset: rows declare
  `prelim_dir`, `available_releases()` shows where each scope is, every row
  carries `_source_release`, `publications()` exposes `release`, and
  `outdated()` lists the scopes whose year moved to final (re-import with
  `policy="replace"`). SIM and SINASC 2025–2026 preliminary files are now
  discoverable.
- Source identity is declared in the dictionary (`x-identity`) and checked
  by one rule for every row; the Chagas-specific validator is gone.

### Added

- `sinan_hanseniase` (SINAN HANS, 2001–, final and preliminary).
- `scripts/gen_dicionario.py`: physical-inventory YAML from one DBC file.
```

Append to `reports/2026-09-11-handoff-omnisus-app.md` a section `## Adendo 2026-09-12 — nomes` with the same rename table and the sentence that no alias exists and lakes are rebuilt.

- [ ] **Step 4: Full verification**

Run: `uv run --locked pytest tests -m 'not e2e and not perf' -q && uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked mypy src && uv run --locked python scripts/gen_datasets_doc.py --check && uv run --locked mkdocs build --strict && uv run --locked pre-commit run --all-files`
Expected: all PASS. `git grep -n -e "sinan_chagas_prelim" -e "import_cnes_st" -e "ALIASES" -- src tests scripts notebooks docs/*.md docs/sources docs/guides mkdocs.yml README.md CHANGELOG.md` prints only the CHANGELOG rename lines.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Document release directories, readable names and outdated()

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## Self-review against the spec

- §3.1 `prelim_dir`/`directories()` → Task 2. §3.2 `decode_for`, union listing, duplicate error, `available_releases`, CLI column → Tasks 3–4. §3.3 fetch from listing, no try-both → Task 5 (release resolved once per run; pure `ftp_path_for`). §3.4 `_source_release`, `release` in `publications()`, no manifest change → Task 6. §3.5 `outdated()` → Task 9. §3.6 `x-identity` → Task 8. §3.7 names, aliases deleted, rebuild note, docs column, probe over union → Tasks 1, 2, 7, 11. §3.8 pilot → Task 10. §4 errors → Tasks 4, 5, 6, 8, 9. §5 tests incl. falsification → Global Constraints + every task.
- Deviation from the spec recorded here: the spec's §3.3 has `ftp_path_for` consult the listing itself; the plan resolves the release map once in the runner and keeps `ftp_path_for` pure, because the runner's unit tests patch only `fetch_dbc_bytes` and a listing inside every fetch would be one LIST per producer on a cache miss. Same observable behaviour: directory from the listing, 550 → skipped.
- Names used consistently: `Release`, `prelim_dir`, `directories()`, `release_from_uri`, `decode_for`, `available_releases`, `release_map`, `ftp_path_for(d, scope, release)`, `validate_identity`, `outdated`, `import_cnes_estabelecimentos`, `ibge_populacao`.
