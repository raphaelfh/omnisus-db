# Researcher guide and per-database notebooks — design

Date: 2026-09-13. Status: approved section by section (1–5) by Raphael;
implementation pending. Branch: `worktree-guia-pesquisador` (worktree
`.claude/worktrees/guia-pesquisador`, created from `origin/main` at `827d7a7`).

## Goal

A researcher who has never used omnisus-db should be able to pick the open
database that answers their question, understand what one record means and
which pitfalls apply, import a small slice, analyse it and keep a provenance
record — through a documented, didactic path in Portuguese.

## Decisions taken with Raphael

| # | Decision | Rejected |
| --- | --- | --- |
| D1 | The guide and the per-database material are in **Portuguese**; API, architecture and existing English guides stay in English as reference. | English only (harder for the main audience); bilingual pages (two copies that drift). |
| D2 | **Python end to end**, in marimo notebooks. | Acquisition in Python/CLI with analysis in any tool; CLI only. |
| D3 | Eight databases, **one notebook each**: SIM, SINASC, SIH, SIA, CNES, IBGE population, SINAN, medicines. | Core set only; all 14 products at equal depth. |
| D4 | SINAN and medicines stay **within what the package imports today**: SINAN = `sinan_chagas` and `sinan_hanseniase`; medicines = SIA-APAC medicamentos + Hórus stock, stating that no public dispensing-event source exists (`reports/2026-09-12-sinan-e-dispensacao.md`). | Expanding the registry or looking for a dispensing source first (done separately; see that report). |
| D5 | **Approach 1**: a guide section on the site plus one notebook per database with a fixed structure; profiles improved in place. | Notebooks only (profiles unreadable before installing, not searchable); one parameterised notebook (base-specific analyses and pitfalls turn into `if` chains). |

## 1. Structure

### Notebooks (moved with `git mv`)

```text
notebooks/
  README.md                     short index: three folders, how to open, suggested order
  bases/
    _comum.py                   boilerplate only (see §2)
    sim_obitos.py               ← api_dados_reais.py (SIM analysis; its transaction section is dropped)
    sinasc_nascidos_vivos.py    new
    sih_aih_reduzida.py         new
    sia.py                      new — one of the 7 SIA tables, chosen in the notebook
    cnes_estabelecimentos.py    new
    ibge_populacao.py           new
    sinan.py                    ← sinan_chagas.py, plus hanseníase
    medicamentos.py             ← medicamentos.py
  explorar/
    panorama_datasus.py, _acervo/, inventario_dados_reais.py
  desenvolvimento/
    api_cenarios.py, performance_dbf.py, _performance_dbf.py, metadados_cli.py
```

- Six notebooks resolve the repository root with `Path(__file__).resolve().parent.parent`;
  after the move they use `parents[2]`. Data stays under `data/lake/` (ignored by Git).
