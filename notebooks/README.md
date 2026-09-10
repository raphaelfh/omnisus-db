# API na prática com marimo

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
7. Receitas de consulta, enriquecimento CNES e diagnóstico IBGE.

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
