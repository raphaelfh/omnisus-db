# Scoped removal and publication reconciliation — design

Date: 2026-09-11. Status: approved (design), implementation pending.
Origin: Omnisus app integration requests U4 (reconciliation, adoption and
migration of publications) and U5 (removal by scope coherent with
publications), which block the app's cutover (T14).

## Goal

1. Remove one source scope from a lake so that data rows and the publication
   manifest never disagree afterwards (U5).
2. Let a caller reconcile an unknown commit without decoding the package's
   private manifest encoding (U4).
3. State the migration procedure for a lake built before publications existed,
   and declare where reconciliation by `run_id` does not apply (U4).

## Decisions

- **No adoption of legacy rows.** Decision by Raphael, 2026-09-11: rows without
  a manifest are never certified in place. A legacy lake is migrated by
  rebuilding into a new target, so provenance exists from the first import.
  Rejected: `adopt_scope` recording found rows as an unverified publication —
  faster cutover, but it makes the manifest say "verified" about rows nobody
  verified.
- **`delete_scope` is a managed operation**, not a policy of `publish_scope`.
  Rejected: `publish_scope(policy="replace")` with empty staging — the code
  refuses empty staging on purpose, and a publication of nothing is the wrong
  record.
- **`publications()` rows gain a decoded `scope`.** The encoder lives in
  `publication.py`; the decoder belongs beside it. Rejected: a package-level
  `Lake.reconcile(run_id, scopes)` — duplicates logic the app owns, and
  asserting "absent ⇒ not committed" is only safe while `run_id` reuse is the
  caller's discipline.
- **No `retired_at`/reason column** on the manifest: a schema migration on
  every existing lake for a distinction nobody asked for; the caller logs the
  deletion. Retired rows are `active = false`, indistinguishable from replaced
  ones, which is what the app's reconcile already treats as "historical".
- **No CLI command.** Nobody asked; the API is the contract.
- **IBGE and cnes_master keep their models.** The limitation is declared, not
  papered over: IBGE editions reconcile by `publication_id` in
  `ibge_population_manifest`; cnes_master is an idempotent upsert with no
  publication identity, so its reconciliation is a re-run.

## API

### `Lake.delete_scope(table, scope) -> DeletionResult`

Implemented as `publication.delete_scope(lake, table, scope)` with a thin
`Lake` wrapper, like `publish_scope`.

- Validation reuses `publish_scope`'s rules: scope shape (two-letter UF or
  `None`, year range, month range, no month on a national scope), reserved
  table names, and the national-vs-state compatibility check against the
  table's columns. An unknown table raises `ValueError` — silently deleting
  nothing from a mistyped name is wrong.
- Runs inside the caller's managed transaction when one is active, otherwise
  opens one (same pattern as `publish_scope`). A rollback leaves data and
  manifest untouched.
- Rows are deleted by the same predicate `publish_scope` uses. The scope's
  fields (`_source_ano` for national; `ano`, `uf`, optionally `mes` for state)
  and the predicate builder are extracted into two helpers shared by both
  functions, so the definition stays single.
- Manifest rows are retired by **containment**: every active row for the table
  whose decoded scope fields include all of the requested fields with equal
  values. `ScopeKey(uf="RR", ano=2023)` on a monthly table therefore deletes
  all twelve months and retires each month's publication.
- Rows without a manifest (for example from `Lake.ingest`) are deleted as
  well; `publications_retired` may be zero. `rows_deleted` exceeding the
  retired publications' row sum is the caller's signal that unmanaged rows
  were present.
- `DeletionResult(rows_deleted: int, publications_retired: int)` is a frozen
  dataclass in `publication.py`, exported from `omnisus_db`.

### `Session.publications()` rows gain `"scope"`

Each row keeps its current keys and gains `scope`: a `ScopeKey` decoded from
`scope_json` — `{"_source_ano": y}` becomes `ScopeKey(uf=None, ano=y)`;
`{"ano", "uf"[, "mes"]}` becomes the state scope. Any other shape decodes to
`None`, with `scope_json` still present for inspection. Available to
`LakeReader` as well, since the method lives on the session base.

### Declared limitations

`import_ibge_pop` and `import_cnes_master` docstrings and `docs/api.md` state
that neither accepts `run_id` or `policy` and neither appears in
`Lake.publications()`; each names its own reconciliation key as above.

## Documentation

- `docs/guides/reprocessing-and-maintenance.md`: "Remove a scope"; "Migrate a
  legacy lake" (new target → `available()` + import → verify `publications()`
  → switch the target string → retire the old lake); "Inspect an interrupted
  run" rewritten around the decoded `scope`.
- `docs/api.md`: `delete_scope`, `DeletionResult`, the `scope` key, the
  declared limitations.
- `CHANGELOG.md`: Added (`delete_scope`, `DeletionResult`, `scope`), Changed
  (`publications()` rows), the declared limitations.

## Tests

Unit, in `tests/unit/lake/test_publication.py` (the manifest's existing test
file, nine tests today): yearly and monthly tables (all months
deleted, each month's manifest retired, neighbouring scopes untouched);
national table; unmanaged rows deleted with zero retirements; unknown table
raises; rollback of the caller's transaction leaves both data and manifest
intact; `publications()[i]["scope"]` round-trips state, monthly and national
scopes and is `None` for an unrecognised shape. Integration: one PostgreSQL
case in `tests/integration/test_postgres_lake.py` deleting the published
scope and observing it through `LakeReader`.

## Out of scope

Adoption of legacy rows; a CLI command; a retirement column; unifying the IBGE
or cnes_master manifests with `_omnisus_publications`; the app's worker-side
maintenance contract (its auxiliaries/maintenance 501s cite that contract;
`bootstrap_auxiliares`, `optimize`, `expire_snapshots` and `cleanup_files`
already exist in the package).
