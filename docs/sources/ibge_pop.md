# ibge_pop

This is a separate HTTP/SIDRA importer, outside the DATASUS-FTP registry.
`import_ibge_pop(years=...)` returns `list[ImportResult]`; it does not use FTP
inventory or return `ImportReport`.

## Current source-selection limitation

The implementation fixes aggregate `793` and variable `93` in
`src/omnisus_db/sources/ibge/fetch.py`, substitutes the requested year in the URL,
and does not validate whether that aggregate is the intended population product
or covers the requested year. Correct annual population-series selection remains
pending in delivery D2. A successful request or an empty result is not evidence
that a requested annual population estimate was obtained.

The intended table is `lake.ibge_pop`, partitioned by `ano`, with columns
`codigo_ibge`, `ano` and `populacao`. The dictionary at
`src/omnisus_db/data/dicionarios/ibge_pop.yaml` describes this output contract;
it does not resolve or certify the source product. D1's transactional fixes do
not correct source selection.
