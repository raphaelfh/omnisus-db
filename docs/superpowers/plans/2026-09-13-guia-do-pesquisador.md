# Guia do pesquisador — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A researcher new to omnisus-db picks an open database, understands one record and its pitfalls, imports a small slice, analyses it and keeps a provenance record, through Portuguese profiles, three guide pages and one marimo notebook per database.

**Architecture:** Notebooks move into `notebooks/bases/` (one per database, same six steps), `explorar/` and `desenvolvimento/`. The `bases/` notebooks share a small `_comum.py` for files and counts. They write to one research lake behind buttons and read only through `LakeReader`. Nine profiles in `docs/sources/` follow one seven-heading template, and `docs/pesquisa/` adds Comece aqui, Indicadores and Reprodutibilidade. Three pytest checks guard the result: opening a notebook downloads and writes nothing, the notebook check passes, and the guide keeps its structure. A manual end-to-end run and an adversarial claim review close the work.

**Tech Stack:** Python ≥ 3.12, marimo 0.23.16 (`notebooks` extra), DuckDB/DuckLake through `omnisus_db`, Polars, pytest, MkDocs Material, uv.

**Spec:** `docs/superpowers/specs/2026-09-13-guia-do-pesquisador-design.md` (commit `4e7710d`). Read it before any task.

## Global Constraints

