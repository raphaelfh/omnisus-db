# Reprodutibilidade

Um resultado é reprodutível quando outra pessoa consegue saber exatamente quais arquivos
entraram, com qual versão da biblioteca, e ler o lake no mesmo estado. Esta página mostra
o que registrar e onde cada informação fica.

## Antes de importar

- **Escolha o `run_id` antes de começar e nunca o reutilize.** Se uma importação for
  interrompida, um escopo ausente de `publications(run_id=...)` não foi gravado com
  aquele `run_id`, porque dados e manifesto são gravados na mesma transação; com um
  `run_id` repetido essa conclusão não vale
  ([reprocessing and maintenance](../guides/reprocessing-and-maintenance.md#inspect-an-interrupted-run)).
  Os notebooks geram um `run_id` novo e o gravam em `plano.json` antes do download
  (`omnisus_db.notebooks`, `fixar_plano`).
- **Use `policy="skip_same"`.** A política padrão é `append`, que acrescenta de novo um
  escopo já importado. `skip_same` pula o escopo só quando todas as publicações ativas
  dele têm o mesmo SHA-256 de origem e a mesma versão do parser, e falha nos outros
  casos; o arquivo é baixado de qualquer forma, para conferir essa identidade
  ([reprocessing and maintenance](../guides/reprocessing-and-maintenance.md#choose-a-replay-policy)).

```python
import omnisus_db as odb

alvo = "ducklake:./data/lake/pesquisa/dados.ducklake"
escopos = odb.available("sim_obitos", years=[2022], ufs=["RR"], refresh=True)
relatorio = odb.import_dataset(
    "sim_obitos", scopes=escopos, target=alvo, policy="skip_same", run_id="sim-rr-2022-01"
)
for desfecho in relatorio.outcomes:
    print(desfecho.scope, desfecho.status, desfecho.reason)
```

O que cada desfecho quer dizer:

- `ok`: o escopo foi publicado.
- `skipped` com o motivo *same source and parser version already published*: o mesmo
  arquivo já estava no lake e nada foi duplicado
  (`src/omnisus_db/sources/datasus_ftp/_runner.py`). Na validação de 2026-09-13, a
  segunda execução do notebook do SIM terminou assim, com 0 linhas importadas e nenhum
  snapshot novo
  ([relatório, §3](https://github.com/raphaelfh/omnisus-db/blob/main/reports/2026-09-13-guia-pesquisador-validacao.md)).
- `skipped` também aparece quando o servidor responde que o arquivo não existe (código
  550 do FTP) (`src/omnisus_db/sources/datasus_ftp/_runner.py`, docstring de
  `run_scopes`).
- `failed` com o motivo *different source/parser version exists; request replace
  explicitly*: o escopo já está no lake com outro arquivo ou outra versão do parser
  (`src/omnisus_db/lake/publication.py`). Não é um erro de rede: veja
  [Quando o DATASUS revisa](#quando-o-datasus-revisa).
- `failed` com *legacy or unmanaged rows in scope*: há linhas sem manifesto nesse escopo
  (`src/omnisus_db/lake/publication.py`), gravadas por um importador antigo ou por SQL
  direto.

Confira `relatorio.failed`, não o valor verdadeiro ou falso do relatório
([inventory](../guides/inventory.md)).

## O que o manifesto guarda

`LakeReader.publications()` devolve uma linha por publicação
(`src/omnisus_db/lake/publication.py`, `publications`):

| Campo | O que é | Fonte |
| --- | --- | --- |
| `publication_id` | identificador único (UUID) da publicação | `publication.py`, `uuid4()` |
| `dataset` | a tabela do lake, por exemplo `sim_obitos` | `publication.py` |
| `scope` | o escopo (UF, ano, mês) lido de `scope_json` | `publication.py`, `publications` |
| `release` | `final` ou `prelim`, deduzido de `source_uri` | `publication.py`, `publications` |
| `source_uri` | o endereço do arquivo de origem | `publication.py` |
| `source_sha256` | o SHA-256 do arquivo comprimido baixado | [reprocessing and maintenance](../guides/reprocessing-and-maintenance.md#choose-a-replay-policy) |
| `parser_version` | `dbc-staging-v1:` seguido do SHA-256 do dicionário | `src/omnisus_db/sources/datasus_ftp/dbf_contract.py`, `publication_parser_version` |
| `run_id` | o `run_id` passado à importação | `publication.py` |
| `published_at` | o instante UTC em que a publicação foi gravada | `publication.py`, `datetime.now(UTC)` |
| `rows` | as linhas publicadas | `publication.py` |
| `active` | `false` depois de um `replace` ou de `delete_scope` | [reprocessing and maintenance](../guides/reprocessing-and-maintenance.md#remove-a-scope) |

O manifesto também guarda `batch_id` e `managed` (`src/omnisus_db/lake/publication.py`).

```python
with odb.LakeReader(alvo) as leitor:
    for p in leitor.publications(run_id="sim-rr-2022-01"):
        print(p["dataset"], p["scope"], p["release"], p["source_uri"], p["source_sha256"], p["rows"])
```

## Fixar a leitura

O lake guarda um histórico de snapshots. `snapshots()` devolve o histórico do catálogo
inteiro, do mais antigo ao mais novo, com `snapshot_id`, `snapshot_time` e `changes`;
`LakeReader(alvo, snapshot_id=...)` prende a sessão a um snapshot, e sem esse argumento
cada consulta lê o snapshot mais recente (`src/omnisus_db/lake/session.py`,
`Session.snapshots` e `LakeReader`).

```python
with odb.LakeReader(alvo) as leitor:
    snapshot_id = leitor.snapshots()[-1]["snapshot_id"]

with odb.LakeReader(alvo, snapshot_id=snapshot_id) as leitor:
    print(leitor.connect().sql("SELECT count(*) FROM lake.sim_obitos").pl())
```

Um `snapshot_id` desconhecido gera `CatalogAttachError` (`src/omnisus_db/lake/session.py`).
Na validação de 2026-09-13, cada um dos oito notebooks criou um snapshot (1 a 8) e a
repetição do SIM não criou nenhum
([relatório, §2 e §3](https://github.com/raphaelfh/omnisus-db/blob/main/reports/2026-09-13-guia-pesquisador-validacao.md)).

Cuidado deste guia: `lake.expire_snapshots` remove histórico antigo
([reprocessing and maintenance](../guides/reprocessing-and-maintenance.md#compact-expire-history-and-clean-files));
não expire um snapshot que um trabalho seu cita.

## Quando o DATASUS revisa

Quando o DATASUS move um ano do diretório preliminar para o final, nada muda no lake
sozinho. `odb.outdated(dataset, lake=leitor)` compara o `release` de cada publicação
ativa com o que o servidor lista hoje e devolve só os escopos que mudaram; não escreve
nada, e um escopo que o servidor deixou de listar não é devolvido
(`src/omnisus_db/__init__.py`, `outdated`).

```python
with odb.LakeReader(alvo) as leitor:
    movidos = odb.outdated("sim_obitos", lake=leitor)
odb.import_dataset(
    "sim_obitos", scopes=movidos, target=alvo, policy="replace", run_id="sim-final-2026-01"
)
```

`replace` valida os dados novos, apaga as linhas do escopo e grava a nova publicação na
mesma transação; a publicação antiga fica no manifesto com `active = false`
([reprocessing and maintenance](../guides/reprocessing-and-maintenance.md#choose-a-replay-policy);
`src/omnisus_db/lake/publication.py`).

Cuidado deste guia: `outdated` só percebe a troca de diretório. Um arquivo reescrito no
mesmo diretório com outro conteúdo não aparece ali; uma nova importação com
`skip_same` desse escopo termina em `failed`, pedindo `replace`
(`src/omnisus_db/lake/publication.py`). Anote o `snapshot_id` anterior antes de
substituir: um leitor preso a ele continua lendo o lake como estava.

## IBGE

A população do IBGE tem outro modelo de publicação. `odb.import_ibge_populacao` não
aceita `run_id` nem `policy` e não aparece em `publications()`: cada edição é uma
publicação identificada pelo `publication_id` em `ibge_population_manifest`, que guarda
produto, agregado, variável, URL, SHA-256 do corpo da resposta e instante da coleta
([perfil da população](../sources/ibge_populacao.md#detalhes-tecnicos)).

```python
with odb.LakeReader(alvo) as leitor:
    print(
        leitor.connect().sql(
            "SELECT publication_id, product, ano, sha256, url, collected_at "
            "FROM lake.ibge_population_manifest"
        ).pl()
    )
```

Importar a mesma edição duas vezes cria duas publicações, e a visão `ibge_populacao`
passa a falhar (`src/omnisus_db/sources/ibge/importers/pop.py`, `import_pop_year`). O
notebook da população consulta esse manifesto e não importa uma edição que já está lá
(`notebooks/bases/ibge_populacao.py`).

## Como citar

Modelo para uma base do DATASUS:

```text
<Base> (<dataset>), arquivo <nome do arquivo> (<source_uri>), SHA-256 <source_sha256>,
acessado em <AAAA-MM-DD> pelo DATASUS. Importado com omnisus-db <versão>, lake snapshot
<snapshot_id>, execução <run_id>.
```

Onde encontrar cada valor:

- `<dataset>`, `<source_uri>`, `<source_sha256>` e `<run_id>`: na publicação, em
  `publications()`; o nome do arquivo é o fim de `source_uri`.
- `<AAAA-MM-DD>`: sugestão deste guia, a data de `published_at`.
- `<versão>`: `odb.__version__`.
- `<snapshot_id>`: o snapshot em que você leu os dados.

Nos notebooks, `proveniencia.json` junta o plano (com o `run_id` e a versão), as
publicações, o `snapshot_id` e as consultas (`omnisus_db.notebooks`,
`registrar_proveniencia`).

Para a população do IBGE, sugestão deste guia: troque o arquivo pelo `url`, o
`source_sha256` pelo `sha256`, a data pela de `collected_at` e a execução pelo
`publication_id` de `ibge_population_manifest`.
