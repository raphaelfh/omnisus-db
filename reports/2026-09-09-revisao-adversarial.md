# Revisão adversarial do relatório de engenharia de dados

**Data:** 09/09/2026  
**Objeto:** relatório técnico e seus anexos, não uma nova implementação.  
**Referência atual:** `011e77bdf14afcc3d72ebb666247d0968f92c165`.  
**Referência atribuída pelo relatório original:** `e681aceb869004dc192c4aaa588a51adc6d54ac7`.

## Parecer

**O relatório original contém evidências úteis, mas precisava ser corrigido antes de orientar um backlog de implementação.** A revisão encontrou um falso positivo de configuração, uma falha de proveniência, prioridades que misturavam defeito com decisão de produto e recomendações incompletas para substituição de dados.

A07 foi retirado. A02 foi separado como decisão de contrato. A05 foi reduzido a P2, pois a corrupção foi demonstrada na API com dados sintéticos, sem estabelecer incidência em layouts reais. O resultado revisado é **10 grupos de defeitos: 4 P1 e 6 P2, uma decisão de contrato e um achado retirado**. O agrupamento de manutenção A09 contém mais de uma falha; essa contagem não equivale a causas-raiz independentes.

As conclusões sobre falhas omitidas, cache após rollback, origem populacional incompatível com os anos documentados e ausência de atomicidade no refresh CNES resistiram às contestações. O relatório revisado preserva esses problemas, com alcance mais preciso.

## 1. Problemas encontrados no próprio relatório

### R01 — P1: A07 não é sustentado pelo commit citado nem pelos anexos

**Contestação:** a alegada combinação de Python >=3.13 com gate 3.12 existe no estado versionado atribuído ao achado?

**Resposta:** não. A leitura dos blobs Git mostrou:

| Estado | pyproject.toml | uv.lock | Ambiente do gate de release |
|---|---|---|---|
| `e681ace` | >=3.13 | >=3.13 | 3.13 |
| `011e77b` | >=3.12 | >=3.12 | 3.12 |

Além disso, o anexo original `verification.json` já continha `requires_python: >=3.12` e `gate_version_meets_package_requirement: true`, contradizendo a afirmação textual de que a comparação retornou falso.

**Julgamento:** falso positivo na atribuição ao estado versionado. Uma leitura transitória do working tree não congelado pode explicar a combinação observada, mas não permite atribuí-la ao commit. Não basta dizer que o bug foi corrigido depois: o relatório errou ao apresentar essa configuração como fato do commit auditado.

**Correção realizada:** A07 retirado do diagnóstico e do plano de correções, com os IDs restantes preservados. A indisponibilidade de wheels é uma questão separada, não confirmada nem refutada por essa retirada.

### R02 — P1: a proveniência não garantia que todos os resultados pertenciam ao mesmo estado

**Contestação:** o commit informado identifica os bytes realmente lidos em todos os passos?

**Resposta:** não. O relatório foi produzido sobre um workspace compartilhado sem manifesto de hashes ou validação de estabilidade entre as leituras. Houve alteração de configuração durante a coleta. O anexo combina o SHA original com requisitos de Python do estado posterior.

O exame atual mostra que `src` e `tests` não mudaram entre os dois commits. Isso permite revalidar os achados de execução sem assumir que as conclusões de CI também continuem válidas. O número de arquivos inventariados tampouco é prova de inspeção exaustiva de todas as linhas; a metodologia foi reescrita para distinguir essas duas coisas.

**Correção realizada:** preservação do original, comparação de blobs versionados, identificação do módulo Python efetivamente importado e hashes dos 35 arquivos Python de código mais quatro arquivos de configuração antes/depois dos novos controles. Os hashes e HEAD permaneceram estáveis durante esses controles. Os resultados históricos de 386 testes foram mantidos como históricos, sem anunciar uma nova execução da suíte ou certificação da CI atual.

### R03 — P2: a classificação misturava comportamento de append, defeito e risco de domínio

**Contestação A02:** acrescentar a mesma carga duas vezes viola o contrato atual de `Lake.ingest`?

O método é documentado como CREATE/INSERT. O experimento confirma append e duplicação, mas não prova violação de uma promessa de idempotência. A própria versão original fazia essa ressalva, mas ainda colocava A02 entre os P1 e impunha substituição como critério de aceite.