- The guide, profiles, notebook text and notebook variable names are in **Portuguese**; `docs/api.md`, `docs/architecture.md`, `docs/guides/*` and tests stay in English.
- **No change under `src/`.** The library API is out of scope.
- marimo leaves `[project] dependencies`. It is pinned once, in the `notebooks` extra (`"marimo>=0.23.16,<0.24"` until PR #4 merges), and `dev` includes `"omnisus-db[notebooks]"`.
- Opening any notebook **opens no network connection**; opening a `bases/` notebook **writes nothing**. Every network call or write sits behind `mo.ui.run_button` and `mo.stop(not (executar or <botão>.value), ...)`.
- `bases/` notebooks default to the lake `ducklake:<raiz>/dados.ducklake`, where `<raiz>` is `data/lake/pesquisa` in the repository or `$OMNISUS_NOTEBOOK_DATA`; each run gets `<raiz>/execucoes/<run_id>/`.
- FTP imports in `bases/` use `policy="skip_same"`, the plan's `run_id`, `concurrency=1`, `max_payload_bytes=max_inflight_bytes=25 * 1024 * 1024`.
- Reading a lake uses `odb.LakeReader`; `odb.Lake.local` only when writing.
- DATASUS is never contacted from CI or unit tests. The end-to-end run is manual.
- A profile claim about meaning, dates, geography or pitfalls is published **only with a citation** (document + page or section) or evidence verified in the repository; otherwise it goes to "Em aberto" or is dropped.
- Links from `docs/` to notebooks use absolute GitHub URLs (`https://github.com/raphaelfh/omnisus-db/blob/main/notebooks/...`): `mkdocs build --strict` rejects relative links that leave `docs/`.
- Ruff line length 99; after editing Python run `uv run ruff check --fix <paths>` and `uv run ruff format <paths>`.
- Every commit message ends with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Work only in the worktree `.claude/worktrees/guia-pesquisador`. Never `git -C` into the main checkout, never bare `git stash`. Ask Raphael before opening the PR.

## Environment

Run every command from the worktree root. Sync once (after Task 1 `dev` brings marimo):

```bash
uv sync --locked --extra dev --extra docs
```

`uv run` syncs inexactly, so the extras stay installed.

## Verifications already done (2026-09-13, while planning)

| Spec item | Result |
| --- | --- |
| uv resolves `dev = [..., "omnisus-db[notebooks]"]` | Yes. `uv lock` on a scratch copy: 162 packages; `uv export --extra dev` contains `marimo==0.23.16`, base export contains no marimo. |
| `marimo check` accepts a glob | Takes files **or a folder**. `marimo check --strict notebooks` fails on helper modules ("not a valid notebook"); `marimo check --strict --ignore-scripts notebooks` exits 0. |
| `app.run()` inside pytest | Gated notebook passes with `socket.socket.connect` blocked; the same notebook without `mo.stop` fails with the blocked socket. |
| Current notebooks open offline | All 8 open with `socket.socket.connect` blocked (api_cenarios 0.9 s, metadados_cli 2.4 s, others < 0.2 s). |
| `skip_same` on an identical re-import | Outcome `skipped`, reason `same source and parser version already published`; a different source or parser version is `failed` ("request replace explicitly"). |
| Scope columns in FTP tables | State files: `ano`, `uf`, plus `mes` when monthly. National files: `_source_ano`. Tables with a preliminary directory also carry `_source_release`. |
| IBGE re-import | Each import is a new publication; the `ibge_populacao` view raises when a municipality/year has two. The notebook checks `ibge_population_manifest` first. |
| Hanseníase dictionary in `registro.json` | **Absent** (14 sources; SINAN has only Chagas and Notificação Individual). Cite its URL without SHA-256. |
| Dictionary types of analysis fields | SIM `dtobito` date, `sexo` integer, `causabas`/`codmunres`/`codmunocor` string; SINASC `peso` integer, `consultas`/`parto`/`codmunres` string; SIH `diag_princ` string, `dias_perm`/`morte` integer, `val_tot` number; SIA-AM `ap_pripal` string, `ap_vl_ap` number; BPA-I `proc_id` string, `qt_aprov` integer; psicossocial `pa_proc_id`/`cidpri` string; CNES `tp_unid`/`codufmun`/`competen`/`cnes` string; SINAN fields string; hanseníase has no `classoper`. Physical DBF types can differ from the dictionary, so SQL casts with `TRY_CAST`/`CAST(... AS VARCHAR)`. |

Still to verify during implementation: marimo 0.24 keeps the notebook folder on `sys.path` (Task 22), a newer SIASUS technical report (Task 16), the RIPSA URL (Task 20), the municipality code format on real data (Task 19), analysis fields for the four remaining SIA tables (stay "dicionário + contagem").

## Deviations from the spec (decided while planning; tell Raphael)

1. **SIM default slice is RR 2022, not 2023.** The only population edition that matches a SIM year near 2023 is census 2022 (`ESTIMATE_UNAVAILABLE_YEARS = (2007, 2010, 2022, 2023)`), so the worked rate in the IBGE notebook and on the indicators page needs SIM 2022.
2. **`_comum.py` also holds `filtro_escopo` and `conferir`**: the row-count reconciliation would otherwise be the same dozen lines in six notebooks. `LakeReader`, `publications(run_id=)` and `outdated` stay visible in each notebook.
3. **Step 2 uses `available_releases`** for every database with a preliminary directory (SIM, SINASC, SINAN), not only SINAN, and `available` for the others.
4. **The offline test lets loopback connections through**: on Windows, asyncio builds its self-pipe with a localhost `connect`.

## File Structure

```text
notebooks/
  README.md                                short index (Task 14)
  bases/
    _comum.py                              Task 5 — run folder, JSON, outcomes, scope filter, counts, provenance
    sim_obitos.py                          Task 2 move of api_dados_reais.py; Task 6 rewrite
    sinasc_nascidos_vivos.py               Task 7
    sih_aih_reduzida.py                    Task 8
    sia.py                                 Task 9
    cnes_estabelecimentos.py               Task 10
    ibge_populacao.py                      Task 11
    sinan.py                               Task 2 move of sinan_chagas.py; Task 12 rewrite
    medicamentos.py                        Task 2 move; Task 13 rewrite
  explorar/
    panorama_datasus.py, _acervo/, inventario_dados_reais.py     Task 2 move; Task 3, Task 14 edits
  desenvolvimento/
    api_cenarios.py, performance_dbf.py, _performance_dbf.py, metadados_cli.py   Task 2 move; Task 3 edit
docs/
  pesquisa/index.md, indicadores.md, reprodutibilidade.md       Task 20
  sources/<9 perfis>.md                                         Tasks 15–18 (sia.md new)
  index.md                                                      Task 3
mkdocs.yml                                                      Task 20
tests/unit/
  test_packaging.py                                             Task 1
  test_guia_pesquisador.py                                      Task 15 (grows in 16–18, 20)
  notebooks/test_notebooks_abrem_offline.py                     Task 4 (grows in 6–13)
  notebooks/test_comum.py                                       Task 5
  notebooks/test_acervo.py, test_performance_dbf.py, test_sinan_inventory.py   Task 2 paths
.github/workflows/test.yml                                      Task 4
pyproject.toml, uv.lock, CHANGELOG.md, README.md                Tasks 1, 2, 20
reports/benchmarks-baseline.json, reports/profile-timings.txt   Task 1 (moved)
reports/<AAAA-MM-DD>-guia-pesquisador-validacao.md              Tasks 19, 21
```

---

### Task 1: Repository hygiene and marimo as an optional extra

**Files:**
- Delete from Git: `.playwright-mcp/` (6 files; already in `.gitignore`)
- Move: `benchmarks-baseline.json`, `profile-timings.txt` → `reports/`
- Modify: `pyproject.toml`, `uv.lock`, `CHANGELOG.md`, `scripts/metadados/README.md:31`
- Modify (remove inline noqa): `notebooks/sinan_chagas.py:3`, `notebooks/medicamentos.py:2`, `notebooks/performance_dbf.py:2-3`, `notebooks/inventario_dados_reais.py:2-3`, `notebooks/panorama_datasus.py:2-3`
- Test: `tests/unit/test_packaging.py`

**Interfaces:**
- Produces: marimo installed by `--extra dev` and `--extra notebooks` only; ruff ignores `B018`, `N803` for `notebooks/**/*.py`.

- [ ] **Step 1: Write the failing test**

`tests/unit/test_packaging.py`:

```python
"""Packaging contract: a base install does not pull the notebook runtime."""

import re
import tomllib
from pathlib import Path

PYPROJECT = tomllib.loads(
    (Path(__file__).resolve().parents[2] / "pyproject.toml").read_text(encoding="utf-8")
)


def _names(requirements: list[str]) -> set[str]:
    return {re.split(r"[<>=!~;\[ ]", r, maxsplit=1)[0].strip().lower() for r in requirements}


def test_marimo_is_only_an_optional_extra():
    project = PYPROJECT["project"]
    assert "marimo" not in _names(project["dependencies"])
    assert "marimo" in _names(project["optional-dependencies"]["notebooks"])


def test_dev_installs_the_notebooks_extra():
    # CI syncs only --extra dev, and tests/unit/notebooks imports marimo.
    assert "omnisus-db[notebooks]" in PYPROJECT["project"]["optional-dependencies"]["dev"]
```

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run pytest tests/unit/test_packaging.py -q`
Expected: 2 failed (`marimo` is in `dependencies`; `dev` lacks the extra).

- [ ] **Step 3: Edit `pyproject.toml`**

Delete the line `    "marimo>=0.23.16",` from `[project] dependencies`. Append to the `dev` list, after `"pre-commit>=4.6.2",`:

```toml
    # The notebook tests import marimo; keep one pin, in the notebooks extra.
    "omnisus-db[notebooks]",
```

Replace the two per-file ignores with one glob:

```toml
[tool.ruff.lint.per-file-ignores]
# marimo displays final expressions and injects imported classes as cell arguments.
"notebooks/**/*.py" = ["B018", "N803"]
```

- [ ] **Step 4: Lock, sync, pass**

```bash
uv lock
uv sync --locked --extra dev --extra docs
uv run pytest tests/unit/test_packaging.py -q
uv export --frozen --no-hashes | grep -ci '^marimo'
```

Expected: `2 passed`; the last command prints `0`.

- [ ] **Step 5: Remove the inline noqa comments**

Delete `# ruff: noqa: ...` and the explanatory comment line directly above it, if any (for example `# Expressões finais são saídas visuais; marimo injeta as classes importadas.`) from the five notebooks listed above. Then:

Run: `uv run ruff check notebooks && uv run ruff format --check notebooks`
Expected: `All checks passed!` and no files to reformat.

- [ ] **Step 6: Hygiene moves**

```bash
git rm -r -q .playwright-mcp
git mv benchmarks-baseline.json profile-timings.txt reports/
grep -rn "benchmarks-baseline\|profile-timings" --include='*.py' --include='*.toml' --include='*.yml' --include='*.yaml' . | grep -v '^./.venv\|^./reports/'
```

Expected: the grep prints nothing.

- [ ] **Step 7: Fix the command marimo no longer satisfies**

In `scripts/metadados/README.md`, change `uv run --locked marimo edit notebooks/metadados_cli.py` to `uv run --locked --extra notebooks marimo edit notebooks/metadados_cli.py` (Task 2 changes the path).

- [ ] **Step 8: CHANGELOG**

Under `## Unreleased`, add before `### Fixed`:

```markdown
### Changed

- **marimo is no longer installed with the package.** A base install pulls
  only what imports need. The notebooks need the extra:
  `uv sync --locked --extra notebooks` (or `pip install ".[notebooks]"`).
```

- [ ] **Step 9: Full unit run and commit**

Run: `uv run pytest -m "not e2e and not perf" -q`
Expected: the baseline (692 passed, 54 skipped) plus 2 new passes, 0 failed.

```bash
git add -A
git status --short   # only the files named in this task
git commit -m "Make marimo an optional extra and tidy the repository root

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Move notebooks into `bases/`, `explorar/`, `desenvolvimento/`

**Files:**
- Move (`git mv`): `notebooks/api_dados_reais.py` → `notebooks/bases/sim_obitos.py`; `notebooks/sinan_chagas.py` → `notebooks/bases/sinan.py`; `notebooks/medicamentos.py` → `notebooks/bases/medicamentos.py`; `notebooks/panorama_datasus.py`, `notebooks/_acervo/`, `notebooks/inventario_dados_reais.py` → `notebooks/explorar/`; `notebooks/api_cenarios.py`, `notebooks/performance_dbf.py`, `notebooks/_performance_dbf.py`, `notebooks/metadados_cli.py` → `notebooks/desenvolvimento/`
- Modify: the six moved notebooks' root paths, `explorar/inventario_dados_reais.py:217`, `explorar/panorama_datasus.py:15,24-25`, `desenvolvimento/performance_dbf.py:14,20-21`
- Modify: `tests/unit/notebooks/test_acervo.py:11`, `test_performance_dbf.py:11`, `test_sinan_inventory.py:12`
- Modify (path text): `README.md`, `notebooks/README.md`, `docs/sources/sinan_chagas.md:100,105`, `docs/sources/medicamentos.md:108`, `scripts/metadados/README.md:10,31`

**Interfaces:**
- Produces: notebook paths used by every later task; helper modules import from their own folder (`from _acervo...`, `from _performance_dbf ...`, later `from _comum ...`) because marimo and `python notebook.py` put the notebook folder on `sys.path`.

- [ ] **Step 1: Move**

```bash
mkdir -p notebooks/bases notebooks/explorar notebooks/desenvolvimento
git mv notebooks/api_dados_reais.py notebooks/bases/sim_obitos.py
git mv notebooks/sinan_chagas.py notebooks/bases/sinan.py
git mv notebooks/medicamentos.py notebooks/bases/medicamentos.py
git mv notebooks/panorama_datasus.py notebooks/_acervo notebooks/inventario_dados_reais.py notebooks/explorar/
git mv notebooks/api_cenarios.py notebooks/performance_dbf.py notebooks/_performance_dbf.py notebooks/metadados_cli.py notebooks/desenvolvimento/
```

- [ ] **Step 2: Run the notebook tests and watch them fail**

Run: `uv run pytest tests/unit/notebooks -q`
Expected: collection errors or failures (`No module named '_acervo'`, missing `inventario_dados_reais.py`).

- [ ] **Step 3: Fix the tests**

- `test_acervo.py`: `sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "notebooks/explorar"))`
- `test_performance_dbf.py`: `sys.path.insert(0, str(ROOT / "notebooks/desenvolvimento"))`
- `test_sinan_inventory.py`: `NOTEBOOK = Path(__file__).resolve().parents[3] / "notebooks/explorar/inventario_dados_reais.py"`

- [ ] **Step 4: Fix the notebooks' root paths**

In `bases/sim_obitos.py`, `bases/sinan.py`, `bases/medicamentos.py`, `explorar/panorama_datasus.py`, `desenvolvimento/performance_dbf.py`, `desenvolvimento/metadados_cli.py`: replace `Path(__file__).resolve().parent.parent` with `Path(__file__).resolve().parents[2]`.

In `explorar/inventario_dados_reais.py`, the run folder uses the notebook location: change `Path(mo.notebook_location()).parent` to `Path(mo.notebook_location()).parents[1]` (the notebook folder is now `notebooks/explorar`, so `.parent` would put data under `notebooks/data/`).

In `explorar/panorama_datasus.py` delete `sys.path.insert(0, str(project_root / "notebooks"))` and the comment above it; in `desenvolvimento/performance_dbf.py` delete `sys.path.insert(0, str(root / "notebooks"))`. Delete `import sys` from either file when `grep -n "sys\." <file>` finds no other use.

- [ ] **Step 5: Pass, and prove the helper imports under marimo itself**

```bash
uv run pytest tests/unit/notebooks -q
uv run marimo export html notebooks/desenvolvimento/performance_dbf.py -o "$TMPDIR/perf.html"
uv run marimo export html notebooks/explorar/panorama_datasus.py -o "$TMPDIR/panorama.html"
```

Expected: tests pass; both exports exit 0 (they import `_performance_dbf` and `_acervo` without `sys.path.insert`). If an export fails with `ModuleNotFoundError`, stop and report: the spec's `sys.path` premise no longer holds.

- [ ] **Step 6: Update path references**

```bash
grep -rn "notebooks/[a-z_]*\.py\|notebooks/_acervo" README.md notebooks docs/*.md docs/sources docs/guides scripts tests .github
```

Replace each old path with the new one (`notebooks/api_dados_reais.py` → `notebooks/bases/sim_obitos.py`, `notebooks/sinan_chagas.py` → `notebooks/bases/sinan.py`, and so on). Leave `reports/` and `docs/superpowers/` untouched: they are historical. Re-run the grep; every match must point to an existing file:

```bash
grep -rhno "notebooks/[a-z_/]*\.py" README.md notebooks docs/*.md docs/sources scripts tests | sed 's/.*:\(notebooks.*\)/\1/' | sort -u | while read p; do [ -f "$p" ] || echo "MISSING $p"; done
```

Expected: no `MISSING` line.

- [ ] **Step 7: Lint, full run, commit**

```bash
uv run ruff check notebooks tests && uv run ruff format --check notebooks tests
uv run pytest -m "not e2e and not perf" -q
git add -A notebooks tests README.md docs scripts
git commit -m "Group notebooks by audience: bases, explorar, desenvolvimento

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Read-only cells use `LakeReader`

**Files:**
- Modify: `notebooks/explorar/inventario_dados_reais.py:303` (result cell)
- Modify: `notebooks/desenvolvimento/api_cenarios.py:492` (reopen cell) and the two read recipes in its "Receitas" markdown (`with odb.Lake.local(live_target) as lake:` before `lake.connect().execute(` and before `codes = [...]`)
- Modify: `docs/index.md:47-52`
- Inspect: `docs/guides/migration-from-pysus.md:27`, `docs/guides/reprocessing-and-maintenance.md:58,108,182`
- Test: `tests/unit/notebooks/test_sinan_inventory.py` (existing; exercises the inventory result cell)

**Interfaces:**
- Consumes: `odb.LakeReader(target: str, *, snapshot_id: int | None = None, alias: str = "lake")`, same `connect()`, `tables()`, `snapshots()`, `publications(run_id=)` as `Lake`.

- [ ] **Step 1: Switch the inventory result cell**

In the cell that defines `total, amostra, esquema, resumo`, replace `with odb.Lake.local(target) as _lake:` with `with odb.LakeReader(target) as _leitor:` and every `_lake` in that cell with `_leitor`. The cell also runs `COPY ... TO` a local file, which a read-only attach allows.

- [ ] **Step 2: Run the test that executes that cell**

Run: `uv run pytest tests/unit/notebooks/test_sinan_inventory.py -q`
Expected: 1 passed (the Parquet and CSV exports are still written).

- [ ] **Step 3: Switch `api_cenarios.py`**

- Reopen cell: `with odb.Lake.local(live_target) as _read_lake:` → `with odb.LakeReader(live_target) as _read_lake:`.
- In the "Receitas" markdown, the query recipe and the CNES codes recipe: `with odb.Lake.local(live_target) as lake:` → `with odb.LakeReader(live_target) as lake:`. Leave the write demo (`TemporaryDirectory` + `transaction`) on `Lake.local`.

- [ ] **Step 4: Switch `docs/index.md`**

Replace the "Hello, mortality" read with:

```python
if report.ok:
    with odb.LakeReader(odb.DEFAULT_TARGET) as reader:
        df = reader.connect().sql(
            "SELECT count(*) AS obitos FROM lake.sim_obitos WHERE ano = 2024"
        ).pl()
        print(df)
```

- [ ] **Step 5: Guides**

Open each snippet in `docs/guides/migration-from-pysus.md:27` and `docs/guides/reprocessing-and-maintenance.md:58,108,182`. When the `with` block only reads (`connect().sql`, `tables`, `snapshots`, `publications`, `outdated(lake=...)`), switch it to `odb.LakeReader(...)`; when it calls `ingest`, `transaction`, `delete_scope`, `expire_snapshots`, `cleanup_files` or any other writer method, leave it.

- [ ] **Step 6: Verify and commit**

```bash
grep -rn "Lake.local" notebooks docs/index.md docs/guides
uv run pytest tests/unit/notebooks -q
uv run marimo export html notebooks/desenvolvimento/api_cenarios.py -o "$TMPDIR/api.html"
git add notebooks docs/index.md docs/guides
git commit -m "Read lakes through LakeReader in notebooks and docs

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

Expected: every remaining `Lake.local` match writes; tests pass; export exits 0.

---

### Task 4: Opening a notebook downloads and writes nothing; `marimo check` in CI

**Files:**
- Create: `tests/unit/notebooks/test_notebooks_abrem_offline.py`
- Modify: `.github/workflows/test.yml` (new step after `Lint`)

**Interfaces:**
- Produces: `ESPERADOS` — the set of notebook paths relative to `notebooks/`. Tasks 6–13 add their notebook to it. The test sets `OMNISUS_NOTEBOOK_DATA` to `tmp_path / "dados"` and requires, for `bases/`, that the folder is never created.

- [ ] **Step 1: Write the test**

```python
"""Opening a notebook opens no network connection; a bases/ notebook writes nothing.

Every notebook runs in-process with `app.run()`, as `marimo export` would.
Button-gated cells stop at `mo.stop`, so anything reaching the network or the
research lake on open is a failure. The unit conftest also refuses FTP listings.
"""

import importlib.util
import socket
from pathlib import Path

import pytest

NOTEBOOKS = Path(__file__).resolve().parents[3] / "notebooks"

# Helper modules are not notebooks: `_comum.py`, `_performance_dbf.py`, `_acervo/`.
TODOS = sorted(
    p
    for p in NOTEBOOKS.rglob("*.py")
    if not any(part.startswith("_") for part in p.relative_to(NOTEBOOKS).parts)
)

ESPERADOS = {
    "bases/medicamentos.py",
    "bases/sim_obitos.py",
    "bases/sinan.py",
    "desenvolvimento/api_cenarios.py",
    "desenvolvimento/metadados_cli.py",
    "desenvolvimento/performance_dbf.py",
    "explorar/inventario_dados_reais.py",
    "explorar/panorama_datasus.py",
}

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def test_every_notebook_is_checked():
    assert {p.relative_to(NOTEBOOKS).as_posix() for p in TODOS} == ESPERADOS


@pytest.mark.parametrize("caminho", TODOS, ids=lambda p: p.relative_to(NOTEBOOKS).as_posix())
def test_opening_downloads_and_writes_nothing(caminho, monkeypatch, tmp_path):
    real_connect = socket.socket.connect

    def guarded_connect(self, address):
        # Windows asyncio builds its self-pipe with a loopback connect.
        if not isinstance(address, tuple) or address[0] in _LOOPBACK:
            return real_connect(self, address)
        raise AssertionError(f"{caminho.name} opened a connection to {address!r}")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    dados = tmp_path / "dados"
    monkeypatch.setenv("OMNISUS_NOTEBOOK_DATA", str(dados))
    # `python notebook.py` and marimo put the notebook's folder on sys.path.
    monkeypatch.syspath_prepend(str(caminho.parent))
    spec = importlib.util.spec_from_file_location(f"notebook_{caminho.stem}", caminho)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    module.app.run()

    if caminho.parent.name == "bases":
        assert not dados.exists(), f"{caminho.name} wrote to the research lake on open"
```

- [ ] **Step 2: Run it**

Run: `uv run pytest tests/unit/notebooks/test_notebooks_abrem_offline.py -q`
Expected: 9 passed.

- [ ] **Step 3: Falsify the network guard**

Append a temporary cell to `notebooks/explorar/panorama_datasus.py`, just above `if __name__ == "__main__":`:

```python
@app.cell
def _():
    import urllib.request

    urllib.request.urlopen("http://example.org", timeout=3)
    return
```

Run: `uv run pytest tests/unit/notebooks/test_notebooks_abrem_offline.py -q -k panorama`
Expected: FAIL with `opened a connection to`. Then `git checkout -- notebooks/explorar/panorama_datasus.py`.

- [ ] **Step 4: Falsify a gate**

In `notebooks/explorar/inventario_dados_reais.py`, change `mo.stop(not (executar or consultar.value), mo.md("Clique em **Consultar inventário**."))` to `mo.stop(False, mo.md("Clique em **Consultar inventário**."))`.

Run: `uv run pytest tests/unit/notebooks/test_notebooks_abrem_offline.py -q -k inventario`
Expected: FAIL (`network: unit test attempted to LIST` or `opened a connection`). Then `git checkout -- notebooks/explorar/inventario_dados_reais.py` and re-run the whole file: 9 passed.

- [ ] **Step 5: CI step**

In `.github/workflows/test.yml`, after the `Lint` step:

```yaml
      - name: Notebook check
        # A folder, not a glob: Windows runners do not expand globs.
        # --ignore-scripts skips helper modules; the offline-open test still
        # imports every notebook, so a notebook marimo cannot parse still fails.
        run: uv run marimo check --strict --ignore-scripts notebooks
```

Run locally: `uv run marimo check --strict --ignore-scripts notebooks`
Expected: exit 0.

- [ ] **Step 6: Commit**

```bash
git add tests/unit/notebooks/test_notebooks_abrem_offline.py .github/workflows/test.yml
git commit -m "Check that opening a notebook downloads and writes nothing

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: `notebooks/bases/_comum.py`

**Files:**
- Create: `notebooks/bases/_comum.py`
- Test: `tests/unit/notebooks/test_comum.py`

**Interfaces:**
- Consumes: `omnisus_db.lake.publication.scope_fields(scope: ScopeKey) -> dict[str, object]` (`{"ano", "uf"[, "mes"]}` or `{"_source_ano"}`); `odb.ImportReport`, `odb.ScopeKey`, `odb.LakeReader`.
- Produces (imported by Tasks 6–13 as `from _comum import ...`):
  - `LIMITE_BYTES: int = 25 * 1024 * 1024`
  - `raiz_dados() -> Path`
  - `target_padrao() -> str`
  - `executar_sem_botoes(cli_args: Mapping[str, object]) -> bool`
  - `salvar_json(caminho: Path, conteudo: object) -> Path`
  - `fixar_plano(target: str, **detalhes: Any) -> tuple[dict[str, Any], Path]` — creates `raiz_dados()/execucoes/<run_id>/plano.json`; `plano` has `**detalhes`, `target`, `run_id`, `omnisus_db`, `fixado_em_utc`
  - `desfechos(relatorio: odb.ImportReport) -> list[dict]` — keys `escopo`, `status`, `linhas`, `motivo`
  - `registrar_importacao(pasta: Path, relatorio: odb.ImportReport, nao_resolvidos: Iterable[tuple[int, odb.ScopeKey]] = ()) -> list[dict]` — writes `resultado.json`
  - `filtro_escopo(escopo: odb.ScopeKey) -> tuple[str, list[object]]`
  - `conferir(leitor, dataset: str, escopos: Sequence[odb.ScopeKey]) -> tuple[list[dict], list[dict]]` — (rows per scope: `escopo`, `linhas_no_lake`, `linhas_publicadas`, `confere`; active publications of those scopes)
  - `registrar_proveniencia(pasta: Path, *, plano, publicacoes, snapshot_id: int, consultas: Mapping[str, str]) -> dict` — writes `proveniencia.json`

- [ ] **Step 1: Write the failing tests**

`tests/unit/notebooks/test_comum.py`:

```python
"""The bases/ notebook helpers: where a run lives, what it records, how rows reconcile."""

import importlib.util
import json
from pathlib import Path

import duckdb
import pytest

import omnisus_db as odb

_PATH = Path(__file__).resolve().parents[3] / "notebooks/bases/_comum.py"
_spec = importlib.util.spec_from_file_location("_comum_under_test", _PATH)
comum = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(comum)

RR_2022 = odb.ScopeKey(uf="RR", ano=2022)


def test_data_root_defaults_to_the_shared_research_lake(monkeypatch):
    monkeypatch.delenv("OMNISUS_NOTEBOOK_DATA", raising=False)
    raiz = _PATH.parents[2] / "data/lake/pesquisa"
    assert comum.raiz_dados() == raiz
    assert comum.target_padrao() == f"ducklake:{raiz / 'dados.ducklake'}"


def test_environment_overrides_the_data_root(monkeypatch, tmp_path):
    monkeypatch.setenv("OMNISUS_NOTEBOOK_DATA", str(tmp_path))
    assert comum.raiz_dados() == tmp_path


@pytest.mark.parametrize(
    ("cli_args", "esperado"),
    [({}, False), ({"executar": "true"}, True), ({"executar": "True"}, True),
     ({"executar": True}, True), ({"executar": "false"}, False)],
)
def test_executar_flag(cli_args, esperado):
    assert comum.executar_sem_botoes(cli_args) is esperado


def test_fixing_a_plan_writes_only_the_plan(monkeypatch, tmp_path):
    monkeypatch.setenv("OMNISUS_NOTEBOOK_DATA", str(tmp_path))
    plano, pasta = comum.fixar_plano(
        "ducklake:x", dataset="sim_obitos", escopos=[{"uf": "RR", "ano": 2022, "mes": None}]
    )
    assert pasta == tmp_path / "execucoes" / plano["run_id"]
    assert [p.name for p in pasta.iterdir()] == ["plano.json"]
    assert json.loads((pasta / "plano.json").read_text(encoding="utf-8")) == plano
    assert plano["dataset"] == "sim_obitos"
    assert plano["target"] == "ducklake:x"
    assert plano["omnisus_db"] == odb.__version__


def test_two_plans_never_share_a_folder(monkeypatch, tmp_path):
    monkeypatch.setenv("OMNISUS_NOTEBOOK_DATA", str(tmp_path))
    assert comum.fixar_plano("ducklake:x")[1] != comum.fixar_plano("ducklake:x")[1]


def test_import_record_keeps_every_outcome_and_unresolved_scope(tmp_path):
    ja_publicado = odb.ScopeKey(uf="RR", ano=2021)
    relatorio = odb.ImportReport(
        outcomes=(
            odb.ScopeOutcome(
                scope=RR_2022,
                status="ok",
                result=odb.ImportResult(rows=7, bytes_written=0, duration_seconds=0.1),
            ),
            odb.ScopeOutcome(
                scope=ja_publicado,
                status="skipped",
                reason="same source and parser version already published",
            ),
        ),
        run_id="r1",
    )
    nao_resolvido = odb.ScopeKey(uf="RR", ano=2020)

    linhas = comum.registrar_importacao(tmp_path, relatorio, [(2, nao_resolvido)])

    assert linhas == [
        {"escopo": str(RR_2022), "status": "ok", "linhas": 7, "motivo": None},
        {
            "escopo": str(ja_publicado),
            "status": "skipped",
            "linhas": None,
            "motivo": "same source and parser version already published",
        },
    ]
    salvo = json.loads((tmp_path / "resultado.json").read_text(encoding="utf-8"))
    assert salvo == {
        "linhas_importadas": 7,
        "desfechos": linhas,
        "nao_resolvidos": [{"indice": 2, "escopo": str(nao_resolvido)}],
    }


@pytest.mark.parametrize(
    ("escopo", "esperado"),
    [
        (RR_2022, ('"ano" = ? AND "uf" = ?', [2022, "RR"])),
        (odb.ScopeKey(uf="RR", ano=2024, mes=1), ('"ano" = ? AND "uf" = ? AND "mes" = ?', [2024, "RR", 1])),
        (odb.ScopeKey(uf=None, ano=2022), ('"_source_ano" = ?', [2022])),
    ],
)
def test_scope_filter_uses_the_columns_the_library_writes(escopo, esperado):
    assert comum.filtro_escopo(escopo) == esperado


class _Leitor:
    alias = "lake"

    def __init__(self, publicacoes):
        self._con = duckdb.connect()
        self._con.execute("ATTACH ':memory:' AS lake")
        self._con.execute(
            "CREATE TABLE lake.sim_obitos AS SELECT * FROM "
            "(VALUES ('RR', 2022), ('RR', 2022), ('RR', 2021)) AS t(uf, ano)"
        )
        self._publicacoes = publicacoes

    def connect(self):
        return self._con

    def publications(self):
        return self._publicacoes


def test_reconciliation_counts_only_active_publications_of_the_dataset():
    ativa = {"dataset": "sim_obitos", "active": True, "scope": RR_2022, "rows": 2}
    publicacoes = [
        ativa,
        {"dataset": "sim_obitos", "active": False, "scope": RR_2022, "rows": 5},
        {"dataset": "sinasc_nascidos_vivos", "active": True, "scope": RR_2022, "rows": 9},
    ]
    ausente = odb.ScopeKey(uf="RR", ano=2020)

    conferencia, ativas = comum.conferir(_Leitor(publicacoes), "sim_obitos", [RR_2022, ausente])

    assert conferencia == [
        {"escopo": str(RR_2022), "linhas_no_lake": 2, "linhas_publicadas": 2, "confere": True},
        {"escopo": str(ausente), "linhas_no_lake": 0, "linhas_publicadas": 0, "confere": True},
    ]
    assert ativas == [ativa]


def test_provenance_names_what_a_citation_needs(tmp_path):
    plano = {"run_id": "r1", "dataset": "sim_obitos"}
    publicacoes = [{"publication_id": "p1", "scope": RR_2022, "source_sha256": "ab"}]

    registro = comum.registrar_proveniencia(
        tmp_path, plano=plano, publicacoes=publicacoes, snapshot_id=3,
        consultas={"obitos_por_mes": "SELECT 1"},
    )

    salvo = json.loads((tmp_path / "proveniencia.json").read_text(encoding="utf-8"))
    assert salvo == json.loads(json.dumps(registro, default=str))
    assert salvo["plano"] == plano
    assert salvo["publicacoes"][0]["scope"] == str(RR_2022)
    assert salvo["snapshot_id"] == 3
    assert salvo["consultas"] == {"obitos_por_mes": "SELECT 1"}
    assert salvo["omnisus_db"] == odb.__version__
    assert salvo["gerado_em_utc"]
```

- [ ] **Step 2: Run and watch them fail**

Run: `uv run pytest tests/unit/notebooks/test_comum.py -q`
Expected: collection error, `FileNotFoundError` for `notebooks/bases/_comum.py`.

- [ ] **Step 3: Write `_comum.py`**

```python
"""O que se repete nos notebooks de bases/: onde uma execução fica e o que ela registra.

As chamadas da biblioteca que cada notebook ensina (`available`, `import_dataset`,
`LakeReader`, `publications`, `outdated`) ficam visíveis nas células. Este módulo
só grava arquivos, monta o filtro de um escopo e confere contagens.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import omnisus_db as odb
from omnisus_db.lake.publication import scope_fields

LIMITE_BYTES = 25 * 1024 * 1024
"""Teto do arquivo comprimido baixado nos recortes didáticos."""

_REPOSITORIO = Path(__file__).resolve().parents[2]


def raiz_dados() -> Path:
    """Pasta do lake de pesquisa compartilhado; `OMNISUS_NOTEBOOK_DATA` a substitui."""
    return Path(os.environ.get("OMNISUS_NOTEBOOK_DATA") or _REPOSITORIO / "data/lake/pesquisa")


def target_padrao() -> str:
    return f"ducklake:{raiz_dados() / 'dados.ducklake'}"


def executar_sem_botoes(cli_args: Mapping[str, object]) -> bool:
    """`-- --executar true` percorre as etapas dos botões sem interface."""
    return str(cli_args.get("executar", "false")).lower() == "true"


def salvar_json(caminho: Path, conteudo: object) -> Path:
    texto = json.dumps(conteudo, default=str, ensure_ascii=False, indent=2)
    caminho.write_text(texto, encoding="utf-8")
    return caminho


def fixar_plano(target: str, **detalhes: Any) -> tuple[dict[str, Any], Path]:
    """Cria a pasta da execução e grava `plano.json` antes de qualquer download."""
    agora = datetime.now(UTC)
    run_id = f"{agora:%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
    pasta = raiz_dados() / "execucoes" / run_id
    pasta.mkdir(parents=True)
    plano = {
        **detalhes,
        "target": target,
        "run_id": run_id,
        "omnisus_db": odb.__version__,
        "fixado_em_utc": agora.isoformat(),
    }
    salvar_json(pasta / "plano.json", plano)
    return plano, pasta


def desfechos(relatorio: odb.ImportReport) -> list[dict[str, Any]]:
    return [
        {
            "escopo": str(o.scope),
            "status": o.status,
            "linhas": o.result.rows if o.result else None,
            "motivo": o.reason,
        }
        for o in relatorio.outcomes
    ]


def registrar_importacao(
    pasta: Path,
    relatorio: odb.ImportReport,
    nao_resolvidos: Iterable[tuple[int, odb.ScopeKey]] = (),
) -> list[dict[str, Any]]:
    """Grava `resultado.json` e devolve a tabela de desfechos para exibir."""
    linhas = desfechos(relatorio)
    salvar_json(
        pasta / "resultado.json",
        {
            "linhas_importadas": relatorio.rows,
            "desfechos": linhas,
            "nao_resolvidos": [{"indice": i, "escopo": str(e)} for i, e in nao_resolvidos],
        },
    )
    return linhas


def filtro_escopo(escopo: odb.ScopeKey) -> tuple[str, list[object]]:
    """`WHERE` que seleciona as linhas de um escopo, nas colunas que a biblioteca grava."""
    campos = scope_fields(escopo)
    return " AND ".join(f'"{nome}" = ?' for nome in campos), list(campos.values())


def conferir(
    leitor: odb.LakeReader, dataset: str, escopos: Sequence[odb.ScopeKey]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Linhas no lake contra linhas publicadas, por escopo, e as publicações ativas."""
    ativas = [
        p
        for p in leitor.publications()
        if p["dataset"] == dataset and p["active"] and p["scope"] in escopos
    ]
    conferencia = []
    for escopo in escopos:
        where, args = filtro_escopo(escopo)
        sql = f'SELECT count(*) FROM "{leitor.alias}"."{dataset}" WHERE {where}'
        (no_lake,) = leitor.connect().execute(sql, args).fetchone()
        publicadas = sum(p["rows"] for p in ativas if p["scope"] == escopo)
        conferencia.append(
            {
                "escopo": str(escopo),
                "linhas_no_lake": no_lake,
                "linhas_publicadas": publicadas,
                "confere": no_lake == publicadas,
            }
        )
    return conferencia, ativas


def registrar_proveniencia(
    pasta: Path,
    *,
    plano: Mapping[str, Any],
    publicacoes: Sequence[Mapping[str, Any]],
    snapshot_id: int,
    consultas: Mapping[str, str],
) -> dict[str, Any]:
    """Grava `proveniencia.json`: o suficiente para citar e refazer o resultado."""
    registro = {
        "plano": dict(plano),
        "publicacoes": [dict(p) for p in publicacoes],
        "snapshot_id": snapshot_id,
        "consultas": dict(consultas),
        "omnisus_db": odb.__version__,
        "gerado_em_utc": datetime.now(UTC).isoformat(),
    }
    salvar_json(pasta / "proveniencia.json", registro)
    return registro
```

- [ ] **Step 4: Pass**

Run: `uv run pytest tests/unit/notebooks/test_comum.py -q`
Expected: all passed. If `ScopeOutcome` or `ImportReport` rejects the constructor arguments, read `src/omnisus_db/sources/_base.py:40-100` and adjust the test fixture only — not `_comum.py`'s contract.

- [ ] **Step 5: Falsify the reconciliation**

In `conferir`, delete `and p["active"]`. Run the reconciliation test: expected FAIL (`linhas_publicadas` 7 ≠ 2). Restore the condition; re-run: pass.

- [ ] **Step 6: Lint and commit**

```bash
uv run ruff check --fix notebooks/bases/_comum.py tests/unit/notebooks/test_comum.py
uv run ruff format notebooks/bases/_comum.py tests/unit/notebooks/test_comum.py
uv run pytest tests/unit/notebooks -q
git add notebooks/bases/_comum.py tests/unit/notebooks/test_comum.py
git commit -m "Add the run-folder, reconciliation and provenance helpers for bases notebooks

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

`test_notebooks_abrem_offline.py` must still pass: `_comum.py` starts with `_`, so it is not collected as a notebook.

---

### Task 6: `notebooks/bases/sim_obitos.py` — the reference notebook

**Files:**
- Rewrite: `notebooks/bases/sim_obitos.py` (moved from `api_dados_reais.py` in Task 2; its derived-transaction section is dropped because `desenvolvimento/api_cenarios.py` already teaches transactions)
- Test: `tests/unit/notebooks/test_notebooks_abrem_offline.py` (already lists `bases/sim_obitos.py`)

**Interfaces:**
- Consumes: everything `_comum` produces (Task 5); `odb.available_releases`, `odb.scopes_for`, `odb.import_dataset`, `odb.LakeReader`, `odb.outdated`, `load_dicionario(name).fields` (dicts with `name`, `type`, optional `label`).
- Produces: the six-step cell layout every later `bases/` notebook follows. A reviewer compares Tasks 7–13 against this file.

- [ ] **Step 1: Replace the file**

```python
"""SIM · óbitos: do arquivo do DATASUS a uma tabela citável, em seis etapas."""

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", app_title="SIM · óbitos")


@app.cell
def _():
    import asyncio
    from dataclasses import asdict

    import marimo as mo
    from _comum import (
        LIMITE_BYTES,
        conferir,
        executar_sem_botoes,
        fixar_plano,
        registrar_importacao,
        registrar_proveniencia,
        target_padrao,
    )

    import omnisus_db as odb
    from omnisus_db.transforms.dictionaries import load_dicionario

    dataset = "sim_obitos"
    executar = executar_sem_botoes(mo.cli_args())
    return (
        LIMITE_BYTES,
        asdict,
        asyncio,
        conferir,
        dataset,
        executar,
        fixar_plano,
        load_dicionario,
        mo,
        odb,
        registrar_importacao,
        registrar_proveniencia,
        target_padrao,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # SIM · óbitos

    Base de óbitos do Sistema de Informações sobre Mortalidade (SIM), publicada
    pelo DATASUS. Este notebook percorre as seis etapas do
    [guia do pesquisador](https://raphaelfh.github.io/omnisus-db/pesquisa/) com um
    recorte pequeno: **Roraima, 2022**.

    **Abrir este notebook não baixa nem grava nada.** Cada etapa com rede ou escrita
    começa por um botão. Os dados vão para o lake de pesquisa compartilhado
    (`data/lake/pesquisa/`), o mesmo dos outros notebooks de `bases/`.

    Antes de interpretar números, leia o
    [perfil do SIM](https://raphaelfh.github.io/omnisus-db/sources/sim_obitos/):
    o que um registro representa, datas, geografia e armadilhas, com as fontes.
    """)
    return


@app.cell
def _(dataset, load_dicionario, mo):
    _dicionario = load_dicionario(dataset)
    mo.vstack(
        [
            mo.md(
                "## 1 · O que a base registra\n\n"
                "Campos do dicionário que a biblioteca aplica na importação. "
                "O significado dos códigos está no perfil e no documento oficial citado nele."
            ),
            mo.ui.table(
                [
                    {"campo": f["name"], "tipo": f["type"], "rótulo": f.get("label", "")}
                    for f in _dicionario.fields
                ],
                selection=None,
                page_size=10,
            ),
        ]
    )
    return


@app.cell
def _(mo):
    descobrir = mo.ui.run_button(label="Consultar o que o DATASUS publica")
    mo.vstack(
        [
            mo.md(
                "## 2 · Descobrir\n\n"
                "Lista agora o FTP do DATASUS (`refresh=True`). O SIM tem um diretório "
                "final e um preliminar; a coluna `diretorio` diz onde cada ano está."
            ),
            descobrir,
        ]
    )
    return (descobrir,)


@app.cell
async def _(asyncio, dataset, descobrir, executar, mo, odb):
    mo.stop(not (executar or descobrir.value), mo.md("A consulta começa pelo botão acima."))
    _publicados = await asyncio.to_thread(
        odb.available_releases, dataset, ufs=["RR"], refresh=True
    )
    mo.ui.table(
        [
            {"uf": e.uf, "ano": e.ano, "diretorio": r}
            for e, r in sorted(_publicados.items(), key=lambda item: -item[0].ano)
        ],
        selection=None,
        label="Arquivos publicados para RR",
    )
    return


@app.cell
def _(mo, odb, target_padrao):
    uf = mo.ui.dropdown(list(odb.ALL_UFS), value="RR", label="UF do arquivo")
    ano = mo.ui.number(start=1996, stop=2100, step=1, value=2022, label="Ano")
    target = mo.ui.text(value=target_padrao(), label="Lake", full_width=True)
    fixar = mo.ui.run_button(label="Fixar o plano")
    mo.vstack(
        [
            mo.md(
                "## 3 · Planejar e importar\n\n"
                "Confira o ano na etapa 2. Fixar o plano grava `plano.json` com um "
                "`run_id` antes de qualquer download: é o `run_id` que permite "
                "reconciliar uma importação interrompida."
            ),
            mo.hstack([uf, ano]),
            target,
            fixar,
        ]
    )
    return ano, fixar, target, uf


@app.cell
def _(LIMITE_BYTES, ano, asdict, dataset, executar, fixar, fixar_plano, mo, odb, target, uf):
    mo.stop(not (executar or fixar.value), mo.md("Fixe o plano para continuar."))
    escopos = odb.scopes_for(dataset, years=[int(ano.value)], ufs=[uf.value])
    plano, pasta = fixar_plano(
        target.value,
        dataset=dataset,
        escopos=[asdict(e) for e in escopos],
        policy="skip_same",
        limite_bytes=LIMITE_BYTES,
    )
    importar = mo.ui.run_button(label="Baixar e publicar este plano")
    mo.vstack([mo.md(f"Plano gravado em `{pasta / 'plano.json'}`."), mo.json(plano), importar])
    return escopos, importar, pasta, plano


@app.cell
async def _(
    LIMITE_BYTES, asyncio, escopos, executar, importar, mo, odb, pasta, plano, registrar_importacao
):
    mo.stop(not (executar or importar.value), mo.md("O download só começa pelo botão acima."))
    mo.output.append(
        mo.md(
            "Importando. Interromper a célula não cancela a thread: espere terminar "
            "antes de outra escrita no mesmo lake."
        )
    )
    try:
        relatorio = await asyncio.to_thread(
            odb.import_dataset,
            plano["dataset"],
            scopes=escopos,
            target=plano["target"],
            policy="skip_same",
            run_id=plano["run_id"],
            concurrency=1,
            max_payload_bytes=LIMITE_BYTES,
            max_inflight_bytes=LIMITE_BYTES,
        )
        _nao_resolvidos = ()
    except odb.ImportAbortedError as _erro:
        relatorio, _nao_resolvidos = _erro.report, _erro.unresolved
    _linhas = registrar_importacao(pasta, relatorio, _nao_resolvidos)
    if executar and (relatorio.failed or _nao_resolvidos):
        raise RuntimeError(f"Importação incompleta; veja {pasta / 'resultado.json'}")
    mo.vstack(
        [
            mo.ui.table(_linhas, selection=None, label="Desfecho por escopo"),
            mo.md(
                "`skipped` com *same source and parser version already published* quer "
                "dizer que o mesmo arquivo já estava no lake: nada foi duplicado. "
                "Um arquivo que o DATASUS não publica também aparece como `skipped`."
            ),
        ]
    )
    return (relatorio,)


@app.cell
def _(conferir, dataset, escopos, mo, odb, plano, relatorio):
    with odb.LakeReader(plano["target"]) as _leitor:
        mo.stop(
            dataset not in _leitor.tables(),
            mo.md("Nenhuma tabela publicada; veja os desfechos acima."),
        )
        _desta_execucao = _leitor.publications(run_id=plano["run_id"])
        _conferencia, publicacoes = conferir(_leitor, dataset, escopos)
        snapshot_id = _leitor.snapshots()[-1]["snapshot_id"]
        # refresh=False reaproveita a listagem da etapa 2: o FTP é um recurso público.
        _desatualizados = odb.outdated(dataset, lake=_leitor)
    mo.vstack(
        [
            mo.md(
                "## 4 · Conferir\n\n"
                f"O relatório informou **{relatorio.rows:,} linhas novas**. Abaixo, as "
                "publicações desta execução, a contagem no lake contra o manifesto e os "
                "escopos que o DATASUS moveu de diretório desde a importação (`outdated`)."
            ),
            mo.ui.table(_desta_execucao, selection=None, label="publications(run_id=...)"),
            mo.ui.table(_conferencia, selection=None, label="Linhas no lake × publicadas"),
            mo.md(f"Desatualizados: `{[str(e) for e in _desatualizados]}` · snapshot `{snapshot_id}`"),
        ]
    )
    return publicacoes, snapshot_id


@app.cell
def _(escopos, mo, odb, plano, snapshot_id):
    consultas = {
        "obitos_por_mes": """
            WITH obitos AS (
                SELECT COALESCE(
                    TRY_CAST(dtobito AS DATE),
                    TRY_STRPTIME(trim(CAST(dtobito AS VARCHAR)), '%d%m%Y')::DATE
                ) AS data_obito
                FROM lake.sim_obitos WHERE uf = ? AND ano = ?
            )
            SELECT coalesce(strftime(data_obito, '%Y-%m'), 'sem data válida') AS mes,
                   count(*) AS obitos
            FROM obitos GROUP BY ALL ORDER BY mes
        """,
        "obitos_por_sexo_e_causa": """
            SELECT trim(CAST(sexo AS VARCHAR)) AS sexo_codigo,
                   left(upper(trim(CAST(causabas AS VARCHAR))), 3) AS causa_basica_cid10_3,
                   count(*) AS obitos
            FROM lake.sim_obitos WHERE uf = ? AND ano = ?
            GROUP BY ALL ORDER BY obitos DESC
        """,
        "residencia_e_ocorrencia": """
            SELECT left(trim(CAST(codmunres AS VARCHAR)), 2) AS uf_residencia_ibge,
                   left(trim(CAST(codmunocor AS VARCHAR)), 2) AS uf_ocorrencia_ibge,
                   count(*) AS obitos
            FROM lake.sim_obitos WHERE uf = ? AND ano = ?
            GROUP BY ALL ORDER BY obitos DESC
        """,
    }
    _parametros = [escopos[0].uf, escopos[0].ano]
    with odb.LakeReader(plano["target"], snapshot_id=snapshot_id) as _leitor:
        resultados = {
            nome: _leitor.connect().execute(sql, _parametros).pl()
            for nome, sql in consultas.items()
        }
    mo.vstack(
        [
            mo.md(
                "## 5 · Analisar\n\n"
                f"Consultas sobre o snapshot `{snapshot_id}`: com o mesmo número, a "
                "consulta devolve as mesmas linhas mesmo depois de novas importações. "
                "Os códigos aparecem como publicados; o perfil explica cada um, e a "
                "diferença entre residência e ocorrência."
            ),
            mo.ui.tabs(
                {
                    nome: mo.vstack(
                        [
                            mo.ui.table(tabela, selection=None),
                            mo.accordion({"SQL": mo.md(f"```sql\n{consultas[nome]}\n```")}),
                        ]
                    )
                    for nome, tabela in resultados.items()
                }
            ),
        ]
    )
    return consultas, resultados


@app.cell
def _(consultas, mo, pasta, plano, publicacoes, registrar_proveniencia, resultados, snapshot_id):
    registrar_proveniencia(
        pasta, plano=plano, publicacoes=publicacoes, snapshot_id=snapshot_id, consultas=consultas
    )
    for _nome, _tabela in resultados.items():
        _tabela.write_csv(pasta / f"{_nome}.csv")
    mo.vstack(
        [
            mo.md(
                "## 6 · Guardar\n\n"
                f"Resultados e `proveniencia.json` gravados em `{pasta}`. Para citar: "
                "arquivo e SHA-256 de cada publicação, `snapshot_id`, versão do "
                "omnisus-db e data de acesso — veja "
                "[Reprodutibilidade](https://raphaelfh.github.io/omnisus-db/pesquisa/reprodutibilidade/)."
            ),
            mo.hstack(
                [
                    mo.download(
                        (pasta / f"{nome}.csv").read_bytes(),
                        filename=f"{plano['dataset']}-{nome}.csv",
                        label=f"CSV · {nome}",
                    )
                    for nome in resultados
                ],
                wrap=True,
            ),
            mo.download(
                (pasta / "proveniencia.json").read_bytes(),
                filename=f"{plano['dataset']}-proveniencia.json",
                label="proveniencia.json",
            ),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
```

- [ ] **Step 2: Lint, marimo check, offline test**

```bash
uv run ruff check --fix notebooks/bases/sim_obitos.py && uv run ruff format notebooks/bases/sim_obitos.py
uv run marimo check --strict --ignore-scripts notebooks
uv run pytest tests/unit/notebooks/test_notebooks_abrem_offline.py -q
```

Expected: no lint errors, marimo check exit 0, 9 passed. `marimo check` may ask to reorder the returned names; accept its `--fix` output only if the diff is ordering.

- [ ] **Step 3: Falsify both guarantees**

a) In the step-2 cell change `mo.stop(not (executar or descobrir.value), ...)` to `mo.stop(False, ...)`. Run `uv run pytest tests/unit/notebooks/test_notebooks_abrem_offline.py -q -k sim_obitos` → FAIL (`network: unit test attempted to LIST`). Restore.

b) In the plan cell change `mo.stop(not (executar or fixar.value), ...)` to `mo.stop(False, ...)`. Run the same → FAIL (`wrote to the research lake on open`). Restore the original line; re-run → pass.

- [ ] **Step 4: Commit**

```bash
git add notebooks/bases/sim_obitos.py
git commit -m "Rewrite the SIM notebook as the six-step reference for bases

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

The real run of this notebook happens in Task 19.

---

### Task 7: `notebooks/bases/sinasc_nascidos_vivos.py`

**Files:**
- Create: `notebooks/bases/sinasc_nascidos_vivos.py`
- Modify: `tests/unit/notebooks/test_notebooks_abrem_offline.py` (`ESPERADOS`)

**Interfaces:**
- Consumes: `_comum` (Task 5); layout of `bases/sim_obitos.py` (Task 6).
- Produces: nothing new.

- [ ] **Step 1: Add the notebook to the offline test and watch it fail**

Add `"bases/sinasc_nascidos_vivos.py",` to `ESPERADOS`.
Run: `uv run pytest tests/unit/notebooks/test_notebooks_abrem_offline.py -q`
Expected: `test_every_notebook_is_checked` FAILS (the set lacks the new file).

- [ ] **Step 2: Create the notebook**

```python
"""SINASC · nascidos vivos: do arquivo do DATASUS a uma tabela citável, em seis etapas."""

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", app_title="SINASC · nascidos vivos")


@app.cell
def _():
    import asyncio
    from dataclasses import asdict

    import marimo as mo
    from _comum import (
        LIMITE_BYTES,
        conferir,
        executar_sem_botoes,
        fixar_plano,
        registrar_importacao,
        registrar_proveniencia,
        target_padrao,
    )

    import omnisus_db as odb
    from omnisus_db.transforms.dictionaries import load_dicionario

    dataset = "sinasc_nascidos_vivos"
    executar = executar_sem_botoes(mo.cli_args())
    return (
        LIMITE_BYTES,
        asdict,
        asyncio,
        conferir,
        dataset,
        executar,
        fixar_plano,
        load_dicionario,
        mo,
        odb,
        registrar_importacao,
        registrar_proveniencia,
        target_padrao,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # SINASC · nascidos vivos

    Base do Sistema de Informações sobre Nascidos Vivos (SINASC), publicada pelo
    DATASUS. Este notebook percorre as seis etapas do
    [guia do pesquisador](https://raphaelfh.github.io/omnisus-db/pesquisa/) com um
    recorte pequeno: **Roraima, 2022**.

    **Abrir este notebook não baixa nem grava nada.** Cada etapa com rede ou escrita
    começa por um botão. Os dados vão para o lake de pesquisa compartilhado
    (`data/lake/pesquisa/`), o mesmo dos outros notebooks de `bases/`.

    Antes de interpretar números, leia o
    [perfil do SINASC](https://raphaelfh.github.io/omnisus-db/sources/sinasc_nascidos_vivos/).
    """)
    return


@app.cell
def _(dataset, load_dicionario, mo):
    _dicionario = load_dicionario(dataset)
    mo.vstack(
        [
            mo.md(
                "## 1 · O que a base registra\n\n"
                "Campos do dicionário que a biblioteca aplica na importação. "
                "O significado dos códigos está no perfil e no documento oficial citado nele."
            ),
            mo.ui.table(
                [
                    {"campo": f["name"], "tipo": f["type"], "rótulo": f.get("label", "")}
                    for f in _dicionario.fields
                ],
                selection=None,
                page_size=10,
            ),
        ]
    )
    return


@app.cell
def _(mo):
    descobrir = mo.ui.run_button(label="Consultar o que o DATASUS publica")
    mo.vstack(
        [
            mo.md(
                "## 2 · Descobrir\n\n"
                "Lista agora o FTP do DATASUS (`refresh=True`). A coluna `diretorio` "
                "diz se cada ano está no diretório final ou no preliminar."
            ),
            descobrir,
        ]
    )
    return (descobrir,)


@app.cell
async def _(asyncio, dataset, descobrir, executar, mo, odb):
    mo.stop(not (executar or descobrir.value), mo.md("A consulta começa pelo botão acima."))
    _publicados = await asyncio.to_thread(
        odb.available_releases, dataset, ufs=["RR"], refresh=True
    )
    mo.ui.table(
        [
            {"uf": e.uf, "ano": e.ano, "diretorio": r}
            for e, r in sorted(_publicados.items(), key=lambda item: -item[0].ano)
        ],
        selection=None,
        label="Arquivos publicados para RR",
    )
    return


@app.cell
def _(mo, odb, target_padrao):
    uf = mo.ui.dropdown(list(odb.ALL_UFS), value="RR", label="UF do arquivo")
    ano = mo.ui.number(start=1994, stop=2100, step=1, value=2022, label="Ano")
    target = mo.ui.text(value=target_padrao(), label="Lake", full_width=True)
    fixar = mo.ui.run_button(label="Fixar o plano")
    mo.vstack(
        [
            mo.md(
                "## 3 · Planejar e importar\n\n"
                "Confira o ano na etapa 2. Fixar o plano grava `plano.json` com um "
                "`run_id` antes de qualquer download."
            ),
            mo.hstack([uf, ano]),
            target,
            fixar,
        ]
    )
    return ano, fixar, target, uf


@app.cell
def _(LIMITE_BYTES, ano, asdict, dataset, executar, fixar, fixar_plano, mo, odb, target, uf):
    mo.stop(not (executar or fixar.value), mo.md("Fixe o plano para continuar."))
    escopos = odb.scopes_for(dataset, years=[int(ano.value)], ufs=[uf.value])
    plano, pasta = fixar_plano(
        target.value,
        dataset=dataset,
        escopos=[asdict(e) for e in escopos],
        policy="skip_same",
        limite_bytes=LIMITE_BYTES,
    )
    importar = mo.ui.run_button(label="Baixar e publicar este plano")
    mo.vstack([mo.md(f"Plano gravado em `{pasta / 'plano.json'}`."), mo.json(plano), importar])
    return escopos, importar, pasta, plano


@app.cell
async def _(
    LIMITE_BYTES, asyncio, escopos, executar, importar, mo, odb, pasta, plano, registrar_importacao
):
    mo.stop(not (executar or importar.value), mo.md("O download só começa pelo botão acima."))
    mo.output.append(
        mo.md(
            "Importando. Interromper a célula não cancela a thread: espere terminar "
            "antes de outra escrita no mesmo lake."
        )
    )
    try:
        relatorio = await asyncio.to_thread(
            odb.import_dataset,
            plano["dataset"],
            scopes=escopos,
            target=plano["target"],
            policy="skip_same",
            run_id=plano["run_id"],
            concurrency=1,
            max_payload_bytes=LIMITE_BYTES,
            max_inflight_bytes=LIMITE_BYTES,
        )
        _nao_resolvidos = ()
    except odb.ImportAbortedError as _erro:
        relatorio, _nao_resolvidos = _erro.report, _erro.unresolved
    _linhas = registrar_importacao(pasta, relatorio, _nao_resolvidos)
    if executar and (relatorio.failed or _nao_resolvidos):
        raise RuntimeError(f"Importação incompleta; veja {pasta / 'resultado.json'}")
    mo.vstack(
        [
            mo.ui.table(_linhas, selection=None, label="Desfecho por escopo"),
            mo.md(
                "`skipped` com *same source and parser version already published* quer "
                "dizer que o mesmo arquivo já estava no lake: nada foi duplicado. "
                "Um arquivo que o DATASUS não publica também aparece como `skipped`."
            ),
        ]
    )
    return (relatorio,)


@app.cell
def _(conferir, dataset, escopos, mo, odb, plano, relatorio):
    with odb.LakeReader(plano["target"]) as _leitor:
        mo.stop(
            dataset not in _leitor.tables(),
            mo.md("Nenhuma tabela publicada; veja os desfechos acima."),
        )
        _desta_execucao = _leitor.publications(run_id=plano["run_id"])
        _conferencia, publicacoes = conferir(_leitor, dataset, escopos)
        snapshot_id = _leitor.snapshots()[-1]["snapshot_id"]
        # refresh=False reaproveita a listagem da etapa 2: o FTP é um recurso público.
        _desatualizados = odb.outdated(dataset, lake=_leitor)
    mo.vstack(
        [
            mo.md(
                "## 4 · Conferir\n\n"
                f"O relatório informou **{relatorio.rows:,} linhas novas**. Abaixo, as "
                "publicações desta execução, a contagem no lake contra o manifesto e os "
                "escopos que o DATASUS moveu de diretório desde a importação (`outdated`)."
            ),
            mo.ui.table(_desta_execucao, selection=None, label="publications(run_id=...)"),
            mo.ui.table(_conferencia, selection=None, label="Linhas no lake × publicadas"),
            mo.md(f"Desatualizados: `{[str(e) for e in _desatualizados]}` · snapshot `{snapshot_id}`"),
        ]
    )
    return publicacoes, snapshot_id


@app.cell
def _(escopos, mo, odb, plano, snapshot_id):
    consultas = {
        "nascidos_por_municipio_de_residencia": """
            SELECT trim(CAST(codmunres AS VARCHAR)) AS municipio_residencia,
                   count(*) AS nascidos_vivos
            FROM lake.sinasc_nascidos_vivos WHERE uf = ? AND ano = ?
            GROUP BY ALL ORDER BY nascidos_vivos DESC
        """,
        "peso_ao_nascer": """
            SELECT count(*) AS nascidos_vivos,
                   count(TRY_CAST(peso AS INTEGER)) AS com_peso_numerico,
                   count(*) FILTER (WHERE TRY_CAST(peso AS INTEGER) < 2500)
                       AS peso_abaixo_de_2500_g
            FROM lake.sinasc_nascidos_vivos WHERE uf = ? AND ano = ?
        """,
        "consultas_pre_natal": """
            SELECT trim(CAST(consultas AS VARCHAR)) AS consultas_codigo, count(*) AS nascidos_vivos
            FROM lake.sinasc_nascidos_vivos WHERE uf = ? AND ano = ?
            GROUP BY ALL ORDER BY consultas_codigo
        """,
        "tipo_de_parto": """
            SELECT trim(CAST(parto AS VARCHAR)) AS parto_codigo, count(*) AS nascidos_vivos
            FROM lake.sinasc_nascidos_vivos WHERE uf = ? AND ano = ?
            GROUP BY ALL ORDER BY parto_codigo
        """,
    }
    _parametros = [escopos[0].uf, escopos[0].ano]
    with odb.LakeReader(plano["target"], snapshot_id=snapshot_id) as _leitor:
        resultados = {
            nome: _leitor.connect().execute(sql, _parametros).pl()
            for nome, sql in consultas.items()
        }
    mo.vstack(
        [
            mo.md(
                "## 5 · Analisar\n\n"
                f"Consultas sobre o snapshot `{snapshot_id}`. `com_peso_numerico` mostra "
                "quantos registros têm peso utilizável antes de qualquer proporção. Os "
                "códigos aparecem como publicados; o perfil explica cada um."
            ),
            mo.ui.tabs(
                {
                    nome: mo.vstack(
                        [
                            mo.ui.table(tabela, selection=None),
                            mo.accordion({"SQL": mo.md(f"```sql\n{consultas[nome]}\n```")}),
                        ]
                    )
                    for nome, tabela in resultados.items()
                }
            ),
        ]
    )
    return consultas, resultados


@app.cell
def _(consultas, mo, pasta, plano, publicacoes, registrar_proveniencia, resultados, snapshot_id):
    registrar_proveniencia(
        pasta, plano=plano, publicacoes=publicacoes, snapshot_id=snapshot_id, consultas=consultas
    )
    for _nome, _tabela in resultados.items():
        _tabela.write_csv(pasta / f"{_nome}.csv")
    mo.vstack(
        [
            mo.md(
                "## 6 · Guardar\n\n"
                f"Resultados e `proveniencia.json` gravados em `{pasta}`. Veja "
                "[Reprodutibilidade](https://raphaelfh.github.io/omnisus-db/pesquisa/reprodutibilidade/)."
            ),
            mo.hstack(
                [
                    mo.download(
                        (pasta / f"{nome}.csv").read_bytes(),
                        filename=f"{plano['dataset']}-{nome}.csv",
                        label=f"CSV · {nome}",
                    )
                    for nome in resultados
                ],
                wrap=True,
            ),
            mo.download(
                (pasta / "proveniencia.json").read_bytes(),
                filename=f"{plano['dataset']}-proveniencia.json",
                label="proveniencia.json",
            ),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
```

- [ ] **Step 3: Lint, check, pass**

```bash
uv run ruff check --fix notebooks/bases/sinasc_nascidos_vivos.py && uv run ruff format notebooks/bases/sinasc_nascidos_vivos.py
uv run marimo check --strict --ignore-scripts notebooks
uv run pytest tests/unit/notebooks/test_notebooks_abrem_offline.py -q
```

Expected: exit 0; 10 passed.

- [ ] **Step 4: Falsify the write guarantee**

Change the plan cell's `mo.stop(not (executar or fixar.value), ...)` to `mo.stop(False, ...)`; run `-k sinasc` → FAIL (`wrote to the research lake on open`). Restore; re-run → pass.

- [ ] **Step 5: Commit**

```bash
git add notebooks/bases/sinasc_nascidos_vivos.py tests/unit/notebooks/test_notebooks_abrem_offline.py
git commit -m "Add the SINASC notebook

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: `notebooks/bases/sih_aih_reduzida.py`

**Files:**
- Create: `notebooks/bases/sih_aih_reduzida.py`
- Modify: `tests/unit/notebooks/test_notebooks_abrem_offline.py` (`ESPERADOS`)

**Interfaces:**
- Consumes: `_comum` (Task 5); layout of Task 6. SIH is monthly and has no preliminary directory: step 2 uses `odb.available`, the plan adds a month.

- [ ] **Step 1: Add to the offline test and watch it fail**

Add `"bases/sih_aih_reduzida.py",` to `ESPERADOS`. Run the offline test: `test_every_notebook_is_checked` FAILS.

- [ ] **Step 2: Create the notebook**

```python
"""SIH · AIH reduzida: do arquivo do DATASUS a uma tabela citável, em seis etapas."""

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", app_title="SIH · AIH reduzida")


@app.cell
def _():
    import asyncio
    from dataclasses import asdict

    import marimo as mo
    from _comum import (
        LIMITE_BYTES,
        conferir,
        executar_sem_botoes,
        fixar_plano,
        registrar_importacao,
        registrar_proveniencia,
        target_padrao,
    )

    import omnisus_db as odb
    from omnisus_db.transforms.dictionaries import load_dicionario

    dataset = "sih_aih_reduzida"
    executar = executar_sem_botoes(mo.cli_args())
    return (
        LIMITE_BYTES,
        asdict,
        asyncio,
        conferir,
        dataset,
        executar,
        fixar_plano,
        load_dicionario,
        mo,
        odb,
        registrar_importacao,
        registrar_proveniencia,
        target_padrao,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # SIH · AIH reduzida

    Autorizações de internação hospitalar (AIH) do Sistema de Informações
    Hospitalares do SUS (SIH/SUS), publicadas pelo DATASUS por UF e mês. Este
    notebook percorre as seis etapas do
    [guia do pesquisador](https://raphaelfh.github.io/omnisus-db/pesquisa/) com um
    recorte pequeno: **Roraima, janeiro de 2024**.

    **Abrir este notebook não baixa nem grava nada.** Cada etapa com rede ou escrita
    começa por um botão. Os dados vão para o lake de pesquisa compartilhado.

    Uma AIH não é um paciente. Antes de interpretar números, leia o
    [perfil do SIH](https://raphaelfh.github.io/omnisus-db/sources/sih_aih_reduzida/).
    """)
    return


@app.cell
def _(dataset, load_dicionario, mo):
    _dicionario = load_dicionario(dataset)
    mo.vstack(
        [
            mo.md(
                "## 1 · O que a base registra\n\n"
                "Campos do dicionário que a biblioteca aplica na importação. "
                "O significado dos códigos está no perfil e no documento oficial citado nele."
            ),
            mo.ui.table(
                [
                    {"campo": f["name"], "tipo": f["type"], "rótulo": f.get("label", "")}
                    for f in _dicionario.fields
                ],
                selection=None,
                page_size=10,
            ),
        ]
    )
    return


@app.cell
def _(mo):
    descobrir = mo.ui.run_button(label="Consultar o que o DATASUS publica")
    mo.vstack(
        [
            mo.md(
                "## 2 · Descobrir\n\n"
                "Lista agora o FTP do DATASUS (`refresh=True`): um arquivo por UF e mês."
            ),
            descobrir,
        ]
    )
    return (descobrir,)


@app.cell
async def _(asyncio, dataset, descobrir, executar, mo, odb):
    mo.stop(not (executar or descobrir.value), mo.md("A consulta começa pelo botão acima."))
    _publicados = await asyncio.to_thread(odb.available, dataset, ufs=["RR"], refresh=True)
    mo.ui.table(
        [
            {"uf": e.uf, "ano": e.ano, "mes": e.mes}
            for e in sorted(_publicados, key=lambda e: (-e.ano, -(e.mes or 0)))
        ],
        selection=None,
        label="Arquivos publicados para RR",
    )
    return


@app.cell
def _(mo, odb, target_padrao):
    uf = mo.ui.dropdown(list(odb.ALL_UFS), value="RR", label="UF do arquivo")
    ano = mo.ui.number(start=2008, stop=2100, step=1, value=2024, label="Ano")
    mes = mo.ui.number(start=1, stop=12, step=1, value=1, label="Mês")
    target = mo.ui.text(value=target_padrao(), label="Lake", full_width=True)
    fixar = mo.ui.run_button(label="Fixar o plano")
    mo.vstack(
        [
            mo.md(
                "## 3 · Planejar e importar\n\n"
                "Confira ano e mês na etapa 2. Fixar o plano grava `plano.json` com um "
                "`run_id` antes de qualquer download."
            ),
            mo.hstack([uf, ano, mes]),
            target,
            fixar,
        ]
    )
    return ano, fixar, mes, target, uf


@app.cell
def _(
    LIMITE_BYTES, ano, asdict, dataset, executar, fixar, fixar_plano, mes, mo, odb, target, uf
):
    mo.stop(not (executar or fixar.value), mo.md("Fixe o plano para continuar."))
    escopos = odb.scopes_for(
        dataset, years=[int(ano.value)], ufs=[uf.value], months=[int(mes.value)]
    )
    plano, pasta = fixar_plano(
        target.value,
        dataset=dataset,
        escopos=[asdict(e) for e in escopos],
        policy="skip_same",
        limite_bytes=LIMITE_BYTES,
    )
    importar = mo.ui.run_button(label="Baixar e publicar este plano")
    mo.vstack([mo.md(f"Plano gravado em `{pasta / 'plano.json'}`."), mo.json(plano), importar])
    return escopos, importar, pasta, plano


@app.cell
async def _(
    LIMITE_BYTES, asyncio, escopos, executar, importar, mo, odb, pasta, plano, registrar_importacao
):
    mo.stop(not (executar or importar.value), mo.md("O download só começa pelo botão acima."))
    mo.output.append(
        mo.md(
            "Importando. Interromper a célula não cancela a thread: espere terminar "
            "antes de outra escrita no mesmo lake."
        )
    )
    try:
        relatorio = await asyncio.to_thread(
            odb.import_dataset,
            plano["dataset"],
            scopes=escopos,
            target=plano["target"],
            policy="skip_same",
            run_id=plano["run_id"],
            concurrency=1,
            max_payload_bytes=LIMITE_BYTES,
            max_inflight_bytes=LIMITE_BYTES,
        )
        _nao_resolvidos = ()
    except odb.ImportAbortedError as _erro:
        relatorio, _nao_resolvidos = _erro.report, _erro.unresolved
    _linhas = registrar_importacao(pasta, relatorio, _nao_resolvidos)
    if executar and (relatorio.failed or _nao_resolvidos):
        raise RuntimeError(f"Importação incompleta; veja {pasta / 'resultado.json'}")
    mo.vstack(
        [
            mo.ui.table(_linhas, selection=None, label="Desfecho por escopo"),
            mo.md(
                "`skipped` com *same source and parser version already published* quer "
                "dizer que o mesmo arquivo já estava no lake: nada foi duplicado. "
                "Um arquivo que o DATASUS não publica também aparece como `skipped`."
            ),
        ]
    )
    return (relatorio,)


@app.cell
def _(conferir, dataset, escopos, mo, odb, plano, relatorio):
    with odb.LakeReader(plano["target"]) as _leitor:
        mo.stop(
            dataset not in _leitor.tables(),
            mo.md("Nenhuma tabela publicada; veja os desfechos acima."),
        )
        _desta_execucao = _leitor.publications(run_id=plano["run_id"])
        _conferencia, publicacoes = conferir(_leitor, dataset, escopos)
        snapshot_id = _leitor.snapshots()[-1]["snapshot_id"]
    mo.vstack(
        [
            mo.md(
                "## 4 · Conferir\n\n"
                f"O relatório informou **{relatorio.rows:,} linhas novas**. Abaixo, as "
                "publicações desta execução e a contagem no lake contra o manifesto. "
                "O SIH é publicado num único diretório, então `outdated` não se aplica."
            ),
            mo.ui.table(_desta_execucao, selection=None, label="publications(run_id=...)"),
            mo.ui.table(_conferencia, selection=None, label="Linhas no lake × publicadas"),
            mo.md(f"Snapshot `{snapshot_id}`"),
        ]
    )
    return publicacoes, snapshot_id


@app.cell
def _(escopos, mo, odb, plano, snapshot_id):
    consultas = {
        "aih_por_diagnostico_principal": """
            SELECT left(upper(trim(CAST(diag_princ AS VARCHAR))), 3) AS diagnostico_cid10_3,
                   count(*) AS aih,
                   sum(TRY_CAST(dias_perm AS INTEGER)) AS dias_de_permanencia,
                   round(avg(TRY_CAST(dias_perm AS INTEGER)), 1) AS media_dias,
                   round(sum(TRY_CAST(val_tot AS DOUBLE)), 2) AS valor_total
            FROM lake.sih_aih_reduzida WHERE uf = ? AND ano = ? AND mes = ?
            GROUP BY ALL ORDER BY aih DESC
        """,
        "campo_morte": """
            SELECT trim(CAST(morte AS VARCHAR)) AS morte_codigo, count(*) AS aih
            FROM lake.sih_aih_reduzida WHERE uf = ? AND ano = ? AND mes = ?
            GROUP BY ALL ORDER BY morte_codigo
        """,
        "aih_distintas": """
            SELECT count(*) AS linhas, count(DISTINCT n_aih) AS numeros_de_aih_distintos
            FROM lake.sih_aih_reduzida WHERE uf = ? AND ano = ? AND mes = ?
        """,
    }
    _parametros = [escopos[0].uf, escopos[0].ano, escopos[0].mes]
    with odb.LakeReader(plano["target"], snapshot_id=snapshot_id) as _leitor:
        resultados = {
            nome: _leitor.connect().execute(sql, _parametros).pl()
            for nome, sql in consultas.items()
        }
    mo.vstack(
        [
            mo.md(
                "## 5 · Analisar\n\n"
                f"Consultas sobre o snapshot `{snapshot_id}`. `aih_distintas` compara "
                "linhas e números de AIH antes de qualquer contagem de internações. Os "
                "códigos aparecem como publicados; o perfil explica cada um."
            ),
            mo.ui.tabs(
                {
                    nome: mo.vstack(
                        [
                            mo.ui.table(tabela, selection=None),
                            mo.accordion({"SQL": mo.md(f"```sql\n{consultas[nome]}\n```")}),
                        ]
                    )
                    for nome, tabela in resultados.items()
                }
            ),
        ]
    )
    return consultas, resultados


@app.cell
def _(consultas, mo, pasta, plano, publicacoes, registrar_proveniencia, resultados, snapshot_id):
    registrar_proveniencia(
        pasta, plano=plano, publicacoes=publicacoes, snapshot_id=snapshot_id, consultas=consultas
    )
    for _nome, _tabela in resultados.items():
        _tabela.write_csv(pasta / f"{_nome}.csv")
    mo.vstack(
        [
            mo.md(
                "## 6 · Guardar\n\n"
                f"Resultados e `proveniencia.json` gravados em `{pasta}`. Veja "
                "[Reprodutibilidade](https://raphaelfh.github.io/omnisus-db/pesquisa/reprodutibilidade/)."
            ),
            mo.hstack(
                [
                    mo.download(
                        (pasta / f"{nome}.csv").read_bytes(),
                        filename=f"{plano['dataset']}-{nome}.csv",
                        label=f"CSV · {nome}",
                    )
                    for nome in resultados
                ],
                wrap=True,
            ),
            mo.download(
                (pasta / "proveniencia.json").read_bytes(),
                filename=f"{plano['dataset']}-proveniencia.json",
                label="proveniencia.json",
            ),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
```

- [ ] **Step 3: Lint, check, pass**

```bash
uv run ruff check --fix notebooks/bases/sih_aih_reduzida.py && uv run ruff format notebooks/bases/sih_aih_reduzida.py
uv run marimo check --strict --ignore-scripts notebooks
uv run pytest tests/unit/notebooks/test_notebooks_abrem_offline.py -q
```

Expected: exit 0; 11 passed.

- [ ] **Step 4: Falsify the write guarantee**

Change the plan cell's gate to `mo.stop(False, ...)`; run `-k sih` → FAIL. Restore; re-run → pass.

- [ ] **Step 5: Commit**

```bash
git add notebooks/bases/sih_aih_reduzida.py tests/unit/notebooks/test_notebooks_abrem_offline.py
git commit -m "Add the SIH notebook

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: `notebooks/bases/sia.py`

**Files:**
- Create: `notebooks/bases/sia.py`
- Modify: `tests/unit/notebooks/test_notebooks_abrem_offline.py` (`ESPERADOS`)

**Interfaces:**
- Consumes: `_comum` (Task 5); layout of Task 6. The seven SIA tables are monthly, one directory, state files. The table is chosen in the notebook; everything after the plan uses `plano["dataset"]`, never the dropdown, so changing the dropdown cannot mix tables.
- Analyses exist for three tables whose fields were verified in the packaged dictionaries (APAC medicamentos `ap_pripal`, `ap_vl_ap`; BPA-I `proc_id`, `qt_aprov`; psicossocial `pa_proc_id`, `cidpri`). The other four show a row count and point to the dictionary.

- [ ] **Step 1: Add to the offline test and watch it fail**

Add `"bases/sia.py",` to `ESPERADOS`; run the offline test → `test_every_notebook_is_checked` FAILS.

- [ ] **Step 2: Create the notebook**

```python
"""SIA · produção ambulatorial: escolha uma das sete tabelas e siga as seis etapas."""

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", app_title="SIA · produção ambulatorial")


@app.cell
def _():
    import asyncio
    from dataclasses import asdict

    import marimo as mo
    from _comum import (
        LIMITE_BYTES,
        conferir,
        executar_sem_botoes,
        fixar_plano,
        registrar_importacao,
        registrar_proveniencia,
        target_padrao,
    )

    import omnisus_db as odb
    from omnisus_db.transforms.dictionaries import load_dicionario

    TABELAS = {
        "sia_bpa_individualizado": "BPA individualizado",
        "sia_apac_medicamentos": "APAC · medicamentos",
        "sia_apac_quimioterapia": "APAC · quimioterapia",
        "sia_apac_tratamento_dialitico": "APAC · tratamento dialítico",
        "sia_apac_laudos_diversos": "APAC · laudos diversos",
        "sia_apac_cirurgia_bariatrica": "APAC · cirurgia bariátrica",
        "sia_psicossocial": "RAAS · atenção psicossocial",
    }
    executar = executar_sem_botoes(mo.cli_args())
    return (
        LIMITE_BYTES,
        TABELAS,
        asdict,
        asyncio,
        conferir,
        executar,
        fixar_plano,
        load_dicionario,
        mo,
        odb,
        registrar_importacao,
        registrar_proveniencia,
        target_padrao,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # SIA · produção ambulatorial

    O Sistema de Informações Ambulatoriais do SUS (SIA/SUS) é publicado pelo DATASUS
    em várias tabelas, por UF e mês; a biblioteca importa sete. Escolha uma e siga as
    seis etapas do [guia do pesquisador](https://raphaelfh.github.io/omnisus-db/pesquisa/)
    com um recorte pequeno: **Roraima, janeiro de 2024**.

    **Abrir este notebook não baixa nem grava nada.** Cada etapa com rede ou escrita
    começa por um botão.

    Cada tabela registra uma coisa diferente. Antes de interpretar números, leia o
    [perfil do SIA](https://raphaelfh.github.io/omnisus-db/sources/sia/).
    """)
    return


@app.cell
def _(TABELAS, mo):
    tabela = mo.ui.dropdown(
        {rotulo: nome for nome, rotulo in TABELAS.items()},
        value="BPA individualizado",
        label="Tabela do SIA",
    )
    tabela
    return (tabela,)


@app.cell
def _(load_dicionario, mo, tabela):
    _dicionario = load_dicionario(tabela.value)
    mo.vstack(
        [
            mo.md(
                f"## 1 · O que a tabela `{tabela.value}` registra\n\n"
                "Campos do dicionário que a biblioteca aplica na importação. "
                "O significado dos códigos está no perfil e no documento oficial citado nele."
            ),
            mo.ui.table(
                [
                    {"campo": f["name"], "tipo": f["type"], "rótulo": f.get("label", "")}
                    for f in _dicionario.fields
                ],
                selection=None,
                page_size=10,
            ),
        ]
    )
    return


@app.cell
def _(mo):
    descobrir = mo.ui.run_button(label="Consultar o que o DATASUS publica")
    mo.vstack(
        [
            mo.md(
                "## 2 · Descobrir\n\n"
                "Lista agora o diretório do SIA no FTP (`refresh=True`) e filtra os "
                "arquivos da tabela escolhida."
            ),
            descobrir,
        ]
    )
    return (descobrir,)


@app.cell
async def _(asyncio, descobrir, executar, mo, odb, tabela):
    mo.stop(not (executar or descobrir.value), mo.md("A consulta começa pelo botão acima."))
    _publicados = await asyncio.to_thread(odb.available, tabela.value, ufs=["RR"], refresh=True)
    mo.ui.table(
        [
            {"uf": e.uf, "ano": e.ano, "mes": e.mes}
            for e in sorted(_publicados, key=lambda e: (-e.ano, -(e.mes or 0)))
        ],
        selection=None,
        label=f"Arquivos de {tabela.value} publicados para RR",
    )
    return


@app.cell
def _(mo, odb, target_padrao):
    uf = mo.ui.dropdown(list(odb.ALL_UFS), value="RR", label="UF do arquivo")
    ano = mo.ui.number(start=2008, stop=2100, step=1, value=2024, label="Ano")
    mes = mo.ui.number(start=1, stop=12, step=1, value=1, label="Mês")
    target = mo.ui.text(value=target_padrao(), label="Lake", full_width=True)
    fixar = mo.ui.run_button(label="Fixar o plano")
    mo.vstack(
        [
            mo.md(
                "## 3 · Planejar e importar\n\n"
                "Confira ano e mês na etapa 2. O plano guarda a tabela escolhida; mudar a "
                "tabela depois exige fixar um novo plano."
            ),
            mo.hstack([uf, ano, mes]),
            target,
            fixar,
        ]
    )
    return ano, fixar, mes, target, uf


@app.cell
def _(
    LIMITE_BYTES, ano, asdict, executar, fixar, fixar_plano, mes, mo, odb, tabela, target, uf
):
    mo.stop(not (executar or fixar.value), mo.md("Fixe o plano para continuar."))
    escopos = odb.scopes_for(
        tabela.value, years=[int(ano.value)], ufs=[uf.value], months=[int(mes.value)]
    )
    plano, pasta = fixar_plano(
        target.value,
        dataset=tabela.value,
        escopos=[asdict(e) for e in escopos],
        policy="skip_same",
        limite_bytes=LIMITE_BYTES,
    )
    importar = mo.ui.run_button(label="Baixar e publicar este plano")
    mo.vstack([mo.md(f"Plano gravado em `{pasta / 'plano.json'}`."), mo.json(plano), importar])
    return escopos, importar, pasta, plano


@app.cell
async def _(
    LIMITE_BYTES, asyncio, escopos, executar, importar, mo, odb, pasta, plano, registrar_importacao
):
    mo.stop(not (executar or importar.value), mo.md("O download só começa pelo botão acima."))
    mo.output.append(
        mo.md(
            "Importando. Interromper a célula não cancela a thread: espere terminar "
            "antes de outra escrita no mesmo lake."
        )
    )
    try:
        relatorio = await asyncio.to_thread(
            odb.import_dataset,
            plano["dataset"],
            scopes=escopos,
            target=plano["target"],
            policy="skip_same",
            run_id=plano["run_id"],
            concurrency=1,
            max_payload_bytes=LIMITE_BYTES,
            max_inflight_bytes=LIMITE_BYTES,
        )
        _nao_resolvidos = ()
    except odb.ImportAbortedError as _erro:
        relatorio, _nao_resolvidos = _erro.report, _erro.unresolved
    _linhas = registrar_importacao(pasta, relatorio, _nao_resolvidos)
    if executar and (relatorio.failed or _nao_resolvidos):
        raise RuntimeError(f"Importação incompleta; veja {pasta / 'resultado.json'}")
    mo.vstack(
        [
            mo.ui.table(_linhas, selection=None, label="Desfecho por escopo"),
            mo.md(
                "`skipped` com *same source and parser version already published* quer "
                "dizer que o mesmo arquivo já estava no lake: nada foi duplicado. "
                "Um arquivo que o DATASUS não publica também aparece como `skipped`: "
                "nem toda tabela existe para toda UF e mês."
            ),
        ]
    )
    return (relatorio,)


@app.cell
def _(conferir, escopos, mo, odb, plano, relatorio):
    with odb.LakeReader(plano["target"]) as _leitor:
        mo.stop(
            plano["dataset"] not in _leitor.tables(),
            mo.md("Nenhuma tabela publicada; veja os desfechos acima."),
        )
        _desta_execucao = _leitor.publications(run_id=plano["run_id"])
        _conferencia, publicacoes = conferir(_leitor, plano["dataset"], escopos)
        snapshot_id = _leitor.snapshots()[-1]["snapshot_id"]
    mo.vstack(
        [
            mo.md(
                "## 4 · Conferir\n\n"
                f"O relatório informou **{relatorio.rows:,} linhas novas**. Abaixo, as "
                "publicações desta execução e a contagem no lake contra o manifesto. "
                "O SIA é publicado num único diretório, então `outdated` não se aplica."
            ),
            mo.ui.table(_desta_execucao, selection=None, label="publications(run_id=...)"),
            mo.ui.table(_conferencia, selection=None, label="Linhas no lake × publicadas"),
            mo.md(f"Snapshot `{snapshot_id}`"),
        ]
    )
    return publicacoes, snapshot_id


@app.cell
def _(escopos, mo, odb, plano, snapshot_id):
    _tabela = plano["dataset"]
    _recorte = "WHERE uf = ? AND ano = ? AND mes = ?"
    _analises = {
        "sia_apac_medicamentos": {
            "apac_por_procedimento_principal": f"""
                SELECT trim(CAST(ap_pripal AS VARCHAR)) AS procedimento_principal,
                       count(*) AS apac,
                       round(sum(TRY_CAST(ap_vl_ap AS DOUBLE)), 2) AS valor_aprovado
                FROM lake.sia_apac_medicamentos {_recorte}
                GROUP BY ALL ORDER BY apac DESC
            """
        },
        "sia_bpa_individualizado": {
            "quantidade_por_procedimento": f"""
                SELECT trim(CAST(proc_id AS VARCHAR)) AS procedimento,
                       count(*) AS registros,
                       sum(TRY_CAST(qt_aprov AS BIGINT)) AS quantidade_aprovada
                FROM lake.sia_bpa_individualizado {_recorte}
                GROUP BY ALL ORDER BY quantidade_aprovada DESC NULLS LAST
            """
        },
        "sia_psicossocial": {
            "acoes_por_cid_principal": f"""
                SELECT trim(CAST(pa_proc_id AS VARCHAR)) AS acao_realizada,
                       upper(trim(CAST(cidpri AS VARCHAR))) AS cid10_principal,
                       count(*) AS registros
                FROM lake.sia_psicossocial {_recorte}
                GROUP BY ALL ORDER BY registros DESC
            """
        },
    }
    # _tabela vem do plano, que só aceita as sete chaves de TABELAS.
    consultas = _analises.get(
        _tabela,
        {"registros_no_recorte": f'SELECT count(*) AS registros FROM lake."{_tabela}" {_recorte}'},
    )
    _parametros = [escopos[0].uf, escopos[0].ano, escopos[0].mes]
    with odb.LakeReader(plano["target"], snapshot_id=snapshot_id) as _leitor:
        resultados = {
            nome: _leitor.connect().execute(sql, _parametros).pl()
            for nome, sql in consultas.items()
        }
    _aviso = (
        ""
        if _tabela in _analises
        else "\n\nPara esta tabela os campos de análise ainda não foram verificados; "
        "a etapa mostra só a contagem. Use o dicionário da etapa 1 e o perfil."
    )
    mo.vstack(
        [
            mo.md(f"## 5 · Analisar\n\nConsultas sobre o snapshot `{snapshot_id}`.{_aviso}"),
            mo.ui.tabs(
                {
                    nome: mo.vstack(
                        [
                            mo.ui.table(tabela_resultado, selection=None),
                            mo.accordion({"SQL": mo.md(f"```sql\n{consultas[nome]}\n```")}),
                        ]
                    )
                    for nome, tabela_resultado in resultados.items()
                }
            ),
        ]
    )
    return consultas, resultados


@app.cell
def _(consultas, mo, pasta, plano, publicacoes, registrar_proveniencia, resultados, snapshot_id):
    registrar_proveniencia(
        pasta, plano=plano, publicacoes=publicacoes, snapshot_id=snapshot_id, consultas=consultas
    )
    for _nome, _resultado in resultados.items():
        _resultado.write_csv(pasta / f"{_nome}.csv")
    mo.vstack(
        [
            mo.md(
                "## 6 · Guardar\n\n"
                f"Resultados e `proveniencia.json` gravados em `{pasta}`. Veja "
                "[Reprodutibilidade](https://raphaelfh.github.io/omnisus-db/pesquisa/reprodutibilidade/)."
            ),
            mo.hstack(
                [
                    mo.download(
                        (pasta / f"{nome}.csv").read_bytes(),
                        filename=f"{plano['dataset']}-{nome}.csv",
                        label=f"CSV · {nome}",
                    )
                    for nome in resultados
                ],
                wrap=True,
            ),
            mo.download(
                (pasta / "proveniencia.json").read_bytes(),
                filename=f"{plano['dataset']}-proveniencia.json",
                label="proveniencia.json",
            ),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
```

- [ ] **Step 3: Lint, check, pass**

```bash
uv run ruff check --fix notebooks/bases/sia.py && uv run ruff format notebooks/bases/sia.py
uv run marimo check --strict --ignore-scripts notebooks
uv run pytest tests/unit/notebooks/test_notebooks_abrem_offline.py -q
```

Expected: exit 0; 12 passed. If `mo.ui.dropdown` with a dict rejects `value="BPA individualizado"`, read `uv run python -c "import marimo as mo; help(mo.ui.dropdown)"`: with a dict of options, `value` is the displayed key and `.value` is the mapped name.

- [ ] **Step 4: Falsify the write guarantee**

Change the plan cell's gate to `mo.stop(False, ...)`; run `-k sia` → FAIL. Restore; re-run → pass.

- [ ] **Step 5: Commit**

```bash
git add notebooks/bases/sia.py tests/unit/notebooks/test_notebooks_abrem_offline.py
git commit -m "Add the SIA notebook with a table selector

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 10: `notebooks/bases/cnes_estabelecimentos.py`

**Files:**
- Create: `notebooks/bases/cnes_estabelecimentos.py`
- Modify: `tests/unit/notebooks/test_notebooks_abrem_offline.py` (`ESPERADOS`)

**Interfaces:**
- Consumes: `_comum` (Task 5); layout of Task 6. CNES-ST is monthly, one directory, state files. The notebook uses `import_dataset` like the others and names `import_cnes_estabelecimentos` in text: that function also refreshes the `aux_cnes` view.

- [ ] **Step 1: Add to the offline test and watch it fail**

Add `"bases/cnes_estabelecimentos.py",` to `ESPERADOS`; run → `test_every_notebook_is_checked` FAILS.

- [ ] **Step 2: Create the notebook**

```python
"""CNES · estabelecimentos: do arquivo do DATASUS a uma tabela citável, em seis etapas."""

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", app_title="CNES · estabelecimentos")


@app.cell
def _():
    import asyncio
    from dataclasses import asdict

    import marimo as mo
    from _comum import (
        LIMITE_BYTES,
        conferir,
        executar_sem_botoes,
        fixar_plano,
        registrar_importacao,
        registrar_proveniencia,
        target_padrao,
    )

    import omnisus_db as odb
    from omnisus_db.transforms.dictionaries import load_dicionario

    dataset = "cnes_estabelecimentos"
    executar = executar_sem_botoes(mo.cli_args())
    return (
        LIMITE_BYTES,
        asdict,
        asyncio,
        conferir,
        dataset,
        executar,
        fixar_plano,
        load_dicionario,
        mo,
        odb,
        registrar_importacao,
        registrar_proveniencia,
        target_padrao,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # CNES · estabelecimentos

    Arquivo de estabelecimentos (ST) do Cadastro Nacional de Estabelecimentos de
    Saúde (CNES), publicado pelo DATASUS por UF e competência. Este notebook percorre
    as seis etapas do [guia do pesquisador](https://raphaelfh.github.io/omnisus-db/pesquisa/)
    com um recorte pequeno: **Roraima, janeiro de 2024**.

    **Abrir este notebook não baixa nem grava nada.** Cada etapa com rede ou escrita
    começa por um botão.

    O dicionário empacotado declara 12 colunas. Antes de interpretar números, leia o
    [perfil do CNES](https://raphaelfh.github.io/omnisus-db/sources/cnes_estabelecimentos/).
    """)
    return


@app.cell
def _(dataset, load_dicionario, mo):
    _dicionario = load_dicionario(dataset)
    mo.vstack(
        [
            mo.md(
                "## 1 · O que a base registra\n\n"
                "Campos do dicionário que a biblioteca aplica na importação; colunas do "
                "arquivo fora do dicionário também são preservadas."
            ),
            mo.ui.table(
                [
                    {"campo": f["name"], "tipo": f["type"], "rótulo": f.get("label", "")}
                    for f in _dicionario.fields
                ],
                selection=None,
                page_size=12,
            ),
        ]
    )
    return


@app.cell
def _(mo):
    descobrir = mo.ui.run_button(label="Consultar o que o DATASUS publica")
    mo.vstack(
        [
            mo.md("## 2 · Descobrir\n\nLista agora o FTP do DATASUS (`refresh=True`)."),
            descobrir,
        ]
    )
    return (descobrir,)


@app.cell
async def _(asyncio, dataset, descobrir, executar, mo, odb):
    mo.stop(not (executar or descobrir.value), mo.md("A consulta começa pelo botão acima."))
    _publicados = await asyncio.to_thread(odb.available, dataset, ufs=["RR"], refresh=True)
    mo.ui.table(
        [
            {"uf": e.uf, "ano": e.ano, "mes": e.mes}
            for e in sorted(_publicados, key=lambda e: (-e.ano, -(e.mes or 0)))
        ],
        selection=None,
        label="Competências publicadas para RR",
    )
    return


@app.cell
def _(mo, odb, target_padrao):
    uf = mo.ui.dropdown(list(odb.ALL_UFS), value="RR", label="UF do arquivo")
    ano = mo.ui.number(start=2005, stop=2100, step=1, value=2024, label="Ano")
    mes = mo.ui.number(start=1, stop=12, step=1, value=1, label="Mês")
    target = mo.ui.text(value=target_padrao(), label="Lake", full_width=True)
    fixar = mo.ui.run_button(label="Fixar o plano")
    mo.vstack(
        [
            mo.md(
                "## 3 · Planejar e importar\n\n"
                "Confira ano e mês na etapa 2. Fixar o plano grava `plano.json` com um "
                "`run_id` antes de qualquer download. Para também atualizar a visão "
                "`aux_cnes`, a biblioteca oferece `import_cnes_estabelecimentos`."
            ),
            mo.hstack([uf, ano, mes]),
            target,
            fixar,
        ]
    )
    return ano, fixar, mes, target, uf


@app.cell
def _(
    LIMITE_BYTES, ano, asdict, dataset, executar, fixar, fixar_plano, mes, mo, odb, target, uf
):
    mo.stop(not (executar or fixar.value), mo.md("Fixe o plano para continuar."))
    escopos = odb.scopes_for(
        dataset, years=[int(ano.value)], ufs=[uf.value], months=[int(mes.value)]
    )
    plano, pasta = fixar_plano(
        target.value,
        dataset=dataset,
        escopos=[asdict(e) for e in escopos],
        policy="skip_same",
        limite_bytes=LIMITE_BYTES,
    )
    importar = mo.ui.run_button(label="Baixar e publicar este plano")
    mo.vstack([mo.md(f"Plano gravado em `{pasta / 'plano.json'}`."), mo.json(plano), importar])
    return escopos, importar, pasta, plano


@app.cell
async def _(
    LIMITE_BYTES, asyncio, escopos, executar, importar, mo, odb, pasta, plano, registrar_importacao
):
    mo.stop(not (executar or importar.value), mo.md("O download só começa pelo botão acima."))
    mo.output.append(
        mo.md(
            "Importando. Interromper a célula não cancela a thread: espere terminar "
            "antes de outra escrita no mesmo lake."
        )
    )
    try:
        relatorio = await asyncio.to_thread(
            odb.import_dataset,
            plano["dataset"],
            scopes=escopos,
            target=plano["target"],
            policy="skip_same",
            run_id=plano["run_id"],
            concurrency=1,
            max_payload_bytes=LIMITE_BYTES,
            max_inflight_bytes=LIMITE_BYTES,
        )
        _nao_resolvidos = ()
    except odb.ImportAbortedError as _erro:
        relatorio, _nao_resolvidos = _erro.report, _erro.unresolved
    _linhas = registrar_importacao(pasta, relatorio, _nao_resolvidos)
    if executar and (relatorio.failed or _nao_resolvidos):
        raise RuntimeError(f"Importação incompleta; veja {pasta / 'resultado.json'}")
    mo.vstack(
        [
            mo.ui.table(_linhas, selection=None, label="Desfecho por escopo"),
            mo.md(
                "`skipped` com *same source and parser version already published* quer "
                "dizer que o mesmo arquivo já estava no lake: nada foi duplicado. "
                "Um arquivo que o DATASUS não publica também aparece como `skipped`."
            ),
        ]
    )
    return (relatorio,)


@app.cell
def _(conferir, dataset, escopos, mo, odb, plano, relatorio):
    with odb.LakeReader(plano["target"]) as _leitor:
        mo.stop(
            dataset not in _leitor.tables(),
            mo.md("Nenhuma tabela publicada; veja os desfechos acima."),
        )
        _desta_execucao = _leitor.publications(run_id=plano["run_id"])
        _conferencia, publicacoes = conferir(_leitor, dataset, escopos)
        snapshot_id = _leitor.snapshots()[-1]["snapshot_id"]
    mo.vstack(
        [
            mo.md(
                "## 4 · Conferir\n\n"
                f"O relatório informou **{relatorio.rows:,} linhas novas**. Abaixo, as "
                "publicações desta execução e a contagem no lake contra o manifesto. "
                "O CNES-ST é publicado num único diretório, então `outdated` não se aplica."
            ),
            mo.ui.table(_desta_execucao, selection=None, label="publications(run_id=...)"),
            mo.ui.table(_conferencia, selection=None, label="Linhas no lake × publicadas"),
            mo.md(f"Snapshot `{snapshot_id}`"),
        ]
    )
    return publicacoes, snapshot_id


@app.cell
def _(escopos, mo, odb, plano, snapshot_id):
    consultas = {
        "estabelecimentos_por_tipo": """
            SELECT trim(CAST(competen AS VARCHAR)) AS competencia,
                   trim(CAST(tp_unid AS VARCHAR)) AS tipo_de_unidade,
                   count(DISTINCT cnes) AS estabelecimentos,
                   count(*) AS linhas
            FROM lake.cnes_estabelecimentos WHERE uf = ? AND ano = ? AND mes = ?
            GROUP BY ALL ORDER BY estabelecimentos DESC
        """,
        "estabelecimentos_por_municipio": """
            SELECT trim(CAST(codufmun AS VARCHAR)) AS municipio,
                   count(DISTINCT cnes) AS estabelecimentos
            FROM lake.cnes_estabelecimentos WHERE uf = ? AND ano = ? AND mes = ?
            GROUP BY ALL ORDER BY estabelecimentos DESC
        """,
    }
    _parametros = [escopos[0].uf, escopos[0].ano, escopos[0].mes]
    with odb.LakeReader(plano["target"], snapshot_id=snapshot_id) as _leitor:
        resultados = {
            nome: _leitor.connect().execute(sql, _parametros).pl()
            for nome, sql in consultas.items()
        }
    mo.vstack(
        [
            mo.md(
                "## 5 · Analisar\n\n"
                f"Consultas sobre o snapshot `{snapshot_id}`. Compare `linhas` e "
                "`estabelecimentos` (códigos CNES distintos) antes de contar unidades. Os "
                "códigos de tipo aparecem como publicados; o perfil explica cada um."
            ),
            mo.ui.tabs(
                {
                    nome: mo.vstack(
                        [
                            mo.ui.table(tabela, selection=None),
                            mo.accordion({"SQL": mo.md(f"```sql\n{consultas[nome]}\n```")}),
                        ]
                    )
                    for nome, tabela in resultados.items()
                }
            ),
        ]
    )
    return consultas, resultados


@app.cell
def _(consultas, mo, pasta, plano, publicacoes, registrar_proveniencia, resultados, snapshot_id):
    registrar_proveniencia(
        pasta, plano=plano, publicacoes=publicacoes, snapshot_id=snapshot_id, consultas=consultas
    )
    for _nome, _tabela in resultados.items():
        _tabela.write_csv(pasta / f"{_nome}.csv")
    mo.vstack(
        [
            mo.md(
                "## 6 · Guardar\n\n"
                f"Resultados e `proveniencia.json` gravados em `{pasta}`. Veja "
                "[Reprodutibilidade](https://raphaelfh.github.io/omnisus-db/pesquisa/reprodutibilidade/)."
            ),
            mo.hstack(
                [
                    mo.download(
                        (pasta / f"{nome}.csv").read_bytes(),
                        filename=f"{plano['dataset']}-{nome}.csv",
                        label=f"CSV · {nome}",
                    )
                    for nome in resultados
                ],
                wrap=True,
            ),
            mo.download(
                (pasta / "proveniencia.json").read_bytes(),
                filename=f"{plano['dataset']}-proveniencia.json",
                label="proveniencia.json",
            ),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
```

- [ ] **Step 3: Lint, check, pass**

```bash
uv run ruff check --fix notebooks/bases/cnes_estabelecimentos.py && uv run ruff format notebooks/bases/cnes_estabelecimentos.py
uv run marimo check --strict --ignore-scripts notebooks
uv run pytest tests/unit/notebooks/test_notebooks_abrem_offline.py -q
```

Expected: exit 0; 13 passed.

- [ ] **Step 4: Falsify the write guarantee**

Change the plan cell's gate to `mo.stop(False, ...)`; run `-k cnes` → FAIL. Restore; re-run → pass.

- [ ] **Step 5: Commit**

```bash
git add notebooks/bases/cnes_estabelecimentos.py tests/unit/notebooks/test_notebooks_abrem_offline.py
git commit -m "Add the CNES notebook

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 11: `notebooks/bases/ibge_populacao.py`

**Files:**
- Create: `notebooks/bases/ibge_populacao.py`
- Modify: `tests/unit/notebooks/test_notebooks_abrem_offline.py` (`ESPERADOS`)

**Interfaces:**
- Consumes: `_comum.salvar_json`, `fixar_plano`, `registrar_proveniencia`, `executar_sem_botoes`, `target_padrao` (Task 5); `odb.import_ibge_populacao(*, years, product, target) -> list[ImportResult]`; `odb.CatalogAttachError`; `omnisus_db.sources.ibge.products.CENSUS_YEARS`, `ESTIMATE_UNAVAILABLE_YEARS`; tables `ibge_population_manifest` (columns `publication_id, product, ano, source, aggregate, variable, sha256, url, collected_at, ...`) and view `ibge_populacao(codigo_ibge, ano, populacao)`.
- IBGE is not an FTP dataset: no `available`, no `publications()`, no `policy`/`run_id`. Each import is a new publication and the view **raises** when a municipality/year has two, so the import cell checks the manifest first and imports only when the edition is absent.

- [ ] **Step 1: Add to the offline test and watch it fail**

Add `"bases/ibge_populacao.py",` to `ESPERADOS`; run → `test_every_notebook_is_checked` FAILS.

- [ ] **Step 2: Create the notebook**

```python
"""IBGE · população: a edição que serve de denominador, com proveniência."""

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", app_title="IBGE · população")


@app.cell
def _():
    import asyncio
    from dataclasses import asdict

    import marimo as mo
    from _comum import (
        executar_sem_botoes,
        fixar_plano,
        registrar_proveniencia,
        salvar_json,
        target_padrao,
    )

    import omnisus_db as odb
    from omnisus_db.sources.ibge.products import CENSUS_YEARS, ESTIMATE_UNAVAILABLE_YEARS
    from omnisus_db.transforms.dictionaries import load_dicionario

    executar = executar_sem_botoes(mo.cli_args())
    return (
        CENSUS_YEARS,
        ESTIMATE_UNAVAILABLE_YEARS,
        asdict,
        asyncio,
        executar,
        fixar_plano,
        load_dicionario,
        mo,
        odb,
        registrar_proveniencia,
        salvar_json,
        target_padrao,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # IBGE · população

    População municipal publicada pelo IBGE, importada de uma **edição explícita**:
    censo ou estimativa, e um ano. Este notebook percorre as seis etapas do
    [guia do pesquisador](https://raphaelfh.github.io/omnisus-db/pesquisa/) com o
    **censo de 2022** e, se o SIM estiver no mesmo lake, calcula óbitos por 100 mil.

    **Abrir este notebook não baixa nem grava nada.** Cada etapa com rede ou escrita
    começa por um botão.

    Censo e estimativa têm datas de referência diferentes. Leia o
    [perfil da população IBGE](https://raphaelfh.github.io/omnisus-db/sources/ibge_populacao/)
    e a página [Indicadores](https://raphaelfh.github.io/omnisus-db/pesquisa/indicadores/).
    """)
    return


@app.cell
def _(load_dicionario, mo):
    _dicionario = load_dicionario("ibge_populacao")
    mo.vstack(
        [
            mo.md("## 1 · O que a base registra\n\nColunas da visão `ibge_populacao`."),
            mo.ui.table(
                [
                    {"campo": f["name"], "tipo": f["type"], "rótulo": f.get("label", "")}
                    for f in _dicionario.fields
                ],
                selection=None,
            ),
        ]
    )
    return


@app.cell
def _(CENSUS_YEARS, ESTIMATE_UNAVAILABLE_YEARS, mo):
    mo.vstack(
        [
            mo.md(
                "## 2 · Descobrir\n\n"
                "Não há inventário de arquivos: a biblioteca aceita edições conhecidas. "
                "Esta tabela vem do pacote, sem rede."
            ),
            mo.ui.table(
                [{"produto": "census", "anos_aceitos": ", ".join(map(str, CENSUS_YEARS))}]
                + [
                    {
                        "produto": "estimate",
                        "anos_recusados": ", ".join(map(str, ESTIMATE_UNAVAILABLE_YEARS)),
                    }
                ],
                selection=None,
            ),
            mo.md(
                "Uma estimativa só é aceita na edição mais recente do agregado; anos "
                "recusados não têm universo territorial verificado."
            ),
        ]
    )
    return


@app.cell
def _(mo, target_padrao):
    produto = mo.ui.dropdown(["census", "estimate"], value="census", label="Produto")
    ano = mo.ui.number(start=2000, stop=2100, step=1, value=2022, label="Ano da edição")
    target = mo.ui.text(value=target_padrao(), label="Lake", full_width=True)
    fixar = mo.ui.run_button(label="Fixar o plano")
    mo.vstack(
        [
            mo.md(
                "## 3 · Planejar e importar\n\n"
                "Use o mesmo lake do SIM para poder calcular taxas. Uma edição já "
                "importada não é importada de novo: a visão `ibge_populacao` falha "
                "quando um município e ano têm duas publicações."
            ),
            mo.hstack([produto, ano]),
            target,
            fixar,
        ]
    )
    return ano, fixar, produto, target


@app.cell
def _(ano, executar, fixar, fixar_plano, mo, produto, target):
    mo.stop(not (executar or fixar.value), mo.md("Fixe o plano para continuar."))
    plano, pasta = fixar_plano(
        target.value, dataset="ibge_populacao", product=produto.value, ano=int(ano.value)
    )
    importar = mo.ui.run_button(label="Baixar e publicar esta edição")
    mo.vstack([mo.md(f"Plano gravado em `{pasta / 'plano.json'}`."), mo.json(plano), importar])
    return importar, pasta, plano


@app.cell
async def _(asdict, asyncio, executar, importar, mo, odb, pasta, plano, salvar_json):
    mo.stop(not (executar or importar.value), mo.md("O download só começa pelo botão acima."))
    _sql = (
        "SELECT publication_id, product, ano, sha256, url, collected_at "
        "FROM lake.ibge_population_manifest WHERE product = ? AND ano = ?"
    )
    try:
        with odb.LakeReader(plano["target"]) as _leitor:
            _existentes = (
                _leitor.connect().execute(_sql, [plano["product"], plano["ano"]]).pl().to_dicts()
                if "ibge_population_manifest" in _leitor.tables()
                else []
            )
    except odb.CatalogAttachError:
        _existentes = []  # o lake ainda não existe
    if _existentes:
        importadas = []
    else:
        importadas = await asyncio.to_thread(
            odb.import_ibge_populacao,
            years=[plano["ano"]],
            product=plano["product"],
            target=plano["target"],
        )
    salvar_json(
        pasta / "resultado.json",
        {"ja_publicadas": _existentes, "importadas": [asdict(r) for r in importadas]},
    )
    mo.vstack(
        [
            mo.md(
                "Edição já estava no lake; nada foi importado."
                if _existentes
                else f"Importadas **{sum(r.rows for r in importadas):,} linhas**."
            ),
            mo.ui.table(_existentes or [asdict(r) for r in importadas], selection=None),
        ]
    )
    return (importadas,)


@app.cell
def _(importadas, mo, odb, plano):
    with odb.LakeReader(plano["target"]) as _leitor:
        publicacoes = (
            _leitor.connect()
            .execute(
                "SELECT * EXCLUDE (evidence_json) FROM lake.ibge_population_manifest "
                "WHERE product = ? AND ano = ?",
                [plano["product"], plano["ano"]],
            )
            .pl()
            .to_dicts()
        )
        _resumo = (
            _leitor.connect()
            .execute(
                "SELECT count(*) AS municipios, sum(populacao) AS populacao_total "
                "FROM lake.ibge_populacao WHERE ano = ?",
                [plano["ano"]],
            )
            .pl()
        )
        snapshot_id = _leitor.snapshots()[-1]["snapshot_id"]
    mo.vstack(
        [
            mo.md(
                "## 4 · Conferir\n\n"
                f"Esta execução importou {len(importadas)} edição(ões). O manifesto guarda "
                "URL, SHA-256 e data de coleta de cada publicação; a contagem abaixo lê a "
                "visão, que falharia se houvesse publicações ambíguas."
            ),
            mo.ui.table(publicacoes, selection=None, label="ibge_population_manifest"),
            mo.ui.table(_resumo, selection=None),
            mo.md(f"Snapshot `{snapshot_id}`"),
        ]
    )
    return publicacoes, snapshot_id


@app.cell
def _(mo):
    codigo_uf = mo.ui.text(value="14", label="Código IBGE da UF para a análise (14 = RR)")
    codigo_uf
    return (codigo_uf,)


@app.cell
def _(codigo_uf, mo, odb, plano, snapshot_id):
    _ano, _uf = plano["ano"], codigo_uf.value.strip()
    _consultas = {
        "populacao_por_municipio": (
            "SELECT codigo_ibge, populacao FROM lake.ibge_populacao "
            "WHERE ano = ? AND left(codigo_ibge, 2) = ? ORDER BY populacao DESC",
            [_ano, _uf],
        ),
        "digitos_codigo_ibge": (
            "SELECT length(codigo_ibge) AS digitos, count(*) AS municipios "
            "FROM lake.ibge_populacao WHERE ano = ? GROUP BY ALL",
            [_ano],
        ),
    }
    with odb.LakeReader(plano["target"], snapshot_id=snapshot_id) as _leitor:
        _tem_sim = "sim_obitos" in _leitor.tables()
        if _tem_sim:
            _consultas["digitos_codmunres_sim"] = (
                "SELECT length(trim(CAST(codmunres AS VARCHAR))) AS digitos, count(*) AS obitos "
                "FROM lake.sim_obitos WHERE ano = ? GROUP BY ALL",
                [_ano],
            )
            _consultas["obitos_por_100_mil"] = (
                """
                WITH obitos AS (
                    SELECT left(trim(CAST(codmunres AS VARCHAR)), 6) AS municipio,
                           count(*) AS obitos
                    FROM lake.sim_obitos WHERE ano = ? GROUP BY ALL
                ), populacao AS (
                    SELECT left(codigo_ibge, 6) AS municipio, populacao
                    FROM lake.ibge_populacao WHERE ano = ? AND left(codigo_ibge, 2) = ?
                )
                SELECT municipio, obitos, populacao,
                       round(100000.0 * obitos / populacao, 1) AS obitos_por_100_mil
                FROM populacao JOIN obitos USING (municipio)
                ORDER BY municipio
                """,
                [_ano, _ano, _uf],
            )
        resultados = {
            nome: _leitor.connect().execute(sql, parametros).pl()
            for nome, (sql, parametros) in _consultas.items()
        }
    consultas = {nome: sql for nome, (sql, _p) in _consultas.items()}
    _texto = (
        "A taxa junta os municípios pelos **6 primeiros dígitos**: confira nas tabelas de "
        "dígitos que os dois lados têm o formato esperado antes de usar o resultado. "
        "Óbitos entram pelo município de residência (`codmunres`) e só os arquivos do SIM "
        "presentes no lake são contados; veja o perfil do SIM sobre como os arquivos "
        "são organizados."
        if _tem_sim
        else f"`sim_obitos` não está neste lake. Importe SIM {_ano} no notebook "
        "`bases/sim_obitos.py`, com o mesmo lake, para calcular óbitos por 100 mil."
    )
    mo.vstack(
        [
            mo.md(f"## 5 · Analisar\n\nConsultas sobre o snapshot `{snapshot_id}`. {_texto}"),
            mo.ui.tabs(
                {
                    nome: mo.vstack(
                        [
                            mo.ui.table(tabela, selection=None),
                            mo.accordion({"SQL": mo.md(f"```sql\n{consultas[nome]}\n```")}),
                        ]
                    )
                    for nome, tabela in resultados.items()
                }
            ),
        ]
    )
    return consultas, resultados


@app.cell
def _(consultas, mo, pasta, plano, publicacoes, registrar_proveniencia, resultados, snapshot_id):
    registrar_proveniencia(
        pasta, plano=plano, publicacoes=publicacoes, snapshot_id=snapshot_id, consultas=consultas
    )
    for _nome, _tabela in resultados.items():
        _tabela.write_csv(pasta / f"{_nome}.csv")
    mo.vstack(
        [
            mo.md(
                "## 6 · Guardar\n\n"
                f"Resultados e `proveniencia.json` gravados em `{pasta}`. Veja "
                "[Reprodutibilidade](https://raphaelfh.github.io/omnisus-db/pesquisa/reprodutibilidade/)."
            ),
            mo.hstack(
                [
                    mo.download(
                        (pasta / f"{nome}.csv").read_bytes(),
                        filename=f"ibge_populacao-{nome}.csv",
                        label=f"CSV · {nome}",
                    )
                    for nome in resultados
                ],
                wrap=True,
            ),
            mo.download(
                (pasta / "proveniencia.json").read_bytes(),
                filename="ibge_populacao-proveniencia.json",
                label="proveniencia.json",
            ),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
```

- [ ] **Step 3: Lint, check, pass**

```bash
uv run ruff check --fix notebooks/bases/ibge_populacao.py && uv run ruff format notebooks/bases/ibge_populacao.py
uv run marimo check --strict --ignore-scripts notebooks
uv run pytest tests/unit/notebooks/test_notebooks_abrem_offline.py -q
```

Expected: exit 0; 14 passed. If `SELECT * EXCLUDE (evidence_json)` fails because the column is absent in a lake, drop the `EXCLUDE` clause — it only keeps a large JSON out of the table.

- [ ] **Step 4: Falsify the write guarantee**

Change the plan cell's gate to `mo.stop(False, ...)`; run `-k ibge` → FAIL. Restore; re-run → pass.

- [ ] **Step 5: Commit**

```bash
git add notebooks/bases/ibge_populacao.py tests/unit/notebooks/test_notebooks_abrem_offline.py
git commit -m "Add the IBGE population notebook with the SIM rate example

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 12: `notebooks/bases/sinan.py` — Chagas and hanseníase

**Files:**
- Rewrite: `notebooks/bases/sinan.py` (moved from `sinan_chagas.py` in Task 2)
- Test: offline test (already lists `bases/sinan.py`)

**Interfaces:**
- Consumes: `_comum` (Task 5); layout of Task 6. Both SINAN datasets are national yearly files (`ScopeKey(uf=None, ano=...)`, column `_source_ano`) with final and preliminary directories (`_source_release`). `scopes_for` refuses `ufs` for national datasets.
- Replaces the old walkthrough's per-run lake folder (`data/lake/sinan-chagas/`) with the shared research lake.

- [ ] **Step 1: Replace the file**

```python
"""SINAN · notificações nacionais de Chagas aguda e hanseníase, em seis etapas."""

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", app_title="SINAN · Chagas e hanseníase")


@app.cell
def _():
    import asyncio
    from dataclasses import asdict

    import marimo as mo
    from _comum import (
        LIMITE_BYTES,
        conferir,
        executar_sem_botoes,
        fixar_plano,
        registrar_importacao,
        registrar_proveniencia,
        target_padrao,
    )

    import omnisus_db as odb
    from omnisus_db.transforms.dictionaries import load_dicionario

    AGRAVOS = {"sinan_chagas": "Doença de Chagas aguda", "sinan_hanseniase": "Hanseníase"}
    executar = executar_sem_botoes(mo.cli_args())
    return (
        AGRAVOS,
        LIMITE_BYTES,
        asdict,
        asyncio,
        conferir,
        executar,
        fixar_plano,
        load_dicionario,
        mo,
        odb,
        registrar_importacao,
        registrar_proveniencia,
        target_padrao,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # SINAN · Chagas aguda e hanseníase

    Notificações do Sistema de Informação de Agravos de Notificação (SINAN),
    publicadas pelo DATASUS em **um arquivo nacional por ano**, com diretório final e
    preliminar. Este notebook percorre as seis etapas do
    [guia do pesquisador](https://raphaelfh.github.io/omnisus-db/pesquisa/) com
    **Chagas aguda, 2022** (troque para hanseníase no seletor).

    **Abrir este notebook não baixa nem grava nada.** Cada etapa com rede ou escrita
    começa por um botão.

    Uma notificação não é um caso confirmado nem uma pessoa única. Leia os perfis de
    [Chagas](https://raphaelfh.github.io/omnisus-db/sources/sinan_chagas/) e
    [hanseníase](https://raphaelfh.github.io/omnisus-db/sources/sinan_hanseniase/).
    """)
    return


@app.cell
def _(AGRAVOS, mo):
    agravo = mo.ui.dropdown(
        {rotulo: nome for nome, rotulo in AGRAVOS.items()},
        value="Doença de Chagas aguda",
        label="Agravo",
    )
    agravo
    return (agravo,)


@app.cell
def _(agravo, load_dicionario, mo):
    _dicionario = load_dicionario(agravo.value)
    mo.vstack(
        [
            mo.md(
                f"## 1 · O que `{agravo.value}` registra\n\n"
                "Campos do dicionário que a biblioteca aplica na importação. "
                "O significado dos códigos está no dicionário oficial citado no perfil."
            ),
            mo.ui.table(
                [{"campo": f["name"], "tipo": f["type"]} for f in _dicionario.fields],
                selection=None,
                page_size=10,
            ),
        ]
    )
    return


@app.cell
def _(mo):
    descobrir = mo.ui.run_button(label="Consultar o que o DATASUS publica")
    mo.vstack(
        [
            mo.md(
                "## 2 · Descobrir\n\n"
                "Lista agora os diretórios final e preliminar (`refresh=True`). Um ano "
                "preliminar pode ser revisado e depois movido para o final com o mesmo nome."
            ),
            descobrir,
        ]
    )
    return (descobrir,)


@app.cell
async def _(agravo, asyncio, descobrir, executar, mo, odb):
    mo.stop(not (executar or descobrir.value), mo.md("A consulta começa pelo botão acima."))
    _publicados = await asyncio.to_thread(odb.available_releases, agravo.value, refresh=True)
    mo.ui.table(
        [
            {"ano": e.ano, "abrangencia": "nacional", "diretorio": r}
            for e, r in sorted(_publicados.items(), key=lambda item: -item[0].ano)
        ],
        selection=None,
        label=f"Arquivos de {agravo.value}",
    )
    return


@app.cell
def _(mo, target_padrao):
    ano = mo.ui.number(start=2000, stop=2100, step=1, value=2022, label="Ano do arquivo")
    target = mo.ui.text(value=target_padrao(), label="Lake", full_width=True)
    fixar = mo.ui.run_button(label="Fixar o plano")
    mo.vstack(
        [
            mo.md(
                "## 3 · Planejar e importar\n\n"
                "O arquivo é nacional: não há filtro de UF na importação. Filtre a "
                "geografia dos registros depois, na análise."
            ),
            ano,
            target,
            fixar,
        ]
    )
    return ano, fixar, target


@app.cell
def _(LIMITE_BYTES, agravo, ano, asdict, executar, fixar, fixar_plano, mo, odb, target):
    mo.stop(not (executar or fixar.value), mo.md("Fixe o plano para continuar."))
    escopos = odb.scopes_for(agravo.value, years=[int(ano.value)])
    plano, pasta = fixar_plano(
        target.value,
        dataset=agravo.value,
        escopos=[asdict(e) for e in escopos],
        policy="skip_same",
        limite_bytes=LIMITE_BYTES,
    )
    importar = mo.ui.run_button(label="Baixar e publicar este plano")
    mo.vstack([mo.md(f"Plano gravado em `{pasta / 'plano.json'}`."), mo.json(plano), importar])
    return escopos, importar, pasta, plano


@app.cell
async def _(
    LIMITE_BYTES, asyncio, escopos, executar, importar, mo, odb, pasta, plano, registrar_importacao
):
    mo.stop(not (executar or importar.value), mo.md("O download só começa pelo botão acima."))
    mo.output.append(
        mo.md(
            "Importando. Interromper a célula não cancela a thread: espere terminar "
            "antes de outra escrita no mesmo lake."
        )
    )
    try:
        relatorio = await asyncio.to_thread(
            odb.import_dataset,
            plano["dataset"],
            scopes=escopos,
            target=plano["target"],
            policy="skip_same",
            run_id=plano["run_id"],
            concurrency=1,
            max_payload_bytes=LIMITE_BYTES,
            max_inflight_bytes=LIMITE_BYTES,
        )
        _nao_resolvidos = ()
    except odb.ImportAbortedError as _erro:
        relatorio, _nao_resolvidos = _erro.report, _erro.unresolved
    _linhas = registrar_importacao(pasta, relatorio, _nao_resolvidos)
    if executar and (relatorio.failed or _nao_resolvidos):
        raise RuntimeError(f"Importação incompleta; veja {pasta / 'resultado.json'}")
    mo.vstack(
        [
            mo.ui.table(_linhas, selection=None, label="Desfecho por escopo"),
            mo.md(
                "`skipped` com *same source and parser version already published* quer "
                "dizer que o mesmo arquivo já estava no lake. Um `failed` pedindo "
                "`replace` quer dizer que o DATASUS publicou outra versão do arquivo."
            ),
        ]
    )
    return (relatorio,)


@app.cell
def _(conferir, escopos, mo, odb, plano, relatorio):
    with odb.LakeReader(plano["target"]) as _leitor:
        mo.stop(
            plano["dataset"] not in _leitor.tables(),
            mo.md("Nenhuma tabela publicada; veja os desfechos acima."),
        )
        _desta_execucao = _leitor.publications(run_id=plano["run_id"])
        _conferencia, publicacoes = conferir(_leitor, plano["dataset"], escopos)
        snapshot_id = _leitor.snapshots()[-1]["snapshot_id"]
        # refresh=False reaproveita a listagem da etapa 2: o FTP é um recurso público.
        _desatualizados = odb.outdated(plano["dataset"], lake=_leitor)
    mo.vstack(
        [
            mo.md(
                "## 4 · Conferir\n\n"
                f"O relatório informou **{relatorio.rows:,} linhas novas**. `outdated` "
                "lista os anos que o DATASUS moveu entre preliminar e final desde a "
                "importação; atualize-os com `policy=\"replace\"` e um novo `run_id`."
            ),
            mo.ui.table(_desta_execucao, selection=None, label="publications(run_id=...)"),
            mo.ui.table(_conferencia, selection=None, label="Linhas no lake × publicadas"),
            mo.md(f"Desatualizados: `{[str(e) for e in _desatualizados]}` · snapshot `{snapshot_id}`"),
        ]
    )
    return publicacoes, snapshot_id


@app.cell
def _(escopos, mo, odb, plano, snapshot_id):
    _tabela = plano["dataset"]  # uma das duas chaves de AGRAVOS
    _recorte = f'FROM lake."{_tabela}" WHERE _source_ano = ?'
    consultas = {
        "diretorio_de_origem": f"""
            SELECT _source_release AS diretorio, count(*) AS notificacoes {_recorte}
            GROUP BY ALL
        """,
        "notificacoes_por_uf_de_notificacao": f"""
            SELECT trim(CAST(sg_uf_not AS VARCHAR)) AS uf_notificacao_ibge,
                   count(*) AS notificacoes {_recorte}
            GROUP BY ALL ORDER BY notificacoes DESC
        """,
        "notificacoes_por_uf_de_residencia": f"""
            SELECT left(trim(CAST(id_mn_resi AS VARCHAR)), 2) AS uf_residencia_ibge,
                   count(*) AS notificacoes {_recorte}
            GROUP BY ALL ORDER BY notificacoes DESC
        """,
    }
    if _tabela == "sinan_chagas":
        consultas["classificacao_e_evolucao"] = f"""
            SELECT trim(CAST(classi_fin AS VARCHAR)) AS classi_fin,
                   trim(CAST(evolucao AS VARCHAR)) AS evolucao,
                   count(*) AS notificacoes {_recorte}
            GROUP BY ALL ORDER BY classi_fin, evolucao
        """
    else:
        consultas["modo_de_entrada_e_alta"] = f"""
            SELECT trim(CAST(modoentr AS VARCHAR)) AS modoentr,
                   trim(CAST(tpalta_n AS VARCHAR)) AS tpalta_n,
                   count(*) AS notificacoes {_recorte}
            GROUP BY ALL ORDER BY modoentr, tpalta_n
        """
    with odb.LakeReader(plano["target"], snapshot_id=snapshot_id) as _leitor:
        resultados = {
            nome: _leitor.connect().execute(sql, [escopos[0].ano]).pl()
            for nome, sql in consultas.items()
        }
    mo.vstack(
        [
            mo.md(
                "## 5 · Analisar\n\n"
                f"Consultas sobre o snapshot `{snapshot_id}`. Os códigos aparecem como "
                "publicados; confira no dicionário oficial antes de selecionar casos "
                "confirmados ou calcular incidência."
            ),
            mo.ui.tabs(
                {
                    nome: mo.vstack(
                        [
                            mo.ui.table(tabela, selection=None),
                            mo.accordion({"SQL": mo.md(f"```sql\n{consultas[nome]}\n```")}),
                        ]
                    )
                    for nome, tabela in resultados.items()
                }
            ),
        ]
    )
    return consultas, resultados


@app.cell
def _(consultas, mo, pasta, plano, publicacoes, registrar_proveniencia, resultados, snapshot_id):
    registrar_proveniencia(
        pasta, plano=plano, publicacoes=publicacoes, snapshot_id=snapshot_id, consultas=consultas
    )
    for _nome, _tabela in resultados.items():
        _tabela.write_csv(pasta / f"{_nome}.csv")
    mo.vstack(
        [
            mo.md(
                "## 6 · Guardar\n\n"
                f"Resultados e `proveniencia.json` gravados em `{pasta}`. Veja "
                "[Reprodutibilidade](https://raphaelfh.github.io/omnisus-db/pesquisa/reprodutibilidade/)."
            ),
            mo.hstack(
                [
                    mo.download(
                        (pasta / f"{nome}.csv").read_bytes(),
                        filename=f"{plano['dataset']}-{nome}.csv",
                        label=f"CSV · {nome}",
                    )
                    for nome in resultados
                ],
                wrap=True,
            ),
            mo.download(
                (pasta / "proveniencia.json").read_bytes(),
                filename=f"{plano['dataset']}-proveniencia.json",
                label="proveniencia.json",
            ),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
```

- [ ] **Step 2: Lint, check, pass**

```bash
uv run ruff check --fix notebooks/bases/sinan.py && uv run ruff format notebooks/bases/sinan.py
uv run marimo check --strict --ignore-scripts notebooks
uv run pytest tests/unit/notebooks/test_notebooks_abrem_offline.py -q
```

Expected: exit 0; 14 passed.

- [ ] **Step 3: Falsify the network guarantee**

Change the step-2 gate to `mo.stop(False, ...)`; run `-k sinan` → FAIL (`network: unit test attempted to LIST`). Restore; re-run → pass.

- [ ] **Step 4: Update the old walkthrough text**

In `docs/sources/sinan_chagas.md`, the paragraph "O notebook `notebooks/bases/sinan.py` apresenta descoberta..." and its command stay until Task 18 rewrites the page; make sure the command reads `uv run --locked --extra notebooks marimo edit notebooks/bases/sinan.py`.

- [ ] **Step 5: Commit**

```bash
git add notebooks/bases/sinan.py docs/sources/sinan_chagas.md
git commit -m "Rewrite the SINAN notebook for Chagas and hanseníase on the shared lake

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 13: `notebooks/bases/medicamentos.py`

**Files:**
- Rewrite: `notebooks/bases/medicamentos.py` (moved in Task 2)
- Modify: `docs/sources/medicamentos.md` "Trilha Marimo e verificação" paragraph (paths and the per-run lake sentence)
- Test: offline test (already lists `bases/medicamentos.py`)

**Interfaces:**
- Consumes: `_comum` (Task 5), including `raiz_dados`; layout of Task 6; `omnisus_db.sources.medicamentos.fetch_stock_page(*, filters: dict[str, str | int], page: int = 0, limit: int = 100, max_bytes: int = 4 * 1024 * 1024, client=None) -> StockPage` with `.records`, `.raw` (bytes), `.sha256`, `.provenance()`.
- The Hórus page is an observation, not a lake publication: it is saved as `resposta.json` + `proveniencia.json` under `<raiz>/estoque/<uuid>/`.

- [ ] **Step 1: Replace the file**

```python
"""Medicamentos: APAC do SIA no lake, uma página de estoque do Hórus e o que não existe."""

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", app_title="Medicamentos · APAC e estoque")


@app.cell
def _():
    import asyncio
    from dataclasses import asdict
    from uuid import uuid4

    import marimo as mo
    from _comum import (
        LIMITE_BYTES,
        conferir,
        executar_sem_botoes,
        fixar_plano,
        raiz_dados,
        registrar_importacao,
        registrar_proveniencia,
        salvar_json,
        target_padrao,
    )

    import omnisus_db as odb
    from omnisus_db.sources.medicamentos import fetch_stock_page
    from omnisus_db.transforms.dictionaries import load_dicionario

    dataset = "sia_apac_medicamentos"
    executar = executar_sem_botoes(mo.cli_args())
    return (
        LIMITE_BYTES,
        asdict,
        asyncio,
        conferir,
        dataset,
        executar,
        fetch_stock_page,
        fixar_plano,
        load_dicionario,
        mo,
        odb,
        raiz_dados,
        registrar_importacao,
        registrar_proveniencia,
        salvar_json,
        target_padrao,
        uuid4,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Medicamentos: o que dá para estudar com dados abertos

    Três partes:

    - **A · APAC de medicamentos (SIA-AM)** — as seis etapas do
      [guia do pesquisador](https://raphaelfh.github.io/omnisus-db/pesquisa/) com
      **Roraima, janeiro de 2024**, no lake de pesquisa compartilhado.
    - **B · Estoque BNAFAR/Hórus** — uma página da API pública de posição de estoque,
      guardada com proveniência, sem publicar no lake.
    - **C · O que não existe publicamente** — eventos de dispensação.

    **Abrir este notebook não baixa nem grava nada.** Cada etapa com rede ou escrita
    começa por um botão. Leia o
    [perfil de medicamentos](https://raphaelfh.github.io/omnisus-db/sources/medicamentos/)
    antes de interpretar números: um registro de APAC não é uma dose nem uma dispensação.
    """)
    return


@app.cell
def _(dataset, load_dicionario, mo):
    _dicionario = load_dicionario(dataset)
    mo.vstack(
        [
            mo.md("## A1 · O que a APAC de medicamentos registra"),
            mo.ui.table(
                [
                    {"campo": f["name"], "tipo": f["type"], "rótulo": f.get("label", "")}
                    for f in _dicionario.fields
                ],
                selection=None,
                page_size=10,
            ),
        ]
    )
    return


@app.cell
def _(mo):
    descobrir = mo.ui.run_button(label="Consultar o que o DATASUS publica")
    mo.vstack([mo.md("## A2 · Descobrir"), descobrir])
    return (descobrir,)


@app.cell
async def _(asyncio, dataset, descobrir, executar, mo, odb):
    mo.stop(not (executar or descobrir.value), mo.md("A consulta começa pelo botão acima."))
    _publicados = await asyncio.to_thread(odb.available, dataset, ufs=["RR"], refresh=True)
    mo.ui.table(
        [
            {"uf": e.uf, "ano": e.ano, "mes": e.mes}
            for e in sorted(_publicados, key=lambda e: (-e.ano, -(e.mes or 0)))
        ],
        selection=None,
        label="Arquivos SIA-AM publicados para RR",
    )
    return


@app.cell
def _(mo, odb, target_padrao):
    uf = mo.ui.dropdown(list(odb.ALL_UFS), value="RR", label="UF do arquivo")
    ano = mo.ui.number(start=2008, stop=2100, step=1, value=2024, label="Ano")
    mes = mo.ui.number(start=1, stop=12, step=1, value=1, label="Mês de processamento")
    target = mo.ui.text(value=target_padrao(), label="Lake", full_width=True)
    fixar = mo.ui.run_button(label="Fixar o plano")
    mo.vstack(
        [
            mo.md(
                "## A3 · Planejar e importar\n\n"
                "Fixar o plano grava `plano.json` com um `run_id` antes de qualquer download."
            ),
            mo.hstack([uf, ano, mes]),
            target,
            fixar,
        ]
    )
    return ano, fixar, mes, target, uf


@app.cell
def _(
    LIMITE_BYTES, ano, asdict, dataset, executar, fixar, fixar_plano, mes, mo, odb, target, uf
):
    mo.stop(not (executar or fixar.value), mo.md("Fixe o plano para continuar."))
    escopos = odb.scopes_for(
        dataset, years=[int(ano.value)], ufs=[uf.value], months=[int(mes.value)]
    )
    plano, pasta = fixar_plano(
        target.value,
        dataset=dataset,
        escopos=[asdict(e) for e in escopos],
        policy="skip_same",
        limite_bytes=LIMITE_BYTES,
    )
    importar = mo.ui.run_button(label="Baixar e publicar este plano")
    mo.vstack([mo.md(f"Plano gravado em `{pasta / 'plano.json'}`."), mo.json(plano), importar])
    return escopos, importar, pasta, plano


@app.cell
async def _(
    LIMITE_BYTES, asyncio, escopos, executar, importar, mo, odb, pasta, plano, registrar_importacao
):
    mo.stop(not (executar or importar.value), mo.md("O download só começa pelo botão acima."))
    mo.output.append(
        mo.md(
            "Importando. Interromper a célula não cancela a thread: espere terminar "
            "antes de outra escrita no mesmo lake."
        )
    )
    try:
        relatorio = await asyncio.to_thread(
            odb.import_dataset,
            plano["dataset"],
            scopes=escopos,
            target=plano["target"],
            policy="skip_same",
            run_id=plano["run_id"],
            concurrency=1,
            max_payload_bytes=LIMITE_BYTES,
            max_inflight_bytes=LIMITE_BYTES,
        )
        _nao_resolvidos = ()
    except odb.ImportAbortedError as _erro:
        relatorio, _nao_resolvidos = _erro.report, _erro.unresolved
    _linhas = registrar_importacao(pasta, relatorio, _nao_resolvidos)
    if executar and (relatorio.failed or _nao_resolvidos):
        raise RuntimeError(f"Importação incompleta; veja {pasta / 'resultado.json'}")
    mo.vstack(
        [
            mo.ui.table(_linhas, selection=None, label="Desfecho por escopo"),
            mo.md(
                "`skipped` com *same source and parser version already published* quer "
                "dizer que o mesmo arquivo já estava no lake: nada foi duplicado. "
                "Um arquivo que o DATASUS não publica também aparece como `skipped`."
            ),
        ]
    )
    return (relatorio,)


@app.cell
def _(conferir, dataset, escopos, mo, odb, plano, relatorio):
    with odb.LakeReader(plano["target"]) as _leitor:
        mo.stop(
            dataset not in _leitor.tables(),
            mo.md("Nenhuma tabela publicada; veja os desfechos acima."),
        )
        _desta_execucao = _leitor.publications(run_id=plano["run_id"])
        _conferencia, publicacoes = conferir(_leitor, dataset, escopos)
        snapshot_id = _leitor.snapshots()[-1]["snapshot_id"]
    mo.vstack(
        [
            mo.md(
                "## A4 · Conferir\n\n"
                f"O relatório informou **{relatorio.rows:,} linhas novas**. O SIA é "
                "publicado num único diretório, então `outdated` não se aplica."
            ),
            mo.ui.table(_desta_execucao, selection=None, label="publications(run_id=...)"),
            mo.ui.table(_conferencia, selection=None, label="Linhas no lake × publicadas"),
            mo.md(f"Snapshot `{snapshot_id}`"),
        ]
    )
    return publicacoes, snapshot_id


@app.cell
def _(escopos, mo, odb, plano, snapshot_id):
    consultas = {
        "apac_por_procedimento_principal": """
            SELECT trim(CAST(ap_pripal AS VARCHAR)) AS procedimento_principal,
                   count(*) AS apac,
                   round(sum(TRY_CAST(ap_vl_ap AS DOUBLE)), 2) AS valor_aprovado
            FROM lake.sia_apac_medicamentos WHERE uf = ? AND ano = ? AND mes = ?
            GROUP BY ALL ORDER BY apac DESC
        """,
    }
    _parametros = [escopos[0].uf, escopos[0].ano, escopos[0].mes]
    with odb.LakeReader(plano["target"], snapshot_id=snapshot_id) as _leitor:
        resultados = {
            nome: _leitor.connect().execute(sql, _parametros).pl()
            for nome, sql in consultas.items()
        }
    mo.vstack(
        [
            mo.md(
                "## A5 · Analisar\n\n"
                f"Registros de APAC por procedimento principal e valor aprovado, sobre o "
                f"snapshot `{snapshot_id}`. Não são doses nem pacientes únicos."
            ),
            mo.ui.table(resultados["apac_por_procedimento_principal"], selection=None),
            mo.accordion(
                {"SQL": mo.md(f"```sql\n{consultas['apac_por_procedimento_principal']}\n```")}
            ),
        ]
    )
    return consultas, resultados


@app.cell
def _(consultas, mo, pasta, plano, publicacoes, registrar_proveniencia, resultados, snapshot_id):
    registrar_proveniencia(
        pasta, plano=plano, publicacoes=publicacoes, snapshot_id=snapshot_id, consultas=consultas
    )
    for _nome, _tabela in resultados.items():
        _tabela.write_csv(pasta / f"{_nome}.csv")
    mo.vstack(
        [
            mo.md(f"## A6 · Guardar\n\nResultados e `proveniencia.json` gravados em `{pasta}`."),
            mo.download(
                (pasta / "apac_por_procedimento_principal.csv").read_bytes(),
                filename="sia_apac_medicamentos-apac_por_procedimento_principal.csv",
                label="CSV",
            ),
            mo.download(
                (pasta / "proveniencia.json").read_bytes(),
                filename="sia_apac_medicamentos-proveniencia.json",
                label="proveniencia.json",
            ),
        ]
    )
    return


@app.cell
def _(mo):
    codigo_uf = mo.ui.text(value="14", label="Código IBGE da UF")
    data_estoque = mo.ui.text(value="", label="Data da posição AAAA-MM-DD (opcional)")
    consultar_estoque = mo.ui.run_button(label="Consultar uma página (até 20 registros)")
    mo.vstack(
        [
            mo.md(
                "## B · Estoque BNAFAR/Hórus\n\n"
                "Uma página da API pública de **posição de estoque**. Não publica no lake. "
                "Uma página vazia não demonstra ausência de estoque, e uma página curta "
                "não demonstra completude."
            ),
            mo.hstack([codigo_uf, data_estoque]),
            consultar_estoque,
        ]
    )
    return codigo_uf, consultar_estoque, data_estoque


@app.cell
async def _(
    asyncio,
    codigo_uf,
    consultar_estoque,
    data_estoque,
    executar,
    fetch_stock_page,
    mo,
    raiz_dados,
    salvar_json,
    uuid4,
):
    mo.stop(
        not (executar or consultar_estoque.value), mo.md("A consulta começa pelo botão acima.")
    )
    _filtros = {"codigo_uf": codigo_uf.value.strip()}
    if data_estoque.value.strip():
        _filtros["data_posicao_estoque"] = data_estoque.value.strip()
    _pagina = await asyncio.to_thread(fetch_stock_page, filters=_filtros, limit=20)
    _pasta = raiz_dados() / "estoque" / uuid4().hex
    _pasta.mkdir(parents=True)
    (_pasta / "resposta.json").write_bytes(_pagina.raw)
    salvar_json(_pasta / "proveniencia.json", _pagina.provenance())
    mo.vstack(
        [
            mo.md(f"Observação salva em `{_pasta}`. SHA-256 da resposta: `{_pagina.sha256}`."),
            mo.ui.table(_pagina.records, selection=None),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## C · O que não existe publicamente

    A investigação de 2026-09-12
    ([relatório](https://github.com/raphaelfh/omnisus-db/blob/main/reports/2026-09-12-sinan-e-dispensacao.md),
    Parte 2) não encontrou **nenhuma fonte pública de eventos de dispensação**: a
    dispensação enviada à BNAFAR e à RNDS tem envio ou acesso autenticado. Estoque,
    entrega a DSEI e indicadores agregados não substituem dispensação. Para pesquisar
    dispensação, o caminho é uma extração fornecida pelo gestor.
    """)
    return


if __name__ == "__main__":
    app.run()
```

- [ ] **Step 2: Check the report claim before committing it**

Read `reports/2026-09-12-sinan-e-dispensacao.md` lines 12–50 and 457–490. Every sentence in part C must be supported there; delete any that is not.

- [ ] **Step 3: Lint, check, pass, falsify**

```bash
uv run ruff check --fix notebooks/bases/medicamentos.py && uv run ruff format notebooks/bases/medicamentos.py
uv run marimo check --strict --ignore-scripts notebooks
uv run pytest tests/unit/notebooks/test_notebooks_abrem_offline.py -q
```

Expected: exit 0; 14 passed. Then change the Hórus gate to `mo.stop(False, ...)` and run `-k medicamentos` → FAIL (`opened a connection` or `wrote to the research lake`). Restore; re-run → pass.

- [ ] **Step 4: Update the profile paragraph**

In `docs/sources/medicamentos.md`, "Trilha Marimo e verificação": replace `marimo edit notebooks/medicamentos.py` with `uv run --locked --extra notebooks marimo edit notebooks/bases/medicamentos.py`, and replace the sentences about `data/lake/medicamentos/<run_id>/` and "Cada execução APAC cria pasta própria" with: "As APAC vão para o lake de pesquisa compartilhado; cada execução guarda plano, resultado e proveniência em `data/lake/pesquisa/execucoes/<run_id>/`, e `policy=\"skip_same\"` impede duplicar um arquivo já publicado." Task 18 restructures the whole page.

- [ ] **Step 5: Commit**

```bash
git add notebooks/bases/medicamentos.py docs/sources/medicamentos.md
git commit -m "Rewrite the medicines notebook on the shared lake with the six steps

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 14: Short `notebooks/README.md`; operational text into first cells

**Files:**
- Rewrite: `notebooks/README.md` (293 lines → index)
- Modify: `notebooks/explorar/panorama_datasus.py` (header cell), `notebooks/explorar/inventario_dados_reais.py` (header cell)

**Interfaces:**
- Consumes: final notebook paths (Tasks 2, 6–13).

- [ ] **Step 1: Move the panorama and inventory instructions**

From the current `notebooks/README.md`, take the sections "Panorama das 18 categorias do portal" and "Inventário e download com dados reais". Append their operational content (what the notebook downloads, where it writes, the `marimo export ... -- --executar true` commands, the limits) to the first `mo.md` cell of `explorar/panorama_datasus.py` and `explorar/inventario_dados_reais.py` respectively, as a "Como executar" subsection. Update paths to `notebooks/explorar/...`. Drop sentences that duplicate what the cell already says.

- [ ] **Step 2: Replace `notebooks/README.md`**

````markdown
# Notebooks

Notebooks [marimo](https://marimo.io) em três pastas. Abrir um notebook não baixa
nem grava nada: toda etapa com rede ou escrita começa por um botão.

```bash
uv sync --locked --extra notebooks
uv run --locked --extra notebooks marimo edit notebooks/bases/sim_obitos.py
```

## `bases/` — uma base por notebook, para pesquisa

Comece pelo [guia do pesquisador](https://raphaelfh.github.io/omnisus-db/pesquisa/).
Todos seguem as mesmas seis etapas (o que a base registra, descobrir, planejar e
importar, conferir, analisar, guardar) e gravam no lake `data/lake/pesquisa/`.

| Notebook | Base | Recorte inicial |
| --- | --- | --- |
| [sim_obitos.py](bases/sim_obitos.py) | SIM · óbitos | RR, 2022 |
| [sinasc_nascidos_vivos.py](bases/sinasc_nascidos_vivos.py) | SINASC · nascidos vivos | RR, 2022 |
| [sih_aih_reduzida.py](bases/sih_aih_reduzida.py) | SIH · AIH reduzida | RR, jan/2024 |
| [sia.py](bases/sia.py) | SIA · sete tabelas | RR, jan/2024 |
| [cnes_estabelecimentos.py](bases/cnes_estabelecimentos.py) | CNES · estabelecimentos | RR, jan/2024 |
| [ibge_populacao.py](bases/ibge_populacao.py) | IBGE · população | censo 2022 |
| [sinan.py](bases/sinan.py) | SINAN · Chagas aguda e hanseníase | nacional, 2022 |
| [medicamentos.py](bases/medicamentos.py) | SIA-AM, estoque Hórus | RR, jan/2024 |

Para executar as etapas sem interface (validação):

```bash
uv run --locked --extra notebooks marimo export html notebooks/bases/sim_obitos.py \
  -o /tmp/sim_obitos.html -- --executar true
```

`OMNISUS_NOTEBOOK_DATA` troca a pasta do lake de pesquisa.

## `explorar/` — conhecer o que o DATASUS publica

| Notebook | Para quê |
| --- | --- |
| [panorama_datasus.py](explorar/panorama_datasus.py) | Amostras reais das 18 categorias do portal |
| [inventario_dados_reais.py](explorar/inventario_dados_reais.py) | Inventário do FTP, seleção e importação de arquivos |

## `desenvolvimento/` — comportamento da biblioteca

| Notebook | Para quê |
| --- | --- |
| [api_cenarios.py](desenvolvimento/api_cenarios.py) | Transações, rollback e contratos da API |
| [metadados_cli.py](desenvolvimento/metadados_cli.py) | Metadados por coluna pelo terminal |
| [performance_dbf.py](desenvolvimento/performance_dbf.py) | Medições do leitor DBF Python × Rust |

Arquivos com `_` no início (`_comum.py`, `_acervo/`, `_performance_dbf.py`) são
módulos auxiliares, não notebooks.
````

- [ ] **Step 3: Verify**

```bash
uv run marimo check --strict --ignore-scripts notebooks
uv run pytest tests/unit/notebooks -q
wc -l notebooks/README.md
```

Expected: exit 0; tests pass; README under 70 lines.

- [ ] **Step 4: Commit**

```bash
git add notebooks/README.md notebooks/explorar
git commit -m "Shrink the notebooks README to an index; keep run instructions in each notebook

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Profile tasks (15–18): shared procedure

Every profile follows this procedure. It is repeated here once because Tasks 15–18 are the same kind of work on different pages; each task lists its own pages, documents, questions and code.

**Template** (Portuguese; H1 then exactly these H2 headings, in this order; an optional last H2 `Detalhes técnicos`):

```markdown
# <Sigla> · <nome> (`<dataset>`)

## Em uma frase

## O que um registro representa

## Datas e geografia

## Cobertura e modalidade

## Armadilhas

### Em aberto

## Como usar

## Fontes

## Detalhes técnicos
```

`### Em aberto` appears only when a researcher would otherwise assume the wrong thing.

**Research procedure for claims:**

1. Print the archived sources for the category:

   ```bash
   uv run python -c "import json, sys; [print('-', s['title'], s['url'], 'SHA-256', s['sha256'], 'consultado em', s['retrieved_on']) for s in json.load(open('docs/dicionario/fontes/registro.json'))['sources'] if s['category'] in sys.argv[1:]]" SIM
   ```

2. Download each PDF once to the session scratchpad (never into the repository) and check its hash:

   ```bash
   curl -sS -o "$SCRATCH/<arquivo>.pdf" "<url>"
   shasum -a 256 "$SCRATCH/<arquivo>.pdf"
   ```

   A different hash means the document changed: record the new hash and date in the page and in the Task 19 report, and read the new file.

3. Read the relevant pages with the Read tool (`pages` parameter). Every sentence in "O que um registro representa", "Datas e geografia" and "Armadilhas" ends with a citation such as `(Estrutura do SIM 2025, p. 12)` or points to evidence in the repository (a dictionary YAML, a test, a report section). A claim without it moves to "Em aberto" or is deleted.
4. Keep the page's existing technical contracts (preliminary data, integrity checks, IBGE temporal references, SINAN final × preliminary, medicines access limits) under `## Detalhes técnicos`, translated to Portuguese where needed. Do not delete a contract without saying why in the commit message.
5. "Cobertura e modalidade" links `[catálogo de datasets](../datasets.md)` and, for datasets with a preliminary directory, shows `odb.available_releases(...)`.
6. "Como usar" contains the code given in the task and a line linking the notebook with its absolute GitHub URL.
7. Run `uv run pytest tests/unit/test_guia_pesquisador.py -q` and `uv run mkdocs build --strict` before committing.

---

### Task 15: Guide structure test; SIM and SINASC profiles

**Files:**
- Create: `tests/unit/test_guia_pesquisador.py`
- Rewrite: `docs/sources/sim_obitos.md`, `docs/sources/sinasc_nascidos_vivos.md`

**Interfaces:**
- Produces: `PERFIS: dict[str, str]` (profile page stem → notebook stem in `notebooks/bases/`) and `SECOES` in `tests/unit/test_guia_pesquisador.py`; Tasks 16–18 add entries to `PERFIS`, Task 20 adds the Comece aqui test.

- [ ] **Step 1: Write the failing test**

```python
"""The researcher guide keeps its shape: seven sections, notebook links, cited sources."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GITHUB = "https://github.com/raphaelfh/omnisus-db/blob/main/"
SECOES = [
    "Em uma frase",
    "O que um registro representa",
    "Datas e geografia",
    "Cobertura e modalidade",
    "Armadilhas",
    "Como usar",
    "Fontes",
]

# Profile page in docs/sources/ -> notebook in notebooks/bases/.
PERFIS = {
    "sim_obitos": "sim_obitos",
    "sinasc_nascidos_vivos": "sinasc_nascidos_vivos",
}


def _texto(perfil: str) -> str:
    return (ROOT / "docs/sources" / f"{perfil}.md").read_text(encoding="utf-8")


def _secao(texto: str, titulo: str) -> str:
    return texto.split(f"\n## {titulo}\n", 1)[1].split("\n## ", 1)[0]


@pytest.mark.parametrize("perfil", sorted(PERFIS))
def test_profile_has_the_seven_sections_in_order(perfil):
    secoes = re.findall(r"^## (.+?)\s*$", _texto(perfil), flags=re.MULTILINE)
    assert secoes[:7] == SECOES
    assert secoes[7:] in ([], ["Detalhes técnicos"])


@pytest.mark.parametrize("perfil", sorted(PERFIS))
def test_profile_links_its_notebook(perfil):
    caminho = f"notebooks/bases/{PERFIS[perfil]}.py"
    assert (ROOT / caminho).is_file()
    assert GITHUB + caminho in _secao(_texto(perfil), "Como usar")


@pytest.mark.parametrize("perfil", sorted(PERFIS))
def test_sources_section_cites_a_document(perfil):
    assert re.search(r"(https?|ftp)://\S+", _secao(_texto(perfil), "Fontes"))
```

- [ ] **Step 2: Run and watch it fail**

Run: `uv run pytest tests/unit/test_guia_pesquisador.py -q`
Expected: 6 failed (the current pages have English headings).

- [ ] **Step 3: Research SIM** (procedure above; category `SIM`, document `Estrutura_do_SIM_2025.pdf`)

Questions the page must answer from the document (or list under "Em aberto"):
- What one row is (a death certificate? fetal and non-fetal deaths together, told apart by `tipobito`?).
- Which files the `DORES` directory holds: deaths by residence or by occurrence, and what that means for a state file.
- `dtobito` vs the file year; `codmunres` vs `codmunocor`; how many digits the municipality code has.
- How `idade` is encoded (the old notebook warned it is not years).
- `causabas` is the underlying cause in CID-10.
- Preliminary vs final files (from the current page and `available_releases`).

- [ ] **Step 4: Write `docs/sources/sim_obitos.md`**

Fill each section with the cited answers. "Como usar":

````markdown
## Como usar

```python
import omnisus_db as odb

alvo = "ducklake:./data/lake/pesquisa/dados.ducklake"
escopos = odb.available("sim_obitos", years=[2022], ufs=["RR"], refresh=True)
relatorio = odb.import_dataset(
    "sim_obitos", scopes=escopos, target=alvo, policy="skip_same", run_id="sim-rr-2022"
)
with odb.LakeReader(alvo) as leitor:
    print(leitor.connect().sql("SELECT ano, count(*) AS obitos FROM lake.sim_obitos GROUP BY ano").pl())
```

Passo a passo com análise e proveniência:
[notebooks/bases/sim_obitos.py](https://github.com/raphaelfh/omnisus-db/blob/main/notebooks/bases/sim_obitos.py).
````

Move the current "Dados preliminares" section and the CLI/dictionary paragraphs into `## Detalhes técnicos`, in Portuguese; replace its `odb.Lake.local` read with `odb.LakeReader`.

- [ ] **Step 5: Research SINASC** (category `SINASC`, document `Estrutura_SINASC_para_CD.pdf`)

Questions: what one row is (a live-birth declaration); the directory `DNRES` (residence?); `dtnasc` vs file year; `codmunres` vs birth place; `peso` unit and the weight bands; `consultas` bands meaning; `parto` codes; preliminary files.

- [ ] **Step 6: Write `docs/sources/sinasc_nascidos_vivos.md`**

"Como usar": the SIM snippet with `"sinasc_nascidos_vivos"`, `run_id="sinasc-rr-2022"`, the query `SELECT ano, count(*) AS nascidos_vivos FROM lake.sinasc_nascidos_vivos GROUP BY ano`, and the link to `notebooks/bases/sinasc_nascidos_vivos.py`.

- [ ] **Step 7: Pass and commit**

```bash
uv run pytest tests/unit/test_guia_pesquisador.py -q
uv run mkdocs build --strict
git add tests/unit/test_guia_pesquisador.py docs/sources/sim_obitos.md docs/sources/sinasc_nascidos_vivos.md
git commit -m "Rewrite the SIM and SINASC profiles for researchers, with citations

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

Expected: 6 passed; mkdocs exit 0 with no warnings.

---

### Task 16: SIH and SIA profiles

**Files:**
- Rewrite: `docs/sources/sih_aih_reduzida.md`
- Create: `docs/sources/sia.md`
- Modify: `tests/unit/test_guia_pesquisador.py` (`PERFIS`)

- [ ] **Step 1: Extend the test and watch it fail**

Add `"sih_aih_reduzida": "sih_aih_reduzida",` and `"sia": "sia",` to `PERFIS`. Run → the new cases fail (`sia.md` missing, SIH headings).

- [ ] **Step 2: Check for a newer SIA technical report**

```bash
uv run python -c "import omnisus_db as odb; [print(e.name, e.size_bytes, e.modified) for e in odb.browse('/dissemin/publicos/SIASUS/200801_/Doc')]"
```

One listing of the documentation folder. If a report newer than `Informe_Tecnico_SIASUS_2019_07.pdf` exists, download it, record URL, SHA-256 and date, and cite it instead; record the finding in the Task 19 report either way.

- [ ] **Step 3: Research SIH** (category `SIHSUS`, `IT_SIHSUS_1603.pdf`)

Questions: what one AIH row is and why it is not a patient or a single admission (long stays split into several AIH?); processing month vs admission/discharge dates; `munic_res` vs the hospital's municipality; `morte` codes; `val_tot` meaning; `diag_princ` coding.

- [ ] **Step 4: Write `docs/sources/sih_aih_reduzida.md`**

"Como usar":

```python
import omnisus_db as odb

alvo = "ducklake:./data/lake/pesquisa/dados.ducklake"
escopos = odb.available("sih_aih_reduzida", years=[2024], ufs=["RR"], months=[1], refresh=True)
relatorio = odb.import_dataset(
    "sih_aih_reduzida", scopes=escopos, target=alvo, policy="skip_same", run_id="sih-rr-2024-01"
)
with odb.LakeReader(alvo) as leitor:
    print(leitor.connect().sql("SELECT ano, mes, count(*) AS aih FROM lake.sih_aih_reduzida GROUP BY ALL").pl())
```

plus the link to `notebooks/bases/sih_aih_reduzida.py`. Keep the current page's technical text under `Detalhes técnicos`.

- [ ] **Step 5: Research and write `docs/sources/sia.md`** (category `SIASUS`)

"O que um registro representa" has one line per table: `sia_bpa_individualizado`, `sia_apac_medicamentos`, `sia_apac_quimioterapia`, `sia_apac_tratamento_dialitico`, `sia_apac_laudos_diversos`, `sia_apac_cirurgia_bariatrica`, `sia_psicossocial` — each cited, or listed under "Em aberto". Also: processing month (`mes` of the file) vs competence fields (`ap_cmp`); residence fields (`ap_munpcn`, `munpac`); APAC as authorization covering a period. "Como usar" is the SIH snippet with `"sia_bpa_individualizado"`, `run_id="sia-bpai-rr-2024-01"`, table `lake.sia_bpa_individualizado`, and the link to `notebooks/bases/sia.py`. "Detalhes técnicos": the seven dataset names and that all share the SIA directory, from `docs/datasets.md`.

- [ ] **Step 6: Pass and commit**

```bash
uv run pytest tests/unit/test_guia_pesquisador.py -q
uv run mkdocs build --strict
git add tests/unit/test_guia_pesquisador.py docs/sources/sih_aih_reduzida.md docs/sources/sia.md
git commit -m "Rewrite the SIH profile and add a SIA profile, with citations

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

`mkdocs build --strict` may report `sia.md` as not in nav as INFO, not a warning; Task 20 adds it to the nav.

---

### Task 17: CNES and IBGE profiles

**Files:**
- Rewrite: `docs/sources/cnes_estabelecimentos.md`, `docs/sources/ibge_populacao.md`
- Modify: `tests/unit/test_guia_pesquisador.py` (`PERFIS`)

- [ ] **Step 1: Extend the test and watch it fail**

Add `"cnes_estabelecimentos": "cnes_estabelecimentos",` and `"ibge_populacao": "ibge_populacao",`. Run → new cases fail.

- [ ] **Step 2: Research CNES** (category `CNES`, `IT_CNES_1706.pdf`)

Questions: what one ST row is (an establishment in one competence); why a CNES code can repeat across competences (and within one?); `competen` vs file month; `codufmun` digits; `tp_unid` codes source; that the packaged dictionary declares 12 columns and other columns are preserved (evidence: `src/omnisus_db/data/dicionarios/cnes_estabelecimentos.yaml`); `aux_cnes` and `import_cnes_master` (evidence: `src/omnisus_db/__init__.py` docstrings).

- [ ] **Step 3: Write `docs/sources/cnes_estabelecimentos.md`**

"Como usar": the SIH snippet with `"cnes_estabelecimentos"`, `run_id="cnes-rr-2024-01"`, query `SELECT competen, count(DISTINCT cnes) AS estabelecimentos FROM lake.cnes_estabelecimentos GROUP BY ALL`, a sentence naming `odb.import_cnes_estabelecimentos` (also refreshes `aux_cnes`), and the link to `notebooks/bases/cnes_estabelecimentos.py`.

- [ ] **Step 4: Research IBGE** (category `IBGE`, `Pop_Residente_TCU_ate_2023.pdf` plus the 7 URLs already on the page)

Questions: census vs estimate and their reference dates; which editions the library accepts (`CENSUS_YEARS`, `ESTIMATE_UNAVAILABLE_YEARS`, evidence `src/omnisus_db/sources/ibge/products.py`); territorial universe of the edition; `codigo_ibge` digits; why a second import of the same edition makes the view fail (evidence `src/omnisus_db/sources/ibge/importers/pop.py`).

- [ ] **Step 5: Write `docs/sources/ibge_populacao.md`**

Translate the existing English content to Portuguese under the new headings and `Detalhes técnicos`; keep all 7 URLs in "Fontes". "Como usar":

```python
import omnisus_db as odb

alvo = "ducklake:./data/lake/pesquisa/dados.ducklake"
resultados = odb.import_ibge_populacao(years=[2022], product="census", target=alvo)
with odb.LakeReader(alvo) as leitor:
    print(leitor.connect().sql("SELECT ano, count(*) AS municipios, sum(populacao) FROM lake.ibge_populacao GROUP BY ano").pl())
```

State that running the import twice for the same edition makes `ibge_populacao` fail, and link `notebooks/bases/ibge_populacao.py`, which checks the manifest first.

- [ ] **Step 6: Pass and commit**

```bash
uv run pytest tests/unit/test_guia_pesquisador.py -q
uv run mkdocs build --strict
git add tests/unit/test_guia_pesquisador.py docs/sources/cnes_estabelecimentos.md docs/sources/ibge_populacao.md
git commit -m "Rewrite the CNES and IBGE population profiles in Portuguese, with citations

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 18: SINAN Chagas, SINAN hanseníase and medicines profiles; completeness

**Files:**
- Rewrite: `docs/sources/sinan_chagas.md`, `docs/sources/sinan_hanseniase.md`, `docs/sources/medicamentos.md`
- Modify: `tests/unit/test_guia_pesquisador.py`

- [ ] **Step 1: Extend the test and watch it fail**

Add `"sinan_chagas": "sinan",`, `"sinan_hanseniase": "sinan",`, `"medicamentos": "medicamentos",` to `PERFIS`, and append:

```python
def test_every_bases_notebook_has_a_profile():
    notebooks = {
        p.stem for p in (ROOT / "notebooks/bases").glob("*.py") if not p.name.startswith("_")
    }
    assert set(PERFIS.values()) == notebooks
```

Run → new cases fail.

- [ ] **Step 2: Research SINAN** (category `SINAN`: `DIC_DADOS_Chagas_v5.pdf`, `DIC_DADOS_Notificacao_Individual_v5.pdf`; hanseníase dictionary `https://portalsinan.saude.gov.br/images/documentos/Agravos/Hanseniase/DIC_DADOS_Hanseniase_v5.pdf`, **not archived in `registro.json`**: cite URL and access date, compute its SHA-256 and write it in "Fontes" as "calculado em <data>, não arquivado")

Questions: a notification is not a confirmed case (Chagas `classi_fin`; hanseníase entry mode `modoentr` and `tpalta_n`); the national file and `sg_uf_not` vs `id_mn_resi`; notification date vs file year; final vs preliminary directories (evidence: current page contracts and `reports/2026-09-12-sinan-e-dispensacao.md` §1.2, §1.4); `classoper` absent from the packaged hanseníase dictionary (evidence: `src/omnisus_db/data/dicionarios/sinan_hanseniase.yaml`).

- [ ] **Step 3: Write both SINAN pages**

Move the existing contracts into `Detalhes técnicos`. "Como usar" for Chagas:

```python
import omnisus_db as odb

alvo = "ducklake:./data/lake/pesquisa/dados.ducklake"
print(odb.available_releases("sinan_chagas", refresh=True))  # ano -> final ou prelim
escopos = odb.available("sinan_chagas", years=[2022])
relatorio = odb.import_dataset(
    "sinan_chagas", scopes=escopos, target=alvo, policy="skip_same", run_id="chagas-2022"
)
with odb.LakeReader(alvo) as leitor:
    print(leitor.connect().sql("SELECT _source_ano, _source_release, count(*) FROM lake.sinan_chagas GROUP BY ALL").pl())
```

Hanseníase: same with `"sinan_hanseniase"`, `years=[2023]`, `run_id="hanseniase-2023"`. Both link `notebooks/bases/sinan.py`.

- [ ] **Step 4: Write the medicines page**

Reorganize the existing content under the seven headings: "Em uma frase" (three public sources and one missing one); "O que um registro representa" (APAC row, stock observation, Farmácia Popular indicator — each from the page's current sources); "Armadilhas" (stock ≠ dispensing, APAC ≠ dose); "Fontes" keeps every current source and adds the 2026-09-12 report link; the Hórus API details and tests paragraph go to `Detalhes técnicos`. "Como usar":

```python
import omnisus_db as odb
from omnisus_db.sources.medicamentos import fetch_stock_page

alvo = "ducklake:./data/lake/pesquisa/dados.ducklake"
escopos = odb.available("sia_apac_medicamentos", years=[2024], ufs=["RR"], months=[1], refresh=True)
odb.import_dataset(
    "sia_apac_medicamentos", scopes=escopos, target=alvo, policy="skip_same", run_id="apac-am-rr-2024-01"
)
pagina = fetch_stock_page(filters={"codigo_uf": "14"}, limit=20)
print(pagina.sha256, len(pagina.records))
```

and the link to `notebooks/bases/medicamentos.py`.

- [ ] **Step 5: Pass and commit**

```bash
uv run pytest tests/unit/test_guia_pesquisador.py -q
uv run mkdocs build --strict
git add tests/unit/test_guia_pesquisador.py docs/sources/sinan_chagas.md docs/sources/sinan_hanseniase.md docs/sources/medicamentos.md
git commit -m "Rewrite the SINAN and medicines profiles under the researcher template

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

Expected: 28 passed (9 profiles × 3 + completeness).

---

### Task 19: Real end-to-end run and validation report (manual, not CI)

**Files:**
- Create: `reports/<AAAA-MM-DD>-guia-pesquisador-validacao.md` (ISO date of the day the run happens)

**Interfaces:**
- Consumes: all eight `bases/` notebooks; `_comum` run folders (`plano.json`, `resultado.json`, `proveniencia.json`).
- Produces: the numbers Task 20 cites and the evidence Task 21 appends to.

DATASUS FTP is a shared public server: run each notebook once, in order, with `concurrency=1` (already in the notebooks). Do not loop on failures; investigate instead.

- [ ] **Step 1: Fresh research lake**

```bash
export OMNISUS_NOTEBOOK_DATA="$PWD/data/lake/pesquisa-validacao-$(date +%F)"
mkdir -p "$OMNISUS_NOTEBOOK_DATA/html"
```

- [ ] **Step 2: Run the notebooks, SIM before IBGE**

For each of `sim_obitos sinasc_nascidos_vivos sih_aih_reduzida sia cnes_estabelecimentos ibge_populacao sinan medicamentos`, one at a time:

```bash
/usr/bin/time -p uv run --locked --extra notebooks marimo export html notebooks/bases/sim_obitos.py \
  -o "$OMNISUS_NOTEBOOK_DATA/html/sim_obitos.html" -- --executar true
ls "$OMNISUS_NOTEBOOK_DATA"/execucoes/*/proveniencia.json | wc -l
```

Expected after each: exit 0 and the count of `proveniencia.json` files grows by one. If an export exits 0 but no new `proveniencia.json` appears, open the HTML: a cell error does not always set the exit code. Record the error text in the report; fix the notebook in a separate commit and rerun only that notebook.

If a default file is absent or larger than 25 MiB, choose the nearest earlier month or year that `available` lists, change the notebook's default, and record why.

- [ ] **Step 3: Idempotence**

Run the SIM notebook a second time with the same command. Expected: its new `resultado.json` has status `skipped` with `same source and parser version already published`, and `linhas_importadas` is 0.

- [ ] **Step 4: Summarize the runs**

Save to the scratchpad (not the repository) as `resumo_validacao.py` and run with `uv run python resumo_validacao.py "$OMNISUS_NOTEBOOK_DATA"`:

```python
"""Markdown table of every research-notebook run in a data root."""

