# Atualização de dependências e base de compatibilidade

As dependências diretas de execução, desenvolvimento e documentação foram atualizadas para as versões estáveis mais recentes publicadas no PyPI e compatíveis com os requisitos do projeto na consulta de 9 de setembro de 2026. Os mínimos do `pyproject.toml` agora correspondem a essa base; `uv.lock` registra o conjunto resolvido, incluindo dependências transitivas. Python 3.12 continua sendo a versão mínima suportada.

O lockfile contém 148 entradas: 77 pacotes mudaram de versão, dois entraram e dois saíram. `ast-serialize` e `py-cpuinfo2` entraram; `aws-sam-translator` e `py-cpuinfo` saíram pela nova resolução transitiva. A consulta individual ao PyPI confirmou que as 32 dependências diretas, incluindo extras, coincidem com a versão mais recente informada pelo índice. O backend de build Hatchling foi atualizado separadamente para mínimo 1.32.0.

## Versões principais

| Pacote | Lock anterior | Nova base |
|---|---|---|
| DuckDB | 1.5.2 | 1.5.5 |
| Polars | 1.40.1 | 1.44.2 |
| PyArrow | 24.0.0 | 25.0.1 |
| obstore | 0.9.4 | 0.11.1 |
| Pandera | 0.31.1 | 0.33.1 |
| Pydantic | 2.13.3 | 2.13.5 |
| pydantic-settings | 2.14.0 | 2.15.0 |
| Typer | 0.25.1 | 0.27.2 |
| structlog | 25.5.0 | 26.1.0 |
| psycopg | 3.3.4 | 3.3.5 |
| pytest | 9.0.3 | 9.1.1 |
| pytest-asyncio | 1.3.0 | 1.4.0 |
| mypy | 1.20.2 | 2.3.1 |
| Ruff | 0.15.12 | 0.16.6 |
| Material for MkDocs | 9.7.6 | 9.7.7 |
| mkdocstrings | 1.0.4 | 1.0.6 |

`datasus-dbc` 0.1.3, `dbfread2` 0.1.0, Frictionless 5.19.0 e HTTPX 0.28.1 já estavam nas versões mais recentes consultadas. Eles permaneceram nessas versões. A lista completa de versões, requisitos Python e arquivos publicados está em [dependency-pypi-metadata.json](/Users/raphael/PycharmProjects/omnisus-db/reports/evidence/2026-09-09/dependency-pypi-metadata.json), com a URL oficial de cada consulta.

## DuckLake e ferramentas

DuckLake é uma extensão do DuckDB, não uma dependência Python registrada no lockfile. Com DuckDB 1.5.5, a extensão efetivamente carregada nesta validação foi `d8a1881e`, proveniente do repositório oficial `core`. A auditoria anterior utilizou `415a9ebd`; suas evidências continuam históricas e não devem ser apresentadas como reexecução na extensão nova.

Um teste adicional em catálogo temporário confirmou que `ducklake_last_committed_snapshot(?)` aceita o alias parametrizado e retorna o snapshot confirmado no cenário de um escritor. Isso valida a capacidade necessária ao planejamento; não demonstra isolamento entre escritores concorrentes.

O Ruff agora usa `target-version = "py312"`, coerente com o piso do pacote. O pre-commit foi alinhado ao Ruff 0.16.6. A nova versão inclui Markdown na descoberta padrão: o check global inicialmente encontrou seis documentos que seriam reformatados. A configuração `format.exclude = ["*.md"]` mantém o escopo anterior de formatação de código; o check global passou após esse ajuste. Documentos históricos não foram reescritos.

MkDocs permanece limitado a `<2.0`, mantendo a pilha de plugins validada em 1.6.1. A configuração existente de Dependabot já consulta o ecossistema uv semanalmente. Não foi criada nova automação nem habilitado merge automático.

## Validação executada

| Verificação | Resultado |
|---|---|
| Python 3.13.12, testes `not e2e and not perf` | 386 passaram; 47 desmarcados; 40,30 s |
| Python 3.12.13, ambiente separado, mesma seleção | 386 passaram; 47 desmarcados; 38,69 s |
| Cobertura em cada execução | 91,28%; mínimo exigido 85% |
| Ruff lint global | Passou |
| Ruff format global após ajuste | 96 arquivos já formatados |
| mypy 2.3.1 | Passou em 35 arquivos de código |
| Documentação gerada | Atualizada conforme `gen_datasets_doc.py --check` |
| MkDocs build `--strict` | Passou |
| Frictionless nos dicionários | 15 recursos classificados VALID |
| Build com Hatchling atualizado | Wheel e sdist construídos |
| Instalação do wheel, Python 3.12.13, `--only-binary=:all:` | Passou com 60 pacotes, sem compilação |
| Importação isolada com `python -I` fora do repositório | Importou de site-packages; bootstrap incluído |
| `uv pip check` no ambiente do wheel | Sem incompatibilidades declaradas |
| `uv lock --check` | Passou |

A validação ocorreu em macOS arm64. Os jobs existentes de Linux e Windows não foram executados localmente; instalação binária no Python 3.13 também não foi certificada. Os 47 testes excluídos envolvem E2E ou performance. Frictionless validar os arquivos de dicionário não equivale a validar todas as linhas ingeridas.

Nenhuma correção funcional de A01–A12 foi implementada nesta atualização. A passagem da suíte confirma compatibilidade com os comportamentos testados; os defeitos identificados pela auditoria ainda orientam o plano da próxima entrega.

## Diretriz aprovada

A evolução seguirá incrementalmente, com um escritor por lake inicialmente. A primeira entrega funcional abrangerá A01, A04, A06 e A08: resultados completos por escopo, cache coerente após rollback, refresh CNES atômico e snapshot obtido depois do commit. A autorização do usuário para prosseguir automaticamente à skill writing-plans permite detalhar essa entrega sem uma nova rodada de confirmação intermediária.

O planejamento iniciado em 9 de setembro foi concluído em 10 de setembro de 2026: [especificação](/Users/raphael/PycharmProjects/omnisus-db/docs/superpowers/specs/2026-09-09-transactional-ingestion-design.md) e [plano com seis tarefas](/Users/raphael/PycharmProjects/omnisus-db/docs/superpowers/plans/2026-09-09-transactional-ingestion.md). As tarefas funcionais permanecem pendentes. A base de dependências e a especificação foram registradas no commit `5e44fa3`; os resultados da validação estão em [dependency-upgrade-verification.json](/Users/raphael/PycharmProjects/omnisus-db/reports/evidence/2026-09-09/dependency-upgrade-verification.json).

Fontes oficiais consultadas: [DuckDB 1.5.5](https://duckdb.org/2026/07/22/announcing-duckdb-155), [PyArrow 25.0.1](https://arrow.apache.org/blog/2026/08/10/25.0.1-release/), [resolução e atualização de lockfiles no uv](https://docs.astral.sh/uv/concepts/projects/sync/). As versões dos demais pacotes foram verificadas pelas APIs oficiais do PyPI registradas no anexo.
