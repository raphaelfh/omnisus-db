# API na prática com marimo

## Trilha organizada de estudo

| Ordem | Notebook | Finalidade | Dados |
| --- | --- | --- | --- |
| 1 | [Panorama DATASUS](panorama_datasus.py) | Conhecer as **18 categorias** do portal, suas tabelas e colunas | Amostras reais de todas as categorias |
| 2 | [Inventário e seleção](inventario_dados_reais.py) | Filtrar arquivos e importar um recorte das bases suportadas | Arquivos completos escolhidos no FTP |
| 3 | [Análise SIM](api_dados_reais.py) | Aprender filtros, qualidade, agregações e consultas | SIM/RR 2022–2023 completos |
| 4 | [Cenários da API](api_cenarios.py) | Estudar transações, rollback e comportamento da biblioteca | Cenários sintéticos identificados e importações reais opcionais |
| 5 | [Performance Python/Rust](performance_dbf.py) | Comparar tempo, memória e disco por corpus e etapa | Benchmarks locais versionados, com sete rodadas por backend |

Os nomes existentes foram preservados para manter os comandos e referências.
Os auxiliares de aquisição, leitura e relatório ficam juntos em
[`_acervo/`](_acervo/README.md). Downloads e HTMLs ficam em `data/lake/`,
ignorados pelo Git; relatórios de metadados ficam em `reports/`.

## Panorama das 18 categorias do portal

```bash
uv sync --locked --extra notebooks
uv run --locked --extra notebooks marimo edit notebooks/panorama_datasus.py
```

Ao abrir, o notebook reutiliza a última coleta local e permite explorar categoria,
tabela, registros, esquema, indicadores da amostra, arquivos originais e documentos.
Em um checkout novo, clique em **Baixar amostras reais**. O botão prepara uma nova
coleta sem sobrescrever os dados anteriores. No painel de preparação, escolha
categorias e máximo de linhas por tabela (200 por padrão).

As categorias são DATASUS/TABWIN, IBGE, Base Territorial, CIH, CIHA, CNES,
e-SUS Notifica/DCC, PCE, Painel de Oncologia, RESP, SIASUS, SIHSUS, SIM, SINAN,
SINASC, SISCOLO, SISMAMA e SISPRENATAL. **Uma amostra por categoria não cobre todos
os subtipos, agravos, anos ou UFs**; os subtipos descritos no portal aparecem
separadamente no relatório. Aplicativos são inspecionados como pacotes, sem execução.

Cada arquivo escolhido é baixado inteiro (até 64 MiB; até 256 MiB por coleta).
As amostras têm as primeiras 200 linhas ativas de **cada tabela** dos DBC/DBF/ZIP;
IBGE e Base Territorial contêm várias tabelas. Os valores ficam em texto bruto
para preservar códigos e zeros à esquerda. O esquema inclui tipo físico DBF,
largura, decimais e indicadores calculados apenas na amostra. Campos não recebem
interpretações clínicas inferidas. Arquivo vazio e erro de leitura são registrados;
até quatro candidatos podem ser tentados para obter registros reais.

```bash
# Abrir como aplicativo
uv run --locked --extra notebooks marimo run notebooks/panorama_datasus.py

# Exportar o acervo local já preparado (sem novos downloads)
uv run --locked --extra notebooks marimo export html notebooks/panorama_datasus.py \
  -o /tmp/panorama-datasus.html

# Executar uma nova coleta real das 18 categorias e gerar o HTML
uv run --locked --extra notebooks marimo export html notebooks/panorama_datasus.py \
  -o /tmp/panorama-datasus.html -- --preparar true
```

`--preparar true` é para execução automática, não para uma sessão interativa.
Falhas permanecem visíveis no manifesto e fazem a exportação automática terminar
com erro. Aguarde a conclusão: interromper a célula pode não encerrar imediatamente
a thread de aquisição.

Em `data/lake/panorama-datasus/<execucao>/` ficam:

- Por categoria: consulta ao portal, inventário FTP, original, SHA-256,
  tentativas, amostras CSV/Parquet e descritores de todas as colunas.
- `manifesto.json`: proveniência e estado final de todas as categorias.
- `portal_transferencia.js`: cópia da definição do seletor e subtipos.
- `mapa/`: relatório Markdown e mapas CSV/JSON de fontes, tabelas, colunas e ZIPs.

O ponteiro `latest.json` só é publicado quando a tentativa termina, mesmo que
alguma categoria tenha falhado; o notebook apresenta esses estados explicitamente.

