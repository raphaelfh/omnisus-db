# Municipal population (IBGE)

The separate HTTP/SIDRA importer requires both `years` and `product`:

```python
import omnisus_db as odb
odb.import_ibge_populacao(years=[2022], product="census", target="ducklake:population.ducklake")
```

It returns `list[ImportResult]`, outside the FTP inventory and `ImportReport`.

## Supported editions

| Product | Aggregate / variable | Supported edition |
|---|---|---|
| `census` | 202 / 93 | 2010; Sexo Total `2[0]`, Situação do domicílio Total `1[0]` |
| `census` | 4714 / 93 | 2022; no classifications |
| `estimate` | 6579 / 9324 | Latest period returned by the aggregate API (2026 when verified on 2026-09-10) |

The implementation fetches and validates metadata, periods and the aggregate's
municipal localities. It requires the requested edition to be the latest period
of that specific aggregate, making its locality universe applicable to that
edition. The documented locality endpoint has no period filter. **Historical
estimates, including 2024, are therefore explicitly unavailable in this release**;
they need an independently sourced, archived territorial universe for that year.
Merely passing `periodo` to the locality endpoint does not establish this contract.
The current territorial list is never presented as a verified historical list.
No fixed national municipality count is assumed. A future extension can accept
vetted edition artifacts carrying the exact codes, year, official URL and hash.

The 2007 population count and 2023 territorial publication are different products
and unsupported here. Missing estimates never silently become census figures.
Periods absent from the selected product cause an explicit unavailable error.

[Official API documentation](https://servicodados.ibge.gov.br/api/docs/agregados?versao=3)
describes the metadata, periods, localities and population endpoints. The metadata
for [202](https://servicodados.ibge.gov.br/api/v3/agregados/202/metadados),
[4714](https://servicodados.ibge.gov.br/api/v3/agregados/4714/metadados) and
[6579](https://servicodados.ibge.gov.br/api/v3/agregados/6579/metadados) establish the
variable and Total category contracts.

## Validation and provenance

Before any write, the importer validates exactly one variable and Total result,
unit Pessoas, N6 level, seven-digit codes, the exact year, unique municipalities,
nonnegative integral values and exact set equality with the verified universe.
Empty results, missing or extra municipalities and all statistical symbols
(including `...`, `-`, `X`) fail the entire load; symbols are neither dropped nor
converted to zero. Period revision is read again after collection and a change
aborts the load. This check does not constitute a server-side snapshot guarantee.

`ibge_population` is the canonical table: `codigo_ibge`, `ano`, `populacao`
(UInt64), `product`, `publication_id`. It is partitioned by `ano`. Every append
has a new publication UUID. `ibge_population_manifest` contains the same UUID,
product, source, aggregate, variable, original population-body SHA-256, URL,
collection UTC timestamp, source period/revision, expected/accepted/rejected
counts, parser version and JSON evidence. Evidence includes request URLs and body
hashes for all control documents, metadata/period documents and the exact universe
codes. HTTP body hashes describe the response content bytes exposed by HTTPX
(after any HTTP content decoding). Raw population bytes are hashed, not archived.
Data, manifest and compatibility-view creation commit in one transaction; a
failed or cancelled write preserves prior publications.

`ibge_populacao` is a compatibility view exposing the three former columns. Reading
`populacao` fails when multiple publications exist for a municipality/year; select
an explicit `publication_id` from the canonical table instead. The canonical
table preserves append history without deduplication. Existing legacy `ibge_populacao`
tables or unrecognized views cause a migration error and remain untouched.
These checks do not inventory or certify arbitrary data inserted through raw SQL.

## Separate temporal references

The manifest stores `population_reference_date` as a DATE, with
`population_reference_source_url` and a note preserving its interpretation:

| Product / edition | Stored date | Official reference formulation |
|---|---|---|
| Estimate | July 1 of the requested year | July 1 of the calendar year |
| Census 2010 | 2010-08-01 | Night between July 31 and August 1, 2010 |
| Census 2022 | 2022-08-01 | Night between July 31 and August 1, 2022 |

For census dates, August 1 is the storage convention for the midnight boundary,
not a claim that collection occurred that day. The note preserves the two-date
night formulation; no UTC timezone is assigned to this local census reference.
The estimate reference follows the [official product definition](https://www.ibge.gov.br/estatisticas/sociais/populacao/9103-estimativasde-populacao.html).
Census references follow the [2010 methodology](https://ftp.ibge.gov.br/Censos/Censo_Demografico_2010/metodologia/metodologia_censo_dem_2010.pdf)
and [2022 reference periods](https://www.ibge.gov.br/Estatisticas/Sociais/Populacao/22827-censo-demografico-2022.html?edicao=41815).

`territorial_reference_date` and `publication_date` are nullable DATE fields and
remain explicitly NULL: the selected aggregate metadata/periods do not establish
those dates for this response. `temporal_metadata_note` records this uncertainty.
`source_revision` preserves the period's `modificacao` string; `revision` remains
its compatibility alias. `collected_at` is the retrieval UTC timestamp. Neither
revision nor collection is substituted for population, territorial or publication
reference dates. The manifest parser version for this contract is
`ibge-population-v2`; earlier publication manifests remain historical records.
