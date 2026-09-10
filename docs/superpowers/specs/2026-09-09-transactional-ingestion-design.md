# Ingestão transacional confiável com um escritor

## Decisões e objetivo

O usuário escolheu evolução incremental da biblioteca, com um escritor por lake inicialmente, e autorizou seguir automaticamente para writing-plans após atualizar as dependências. Esta especificação detalha a primeira entrega funcional, D1, a partir da pesquisa e revisão adversarial. A implementação dos reparos ainda não foi executada.

O objetivo é corrigir A01, A04, A06 e A08: contabilizar escopos que falham, recuperar o cache após rollback, tornar refresh CNES atômico e associar resultados ao commit concluído. O resultado deve continuar utilizável pela API Python e pela CLI existentes.

## Restrições globais

- Python mínimo: `>=3.12`; verificar Python 3.12 e 3.13.
- Base validada: DuckDB `1.5.5`, Polars `1.44.2`, PyArrow `25.0.1`; preservar `uv.lock` e os mínimos atualizados do `pyproject.toml`.
- Extensão DuckLake observada nessa base: `d8a1881e`, repositório `core`; verificar capacidades na extensão efetivamente carregada.
- Um escritor por lake é precondição operacional desta entrega; o consumidor deve serializar handles, processos e SQL externo que alterem o mesmo catálogo.
- Uma conexão DuckDB e um consumidor de parsing/escrita por execução; downloads podem permanecer concorrentes.
- `Lake.ingest` continua append; nenhuma deduplicação, substituição de escopo ou migração de tabelas antigas.
- Estados de `ScopeOutcome` permanecem `ok`, `skipped`, `failed`; ordem e multiplicidade das entradas devem ser preservadas.
- `ImportResult.snapshot_id` permanece `int | None`; `None` significa que não há identificação confirmada disponível.
- Não adicionar dependências de execução nesta entrega.
- Não executar FTP/IBGE/CNES ao vivo na suíte de aprovação; usar fixtures para rede e DuckLake real em diretórios temporários.
- Nenhum COMMIT de resultado desconhecido pode ser repetido automaticamente.
- Não implementar coordenação distribuída, idempotência durável, fonte IBGE, promoções de tipos ou manutenção nesta entrega.

A precondição de um escritor não equivale a um bloqueio já implementado. Um segundo processo, cliente SQL externo ou duas tarefas escrevendo no mesmo handle violam o contrato deste ciclo. Uma política de bloqueio entre processos, se necessária ao produto, integra o subprojeto de coordenação/reprocessamento. A API cloud não é removida, mas não recebe certificação de concorrência por estes testes.

## Arquitetura

`Lake` possui a fronteira transacional e o ciclo de vida do cache. O runner possui a correspondência entre posições de entrada e outcomes, incluindo rollback de lote. O importador CNES prepara respostas antes de iniciar a transação de atualização. Nenhum desses componentes deve inferir sucesso a partir da ausência de linhas ou de uma exceção capturada.

Criar `src/omnisus_db/lake/_transactions.py` apenas para os tipos transacionais: recibo e exceção de estado desconhecido. Manter o controle de BEGIN/COMMIT/ROLLBACK em `Lake.transaction`, sem criar um segundo gerenciador de conexão. As novas exceções de importação ficam em `sources/_base.py`, com os resultados que carregam.

## Interfaces

### Recibo e erros transacionais

`TransactionReceipt` é uma dataclass mutável com `committed: bool = False` e `snapshot_id: int | None = None`. `Lake.transaction() -> Iterator[TransactionReceipt]` continua sendo context manager. Usos existentes sem `as` permanecem válidos.

`TransactionStateError(RuntimeError)` significa que a operação não pode continuar com confiança naquele handle: BEGIN falhou ou rollback falhou. `CommitOutcomeUnknown(TransactionStateError)` significa que COMMIT lançou exceção e não se afirma se os dados foram publicados. A causa original deve ser preservada com exception chaining.

