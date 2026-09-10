# SINAN Chagas: national publications and researcher workflow

**Goal:** Import the national preliminary Chagas acute notification files using the existing transactional FTP pipeline, with a reproducible Marimo workflow.

**Architecture:** Keep the current state datasets unchanged. A national ScopeKey has no UF; its publication year is stored in reserved `_source_ano`, preserving all source geography and dates. Register `sinan_chagas_prelim` separately from final/historical editions. Reuse bounded acquisition, staging, publication policies and recovery.

**Evidence:** Live FTP listing on 2026-09-10: PRELIM contains CHAGBR23/24/25.dbc; FINAIS contains CHAGBR00 through CHAGBR22. The existing complete CHAGBR23 artifact has 6,253 records, 108 columns, ID_AGRAVO=B571 and NU_ANO=2023. This delivery does not support the historical/final era.

**Constraints:** No new runtime dependency. No artificial UF=BR. No overwrite of original source fields. No automatic publication on notebook opening. `skip_same` is explicit in researcher examples; existing append default remains compatible. Failed or incomplete staging must preserve prior data. No HTTP connector without a selected product.

## Tasks

- [x] Add failing tests for national filename roundtrip, inventory, scope planning, invalid state filters, source-year/agravo checks, and national replacement/rollback isolation.
- [x] Implement optional UF, national registry geography, national filename codec and reserved source-year staging. Guard against mixed national/state publication geometry. Keep existing manifest encodings for state scopes.
- [x] Add Chagas preliminary schema and source validator. Verify complete source content before publishing. Include a small deterministic synthetic DBF fixture for failure tests and a separate optional real-source integration test.
- [x] Add Marimo steps for discovery, dictionary inspection, explicit plan/run, publication recovery and aggregate analysis. Use public API and identify preliminary notifications rather than confirmed incidence.
- [x] Run focused regressions, the offline suite, formatter/linter, generated documentation checks and Marimo static execution. Run a live single-year import, replay and publication verification in a separate local lake. Record results and limitations.

## Acceptance tests

National replacement must leave another year untouched; rollback must restore rows and manifest together. A source with wrong agravo/year or a truncated DBF must fail before publication. A national request with state filters must fail before network access. State imports and their durable manifest identities must remain compatible. Opening/exporting the Marimo notebook must not acquire or publish data.

## Completion evidence

See `reports/2026-09-10-expansao-fontes.md` and both source verification JSONs. Medication scope added by the user: SIA-AM researcher workflow and verified BNAFAR/Hórus stock inspection; basic dispensing extraction remains unconfirmed and is explicitly not advertised as implemented.