import json
import sys
from datetime import datetime
from pathlib import Path

raiz = Path(sys.argv[1])
print("| dataset | escopos | status | linhas importadas | snapshot | duração (s) | arquivos (SHA-256) |")
print("| --- | --- | --- | --- | --- | --- | --- |")
for pasta in sorted((raiz / "execucoes").iterdir()):
    plano = json.loads((pasta / "plano.json").read_text(encoding="utf-8"))
    resultado = json.loads((pasta / "resultado.json").read_text(encoding="utf-8"))
    proveniencia_path = pasta / "proveniencia.json"
    prov = json.loads(proveniencia_path.read_text(encoding="utf-8")) if proveniencia_path.exists() else {}
    inicio = datetime.fromisoformat(plano["fixado_em_utc"])
    fim = datetime.fromisoformat(prov["gerado_em_utc"]) if prov else None
    status = ", ".join(d["status"] for d in resultado.get("desfechos", [])) or "ibge"
    linhas = resultado.get("linhas_importadas", sum(r["rows"] for r in resultado.get("importadas", [])))
    arquivos = "; ".join(
        f"{p.get('source_uri') or p.get('url')} ({(p.get('source_sha256') or p.get('sha256'))})"
        for p in prov.get("publicacoes", [])
    )
    duracao = f"{(fim - inicio).total_seconds():.0f}" if fim else "—"
    print(f"| {plano['dataset']} | {plano.get('escopos') or plano.get('ano')} | {status} | {linhas} | {prov.get('snapshot_id', '—')} | {duracao} | {arquivos} |")
