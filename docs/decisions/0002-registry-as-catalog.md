# 0002 — Registry as catalog, not gate; eras as rows, not fields

**Date:** 2026-09-09
**Status:** Decided
**Spec ref:** `docs/superpowers/specs/2026-09-09-repo-structure-design.md` §3

This ADR records the registry design decision. Examples of additional era rows
describe how to extend the catalog; they do not imply that those rows ship in
the current registry. See [Datasets](../datasets.md) for the implemented rows.

## Context

Dataset facts were spread across `datasets.py`, `inventory.py` and `fetch.py`,
with `monthly` stated twice and nothing cross-checking them. The SIA/APAC
family (7 datasets) was registered in all three but reachable from neither
the public API nor the CLI. Unifying the facts into one row was the obvious
fix, and it raised two design risks worth recording.

## Decision 1 — the registry is a catalog, not a gate

A single-source registry can become a lock: "the eleven keys in this dict are
the only things you may ingest." We reject that reading.

- The pipeline takes `Dataset` **values**: `import_scope(dataset: Dataset, ...)`.
- `REGISTRY` is a dict of pre-built values — convenience, not authority.
- An uncurated dataset is ingested by constructing a `Dataset(...)` and passing
  it through the same code path. There is no second, untyped mode.
- The row holds **identity and location only**. Behaviour goes in an importer
  module (the existing hybrid pattern), never a flag on the row.

## Decision 2 — era variants are separate rows

Live listing of `ftp.datasus.gov.br` shows era directories for three of four
families (`SIM/CID9` vs `CID10`, `SIASUS/199407_200712` vs `200801_`,
`SIHSUS/199201_200712` vs `200801_`). A single `ftp_dir: str` cannot reach
them.

We considered an `eras: tuple[Era, ...]` field and rejected it: one row implies
one dictionary, but CID9 and CID10 have different columns. The row would claim
a schema it does not have.

Instead, each supported era gets its own row with its own dictionary (for
example, the existing `sim_do` and a possible future `sim_do_cid9`, which is not
currently registered). A cross-era union is a deliberate act by the user, which is
correct: it surfaces a real schema break instead of hiding it.

## Consequences

- `ftp_dir: str` survives; `since` becomes `coverage: (first, last | None)`.
- `cadence` (how DATASUS publishes) and `partition_by` (how we store) are
  separate fields. Deriving one from the other would let a storage change
  silently alter filename generation.
- `dictionary` is a field so an ad-hoc `Dataset` can point at a YAML outside
  the package. Uncurated does not mean schemaless: without a YAML the import
  fails fast rather than falling back to all-strings.
- Adding an era is the same operation as adding a dataset: one row, one YAML.
- The row's schema becomes semi-public (users may construct it). Changes are
  additive and keyword-only.
- Tier 3 tests (spec §6) validate each row's `ftp_dir` and `coverage` against
  the live server on a schedule, because centralizing facts centralizes the
  blast radius of a wrong one.
