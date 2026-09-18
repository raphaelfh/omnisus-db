# Caminho de pesquisador Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use sp-executing-plans by default. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Public research helpers: safe import, pinned snapshot, citation, municipality join key.

**Architecture:** New module `omnisus_db.research` re-exported from `__init__.py`. Import path delegates to `import_dataset`. Citation reads `publications()` or `ibge_population_manifest`. Municipality helpers never mutate stored columns.

**Tech Stack:** Python ≥ 3.12, pytest, DuckLake via existing `Lake`/`LakeReader`.

**Spec:** `docs/superpowers/specs/2026-09-18-caminho-pesquisador-design.md`

## Global Constraints

- Portuguese citation text matching `docs/pesquisa/reprodutibilidade.md` “Como citar”.
- Comments and commit messages in Portuguese if committing.
- No new dependencies. Do not change `import_dataset` default policy.
- Do not commit unless the user asks.

---

### Task 1: Citation, snapshot pin, research import

**Files:**
- Create: `src/omnisus_db/research.py`
- Create: `tests/unit/test_research.py`
- Modify: `src/omnisus_db/__init__.py`

**Interfaces:**
- Produces: `Citation`, `cite`, `latest_snapshot_id`, `import_research`

---

### Task 2: Municipality join key

**Files:**
- Modify: `src/omnisus_db/research.py`
- Modify: `tests/unit/test_research.py`

**Interfaces:**
- Produces: `municipality_join_key`, `municipality_join_key_sql`

---

### Task 3: Wire notebooks and docs

**Files:**
- Modify: `notebooks/bases/_comum.py`
- Modify: `tests/unit/notebooks/test_comum.py`
- Modify: `docs/pesquisa/reprodutibilidade.md`, `docs/pesquisa/indicadores.md`, `docs/api.md`, `docs/guides/getting-started.md`, `CHANGELOG.md`

---