```

Compressed sizes: `odb.browse(<directory>)` without `refresh` reads the listing the run cached; record the `size_bytes` of each file named in `source_uri`.

- [ ] **Step 5: Verify the deferred data facts**

From the IBGE run folder's CSVs: `digitos_codigo_ibge.csv` and `digitos_codmunres_sim.csv`. Record both digit counts. If they are not 7 and 6, fix the join in `bases/ibge_populacao.py` (and the indicators page in Task 20) before continuing. Record `obitos_por_100_mil.csv` for RR 2022.

- [ ] **Step 6: Write the report**

`reports/<AAAA-MM-DD>-guia-pesquisador-validacao.md`, in Portuguese:
- Environment: commit SHA, `omnisus_db` version, marimo version, OS, date/time UTC.
- The table from Step 4 plus compressed sizes.
- Idempotence result (Step 3).
- Municipality code formats (Step 5) and the RR 2022 rate table.
- SIA documentation check (Task 16 Step 2).
- Any default slice changed and why; any failure and its fix.
- A heading `## Revisão adversarial das afirmações` left for Task 21.

- [ ] **Step 7: Commit**

```bash
git add reports/*-guia-pesquisador-validacao.md notebooks/bases
git commit -m "Record the end-to-end validation of the research notebooks

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 20: Guide pages, navigation, README and CHANGELOG

**Files:**
- Create: `docs/pesquisa/index.md`, `docs/pesquisa/indicadores.md`, `docs/pesquisa/reprodutibilidade.md`
- Modify: `mkdocs.yml` (nav), `README.md` (notebook section), `CHANGELOG.md`
- Modify: `tests/unit/test_guia_pesquisador.py`

**Interfaces:**
- Consumes: `PERFIS`, `GITHUB`, `ROOT` (Task 15); numbers from the Task 19 report.

- [ ] **Step 1: Extend the test and watch it fail**

Append:

```python
COMECE_AQUI = ROOT / "docs/pesquisa/index.md"


