# D2 implementation report

## Contract delivered

`async import_pop_year(*, year: int, lake: Lake, product: str) -> ImportResult`
(public wrapper and CLI owned by controller). Explicit product registry:
`estimate` = 6579/9324; `census` = 202/93 for 2010 with `2[0]|1[0]`,
4714/93 for 2022 without classifications. No product substitution.

Canonical append-only table `ibge_population`: codigo_ibge String, ano UInt16,
populacao UInt64, product String, publication_id String. UUID publication identity
is new for each call. `ibge_population_manifest` holds source, aggregate, variable,
period, revision, UTC collection, original HTTP response-content SHA-256, URL,
expected/accepted/rejected counts, parser version, and JSON control evidence.
Evidence records metadata and periods documents, exact universe codes, URLs,
content hashes and collection times. Manifest and population are published through
`Lake.ingest` in a single `Lake.transaction`; rollback/cancellation preserve old
rows. Returned ImportResult gets the existing post-commit receipt behavior.
No dependency on D5 scope machinery.

SQL dynamic names use controller's `lake.sql.qualified`; metadata queries bind
values. `ibge_pop` is a compatibility view: it preserves the former three columns
for unambiguous municipality/year values, raises an explicit error when reading
population after multiple publications, and never deduplicates canonical history.
An existing legacy table or unrecognized view fails with migration guidance.

## Evidence-driven scope restriction

Official API documentation:
https://servicodados.ibge.gov.br/api/docs/agregados?versao=3

The API documents locality universe by aggregate/level, with no edition parameter.
Live responses observed 5565 codes for aggregate 202, 5570 for 4714, and 5571 for
6579. The historical 6579/2001 population response contains 5571 entries including
`...`; using current locality list would falsely certify a historical universe.
Passing undocumented `periodo=2001` did not establish historical coverage.

Therefore coverage is only certified against the latest period of each selected
aggregate, determined at runtime from official periods. This admits census 2010
and 2022 and latest estimates (2026 at verification), while older estimates,
including 2024, explicitly fail with a missing edition-universe message. The
controller approved this conservative first scope after being notified. No fixed
national count appears in production. Historical estimates need independently
sourced archived edition code lists with year/URL/hash, left as a documented
extension path. No arbitrary expected-count bypass or unverified universe is
exposed publicly. Count 2007 and territorial publication 2023 are unsupported.

Official full metadata and periods, plus two-municipality population response
fixtures, are archived under tests/unit/sources/ibge/fixtures. Fixture README
states complete request parameters and distinguishes the controlled mini-universe
from national coverage.

## Validation

Initial RED saved to task-1-red.log: parser 19 failures (including explicit empty
payload DID NOT RAISE), fetch 15 failures on absent product-aware API, integration
5 failures on absent product-aware import API. Existing permissive tests were
replaced because dropping symbols/accepting empties described the scientific bug.

Final deterministic GREEN saved to task-1-green.log:
`PYTHONPATH=src .venv/bin/pytest tests/unit/sources/ibge tests/integration/test_ibge_pop_e2e.py -q`
46 passed. Covers official three-product fixtures; empty/malformed data; metadata
variable/unit/level/Total constraints; missing year; unavailable products;
duplicate/invalid codes, missing coverage, extra results, wrong categories/year;
unsupported symbols, negatives, decimals, overflow; empty/duplicate universe;
missing and changing revision; HTTP failures; real temporary DuckLake population
and manifest join; manifest-write rollback preserving a previous publication;
legacy table preservation; append ambiguity; cancellation rollback.

`ruff check` on changed source/tests: passed.
`mypy src/omnisus_db/sources/ibge --follow-imports=silent`: no issues in 6 files.
Used existing shared environment; no install/sync, commit or push.

## Limits

Revision read before/after detects observed changes, not an IBGE server snapshot.
HTTPX content hashes are decoded HTTP entity content bytes; raw population body
is hashed rather than archived. Reading codigo_ibge/ano or COUNT from compatibility
view need not evaluate its population ambiguity guard; selecting population does.
Arbitrary raw SQL writes are outside provenance certification. No historical
estimates beyond the latest aggregate edition are claimed supported.

## Live full-source check

A read-only run of the implemented fetch + strict parser against all national
municipality responses passed for census 2010 (5565 rows, sum 190755799), census
2022 (5570 rows, sum 203080756), and estimate 2026 (5571 rows, sum 214211951).
Collected 2026-09-10 UTC; per-response hashes, URLs, period revisions and counts
are recorded in task-1-live-verification.json. These are source-observed totals,
not hardcoded expectations and not a guarantee of independent statistical truth.

## Temporal metadata follow-up

Added product-registry population_reference_date (Python date), official source
URL and explanatory note; manifest carries them as DATE/String fields. Estimates
use July 1 according to the official product definition:
https://www.ibge.gov.br/estatisticas/sociais/populacao/9103-estimativasde-populacao.html
Census 2010 is documented as the night from July 31 to August 1 in the methodology:
https://ftp.ibge.gov.br/Censos/Censo_Demografico_2010/metodologia/metodologia_censo_dem_2010.pdf
Census 2022 has the same night formulation in its reference periods:
https://www.ibge.gov.br/Estatisticas/Sociais/Populacao/22827-censo-demografico-2022.html?edicao=41815

Stored census DATE uses August 1 as normalization of the midnight boundary;
the accompanying note explicitly preserves the original July31/August1 night,
with no UTC/timezone inference. This is a documented storage convention.

territorial_reference_date and publication_date are explicitly typed nullable
DATE columns, currently NULL with a temporal_metadata_note explaining that
selected API documents do not establish them. source_revision retains the exact
period.modificacao string; revision is retained as compatibility alias. Neither
that revision nor collection UTC drives population reference dates. Updated
parser_version to ibge-population-v2; prior manifests are not rewritten.

Temporal RED: 3 product-parameterized integration tests failed on missing temporal
columns before implementation (task-1-temporal-red.log). GREEN: all 49 targeted
IBGE tests passed (task-1-temporal-green.log). New tests verify actual stored dates
for 2010/2022 census versus estimate, official source links, distinct revision and
period, unknown dates/notes and DATE schemas even for NULL fields. Ruff passed.
