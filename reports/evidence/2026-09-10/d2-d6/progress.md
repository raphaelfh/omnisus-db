# SDD ledger — plan: docs/superpowers/plans/2026-09-10-d2-d6.md

Base: 468145d. Worktree: .claude/worktrees/d2-d6, branch codex/d2-d6.

Ruling: User's 'faça a implementação' approves the previously presented design and authorizes reversible implementation choices; no repeated approval gate.
Ruling: Use existing ignored .claude/worktrees location, preserving dirty main checkout. Shared .venv only for running existing dependencies; never sync it.
Ruling: Explicit product/years required for IBGE, reject unsupported 2007/2023; conservative rejection of unsafe type conversions; append remains default; local cooperative writer lock, external cloud exclusivity unchanged.

| Tasks | Shared boundary | Check |
|---|---|---|
| 1/5 | import_pop_year API | product required; controller integrates public API/CLI |
| 2/3/5 | Lake.operations | owned solely by controller |
| 3/4 | schema compatibility | refuse lossy conversions in parser and lake |
| 4/5 | staging path | agent implements parser staging; controller integrates runner |
| 1 | internal | scoped files and tests match product contract |
| 2 | internal | maintenance signatures verified locally before implementation |
| 3 | internal | fail on incompatible types; preserve NULL and reject ambiguous ties |
| 4 | internal | compatibility LazyFrame retained; new runner path stages incrementally |
| 5 | internal | no guarantee beyond cooperative local writers; exact scope and provenance required |
| 6 | internal | end-to-end verification and evidence, no automatic push/merge |

## Conclusão da implementação

- Tasks 1–6 implementadas e revisadas. D2 spec/qualidade PASS, D3/D4 PASS, revisão de integração PASS após correções de buffers, cancelamento e skips dependentes.
- Ruling D2: somente última edição por agregado pode usar universo sem parâmetro temporal; estimativas históricas ficam indisponíveis até artefatos territoriais específicos, sem promessa de migração automática.
- Referência populacional separada de território/publicação/coleta; campos temporais não estabelecidos ficam DATE NULL.
- Default de staging é Parquet Snappy; Zstd é da escrita final DuckLake. Benchmark ampliado ignora descompressão DBC; medição real de DBC também existe em caso pequeno.
- Integração com main c795b39 somente na branch de trabalho: notebooks atualizados para produto IBGE explícito e contratos CNES/URI atuais.
- Python 3.13: 520 testes, 92,12% de cobertura final. Python 3.12: 520 testes na execução final após obter Hypothesis. Wheel binário em ambiente temporário 3.12 e transação real aprovados.
- Guia operacional, relatório português e evidências publicados no próprio repositório. Sem push/merge em main; branch e worktree preservados para revisão.

- O hook uv run alterou o vínculo editável do ambiente compartilhado; o vínculo foi restaurado para o checkout principal, sem alterar dependências. Os commits finais usam UV_NO_SYNC=1.