- Verified 2026-09-13 with marimo 0.23.16: `marimo export` and `python notebook.py`
  put the notebook's own folder on `sys.path`, so a helper next to its notebook
  imports without `sys.path.insert`. The inserts in `panorama_datasus.py` and
  `performance_dbf.py` are removed. Re-check after the marimo 0.24 bump (PR #4).
- `api_cenarios.py` already teaches transactions and rollback, so the SIM notebook
  does not duplicate that section.

### Documentation

```text
docs/
  pesquisa/
    index.md                Comece aqui
    indicadores.md          numerator/denominator, residence vs occurrence, rates
    reprodutibilidade.md    run_id, pinned snapshot, provenance, how to cite
  sources/<dataset>.md      8 existing pages improved in place, plus new sia.md
```

- The site is public; page addresses under `docs/sources/` do not change.
- `mkdocs.yml` nav: a "Guia do pesquisador" tab right after Home with Comece aqui,
  Bases (the source pages, SIA included), Indicadores, Reprodutibilidade. The
  separate "Sources" tab is removed from the nav only.
- README: the notebooks table becomes a Portuguese "Para pesquisadores" section
  pointing to `docs/pesquisa/` and `notebooks/bases/`.

Rejected: profile copies under `docs/pesquisa/bases/` (break public links or
duplicate pages); a top-level `pesquisa/` folder (not published by the site).

## 2. Notebook skeleton

### One shared research lake

Every notebook in `bases/` defaults to `data/lake/pesquisa/dados.ducklake` (shown
and editable). Each run keeps `plano.json`, the import result and the provenance
record in `data/lake/pesquisa/execucoes/<run_id>/`. The data root can be overridden
with `OMNISUS_NOTEBOOK_DATA`. SIM and IBGE in the same lake is what makes a rate
possible; `skip_same` prevents duplicate imports; `LakeReader` reads without the
writer lock.

Rejected: a fresh lake per run (the current notebooks' pattern) — cannot combine
databases and copies storage each time.

### The same six steps

The header cell says what the notebook teaches, that opening it downloads nothing,
and links to the database profile.

1. **O que a base registra** — short summary linking to the profile; the profile is
   the cited source, the notebook does not repeat its claims.
2. **Descobrir** — a button calls `odb.available(..., refresh=True)`; SINAN also shows
   `available_releases` (final vs preliminary).
3. **Planejar e importar** — a form with a small default slice fixes the plan with a
   `run_id` and saves `plano.json`; a second button runs
   `import_dataset(..., policy="skip_same", run_id=..., concurrency=1)` with a 25 MiB
   payload cap, handling `ImportAbortedError`.
4. **Conferir** — `LakeReader`: `publications(run_id=)`, persisted row count against
   the import report, `outdated()`.
5. **Analisar** — visible SQL over a pinned `snapshot_id`.
6. **Guardar** — CSV download plus `proveniencia.json` (plan, publications,
   `snapshot_id`, SQL, `omnisus_db.__version__`).

Every notebook accepts `-- --executar true` to run the button-gated steps
unattended (the pattern already used by `inventario_dados_reais.py` through
`mo.cli_args()`), for the end-to-end validation in §5.

### `notebooks/bases/_comum.py`

Boilerplate only: the data root (with the environment override), a new run folder,
JSON saving, the outcomes table from an `ImportReport`, the provenance record, and
reading the `executar` flag. Library calls (`available`, `import_dataset`,
`LakeReader`, `publications`, `outdated`) stay visible in the cells.

Rejected: a helper that wraps discover-and-import — it hides exactly what the
notebook teaches.

### Per notebook

Fields verified present in the packaged dictionaries on 2026-09-13; file sizes from
the live FTP listing on the same date.

| Notebook | Default slice | Step 5 analysis |
| --- | --- | --- |
| `sim_obitos` | RR 2023 (282 KB) | deaths by month (`dtobito`), sex (`sexo`), underlying cause (`causabas`); residence (`codmunres`) vs occurrence (`codmunocor`) |
| `sinasc_nascidos_vivos` | RR 2022 (626 KB) | births by municipality of residence (`codmunres`); low birth weight (`peso`); prenatal visits (`consultas`); type of delivery (`parto`) |
| `sih_aih_reduzida` | RR, one month (~220 KB) | admissions by principal diagnosis (`diag_princ`), length of stay (`dias_perm`), in-hospital deaths (`morte`), total value (`val_tot`); an AIH record is not a patient |
| `sia` | chosen table, RR, one month (≤ 870 KB) | APAC medicamentos: `ap_pripal`, `ap_vl_ap`; BPA-I: `proc_id`, `qt_aprov`; psicossocial: `pa_proc_id`, `cidpri`. The other four tables show dictionary and row count until their analysis fields are verified |
| `cnes_estabelecimentos` | RR, one month (55 KB) | facilities by type (`tp_unid`) and municipality (`codufmun`) per competence (`competen`); the dictionary declares 12 columns |
| `ibge_populacao` | census 2022 (no inventory step) | population by municipality (`ibge_populacao` view: `codigo_ibge`, `ano`, `populacao`); if `sim_obitos` is in the same lake, deaths per 100 000 after checking the municipality code format on the data |
| `sinan` | Chagas 2022 (~400 KB) or hanseníase 2023 (~1.9 MB), national | notifications by `sg_uf_not` and `id_mn_resi`; Chagas: `classi_fin`, `evolucao`; hanseníase: `modoentr`, `tpalta_n` (`classoper` is not in the dictionary). A notification is not a case |
| `medicamentos` | SIA-APAC medicamentos RR, one month (~75 KB) + one Hórus page | APAC by main procedure and approved value; one stock page; section "o que não existe publicamente" citing the 2026-09-12 report |

## 3. Profiles and cross-cutting pages

### Profile template — `docs/sources/<dataset>.md`, Portuguese, same headings on all 9 pages

1. **Em uma frase** — what the database is and who produces it.
2. **O que um registro representa** — the unit of record; for SIA, one line per table.
3. **Datas e geografia** — which date answers which question; residence vs
   occurrence or notification.
4. **Cobertura e modalidade** — link to `docs/datasets.md`; final vs preliminary via
   `available_releases()`.
5. **Armadilhas** — only claims with a citation or evidence verified in the repo.
   An uncited claim is not published. A short "Em aberto" list appears only where a
   researcher would otherwise assume the wrong thing.
6. **Como usar** — minimal code (`available` → `import_dataset` → `LakeReader`) and a
   link to the notebook.
7. **Fontes** — official documents with URL, date consulted, and SHA-256 when archived
   in `docs/dicionario/fontes/registro.json`.

Existing technical contracts (integrity checks, IBGE temporal references, SINAN
final vs preliminary) remain on each page under a closing "Detalhes técnicos"
section; IBGE's is translated so each page has one language.

Available official sources (registro.json, verified 2026-09-13): SIM
`Estrutura_do_SIM_2025.pdf`; SINASC `Estrutura_SINASC_para_CD.pdf`; SIH
`IT_SIHSUS_1603.pdf`; SIA `Informe_Tecnico_SIASUS_2019_07.pdf` (check for a newer
edition before citing); CNES `IT_CNES_1706.pdf`; IBGE `Pop_Residente_TCU_ate_2023.pdf`
plus the 7 URLs already on its page; SINAN `DIC_DADOS_Chagas_v5.pdf`,
`DIC_DADOS_Notificacao_Individual_v5.pdf`, `DIC_DADOS_Hanseniase_v5.pdf`; medicines:
its page's sources and the 2026-09-12 report.

### `docs/pesquisa/index.md` — Comece aqui

- Setup from a checkout: `uv sync --locked --extra notebooks`, then open the first
  notebook. PyPI is mentioned only once publishing works.
- "Qual base responde minha pergunta?": kind of question → database → notebook → profile.
- The six notebook steps explained once; the shared lake.
- General cautions: preliminary files, records are not people, one writer at a time.

### `docs/pesquisa/indicadores.md`

Numerator and denominator; residence vs occurrence or notification; IBGE population
(census vs estimate, `ESTIMATE_UNAVAILABLE_YEARS`); checking the municipality code on
the data before joining; a complete worked example (deaths per 100 000 from SIM + IBGE
in the shared lake). Indicator definitions cite an official source (for example
RIPSA), with the URL verified during implementation.

### `docs/pesquisa/reprodutibilidade.md`

Choose `run_id` before importing and use `skip_same`; read `publications()` (hash,
URI, release, parser version); pin with `LakeReader(target, snapshot_id=...)`;
`outdated()` shows when DATASUS revised a file; a citation template with file, URI,
SHA-256, access date, `omnisus_db` version and `snapshot_id`.

Rejected: a separate limitations page (limitations belong next to their database);
pages mixing a Portuguese profile with English technical sections.

## 4. Groundwork

1. Remove the 6 tracked files in `.playwright-mcp/` (already listed in `.gitignore`).
2. `git mv benchmarks-baseline.json profile-timings.txt reports/` — nothing references
   the first; the second is mentioned only historically.
3. `marimo` leaves `[project] dependencies`. The pin stays once, in the `notebooks`
   extra, and `dev` includes `"omnisus-db[notebooks]"` so CI (`--extra dev`) still
   installs it: `tests/unit/notebooks/test_sinan_inventory.py` imports marimo. Confirm
   uv resolves the self-referencing extra with `uv lock`. CHANGELOG tells users to
   install `[notebooks]`. Rejected: `pytest.importorskip("marimo")` (CI would skip the
   test silently).
4. Read-only cells use `LakeReader`: `explorar/inventario_dados_reais.py`,
   `desenvolvimento/api_cenarios.py` (including its recipes) and `docs/index.md`. The
   new `bases/` notebooks use it from the start. The write in
   `test_sinan_inventory.py` keeps `Lake.local`.
5. Moves from §1: `parents[2]`; the `sys.path.insert` calls go; the three notebook
   tests get new paths; `api_dados_reais.py` is removed once `bases/sim_obitos.py`
   absorbs it.
6. `pyproject.toml`: `"notebooks/**/*.py" = ["B018", "N803"]`; the inline
   `# ruff: noqa` comments go.
7. `notebooks/README.md` shrinks from 293 lines to a short index. The operational text
   for the panorama and inventory notebooks moves into their first cell.
8. Nav per §1; `CHANGELOG.md` `## Unreleased` records the guide, notebooks and the
   marimo change.

Delivery: work in the worktree; rebase onto `main` after PR #4 (marimo 0.24) merges —
it changes only the `notebooks` extra bound and `uv.lock`. Deliver as a GitHub PR so
CI runs; ask Raphael before opening it (the repository is public).

## 5. Checks

1. **Opening downloads and writes nothing** — `tests/unit/notebooks/test_notebooks_abrem_offline.py`,
   parametrised over every notebook in `notebooks/**`. Helper modules are not notebooks:
   `_`-prefixed files (`_comum.py`, `_performance_dbf.py`) and everything under
   `_acervo/`. For every notebook: block `socket.socket.connect`, run `app.run()`, require
   no error. For `bases/` notebooks additionally: set `OMNISUS_NOTEBOOK_DATA` to
   `tmp_path` and require it to stay empty (the `explorar/` and `desenvolvimento/`
   notebooks keep their own data paths and write only behind buttons). Probe 2026-09-13 (marimo 0.23.16,
   in-process): a notebook with network behind a button completed and ran its async
   cells; a notebook downloading on open failed with the blocked socket. Falsify during
   implementation by removing a `mo.stop` gate and watching the test fail. A notebook in
   `explorar/` or `desenvolvimento/` that cannot open offline for a legitimate reason is
   named in the test with that reason.
2. **`marimo check --strict`** on the notebooks as a new step in `.github/workflows/test.yml`;
   confirm whether the command accepts a glob or needs an explicit file list.
3. **Guide structure** — `tests/unit/test_guia_pesquisador.py`: every `bases/` notebook is
   linked from Comece aqui and from its profile; every profile has the seven headings in
   order; "Fontes" contains at least one URL.
4. **Docs** — `mkdocs build --strict` locally before the PR (CI already runs it).
5. **Real end-to-end run** before the PR, manual and not in CI (DATASUS is a shared public
   server): all 8 `bases/` notebooks with `-- --executar true` on their default slices.
   Rows, sizes, time, publications and `snapshot_id` recorded in
   `reports/<data-da-execução>-guia-pesquisador-validacao.md`, named with the ISO date
   (`YYYY-MM-DD`) on which the run happens; every number the guide cites comes from
   that report.
6. **Adversarial claim review** before the PR: a fresh-context reviewer checks each claim
   in "O que um registro representa", "Datas e geografia", "Armadilhas" and the
   indicators page against the cited document (PDFs downloaded to a scratch directory,
   SHA-256 checked against `registro.json`). Unsupported claims are removed or moved to
   "Em aberto"; the result goes into the validation report.
7. Existing gates unchanged: ruff, ruff format, mypy, pytest with coverage ≥ 85%,
   `scripts/gen_datasets_doc.py --check`, pre-commit.

Rejected: running the end-to-end check in CI (repeated downloads from a public server on
every PR); checking claims by keyword matching (passes without proving anything).

## Verifications deferred to implementation

- uv resolves `dev = [..., "omnisus-db[notebooks]"]` (§4.3).
- `marimo check` accepts a glob (§5.2).
- `app.run()` behaves inside pytest as in the standalone probe (§5.1).
- marimo 0.24 keeps the notebook folder on `sys.path` (§1).
- A newer SIASUS technical report than 2019-07 (§3).
- The RIPSA (or other official) indicator definition URL (§3).
- Municipality code format in SIM and IBGE data before the join (§2, §3).
- Analysis fields for the four remaining SIA tables (§2).

## Out of scope

New datasets or SINAN agravos; the U2 metadata resolver; PyPI publishing; English
translations of the guide; changes to the library API.