**Julgamento:** risco importante para reprocessamento recorrente, condicionado à política do consumidor. Há alternativas válidas: rejeitar escopos já carregados, pular versões idênticas, substituir snapshots completos ou manter append sob controle externo. Não há autorização implícita para trocar o comportamento de toda a API.

**Contestação A05:** os exemplos UInt8/UInt16 e inteiro/fracionário representam arquivos DATASUS efetivamente observados?

Não. O exemplo UInt8 não representa a inferência usual do parser para inteiros DBF. O controle Int64/Float64 é mais representativo da API e confirmou perda de precisão dependente da ordem, mas ainda não estabelece incidência em layouts reais de um mesmo dataset.

**Correção realizada:** A02 passou a “Contrato”; A05 passou a P2. A05 pode subir de prioridade se houver evidência de layouts reais afetados ou requisito explícito de aceitar esses tipos com preservação automática. Confiança no comportamento reproduzido e prioridade operacional são dimensões distintas.

### R04 — P1: a recomendação de substituir escopos precisava de proteção contra perda de dados

**Contestação:** implementar DELETE do escopo seguido de INSERT, em transação, é suficiente para resolver A02 com segurança?

Não. Uma transação garante que as operações sejam confirmadas juntas; não garante que a entrada seja completa ou corresponda ao escopo correto. A03 já documenta uma resposta HTTP 200 vazia. Uma substituição ingênua poderia confirmar a remoção de dados válidos ao receber uma entrada vazia inesperada.

CNES-ST também distingue identidade lógica e partição física: apagar uma partição ano/mês para substituir uma única UF pode remover as outras UFs. Dois writers substituindo o mesmo escopo exigem controle de conflito; um hash da fonte sozinho não resolve essa disputa.

**Julgamento:** lacuna na recomendação, não defeito adicional da implementação atual, que ainda usa append.

**Correção realizada:** critérios de aceite agora exigem validar identidade e completude antes do DELETE, preservar dados diante de vazio inesperado, definir o tratamento de vazios legítimos, isolar o escopo lógico e controlar disputa entre writers. A troca de contrato continua dependente de desenho e aprovação.

### R05 — P2: o parecer geral excedia o ambiente efetivamente avaliado

**Contestação:** esses testes demonstram que qualquer uso do projeto é impróprio ou que um manifesto interno é condição universal de confiabilidade?

Não. Demonstram falhas em fluxos específicos e ausência de certas garantias dentro da biblioteca. Uma aplicação pode impedir repetição, restringir os tipos aceitos e persistir seu próprio histórico. A biblioteca não precisa incorporar todos esses mecanismos se houver uma fronteira de responsabilidade clara.

**Correção realizada:** o parecer passou a identificar os fluxos atingidos. A necessidade de controles duráveis foi mantida, mas a implementação obrigatória de um manifesto dentro do pacote foi retirada. Não foi validada uma implantação de produção, nem demonstrado que os consumidores existentes possuem esses controles.

### R06 — P2: alguns exemplos precisavam de controles que delimitassem o alcance

**Snapshot:** o controle de ingestão direta reportou snapshot 2, correspondente ao commit 2. Sob transação externa, o resultado reportou 2 e o commit foi 3. A08 é confirmado para batching/transação externa, não para toda chamada de `ingest`.

**CNES:** a mesma falha injetada deixou zero linhas sem transação e preservou uma linha com transação. Isso reforça A06. Entretanto, o caso de perda do registro anterior exige atualização de um código existente: `only_missing=False` ou códigos explícitos. O padrão de selecionar apenas ausentes não percorre esse mesmo cenário.

**IBGE:** múltiplos resultados e ano divergente no diagnóstico foram fabricados. Os metadados arquivados não mostram classificações que justifiquem aquela multiplicidade para os agregados atuais. O exemplo demonstra validação defensiva ausente, mas não prova descarte real de séries pelo endpoint. A resposta vazia real e a incompatibilidade dos períodos sustentam A03 independentemente desse exemplo.

**Correção realizada:** essas condições foram incorporadas ao relatório. Os dez grupos originais foram repetidos sem erros inesperados, e os quatro controles adicionais foram registrados separadamente.

## 2. Disposição de cada achado original