@pytest.mark.parametrize("notebook", sorted(set(PERFIS.values())))
def test_start_page_links_every_bases_notebook(notebook):
    assert f"{GITHUB}notebooks/bases/{notebook}.py" in COMECE_AQUI.read_text(encoding="utf-8")


@pytest.mark.parametrize("perfil", sorted(PERFIS))
def test_start_page_links_every_profile(perfil):
    assert f"../sources/{perfil}.md" in COMECE_AQUI.read_text(encoding="utf-8")
```

Run → fails (`index.md` missing).

- [ ] **Step 2: `docs/pesquisa/index.md` — Comece aqui**

Write, in Portuguese:

1. **O que é** — two sentences: omnisus-db importa bases abertas do DATASUS e do IBGE para um lake local e registra de onde veio cada linha.
2. **Preparar** — from a checkout:

   ```bash
   git clone https://github.com/raphaelfh/omnisus-db.git
   cd omnisus-db
   uv sync --locked --extra notebooks
   uv run --locked --extra notebooks marimo edit notebooks/bases/sim_obitos.py
   ```

3. **Qual base responde minha pergunta?** — a table with columns *Pergunta*, *Base*, *Perfil*, *Notebook*, one row per profile in `PERFIS` (9 rows): mortality → SIM; births, birth weight, prenatal → SINASC; hospital admissions → SIH; outpatient production (seven tables) → SIA; health facilities → CNES; denominators → IBGE população; notifiable diseases (Chagas aguda, hanseníase) → SINAN Chagas / SINAN hanseníase; medicines → Medicamentos. Profile links are relative (`../sources/<perfil>.md`); notebook links are absolute GitHub URLs.
4. **As seis etapas** — one short paragraph each: O que a base registra · Descobrir · Planejar e importar · Conferir · Analisar · Guardar, naming the functions each uses (`available`/`available_releases`, `import_dataset` with `policy="skip_same"` and `run_id`, `LakeReader.publications`/`outdated`, `LakeReader(snapshot_id=...)`, `proveniencia.json`).
5. **O lake de pesquisa** — `data/lake/pesquisa/dados.ducklake`, one folder per run, `OMNISUS_NOTEBOOK_DATA`; why one shared lake (rates need SIM and IBGE together).
6. **Cuidados gerais** — preliminary files can change (link Reprodutibilidade); a record is not a person (link the profiles' Armadilhas); one writer per lake at a time; opening a notebook downloads nothing.

- [ ] **Step 3: Verify the indicator reference**

Fetch `http://tabnet.datasus.gov.br/tabdata/livroidb/2ed/indicadores.pdf` (RIPSA, *Indicadores básicos para a saúde no Brasil: conceitos e aplicações*, 2ª ed., 2008) and `http://tabnet.datasus.gov.br/cgi/idb2012/matriz.htm`. Keep a citation only if the page actually defines the indicator it is cited for (for example "taxa bruta de mortalidade", "proporção de nascidos vivos de baixo peso ao nascer"), with page numbers. If neither URL works, search for the current RIPSA/IDB address; if none is found, the indicators page states formulas as computations of this guide, not as official definitions, and says so.

