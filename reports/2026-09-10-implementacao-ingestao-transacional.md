# D1 — Relatório de implementação e revisão adversarial

## Conclusão executiva

D1 concluída e revisada na branch `codex/transactional-ingestion`, para operação com um escritor por lake. O commit funcional validado é `30ce324`. A entrega corrige A01, A04, A06 e A08. A revisão integral identificou dois defeitos adicionais e um problema de apresentação; os três foram corrigidos e aprovados na revisão pontual final. Não há achados críticos/importantes abertos neste escopo.

A suíte selecionada passou com **429 testes em Python 3.12 e em Python 3.13**, 47 casos excluídos por marcação em cada execução e **91,97% de cobertura**. O wheel final instalou somente com dependências binárias em ambiente limpo Python 3.12 e executou uma transação real com sucesso.

## Rastreabilidade dos problemas

| Achado original | Correção | Prova observável |
|---|---|---|
| A01 — escopo falho omitido | Outcomes por posição, registro antes da ingestão e aborto explícito quando o estado não é determinável | DBC inválido isolado; lote válido/inválido/válido; escopos repetidos; progresso anterior preservado |
| A04 — cache incorreto após rollback | Limpeza nas fronteiras transacionais e invalidação do handle quando a recuperação falha | ALTER revertido seguido de nova ingestão no mesmo handle; falhas de BEGIN/ROLLBACK/COMMIT |
| A06 — perda no refresh CNES | Preparação antes da mutação; tabela, upsert e visão no mesmo commit | Falha depois do DELETE preserva OLD; falha da visão reverte registros; códigos repetidos consultados uma vez |
| A08 — snapshot anunciado antes do commit | Recibo transacional e resultados pendentes finalizados após COMMIT | None dentro do lote; snapshot único contendo CREATE/INSERT; metadado indisponível não desfaz sucesso |

## Ajustes encontrados pela revisão da implementação

- A revisão dos snapshots pediu comprovação de um único snapshot com criação e inserção, além da identidade do snapshot retornado.
- A revisão de concorrência pediu um produtor interrompido após escrita não confirmada: rollback conhecido deve gerar failed determinado e manter apenas as outras posições em unresolved.
- A revisão integral reproduziu o loop ao entrar no runner dentro de uma transação gerenciada existente.
- A revisão integral reproduziu a substituição da primeira interrupção surgida durante limpeza de rollback/commit.
- A revisão integral detectou que largura global fixa e no_wrap poderiam truncar a orientação de inspeção na CLI.

## Método e evidência

Baseline no checkout isolado: 386 testes selecionados, 47 excluídos, 91,28% de cobertura. Seis implementadores com contexto separado, revisão de especificação e qualidade por tarefa e revisão adversarial integral independente. As correções funcionais possuem evidência RED/GREEN nos relatórios de tarefa.

| Gate final | Resultado |
|---|---|
| Python 3.13.12 | 429 passed, 47 deselected; 91,97%; 35,90 s |
| Python 3.12.13 | 429 passed, 47 deselected; 91,97%; 35,45 s |
| Ruff lint e formatação | Aprovados |
| mypy | Aprovado, 36 arquivos de código |
| Documentação gerada e MkDocs strict | Aprovados |
| Frictionless | 15 recursos válidos |
| Build de sdist e wheel | Aprovado |
| uv.lock e git diff --check | Aprovados |
| Wheel limpo Python 3.12 | 60 pacotes compatíveis, instalação `--only-binary=:all:` |
| Smoke test do wheel com `python -I` | Import de `site-packages`, snapshot pendente, commit e leitura de dados aprovados |

Os logs `pre-review-fix-checks` pertencem a `18dd077` (417 testes por versão); os logs `final-checks` e os hashes correspondem ao estado funcional `30ce324`. O commit posterior deste relatório altera apenas documentação/evidência. O gate não infere execução da CI remota.

A base de dependências atualizada anteriormente foi preservada e novamente validada: DuckDB 1.5.5, Polars 1.44.2, PyArrow 25.0.1, datasus-dbc 0.1.3, pytest 9.1.1, Ruff 0.16.6 e mypy 2.3.1. A extensão DuckLake carregada foi `d8a1881e`, instalada de `core`. O manifesto e o lock mantêm as versões compatíveis da base aprovada.