| ID | Resultado adversarial | Classificação atual | Limite da conclusão |
|---|---|---|---|
| A01 | Confirmado e reforçado por lote misto | P1 | O escopo que lança a exceção some; escopos anteriores revertidos ainda são contabilizados |
| A02 | Comportamento confirmado; classificação corrigida | Contrato | Append é permitido pela API atual; idempotência depende da política escolhida |
| A03 | Sustentado por respostas oficiais arquivadas e código inalterado | P1 | Fonte inadequada aos anos documentados; não invalida seu uso para 2007 |
| A04 | Reproduzido novamente | P1 | Cache incorreto no mesmo handle após rollback de evolução de schema |
| A05 | Confirmado na API; severidade reduzida | P2 | Frames sintéticos, sem incidência demonstrada em layouts reais |
| A06 | Confirmado com controle transacional | P1 | Perda de registro anterior durante refresh de códigos já existentes |
| A07 | Refutado no estado versionado | Retirado | Não gera ticket de correção de produto |
| A08 | Confirmado e delimitado | P2 | Dentro de transação externa; chamada direta funcionou no controle |
| A09 | Reproduzido novamente | P2 | Funções/tipos incompatíveis com a extensão testada; várias falhas agrupadas |
| A10 | Reproduzido novamente | P2 | Parsing de URI; não demonstra configuração TLS efetiva de servidor |
| A11 | Reproduzido novamente | P2 | Cenário de NULL na última competência; último valor não nulo exigiria outro contrato |
| A12 | Reproduzido novamente | P2 | Caminho legítimo quebra SQL; exploração remota não demonstrada |

## 3. Evidências adicionais

Os controles produziram os seguintes resultados:

| Controle | Resultado observado | Consequência |
|---|---|---|
| Lote com anos 2021 válido, 2022 inválido, 2023 válido | Outcomes: 2021 failed, 2023 ok; 2022 ausente; somente 3.311 linhas de 2023 persistidas | A01 não se limita a uma carga de arquivo único; rollback do lote foi respeitado |
| Falha de upsert sem/com transação | 0 / 1 linha sobrevivente | Perda ligada à fronteira transacional |
| Inteiro primeiro / float primeiro | BIGINT: 1 e 2 / DOUBLE: 1 e 1,75 | Resultado e schema dependem da ordem de chegada |
| Ingest direto / transação externa | Snapshot correto / snapshot anterior | Limita a afirmação de A08 |

Não foi necessário executar novamente toda a suíte: código e testes não mudaram entre os commits, e a revisão focou em hipóteses não resolvidas pelos resultados anteriores. Isso não valida as alterações recentes nos workflows. Também não foram consultados novamente os endpoints do IBGE; as conclusões externas referem-se às respostas registradas em 09/09/2026, preservadas com suas URLs.

O script de diagnóstico original aceita um caminho de repositório para ler a fixture, mas não garante sozinho que a biblioteca importada venha desse caminho. Também termina com JSON mesmo quando um grupo encontra erro inesperado. O relatório já o descrevia como diagnóstico, não suíte de aprovação. Na revisão, verificou-se explicitamente o caminho do módulo nos controles e a ausência de `unexpected_error` nos dez grupos repetidos. Para portabilidade futura, convém acrescentar essas garantias ao próprio diagnóstico; o script histórico foi preservado.

## 4. Artefatos e limites desta revisão

- [Relatório corrigido](/Users/raphael/PycharmProjects/omnisus-db/reports/2026-09-09-avaliacao-engenharia-dados.md).
- [Relatório original preservado](/Users/raphael/PycharmProjects/omnisus-db/reports/evidence/2026-09-09/adversarial/original-report.md).
- [Controles com commits, hashes e resultados](/Users/raphael/PycharmProjects/omnisus-db/reports/evidence/2026-09-09/adversarial/controls.json) e [script reproduzível](/Users/raphael/PycharmProjects/omnisus-db/reports/evidence/2026-09-09/adversarial/controls.py).
- [Reexecução dos dez grupos originais](/Users/raphael/PycharmProjects/omnisus-db/reports/evidence/2026-09-09/adversarial/repeated-observations.json).

Esta é uma segunda passagem adversarial pelo mesmo agente, apoiada em contraprovas e controles de execução; não deve ser apresentada como parecer independente de um segundo revisor humano ou agente. Não houve implementação de correções na biblioteca, alteração dos testes existentes, commit ou publicação. A revisão corrige a análise e prepara decisões mais seguras para o próximo desenho técnico.
