# D2 independent spec and quality review

Reviewed against base `468145d`, task-1 brief/report, and D2/global design contracts on 2026-09-10. Read-only review of implementation, fixtures, tests, documentation and packaged dictionary; only this report was written.

## Verdict

- **Spec: PASS for the D2 agent scope**, including the controller-approved restriction to the latest published estimate edition and census 2010/2022. Historical estimates are explicitly unsupported, as agreed; their absence is not a finding.
- **Quality: PASS.** No actionable P1/P2 finding identified in the reviewed D2 implementation.
- **Overall feature integration remains pending** in the controller-owned public wrapper/CLI. This verdict does not certify the public API as ready.

## Evidence

`PYTHONPATH=src .venv/bin/pytest tests/unit/sources/ibge tests/integration/test_ibge_pop_e2e.py -q`: **46 passed in 0.73s** using the existing shared environment.

An additional controlled HTTP probe used population response bytes with deliberately added leading/trailing whitespace. The returned SHA-256 matched those exact response-content bytes, matched the population evidence hash, preserved the evidence URL, and recorded UTC collection time. This independently checks that provenance hashes the received content rather than reserialized JSON.

Inspection verified explicit aggregate/variable selection; no product fallback; metadata variable/unit/municipal-level/Total checks; runtime period selection and revision reread; exact source-universe equality; rejection of empty series, duplicates, extra results, wrong periods, invalid codes, unsupported symbols and integer overflow. The miniature official fixtures are clearly distinguished from national-universe evidence.

The importer validates before writing and wraps canonical append, manifest append and first compatibility-view creation in one managed Lake transaction. Focused integration tests exercise an actual temporary DuckLake and verify manifest/data joins, preservation of a prior publication after manifest failure, BaseException cancellation rollback, legacy table preservation, and ambiguity failure after repeated append. Existing managed transaction code supplies post-commit snapshot receipts. SQL names use the central quoting helper and catalog lookups bind parameters.

Documentation and the actual packaged dictionary at `src/omnisus_db/data/dicionarios/ibge_pop.yaml` describe the latest-only estimate scope, publication identity, canonical/manifest tables and compatibility ambiguity accurately. The accepted limitation that `COUNT(*)` or key-only projections can avoid evaluating the compatibility population guard is explicitly documented; reading population remains guarded.

## Controller integration requirement (not a D2-agent defect)

At review time, `src/omnisus_db/__init__.py:193` still defines `import_ibge_pop` without `product`, lines 201–202 still fabricate default years, and line 208 calls the newly required-product importer without forwarding a product. Complete the already assigned wrapper/CLI integration, reject missing years/product clearly, and test the documented public invocation before declaring the full D2 feature complete.

## Limits of this review

No fresh live-network scientific source audit was performed; reviewed the archived official fixtures and the implementation's source-validation contract. The task report records a separate full-national live verification. The revision reread is an observed-change check, not a server snapshot. Raw SQL writes remain outside provenance certification, as specified.

## Final temporal-metadata delta review

**Spec: PASS. Quality: PASS. No new P1/P2 findings.** Reviewed the additions in `products.py`, `importers/pop.py`, the temporal integration cases and the expanded source documentation. No code was changed by the reviewer.

The manifest now separates population reference, territory reference, publication date, source revision and retrieval time. Population dates use explicit product definitions: July 1 for estimates and the midnight boundary from July 31 to August 1 for the two censuses. The census note preserves the original night formulation and explains the DATE representation without introducing a UTC interpretation. Territory/publication dates are explicitly NULL with an uncertainty explanation, rather than being inferred from source revision or retrieval. Explicit Polars DATE overrides keep all-null columns correctly typed. `revision` remains an alias, `source_revision` preserves the source string, and parser version v2 identifies the changed manifest contract. Publication atomicity is unchanged.

Fresh focused suite: **49 passed in 0.91s**. The three added integration cases exercise every supported product/edition against a real temporary DuckLake, asserting date values, DATE storage types, nullable unknown dates, source notes, source revision and separate collection time. Existing rollback and cancellation cases still pass.

Primary-source cross-check corroborated the scientific interpretation: the IBGE [estimate product definition](https://www.ibge.gov.br/estatisticas/sociais/populacao/9103-estimativas-de-populacao.html?edicao=28674&t=resultados) specifies July 1; the [2010 census synthesis](https://censo2010.ibge.gov.br/images/pdf/censo2010/sintese/sintese_censo2010_portugues.pdf) and [2022 official publication](https://biblioteca.ibge.gov.br/visualizacao/livros/liv102018.pdf) specify the July 31/August 1 night. Direct opening of the implementation's two main-portal links was blocked by HTTP 403 and its 2010 methodology PDF exceeded the web reader size limit, so alternate IBGE primary publications were used for this independent corroboration; this is not evidence of a broken source contract.

The earlier public-wrapper integration observation is historical: current `import_ibge_pop` now requires explicit years/product by validation and forwards product. This focused delta review does not independently certify the controller's entire API/CLI test coverage.