Os testes novos de regressão foram observados em RED antes das correções; controles de comportamento já implementado permaneceram verdes quando previsto. A onda final reproduziu nove falhas e manteve quatro controles verdes antes da correção; depois, os 66 testes que cobrem os arquivos alterados passaram.

## Contrato e limites

- Um escritor por catálogo continua sendo precondição operacional: handles, processos e SQL externos devem ser serializados pelo consumidor.
- Append permanece a semântica de ingestão. ImportAbortedError exige inspeção; um COMMIT sem confirmação pode ter persistido dados.
- O relatório parcial contém resultados determinados; posições não resolvidas mantêm seus índices originais. Cancelamento propaga a interrupção e preserva lotes previamente confirmados.
- Validação local em macOS arm64. Linux/Windows dependem dos respectivos jobs de CI; testes de fontes ao vivo e de desempenho não compõem este gate.
- D2–D6 (IBGE, manutenção/URIs, tipos/visão temporal, reprocessamento/coordenação e desempenho) seguem como entregas próprias.
- O build estrito de documentação passa com MkDocs1.x; o banner do Material sobre MkDocs2.0 foi preservado no log e não representa erro desta construção.

## Artefatos de auditoria

- [Metadados, versões e hashes](/Users/raphael/PycharmProjects/omnisus-db/.claude/worktrees/transactional-ingestion/reports/evidence/2026-09-10/transactional-ingestion/verification.json)
- [Registro das decisões e revisões](/Users/raphael/PycharmProjects/omnisus-db/.claude/worktrees/transactional-ingestion/reports/evidence/2026-09-10/transactional-ingestion/progress.md)
- [Resultado da revisão integral](/Users/raphael/PycharmProjects/omnisus-db/.claude/worktrees/transactional-ingestion/reports/evidence/2026-09-10/transactional-ingestion/final-review-result.md)
- [Relatório da correção final com RED/GREEN](/Users/raphael/PycharmProjects/omnisus-db/.claude/worktrees/transactional-ingestion/reports/evidence/2026-09-10/transactional-ingestion/final-fix-report.md)
- [Plano executado](/Users/raphael/PycharmProjects/omnisus-db/.claude/worktrees/transactional-ingestion/docs/superpowers/plans/2026-09-09-transactional-ingestion.md)
- [Especificação](/Users/raphael/PycharmProjects/omnisus-db/.claude/worktrees/transactional-ingestion/docs/superpowers/specs/2026-09-09-transactional-ingestion-design.md)

## Decisões registradas durante a execução

- Ruling: Use the existing ignored .claude/worktrees directory for isolation — repository already maintains worktrees there and this avoids an unrelated main-branch gitignore commit — cost if wrong: relocate this reversible checkout.
- Ruling: Preserve cancellation/KeyboardInterrupt/SystemExit identity and invalidate the handle when BEGIN or cleanup is interrupted, including BaseException failures — the spec's lifecycle and interruption guarantees bind over narrower example catch blocks — cost if wrong: stricter invalidation requires reopening a handle.
- Ruling: Producer cleanup must explicitly cancel and await outstanding child producers after abnormal gather termination — asyncio.gather alone does not guarantee that sibling tasks terminate — cost if wrong: a small additional lifecycle cleanup block.
- Ruling: Add a focused public ImportAbortedError export/payload test in Task 6 — the plan lists the public API test file and acceptance requires the exported contract, although its snippet is absent — cost if wrong: one redundant behavioral test.
- Ruling: Strengthen the existing direct-ingest snapshot test to assert one new snapshot for CREATE plus INSERT — the reviewer flags a named file missing from the diff, while the plan only conditionally requests expectation updates; this assertion directly validates the binding atomic direct-ingest requirement — cost if wrong: a redundant snapshot-count assertion.
- Ruling: Reject runner execution inside an existing managed transaction before starting producers — nesting is already unsupported and retrying entry without consuming causes a busy loop — cost if wrong: callers must move the runner outside their outer transaction.
- Ruling: Preserve the earliest control-flow interruption, including one first raised during cleanup of an ordinary failure, with the original failure chained and handle invalidated — interruption identity applies throughout the managed boundary — cost if wrong: callers see the cleanup interruption instead of a transaction-state exception.
- Ruling: Distinguish new failing regressions from controls of already implemented behavior when recording TDD — the plan itself expects repeated-scope and invalid-DBC compatibility controls to pass before later tasks, so a blanket claim that every new assertion first failed would be false — cost if wrong: a misclassified control would need an additional historical regression probe.
