# Notebooks

Notebooks [marimo](https://marimo.io) em três pastas. Abrir um notebook não baixa
nem grava nada: toda etapa com rede ou escrita começa por um botão.

```bash
uv sync --locked --extra notebooks
uv run --locked --extra notebooks marimo edit notebooks/bases/sim_obitos.py
```

Cada notebook declara as dependências no cabeçalho [PEP 723](https://peps.python.org/pep-0723/).
`omnisus-db` ainda não está no PyPI: o sandbox e o [molab](https://docs.marimo.io/guides/molab/)
instalam a biblioteca a partir do GitHub.

```bash
uvx marimo edit --sandbox notebooks/bases/sim_obitos.py
```

No molab, espelhe o arquivo no GitHub (servidor efêmero, não a prévia WebAssembly):
[sim_obitos.py no molab](https://molab.marimo.io/github/raphaelfh/omnisus-db/blob/main/notebooks/bases/sim_obitos.py).
O repositório inteiro precisa estar disponível — `_comum.py` e `_acervo/` não vão no
pacote instalado. DuckDB, FTP e o lake local não rodam em `/wasm`.

No checkout, continue com `uv run --locked --extra notebooks`: isso usa o código
local. `--sandbox` baixa `omnisus-db` de `main` no GitHub.

## `bases/` — uma base por notebook, para pesquisa

Comece pelo [guia do pesquisador](https://raphaelfh.github.io/omnisus-db/pesquisa/).
Todos seguem as mesmas seis etapas (o que a base registra, descobrir, planejar e
importar, conferir, analisar, guardar) e gravam no lake `data/lake/pesquisa/`.

| Notebook | Base | Recorte inicial |
| --- | --- | --- |
| [sim_obitos.py](bases/sim_obitos.py) | SIM · óbitos | RR, 2022 |
| [sinasc_nascidos_vivos.py](bases/sinasc_nascidos_vivos.py) | SINASC · nascidos vivos | RR, 2022 |
| [sih_aih_reduzida.py](bases/sih_aih_reduzida.py) | SIH · AIH reduzida | RR, jan/2024 |
| [sia.py](bases/sia.py) | SIA · sete tabelas | RR, jan/2024 |
| [cnes_estabelecimentos.py](bases/cnes_estabelecimentos.py) | CNES · estabelecimentos | RR, jan/2024 |
| [ibge_populacao.py](bases/ibge_populacao.py) | IBGE · população | censo 2022 |
| [sinan.py](bases/sinan.py) | SINAN · Chagas aguda e hanseníase | nacional, 2022 |
| [medicamentos.py](bases/medicamentos.py) | SIA-AM, estoque Hórus | RR, jan/2024 |

Para executar as etapas sem interface (validação):

```bash
uv run --locked --extra notebooks marimo export html notebooks/bases/sim_obitos.py \
  -o /tmp/sim_obitos.html -- --executar true
```

`OMNISUS_NOTEBOOK_DATA` troca a pasta do lake de pesquisa.

## `explorar/` — conhecer o que o DATASUS publica

| Notebook | Para quê |
| --- | --- |
| [panorama_datasus.py](explorar/panorama_datasus.py) | Amostras reais das 18 categorias do portal |
| [inventario_dados_reais.py](explorar/inventario_dados_reais.py) | Inventário do FTP, seleção e importação de arquivos |

## `desenvolvimento/` — comportamento da biblioteca

| Notebook | Para quê |
| --- | --- |
| [api_cenarios.py](desenvolvimento/api_cenarios.py) | Transações, rollback e contratos da API |
| [metadados_cli.py](desenvolvimento/metadados_cli.py) | Metadados por coluna pelo terminal |
| [performance_dbf.py](desenvolvimento/performance_dbf.py) | Medições do leitor DBF Python × Rust |

Arquivos com `_` no início (`_comum.py`, `_acervo/`, `_performance_dbf.py`) são
módulos auxiliares, não notebooks.