Validação em 10/09/2026: **18 categorias**, **65 tabelas**, **1.326 ocorrências de
colunas**, **9.784 linhas amostradas** e **189 membros ZIP**. São 17 categorias
tabulares e um pacote de aplicativo. A seleção vazia de SISMAMA/RR foi substituída
por um arquivo de SP, com as tentativas preservadas.

Veja o [relatório completo e mapa de campos](../reports/2026-09-10-mapa-datasus/README.md).
Esses números descrevem esta coleta, não uma garantia de cobertura futura.

```bash
uv run --locked --extra notebooks marimo check --strict notebooks/panorama_datasus.py
uv run --locked --extra dev pytest tests/unit/notebooks/test_acervo.py -q
uv run --locked --extra dev ruff check notebooks/_acervo notebooks/panorama_datasus.py
```

## Análise da API com dados reais já preparados

O [notebook de análise real](api_dados_reais.py) usa os arquivos completos
`DORR2022.dbc` e `DORR2023.dbc`, obtidos do FTP DATASUS pela API da biblioteca.
Na execução de 10/09/2026 foram importados **3.246 + 3.311 = 6.557 registros**.
O lake já preparado neste workspace é reutilizado ao abrir, sem novo download
automático ou dados sintéticos nos cenários analíticos.

```bash
uv run --locked --extra notebooks marimo edit notebooks/api_dados_reais.py
```

O botão **Baixar nova cópia** consulta o inventário e cria um lake separado,
preservando as tentativas anteriores. A referência da última extração concluída
fica em `data/lake/marimo-real/latest.json`; cada diretório de execução contém
`manifest.json`, `import_report.json`, catálogo e Parquets. Os dados locais são
ignorados pelo Git. Em outro checkout, use o botão para preparar sua própria cópia.

O notebook oferece esquema real, reconciliação de contagens e snapshots, qualidade
de datas, filtros por ano/tipo/residência, agregações por mês/sexo/município/CID-10
e download de agregados CSV/Parquet. O exemplo transacional usa uma agregação real
em um lake temporário; somente o erro usado para demonstrar rollback é induzido.

```bash
uv run --locked --extra notebooks marimo check --strict notebooks/api_dados_reais.py
uv run --locked --extra notebooks marimo export html notebooks/api_dados_reais.py -o /tmp/omnisus-real.html
```

A exportação requer a cópia local já preparada para incluir as análises. Os
números representam registros dos arquivos importados, não taxas ou certificação
de cobertura populacional. Datas e códigos são tratados explicitamente nas células.
Detalhes em [validação com dados reais](../reports/2026-09-10-notebook-dados-reais.md).

## Inventário e download com dados reais

O notebook [`inventario_dados_reais.py`](inventario_dados_reais.py) consulta o FTP
DATASUS atualizado, mostra o inventário com nome, tamanho, ano e UF, permite
selecionar até três arquivos e importa a seleção em um DuckLake novo. Depois,
reabre o lake, confere a contagem, mostra 50 registros e o esquema, e exporta
**todos** os registros em CSV e Parquet. Inclui as 11 bases do registro da biblioteca.

```bash
uv sync --locked --extra notebooks
uv run --locked --extra notebooks marimo edit notebooks/inventario_dados_reais.py
```

Clique em **Consultar inventário**, escolha UF/ano/arquivos e clique em **Baixar**.
O padrão é SIM, RR, 2023; a seleção usa nomes realmente encontrados no servidor.
O catálogo inicial é local, mas a consulta sempre usa `odb.browse(..., refresh=True)`.
`BR` representa o arquivo nacional quando presente; o download demonstrativo
seleciona apenas UFs. O limite é de 25 MiB comprimidos por seleção.

Cada tentativa fica em `data/lake/inventario-real/<data-uuid>/`, contendo
`inventario.csv`, `selecao.csv`, `execucao.json`, catálogo DuckLake e exportações.
Os dados não são versionados. Aguarde a importação terminar antes de repetir;
interromper a célula pode não cancelar a thread de download.

Para executar o exemplo real inteiro e gerar um HTML com resultados:

```bash
uv run --locked --extra notebooks marimo export html notebooks/inventario_dados_reais.py \
  -o /tmp/inventario-dados-reais.html -- --executar true
```

Esse comando **acessa o DATASUS e baixa dados**. O HTML é estático; filtros e
botões de download interativos exigem `marimo edit` ou `marimo run`. Os arquivos
CSV/Parquet completos também ficam disponíveis na pasta da execução.
Sem `--executar true`, a exportação valida a abertura e aguarda os botões,
sem consultar o DATASUS. Não use essa opção ao servir uma sessão interativa:
ela automatiza as operações que normalmente dependem de clique.

Verificações locais:

```bash
uv run --locked --extra notebooks marimo check notebooks/inventario_dados_reais.py
uv run --locked --extra dev ruff check notebooks/inventario_dados_reais.py
```