`Lake.in_transaction -> bool` informa somente a transação gerenciada por `Lake`. `Lake.is_usable -> bool` indica que o handle não foi fechado nem invalidado. Transações abertas por SQL bruto não são adotadas automaticamente: o consumidor deve usar `Lake.transaction()` para obter essas garantias.

### Resultado de importação interrompida

`ImportAbortedError(RuntimeError)` recebe `report: ImportReport` e `unresolved: tuple[tuple[int, ScopeKey], ...]`. `report` contém somente resultados determinados; `unresolved` preserva os índices originais de entradas sem resultado determinável ou ainda não processadas. A exceção interrompe a execução em vez de retornar um relatório aparentemente completo.

Exportar `ImportAbortedError` na API de topo, além dos tipos de erro transacional no módulo `omnisus_db.lake`. Uma chamada que termina normalmente sempre devolve um outcome por posição solicitada, inclusive quando duas posições têm o mesmo escopo.

## Transação e cache

Antes de BEGIN, verificar se o handle está utilizável e rejeitar transação gerenciada aninhada. Consultar o último snapshot como referência; falha nessa preparação aborta antes de consumir novos escopos. Limpar caches ao iniciar a fronteira, evitando usar informações antigas após alteração externa sequencial.

Registrar resultados de ingestão em uma lista privada do lote. Dentro da transação, seus snapshots permanecem `None`. Depois de COMMIT bem-sucedido, marcar o recibo como confirmado, consultar `ducklake_last_committed_snapshot(?)` e preencher os resultados pendentes. Se não houver novo snapshot em relação ao início, não atribuir um snapshot anterior à transação vazia.

Se a consulta de snapshot falhar depois de COMMIT concluído, conservar `committed=True` e snapshots `None`, registrar aviso e retornar os dados como confirmados. Isso distingue falha de metadado de falha de persistência. Não consultar `max(snapshot_id)` antes do commit e não anunciar isolamento por conexão.

Se o corpo falhar, executar ROLLBACK e limpar caches em `finally`. Quando rollback funcionar, preservar a exceção original e permitir reutilização do handle. Quando falhar, invalidar o handle e lançar `TransactionStateError` encadeado à falha original, com nota sobre a falha de rollback. Para `CancelledError`, `KeyboardInterrupt` e `SystemExit`, preservar a interrupção original e invalidar o handle se necessário.

Se COMMIT falhar, tentar rollback somente como limpeza, invalidar o handle e lançar `CommitOutcomeUnknown` independentemente do resultado da limpeza. A aplicação deve fechar e reconciliar antes de reprocessar. `close()` precisa ser idempotente e utilizável mesmo após invalidação.

Para ingestão direta sem transação gerenciada, `Lake.ingest` abre uma transação própria e devolve o resultado depois de encerrá-la. Para ingestão em lote, participa da transação existente e registra o resultado pendente. CREATE, ALTER e INSERT passam a compartilhar a mesma unidade de confirmação.

## Runner e contabilidade

Manter `outcomes` indexado pela posição da entrada. Registrar o escopo corrente no lote antes de chamar `ingest_raw`. Uma exceção de parsing/escrita produz `failed` para esse escopo; resultados provisoriamente bem-sucedidos do lote também viram `failed` por rollback. Falhas de download e ausências já classificadas mantêm suas causas.

Somente o ramo de saída normal da transação publica `ok`. Os resultados pendentes terão o snapshot final preenchido pelo `Lake`. Em erro transacional fatal ou encerramento inesperado do produtor, preservar outcomes determinados e lançar `ImportAbortedError` com as posições restantes.

A exceção de falha ordinária deve ser capturada para continuar lotes futuros. Se o handle foi invalidado ou o erro pertence às classes fatais, não continuar. Um lote ainda vazio que não conseguiu iniciar não pode causar um loop sem consumir itens.

Mover a sentinela de fim do produtor para o caminho de conclusão normal. Ao encerrar o runner, cancelar e aguardar o produtor, sem tentar inserir sentinela em fila cheia durante cancelamento. A espera pelo próximo item deve também observar término anormal do produtor, para não aguardar indefinidamente uma fila que não receberá mais itens.

