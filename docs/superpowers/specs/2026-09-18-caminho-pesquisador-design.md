# Caminho de pesquisador — design

Date: 2026-09-18. Status: approved by Raphael as “faça isso após planejar”,
with PyPI already in progress (out of this change).

## Goal

A researcher can import without duplicating rows, pin the snapshot they read,
join municipality codes without inventing a 7th digit, and copy a citation
that matches the Portuguese reproducibility guide.

## Decisions

| # | Decision | Rejected |
| --- | --- | --- |
| D1 | `import_dataset` keeps `policy="append"`. A new `import_research` defaults to `skip_same` and requires `run_id`. | Changing the public default (breaks existing scripts). |
| D2 | Citation is a public function `cite(lake, ...)` returning structured fields plus Portuguese `text`. | Notebook-only `proveniencia.json`; English-only citation. |
| D3 | Municipality helper is `left(trim(...), 6)` (or 7), not `lpad`. Import still does not rewrite stored codes. | Padding to 7 (invents check digit); executing dictionary `x-normalization-hint` at ingest. |
| D4 | No new SINAN agravos in this change. | Matching PySUS coverage. |
| D5 | PyPI publish is already happening elsewhere. Docs may mention `pip install omnisus-db` without adding release machinery. | Wheel/CI work in this change. |

## Public interface

```python
odb.import_research(dataset, *, scopes, run_id, target=..., policy="skip_same", ...)
odb.latest_snapshot_id(lake) -> int
odb.cite(lake, *, dataset=None, snapshot_id=None, run_id=None, accessed=None) -> Citation
odb.municipality_join_key(value, *, digits=6) -> str | None
odb.municipality_join_key_sql(column, *, digits=6) -> str
```

`import_research` refuses `policy="append"`. `cite` uses the latest snapshot when
`snapshot_id` is omitted, and records that id in the result. IBGE rows come from
`ibge_population_manifest` when `dataset == "ibge_populacao"`.

## Out of scope

CLI flags, changing `LIMITE_BYTES`, decoding every categorical field, RIPSA-complete rates.
