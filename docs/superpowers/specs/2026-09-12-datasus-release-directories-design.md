# DATASUS release directories: one structure for final and preliminary data

**Date:** 2026-09-12
**Status:** Approved in conversation; awaiting written review
**Evidence:** `reports/2026-09-12-sinan-e-dispensacao.md` (Parts 1 and 3)
**Amends:** ADR 0002 (registry as catalog)

## 1. Problem

DATASUS publishes "preliminary" files in a directory next to the final one,
with the same filenames and no overlap, and moves files between them without
notice. Observed live on 2026-09-11/12:

| Family | Final directory | Preliminary directory | Preliminary years |
|---|---|---|---|
| SIM | `/dissemin/publicos/SIM/CID10/DORES` | `/dissemin/publicos/SIM/PRELIM/DORES` | 2025–2026 (28 state files each) |
| SINASC | `/dissemin/publicos/SINASC/NOV/DNRES` | `/dissemin/publicos/SINASC/PRELIM/DNRES` | 2025–2026 |
| SINAN | `/dissemin/publicos/SINAN/DADOS/FINAIS` | `/dissemin/publicos/SINAN/DADOS/PRELIM` | per agravo; 13 agravos exist only as preliminary |
| e-SUS Notifica | `/dissemin/publicos/ESUSNOTIFICA/DADOS/FINAIS` | `/dissemin/publicos/ESUSNOTIFICA/DADOS/PRELIM` | 2024–2025 |

Layouts are identical across the boundary in every pair checked (SIM 87
fields, SINASC 61, e-SUS 109, six SINAN agravos). Layout changes happen inside
a directory (dengue: 107 → 67 → 121 fields, all in `FINAIS`), which the lake
already absorbs by widening tables.