- [ ] **Step 4: `docs/pesquisa/indicadores.md`**

Sections: **Numerador e denominador**; **Residência, ocorrência e notificação** (link the SIM, SINASC, SIH and SINAN profiles); **População do IBGE** (census vs estimate, reference dates, `ESTIMATE_UNAVAILABLE_YEARS = (2007, 2010, 2022, 2023)`, one edition per municipality/year); **Conferir o código do município antes de juntar** (show the two digit-count queries from the IBGE notebook and the Task 19 result); **Exemplo completo: óbitos por 100 mil habitantes, RR 2022** — the SQL from `bases/ibge_populacao.py` (`obitos_por_100_mil`), the cautions (deaths of RR residents in other states' files, census reference date vs calendar year — each cited or marked as a caution of this guide), and the result table copied from the Task 19 report with a link to it.

- [ ] **Step 5: `docs/pesquisa/reprodutibilidade.md`**

Sections: **Antes de importar** (choose `run_id`; `policy="skip_same"`; what `skipped` and a `failed` asking for `replace` mean); **O que o manifesto guarda** (`publications()` fields: `publication_id`, `dataset`, `scope`, `release`, `source_uri`, `source_sha256`, `parser_version`, `run_id`, `published_at`, `rows`, `active`); **Fixar a leitura** (`LakeReader(alvo, snapshot_id=...)`, `snapshots()`); **Quando o DATASUS revisa** (`outdated()` then `import_dataset(..., policy="replace", run_id=...)`, link `../guides/reprocessing-and-maintenance.md`); **IBGE** (manifest `ibge_population_manifest`, `publication_id`); **Como citar** — template:

```text
<Base> (<dataset>), arquivo <nome do arquivo> (<source_uri>), SHA-256 <source_sha256>,
acessado em <AAAA-MM-DD> pelo DATASUS. Importado com omnisus-db <versão>, lake snapshot
<snapshot_id>, execução <run_id>.
```

- [ ] **Step 6: Navigation**

In `mkdocs.yml`, insert after `- Home: index.md`:

```yaml
  - Guia do pesquisador:
      - Comece aqui: pesquisa/index.md
      - Bases:
          - SIM · óbitos: sources/sim_obitos.md
          - SINASC · nascidos vivos: sources/sinasc_nascidos_vivos.md
          - SIH · AIH reduzida: sources/sih_aih_reduzida.md
          - SIA · produção ambulatorial: sources/sia.md
          - CNES · estabelecimentos: sources/cnes_estabelecimentos.md
          - IBGE · população: sources/ibge_populacao.md
          - SINAN · Chagas aguda: sources/sinan_chagas.md
          - SINAN · hanseníase: sources/sinan_hanseniase.md
          - Medicamentos: sources/medicamentos.md
      - Indicadores: pesquisa/indicadores.md
      - Reprodutibilidade: pesquisa/reprodutibilidade.md
```

and delete the `- Sources:` block (its pages are now under Bases; addresses do not change).

- [ ] **Step 7: README**

Replace the README from "National Chagas and Hanseníase SINAN notifications..." through the end of "## Notebooks: learning path" (keep "See the documentation site..." and its command) with:

````markdown
## Para pesquisadores

O [guia do pesquisador](https://raphaelfh.github.io/omnisus-db/pesquisa/) mostra qual
base responde a cada pergunta, o que um registro representa e como citar o resultado.
Cada base tem um notebook com as mesmas seis etapas em
[`notebooks/bases/`](notebooks/bases/): SIM, SINASC, SIH, SIA, CNES, população IBGE,
SINAN (Chagas aguda e hanseníase) e medicamentos.

```bash
uv sync --locked --extra notebooks
uv run --locked --extra notebooks marimo edit notebooks/bases/sim_obitos.py
```

Abrir um notebook não baixa nada. Outros notebooks, para explorar o DATASUS e
para quem desenvolve a biblioteca, estão no [índice](notebooks/README.md).
````

- [ ] **Step 8: CHANGELOG**

Under `## Unreleased` → `### Added` (create the heading above `### Changed`):

```markdown
### Added

- **Guia do pesquisador** (`docs/pesquisa/`): comece aqui, indicadores e
  reprodutibilidade, em português. Os perfis das bases em `docs/sources/` seguem
  um mesmo roteiro com fontes citadas; o SIA ganhou perfil.
- **Um notebook por base** em `notebooks/bases/` (SIM, SINASC, SIH, SIA, CNES,
  IBGE, SINAN, medicamentos), com as mesmas seis etapas e um lake de pesquisa
  compartilhado. Abrir um notebook não baixa nem grava nada; um teste garante isso.
  Os demais notebooks estão em `notebooks/explorar/` e `notebooks/desenvolvimento/`.
```

- [ ] **Step 9: Pass and commit**

```bash
uv run pytest tests/unit/test_guia_pesquisador.py -q
uv run mkdocs build --strict
git add docs/pesquisa mkdocs.yml README.md CHANGELOG.md tests/unit/test_guia_pesquisador.py
git commit -m "Add the researcher guide pages and navigation

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

Expected: 45 passed (28 + 8 notebook links + 9 profile links); mkdocs exit 0 with no warnings.

---

### Task 21: Adversarial claim review

**Files:**
- Modify: profiles in `docs/sources/`, `docs/pesquisa/indicadores.md` (removals or moves to "Em aberto")
- Modify: the Task 19 report, section `## Revisão adversarial das afirmações`

- [ ] **Step 1: Dispatch a fresh-context reviewer**

Use the Agent tool (general-purpose), with this prompt:

> You review factual claims in a Portuguese research guide against the documents they cite. You have not seen how they were written. Repository: the current working directory. Pages: `docs/sources/{sim_obitos,sinasc_nascidos_vivos,sih_aih_reduzida,sia,cnes_estabelecimentos,ibge_populacao,sinan_chagas,sinan_hanseniase,medicamentos}.md` (sections "O que um registro representa", "Datas e geografia", "Armadilhas") and `docs/pesquisa/indicadores.md`. For each sentence that states a fact: find its citation; download the cited PDF to `<scratchpad>` if it is not there; check its SHA-256 against `docs/dicionario/fontes/registro.json` (report a mismatch); open the cited page and decide SUPPORTED, NOT SUPPORTED, or NO CITATION. For repository evidence, open the file and decide the same way. Do not edit files. Return a Markdown table: page, sentence (first 12 words), citation, verdict, what the document actually says (one line). Do not keyword-match; read the passage.

- [ ] **Step 2: Act on the verdicts**

For each NOT SUPPORTED or NO CITATION: fix the citation if the claim is in the document at another page, otherwise move it to "Em aberto" (when a researcher would assume the wrong thing) or delete it. Do not argue with a verdict by adding a weaker citation.

- [ ] **Step 3: Record and commit**

Paste the reviewer's table and the list of changes into the report section. Then:

```bash
uv run pytest tests/unit/test_guia_pesquisador.py -q
uv run mkdocs build --strict
git add docs/sources docs/pesquisa reports/*-guia-pesquisador-validacao.md
git commit -m "Apply the adversarial claim review to the researcher guide

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 22: Rebase after PR #4, final gates, ask before the PR

**Files:**
- Modify (only on conflict): `pyproject.toml`, `uv.lock`

- [ ] **Step 1: PR #4 state**

Run: `gh pr view 4 --json state,mergedAt`
- `MERGED`: `git fetch origin && git rebase origin/main`. On conflict in `pyproject.toml` keep marimo **out** of `[project] dependencies`, take PR #4's bound in the `notebooks` extra, keep `"omnisus-db[notebooks]"` in `dev`; then `uv lock` and `uv sync --locked --extra dev --extra docs`.
- `OPEN`: stay on the current base and say so when asking Raphael.

- [ ] **Step 2: marimo 0.24 `sys.path` (only if rebased onto 0.24)**

```bash
uv run marimo --version
uv run marimo export html notebooks/desenvolvimento/performance_dbf.py -o "$TMPDIR/perf.html"
uv run marimo export html notebooks/bases/ibge_populacao.py -o "$TMPDIR/ibge.html"
```

Expected: both exit 0 (`_performance_dbf` and `_comum` import without `sys.path.insert`). A `ModuleNotFoundError` blocks the PR: report it.

- [ ] **Step 3: Every gate**

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run python scripts/gen_datasets_doc.py --check
uv run marimo check --strict --ignore-scripts notebooks
uv run pytest -m "not e2e and not perf" --cov=omnisus_db --cov-fail-under=85
uv run mkdocs build --strict
uv run pre-commit run --all-files
```

Expected: every command exits 0. Report the pytest totals.

- [ ] **Step 4: Ask Raphael**

Do not push or open the PR. Send a summary: commits, test totals, the deviations listed at the top of this plan, the validation report path, claims moved to "Em aberto", and whether PR #4 was merged. Ask whether to push the branch and open the PR.
