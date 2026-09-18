# Comece aqui

## O que é

O omnisus-db importa bases abertas do DATASUS e do IBGE para um lake local, uma base de
dados em arquivos no seu computador. Cada importação fica registrada num manifesto, com
o arquivo de origem, o SHA-256 dele e a execução que o publicou; é isso que permite
dizer de onde veio cada linha.

## Preparar

A partir de uma cópia do repositório:

```bash
git clone https://github.com/raphaelfh/omnisus-db.git
cd omnisus-db
uv sync --locked --extra notebooks
uv run --locked --extra notebooks marimo edit notebooks/bases/sim_obitos.py
```

Sem clonar, o notebook instala `omnisus-db` do GitHub (cabeçalho PEP 723). No
[molab](https://molab.marimo.io/github/raphaelfh/omnisus-db/blob/main/notebooks/bases/sim_obitos.py)
use a prévia em servidor, não WebAssembly. Localmente, isolado:

```bash
uvx marimo edit --sandbox notebooks/bases/sim_obitos.py
```

`--sandbox` e o molab instalam a `main` publicada no GitHub, não o checkout
local. Para desenvolver a biblioteca, use `uv sync --locked --extra notebooks`.

## Qual base responde minha pergunta?

| Pergunta | Base | Perfil | Notebook |
| --- | --- | --- | --- |
| Quantas pessoas morreram, de quê, onde moravam? | SIM · óbitos | [perfil](../sources/sim_obitos.md) | [sim_obitos.py](https://github.com/raphaelfh/omnisus-db/blob/main/notebooks/bases/sim_obitos.py) |
| Quantos nasceram, com que peso, com quantas consultas de pré-natal? | SINASC · nascidos vivos | [perfil](../sources/sinasc_nascidos_vivos.md) | [sinasc_nascidos_vivos.py](https://github.com/raphaelfh/omnisus-db/blob/main/notebooks/bases/sinasc_nascidos_vivos.py) |
| Quantas internações hospitalares foram registradas, por qual diagnóstico? | SIH · AIH reduzida | [perfil](../sources/sih_aih_reduzida.md) | [sih_aih_reduzida.py](https://github.com/raphaelfh/omnisus-db/blob/main/notebooks/bases/sih_aih_reduzida.py) |
| Que produção ambulatorial foi registrada (sete tabelas: BPA-I, APAC, RAAS)? | SIA · produção ambulatorial | [perfil](../sources/sia.md) | [sia.py](https://github.com/raphaelfh/omnisus-db/blob/main/notebooks/bases/sia.py) |
| Quais estabelecimentos de saúde existem, onde, de que tipo? | CNES · estabelecimentos | [perfil](../sources/cnes_estabelecimentos.md) | [cnes_estabelecimentos.py](https://github.com/raphaelfh/omnisus-db/blob/main/notebooks/bases/cnes_estabelecimentos.py) |
| Qual população usar como denominador de uma taxa? | IBGE · população | [perfil](../sources/ibge_populacao.md) | [ibge_populacao.py](https://github.com/raphaelfh/omnisus-db/blob/main/notebooks/bases/ibge_populacao.py) |
| Quantas notificações de doença de Chagas aguda? | SINAN · Chagas aguda | [perfil](../sources/sinan_chagas.md) | [sinan.py](https://github.com/raphaelfh/omnisus-db/blob/main/notebooks/bases/sinan.py) |
| Quantas notificações de hanseníase, e como terminou o tratamento? | SINAN · hanseníase | [perfil](../sources/sinan_hanseniase.md) | [sinan.py](https://github.com/raphaelfh/omnisus-db/blob/main/notebooks/bases/sinan.py) |
| Que medicamentos o SUS registrou em APAC, e que estoque aparece? | Medicamentos | [perfil](../sources/medicamentos.md) | [medicamentos.py](https://github.com/raphaelfh/omnisus-db/blob/main/notebooks/bases/medicamentos.py) |

Leia o perfil antes de contar: ele diz o que uma linha representa, de onde vêm as datas
e os municípios e o que ainda está em aberto.

## As seis etapas

Todo notebook de `notebooks/bases/` segue as mesmas etapas, e cada etapa com rede ou
escrita começa por um botão.

**1 · O que a base registra.** Mostra os campos da base a partir do dicionário da
biblioteca, sem rede.

**2 · Descobrir.** Pergunta ao FTP do DATASUS o que existe agora:
`odb.available_releases(dataset, ufs=[...], refresh=True)` diz se cada ano está no
diretório final ou no preliminar, e `odb.available(...)` devolve os escopos que podem
ser importados. A população do IBGE não tem inventário: o notebook mostra as edições que
a biblioteca aceita.

**3 · Planejar e importar.** Fixar o plano grava `plano.json` com um `run_id` antes de
qualquer download. A importação usa esse `run_id` e
`odb.import_dataset(dataset, scopes=..., target=..., policy="skip_same", run_id=...)`,
para que repetir a etapa não duplique linhas. A população usa
`odb.import_ibge_populacao`. Nos notebooks com download por FTP, esta etapa limita o
arquivo comprimido a 25 MiB (`LIMITE_BYTES` em `omnisus_db.notebooks`); um arquivo
maior (por exemplo outra UF) termina como `failed`, e pode ser importado subindo esse
limite ou com a chamada direta `odb.import_dataset` no perfil da base ("Como usar"). A
população do IBGE não baixa pelo FTP, então esse limite não se aplica a ela.

**4 · Conferir.** Lê o manifesto com `LakeReader.publications(run_id=...)`, compara as
linhas no lake com as linhas publicadas e anota o `snapshot_id` mais recente.
`odb.outdated(dataset, lake=...)` é usado quando a base tem diretório preliminar (SIM,
SINASC, SINAN); as demais bases do DATASUS são publicadas num único diretório, e o
notebook não chama `outdated` para elas.

**5 · Analisar.** Roda as consultas SQL num leitor preso a esse snapshot,
`LakeReader(alvo, snapshot_id=...)`, para que o resultado não mude se outra importação
acontecer depois.

**6 · Guardar.** Grava os resultados em CSV e um `proveniencia.json` com o plano, as
publicações, o `snapshot_id`, as consultas e a versão da biblioteca. Veja
[Reprodutibilidade](reprodutibilidade.md).

## O lake de pesquisa

Os notebooks gravam no mesmo lake, `data/lake/pesquisa/dados.ducklake`, e cada execução
ganha uma pasta própria em `data/lake/pesquisa/execucoes/<run_id>/`, com `plano.json`,
`resultado.json`, os CSVs e `proveniencia.json`
(`omnisus_db.notebooks`, `raiz_dados` e `fixar_plano`). A variável de ambiente
`OMNISUS_NOTEBOOK_DATA` troca essa pasta.

O lake é um só porque uma taxa precisa de duas bases: óbitos por 100 mil habitantes
lê `sim_obitos` e `ibge_populacao` na mesma consulta
(`notebooks/bases/ibge_populacao.py`, consulta `obitos_por_100_mil`). Veja
[Indicadores](indicadores.md).

## Cuidados gerais

- **Arquivos preliminares mudam.** O DATASUS publica anos preliminares que depois são
  revistos; para o SINAN Chagas, veja a nota citada no
  [perfil](../sources/sinan_chagas.md#armadilhas). Guarde o SHA-256 do arquivo e o
  `snapshot_id` e siga [Reprodutibilidade](reprodutibilidade.md).
- **Um registro não é uma pessoa.** Uma linha do SIM é uma declaração de óbito; uma
  linha do SINAN é uma notificação, não um caso confirmado nem um caso novo. Leia as
  Armadilhas de cada perfil, por exemplo as do
  [SINAN Chagas](../sources/sinan_chagas.md#armadilhas) e as do
  [SINAN hanseníase](../sources/sinan_hanseniase.md#armadilhas).
- **Um escritor por lake de cada vez.** Uma importação local segura uma trava de
  escrita, e uma segunda importação no mesmo lake falha com `WriterBusyError`; um
  `LakeReader` não pega a trava e pode ler durante uma importação
  ([reprocessing and maintenance](../guides/reprocessing-and-maintenance.md#coordinate-writers-and-bound-downloads);
  [getting started](../guides/getting-started.md#4-query)).
- **Abrir um notebook não baixa nada.** Um teste abre cada notebook e falha se houver
  conexão de rede ou escrita no lake de pesquisa
  (`tests/unit/notebooks/test_notebooks_abrem_offline.py`).