Today the package handles this with one name-specific branch
(`_runner.py:144`, Chagas validation) and one registry row named after a
directory (`sinan_chagas_prelim`), and ignores it for SIM and SINASC:
`available("sim_do", years=[2025])` returns nothing and the researcher is not
told why. A second SINAN row cannot even be added: filenames are decoded by a
global prefix map, so two rows with the same prefix collide, and a hand-built
`Dataset` (ADR 0002's promise) finds no files at all.

## 2. Goals and non-goals

Goals:

- One structure, used by every FTP row, for a fact DATASUS applies to four
  families. No per-family module, no name-based branch.
- The researcher can always answer "which of my rows are preliminary?" in SQL
  and "which of my years moved to final?" in one call.
- Preliminary data is never converted to final silently.
- Naming convention: every row uses a full readable name (§3.7). No aliases,
  no compatibility shims: the repository rule is no dead code.

Non-goals (recorded, deferred):

- Unifying the state/national scope columns (`ano`, `uf` injected for state
  rows; `_source_ano` for national rows). The rename already rebuilds every
  lake, so this could ride along; it is left out because it changes the
  manifest's `scope_json` shapes the app decodes, and deserves its own design.
- Adding agravos beyond the pilot. Each is one row + one YAML under this
  structure; the pilot proves the structure.

## 3. Design

### 3.1 Registry row

`Dataset` gains one additive, keyword-only field:

```python
prelim_dir: str | None = None
"""Directory where DATASUS publishes this dataset's preliminary files, when
it has one. Same filenames as ``ftp_dir``; a file is in one or the other."""
```

`ftp_dir` stays the final directory, so ADR 0002's "`ftp_dir: str` survives"
holds. A helper `Dataset.directories() -> dict[Release, str]` returns
`{"final": ftp_dir}` plus `{"prelim": prelim_dir}` when set, where
`Release = Literal["final", "prelim"]`. Every consumer iterates this mapping;
a row without `prelim_dir` is the one-entry case, not a special case.

Rows that gain `prelim_dir` in this change: `sim_do`, `sinasc_nv`,
`sinan_chagas` (renamed, §3.7). A row may declare a final directory that
currently holds no file of its prefix (SINAN syphilis exists only as
preliminary); the probe (§3.7) checks the union.

### 3.2 Discovery: decode against the requested dataset

`filenames.parse_filename` is replaced by `decode_for(d: Dataset, name) ->
ScopeKey | None`, the inverse of `scope_to_filename` for one row. The global
`PREFIX_TO_DATASET` map and `decode(name)` are removed; the only remaining
caller that needs "which registered dataset owns this name" is the `browse`
CLI table, which uses the registry rows in turn.

`available(dataset, years=, refresh=)`:

1. lists each directory in `d.directories()` (one cached LIST each);
2. decodes every name with `decode_for(d, name)`;
3. raises `ValueError` if the same scope appears in two directories (never
   observed; must not be resolved by preference);
4. returns scopes sorted as today.

A new `available_releases(dataset, ...) -> dict[ScopeKey, Release]` exposes
the directory each scope was found in. `available` is `list(available_releases(...))`,
so there is one listing path. The `inventory` CLI gains a `Release` column.

### 3.3 Fetch: the directory comes from the listing

`fetch.ftp_path_for(d, scope)` looks the scope up in `available_releases(d)`
(cached listing; `refresh` only when the caller asks). If found, it returns
that directory; if not, it returns `ftp_dir` and the server's 550 marks the
scope `skipped`, exactly as today. No try-one-then-the-other on the wire.

### 3.4 Provenance: `_source_release`

Staging injects a reserved column `_source_release: string` (`final` /
`prelim`) on every FTP row, beside the existing scope columns. Rules mirror
`_source_ano`: a DBF that already has the column is rejected; the column is
not a partition key.

`publications()` adds a decoded `release` key derived from the stored
`source_uri` (the directory is already in it), so the manifest schema does not
change. Existing lakes keep working: old rows have `_source_release` NULL after
the widening `ALTER`, and `release` is `None` for manifests with a NULL URI.

Moving a year from preliminary to final is the existing `replace` policy;
`skip_same` keeps refusing a changed hash with "request replace explicitly".
No policy converts data on its own.

### 3.5 `outdated()`: the yearly operation

```python
def outdated(dataset, *, lake, refresh=False) -> list[ScopeKey]:
    """Scopes whose release in the lake differs from the server's current release."""
```

Joins the dataset's active publications (release from `source_uri`) with
`available_releases()`. Read-only. Composes with the existing pattern:

```python
odb.import_dataset("sim_do", scopes=odb.outdated("sim_do", lake=lake), policy="replace", run_id=...)
```

Scopes present in the lake but absent from the server are not returned; they
are a different fact (withdrawal) and stay visible through `publications()`.

### 3.6 Identity validation declared in the dictionary

The Chagas branch in `_runner.py` is replaced by one generic check driven by
an optional `x-identity` block in the dataset YAML:

```yaml
x-identity:
  year_column: nu_ano        # mode must equal the scope year
  code_column: id_agravo     # optional; mode must equal `code`
  code: B571
```

Rule: the most frequent value of `year_column` equals `scope.ano`; if
`code_column` is declared and present in the file, its most frequent value
equals `code`. The whole file is rejected otherwise. Verified in the report
against 20 real files, including layouts without `ID_AGRAVO` (pre-2007 dengue,
Chagas 2000) and files with a few thousand off-year records (tuberculosis).

Because the YAML hash is already part of `parser_version`, changing the rule
changes the publication version. Rows without the block (all current
non-SINAN rows) get no identity check, as today. The Chagas per-record rule
is dropped; `docs/sources/sinan_chagas.md` states the new rule.

### 3.7 Naming and catalog

Convention (recorded in the ADR amendment): a row name is
`<sistema>_<conteúdo>` in full Portuguese words, matching DATASUS's own
description of the file type, never the two-letter file prefix and never a
publication status. The name is the registry key, the lake table, the YAML
stem, the CLI name and the docs page. Every existing row is renamed:

| Current | New | DATASUS description (portal, 2026-09-10) |
|---|---|---|
| `sim_do` | `sim_obitos` | DO – Declarações de Óbito |
| `sinasc_nv` | `sinasc_nascidos_vivos` | DN – Declarações de nascidos vivos |
| `sih_rd` | `sih_aih_reduzida` | RD – AIH Reduzida |
| `sia_bi` | `sia_bpa_individualizado` | BI – BPA Individualizado (not in the captured list; DATASUS wording) |
| `sia_am` | `sia_apac_medicamentos` | AM – APAC de Medicamentos |
| `sia_aq` | `sia_apac_quimioterapia` | AQ – APAC de Quimioterapia |
| `sia_atd` | `sia_apac_tratamento_dialitico` | ATD – APAC Tratamento Dialítico |
| `sia_ad` | `sia_apac_laudos_diversos` | AD – APAC de Laudos Diversos |
| `sia_abo` | `sia_apac_cirurgia_bariatrica` | ABO – APAC Acompanhamento Pós Cirurgia Bariátrica |
| `sia_ps` | `sia_psicossocial` | PS – Psicossocial |
| `cnes_st` | `cnes_estabelecimentos` | ST – Estabelecimentos |
| `sinan_chagas_prelim` | `sinan_chagas` | CHAG – Doença de Chagas Aguda |

Consequences:

- `ALIASES`, `Dataset.aliases`, `get_config()` and the CLI's alias choices are
  deleted, with their tests. `import_cnes_st` becomes
  `import_cnes_estabelecimentos`; `_NON_FTP` CLI names follow the same rule
  (`ibge_pop` → `ibge_populacao`).
- Lake tables carry the new names. There is no adoption of old tables
  (rebuild-only migration rule): a lake built before this change is rebuilt
  into a new target. The CHANGELOG states this and the app handoff is updated
  with the name table.
- YAML stems, `docs/sources/*.md`, fixture file names, notebooks and guides are
  renamed in the same change; `x-source-prefix` in the YAML keeps the DATASUS
  prefix, which is where the short code now lives.
- `products()` keeps one entry per row; `Product` gains nothing.
- `docs/datasets.md` (generated) gains a "Preliminary directory" column.
- Tier 3 probe: one LIST per distinct directory across all rows; "holds files
  with this prefix" checks the union; "earliest file" and "not stale" use the
  union too, so the coverage window is the dataset's, not one directory's.

### 3.8 Pilot

`sinan_hanseniase` (`HANS`, `FINAIS` 2001–2023, `PRELIM` 2024–2026, 63 fields
throughout, code `A309`): one row, one YAML with `x-identity`, one fixture per
layout, e2e test importing one final and one preliminary year and then
`outdated()` returning `[]`.

## 4. Error handling

- Same scope in two directories → `ValueError` at discovery, before any fetch.
- `x-identity` names a column absent from the file: `year_column` absent →
  reject; `code_column` absent → skip the code check (layouts predate the
  column).
- DBF with a native `_source_release` column → reject (reserved), as for
  `_source_ano`.
- `outdated()` on a lake without the dataset → empty list, not an error.

## 5. Testing

- Unit: `decode_for` round-trip per row (golden test extended); duplicate
  scope across directories raises; `available_releases` with a fake listing;
  `ftp_path_for` picks the listed directory; staging injects
  `_source_release`; `x-identity` mode rule on synthetic DBFs with and without
  the code column; `outdated()` join cases (moved, unchanged, absent).
- Falsification (per project rule): each new test is broken once on purpose
  and seen to fail before it counts.
- Integration (manual/cron): probe over the union; hanseníase e2e.
- Docs: `gen_datasets_doc --check`, mkdocs strict.

## 6. Files touched

`datasets.py`, `filenames.py`, `inventory.py`, `fetch.py`, `_runner.py`,
`staging.py`, `lake/publication.py` (`publications()` release key), new
`outdated` in `omnisus_db/__init__.py`, `cli/main.py` (inventory column),
`products.py` (none), `sources/sinan/chagas.py` (removed),
`sources/cnes/importers/st.py` (renamed function), every
`data/dicionarios/<row>.yaml` (renamed; `sinan_chagas.yaml` also gains
`x-identity`), new `sinan_hanseniase.yaml`, `scripts/gen_datasets_doc.py`,
`scripts/build_fixtures.py` (targets and fixture names), `tests/…`
(including deletion of alias tests), `docs/datasets.md`, every
`docs/sources/<row>.md`, new `docs/sources/sinan_hanseniase.md`, guides and
notebooks that name rows, `docs/decisions/0002-registry-as-catalog.md`
(amendment), `docs/architecture.md`,
`reports/2026-09-11-handoff-omnisus-app.md` (name table), `CHANGELOG`.

## 7. Rejected

- **Separate `_final`/`_prelim` rows.** Breaks the weekly probe every year and
  lets a year be counted twice across two tables (report §3.2).
- **Directory list without a recorded release.** The main researcher question
  becomes unanswerable in SQL and is lost on export.
- **Per-family importer modules.** Three copies of the same directory logic
  and a module per agravo.
- **Automatic upgrade policy.** Silent conversion of preliminary data.
- **Merging with final-over-preliminary precedence** (microdatasus style).
  A year in both directories is an error here, not a choice.