Validação real em 10/09/2026: 812 arquivos SIM encontrados (1996–2024, 27 UFs
e BR). `DORR2023.dbc` tinha 288.798 bytes e produziu **3.311 registros e 89
colunas**, sem falhas. As contagens no DuckLake, CSV e Parquet foram conferidas.
Esses números descrevem essa consulta; execuções futuras podem mudar.

## Outros cenários da API

Execute pela raiz do checkout atual, com Python 3.12 ou 3.13:

```bash
uv sync --locked --extra notebooks
uv run --locked --extra notebooks marimo edit notebooks/api_cenarios.py
```

Para usar como aplicativo, com o código recolhido:

```bash
uv run --locked --extra notebooks marimo run notebooks/api_cenarios.py
```

O extra `notebooks` contém marimo 0.23.16 no lock. As dependências da biblioteca
continuam vindo do projeto; não instale a versão histórica publicada para executar
estes exemplos. A integração segue a [documentação oficial de marimo e uv](https://docs.marimo.io/guides/package_management/using_uv/).

O notebook explica a avaliação documental e cobre:

1. Planejamento anual e mensal com `scopes_for`.
2. Ingestão sintética, particionamento, evolução de esquema, SQL e Polars.
3. Commit, snapshot pendente, rollback e histórico do catálogo.
4. Duplicação por append e exportação do exemplo em Parquet.
5. Leitura de `ImportReport` e `ImportAbortedError` simulados.
6. Inventário e importação real opcionais de SIM, SINASC, SIH, CNES e SIA-BI.
7. Receitas de consulta, enriquecimento CNES e população IBGE com produto explícito.

As demonstrações sintéticas usam um diretório temporário e fecham as conexões
antes de removê-lo. Não acessam DATASUS ou IBGE, mas DuckDB pode baixar a extensão
DuckLake no primeiro uso. As importações reais só começam por botão; cada tentativa
usa um lake próprio em `data/lake/marimo-runs/`, preservado para inspeção. Os botões
também evitam repetir downloads ao alterar filtros. Os wrappers que usam
`asyncio.run` são chamados com `await asyncio.to_thread` dentro do notebook.
Interromper a célula não garante cancelar a thread; o destino aparece antes do
download para permitir inspecionar a tentativa. Aguarde o importador terminar
antes de tentar novamente. Selecione vários meses para exercitar até três escopos
de um dataset mensal; datasets anuais produzem um escopo por ano e UF escolhidos.

Para verificar a estrutura e executar os cenários automáticos:

```bash
uv run --locked --extra notebooks marimo check notebooks/api_cenarios.py
uv run --locked --extra notebooks marimo export html notebooks/api_cenarios.py -o /tmp/omnisus-api.html
```

A exportação executa as células locais e suas assertions; os botões de rede ficam
desligados. O HTML é uma visualização estática: use `marimo edit` ou `marimo run`
para interagir. As receitas CNES master/IBGE são trechos documentais e não fazem
parte da execução automática. Dados externos e exemplos cloud exigem validação
própria; as limitações da implementação atual estão explicadas no notebook.

A avaliação anterior está em
[relatório de documentação](../reports/2026-09-10-avaliacao-documentacao.md).


## Performance do leitor DBF: Python e Rust

[`performance_dbf.py`](performance_dbf.py) apresenta o relatório
[`rust-dbf-performance.json`](../reports/rust-dbf-performance.json) com filtros
por corpus, etapa e métrica. Os gráficos mostram medianas e rodadas individuais;
as tabelas permitem baixar os valores. A análise separa DBF → Arrow,
DBC → Parquet, DBF ampliado → Parquet e publicação em lake novo.

```bash
uv run --no-sync marimo edit notebooks/performance_dbf.py
uv run --no-sync marimo run notebooks/performance_dbf.py
uv run --no-sync marimo export html notebooks/performance_dbf.py -o /tmp/performance-dbf.html
```

A leitura do relatório não precisa da extensão Rust instalada, não acessa a rede
e não executa novos benchmarks. O notebook explica como repetir o teste com o
script existente, gravando um relatório separado. O HTML é uma fotografia dos
resultados: use `edit` ou `run` para os filtros reativos. Os cálculos e gráficos
ficam em `_performance_dbf.py`, sem dependências adicionais de visualização.

Validação: seis testes verificam medianas sem aquecimento, separação das etapas,
rejeição de evidência incompleta/divergente e gráficos com disco igual a zero.

```bash
uv run --no-sync pytest tests/unit/notebooks/test_performance_dbf.py -q
uv run --no-sync marimo check --strict notebooks/performance_dbf.py
```