Cancelamento externo reverte o lote corrente, aguarda a limpeza e propaga `CancelledError`. Os lotes previamente confirmados permanecem persistidos. Este ciclo não promete relatório durável após morte de processo.

## CNES Master

Normalizar e deduplicar códigos explícitos antes do fetch, preservando ordem. A preparação para escrita materializa todos os tuples e verifica códigos canônicos de sete dígitos e nome útil antes de qualquer DELETE. Registros repetidos iguais são consolidados; valores diferentes para o mesmo código na mesma carga causam erro antes da mutação.

`_upsert_master` mantém retorno `None` e usa a transação atual, quando existir; caso contrário, abre uma transação própria. O importador público agrupa criação da tabela, upsert e refresh da visão em uma transação depois de concluir o fetch. Nenhuma operação HTTP ocorre dentro dessa transação.

Código sem resposta útil mantém dados anteriores. A política existente de ignorar falhas individuais de HTTP no retorno inteiro permanece neste ciclo; a nova atomicidade se refere aos registros preparados e à atualização da visão. A semântica temporal de `aux_cnes` é A11 e não será alterada aqui.

## CLI e documentação

Para relatório completo com falhas, manter saída não zero e contagens corretas. Para `ImportAbortedError`, imprimir progresso confirmado e quantidade de entradas não resolvidas, sair com código 1 e orientar inspeção antes de repetir a carga. Nunca apresentar a execução interrompida com marca de sucesso.

Documentar a precondição de um escritor, snapshots pendentes dentro de transação, transações SQL brutas fora do contrato e impossibilidade de retry cego após confirmação desconhecida. Manter as assinaturas públicas de importação existentes.

## Critérios de aceite

1. DBC inválido único: um failed, zero linhas, CLI não zero.
2. Lote válido/inválido/válido: três outcomes ordenados, primeiro lote revertido e somente o último escopo persistido.
3. Escopos duplicados de entrada: duas posições e dois outcomes, mantendo append.
4. ALTER seguido de erro: rollback remove a alteração e o mesmo handle aceita nova ingestão com a coluna.
5. COMMIT falho: handle inválido, erro explícito e nenhum retry automático.
6. ROLLBACK falho: causa original preservada, handle inválido e execução interrompida.
7. Snapshot direto e em lote: pendente dentro da transação e correspondente ao novo snapshot após commit.
8. Falha de leitura do snapshot após commit: linhas confirmadas, `snapshot_id=None` e aviso.
9. Transação vazia: recibo sem atribuição do snapshot anterior.
10. Produtor interrompido ou cancelamento com fila cheia: término dentro do timeout de teste e sem tarefas abandonadas.
11. Refresh CNES com falha depois de DELETE: valor anterior preservado.
12. Falha de refresh da visão CNES: atualização de registros também revertida.
13. Códigos repetidos: uma atualização por código; registros conflitantes rejeitados antes de DELETE.
14. Suíte selecionada em Python 3.12 e 3.13, lint, format, mypy, docs e build permanecem verdes.

## Dependências posteriores

IBGE (D2), manutenção/URIs (D3), tipos/visão CNES (D4), reprocessamento e eventual bloqueio entre escritores (D5) e desempenho (D6) mantêm desenhos próprios. Esta entrega não depende da implementação dessas frentes.

## Referências

- [Pesquisa técnica](/Users/raphael/PycharmProjects/omnisus-db/reports/2026-09-09-pesquisa-e-diretrizes-de-correcao.md).
- [Base atualizada e validação](/Users/raphael/PycharmProjects/omnisus-db/reports/2026-09-09-atualizacao-dependencias.md).
- [Revisão adversarial](/Users/raphael/PycharmProjects/omnisus-db/reports/2026-09-09-revisao-adversarial.md).
- [DuckLake: transações](https://ducklake.select/docs/stable/duckdb/advanced_features/transactions) e [snapshots](https://ducklake.select/docs/stable/duckdb/usage/snapshots). A precondição de um escritor evita depender de isolamento de recibo entre conexões, que o teste da extensão histórica não garante.
