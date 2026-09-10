# Avaliação de atualização da documentação

Data: 2026-09-10. Escopo: os 19 arquivos Markdown de `docs/`, suas fontes de geração e exemplos, comparados ao código da entrega D1. Base da avaliação: `e05d25f`; código funcional D1: `30ce324`.

## Resultado

A documentação estava **parcialmente atualizada**. O guia de inventário já descrevia parte do novo contrato transacional, mas a página inicial, os exemplos de conexão, a referência da API, a arquitetura e os planos históricos continham divergências. Essas diferenças foram corrigidas antes do merge local solicitado.

| Área | Divergência encontrada | Atualização |
|---|---|---|
| Instalação | A tag local `v0.1.0` contém API anterior a `ImportReport`, `available` e `import_dataset` | Instalação pelo checkout atual e distinção explícita da tag histórica; Python mínimo 3.12 |
| Conexão | Exemplos usavam `Lake.local('./omnisus.ducklake')`, rejeitado pelo parser | `DEFAULT_TARGET` ou URI com `ducklake:`; fechamento por context manager |
| API | Exceção de aborto e erros transacionais ausentes; retornos tratados genericamente | Referência das novas exceções, recibo, snapshot pendente, medidas de bytes e retornos por família |
| Arquitetura | IBGE descrito como linha do registry FTP; streaming sugeria memória constante | Registry restrito a FTP, fluxo real de memória por escopo, lotes e fronteiras de commit |
| Resultados/CLI | Alegação de saída não zero somente por escopo failed; retornos list/int omitidos | Aborto e erros de argumentos diferenciados; ordem/multiplicidade, failed/skipped/unresolved e limites de retry |
| Cloud/manutenção | Docstring sugeria multi-writer; vacuum descrito como expiração de snapshots | Um escritor também em Postgres; limitações do parser e dos wrappers de manutenção descritas |
| Fontes | Páginas limitadas a placeholders | Guias de uso do catálogo, CNES master atômico e limites de retornos/visão; IBGE identificado como correção de origem pendente |
| Catálogo gerado | Texto podia ser lido como prova de validação atual do servidor | Geração preservada; workflow configurado distinguido de execução remota verificada |
| Planos/ADRs | Propostas antigas pareciam instruções atuais, incluindo Python >=3.13 | Notas históricas e precedência do contrato atual; benchmarks históricos não apresentados como medição desta versão |
| Spec D1 | Texto ainda não detalhava as decisões da revisão final | Nesting rejeitado antes dos produtores, primeira interrupção preservada e produtores filhos aguardados |

A revisão independente por subagente cobriu página inicial, API, arquitetura e os dois ADRs. O controlador revisou os guias, as fontes, o catálogo gerado, os planos e a especificação, consolidando as correções.

## Validação antes do merge

- `mkdocs build --strict`: aprovado; o banner do Material sobre MkDocs 2.0 permanece informativo, pois a versão utilizada é MkDocs 1.x.
- `python scripts/gen_datasets_doc.py --check`: aprovado.
- Ruff lint e formatação dos arquivos Python alterados: aprovados.
- `git diff --check`: aprovado.
- 16 exemplos de comandos CLI tiveram argumentos analisados pelo parser Click/Typer, sem executar rede.
- 14 blocos Python tiveram sintaxe verificada; 21 links relativos na documentação publicada resolveram para arquivos locais.
- Três exemplos de documentação foram executados em um DuckLake temporário: consulta inicial, consulta de migração e ingestão com recibo/snapshot.
- Comparação de AST, ignorando docstrings, confirmou lógica inalterada nos três módulos de `src/` editados. O script do catálogo mudou somente textos de apresentação.

Merge local concluído por fast-forward em `main`, de `fcb9d5b` para `eb4cf66`, sem conflitos. Após o merge, Python 3.13.12 passou em **429 testes**, com **47 casos excluídos** pela seleção `not e2e and not perf`, **91,97% de cobertura** e duração de 39,50 s. MkDocs strict e a verificação do catálogo gerado também passaram em `main`. Todos os links Markdown locais dos 19 documentos resolveram no checkout principal. Os arquivos locais não versionados anteriores foram preservados. Não se executaram fontes de dados ao vivo nem se inferiu resultado de CI remota durante esta avaliação.

Logs finais em `reports/evidence/2026-09-10/docs-audit/`; o commit de evidência posterior altera apenas este relatório e esses anexos.

## Limites que continuam explícitos

As correções documentais não implementam D2–D6. Origem populacional IBGE, manutenção/URIs, semântica temporal de CNES, coordenação/reprocessamento e desempenho seguem como entregas próprias. Histórico de benchmark e propostas antigas foram preservados com status claro. As referências de pesquisa em `reports/2026-09-09-*` são anexos locais anteriores, preservados sem incluí-los neste commit.

Dois relatórios temporários de subagentes haviam entrado em `.superpowers/`; suas cópias completas estão preservadas em `reports/evidence/2026-09-10/transactional-ingestion/task-reports/`. As cópias temporárias foram retiradas da branch para concluir a limpeza já iniciada. Os links do relatório de implementação foram convertidos em caminhos relativos para continuarem válidos após o merge.

## Referências

- [Guia inicial](../docs/guides/getting-started.md)
- [Referência da API](../docs/api.md)
- [Arquitetura](../docs/architecture.md)
- [Contrato transacional](../docs/guides/inventory.md#transactions-and-interrupted-imports)
- [Relatório de implementação D1](2026-09-10-implementacao-ingestao-transacional.md)
