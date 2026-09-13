# sim_obitos

SIM — Death certificates. This dataset uses the shared DATASUS-FTP ingestion pipeline.
See the generated [registry catalog](../datasets.md) for its cadence,
coverage, partitions and FTP directory.

```bash
omnisus-db inventory sim_obitos --refresh
omnisus-db import sim_obitos --plan inventory --years 2020-2024 --ufs RR
```

Imports append to `lake.sim_obitos`. Completion returns `ImportReport`; interrupted
transaction state is exposed through `ImportAbortedError`. See
[results and transactions](../guides/inventory.md#transactions-and-interrupted-imports).

The field definitions, foreign-key metadata and decoding rules live in
`src/omnisus_db/data/dicionarios/sim_obitos.yaml`. The parser applies the dictionary
and preserves unlisted fields; physical table columns can therefore exceed the
dictionary. Dictionary validation alone does not certify all incoming records.

## Dados preliminares

DATASUS também publica `sim_obitos` em
`/dissemin/publicos/SIM/PRELIM/DORES`, ao lado do diretório final. Um ano pode
estar disponível apenas em um dos dois; `available_releases()` mostra qual:

```python
import omnisus_db as odb

releases = odb.available_releases("sim_obitos", refresh=True)
```

Cada linha carrega `_source_release` (`final` ou `prelim`), então um ano
preliminar convive na mesma tabela com anos finais sem se confundir com eles.
Quando o DATASUS republica um ano preliminar como final:

```python
with odb.Lake.local(odb.DEFAULT_TARGET) as lake:
    moved = odb.outdated("sim_obitos", lake=lake)
odb.import_dataset("sim_obitos", scopes=moved, target=odb.DEFAULT_TARGET,
                   policy="replace", run_id="sim-final-2026")
```
