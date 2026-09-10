# Verificação de D2–D6 e proposta de execução

Data: 2026-09-10. Base local: `468145d`, com alterações preexistentes de documentação, dependências e notebooks preservadas. Escopo: analisar a implementação atual e propor como concluir as entregas; nenhuma correção de produção foi aplicada nesta avaliação.

## Resultado

A afirmação citada continua correta: **D2–D6 não estão concluídas**. D1 fornece transações, resultados após commit e refresh atômico de CNES master; isso não corrige os contratos de produto, manutenção, tipos, tempo, repetição e escala. D6 já possui componentes anteriores úteis, mas ainda não tem a implementação e a medição exigidas pela proposta.

Não havia `graphify-out/graph.json` no checkout. A avaliação usou diretamente código, testes, histórico e evidência local, sem gerar um grafo do projeto.

| Entrega | Evidência atual | Classificação |
|---|---|---|
| D2 — IBGE | Agregado fixo 793/variável 93; ausência de seleção de produto/períodos; importação vazia retorna normalmente; parser aceita período diferente do solicitado | Pendente, com defeitos reproduzidos |
| D3 — Manutenção/URIs/SQL | Função de compactação inexistente; cleanup recebe INTERVAL onde se exige TIMESTAMPTZ; CLI optimize engole erro; query do catálogo perdida; apóstrofo quebra ATTACH | Pendente, com defeitos reproduzidos |
| D4 — Tipos/CNES | Reconciliação adiciona nomes de colunas, mas não compara tipos existentes; ARG_MAX por atributo mistura competências | Pendente, com defeitos reproduzidos |
| D5 — Coordenação/reprocessamento | Append explícito, exclusividade como precondição; sem protocolo próprio de lock, manifesto de publicação, identidade de versão ou substituição por escopo | Pendente; append repetido é contrato atual, não defeito de D1 |
| D6 — Desempenho | Download em BytesIO, DBF completo e todos os DataFrames residentes; há fila por quantidade, batching, staging zstd e testes de comportamento | Parcial como infraestrutura; entrega de escala pendente |

## Verificação executada

Ambiente observado: Python 3.13.12, DuckDB 1.5.5, DuckLake `d8a1881e`. A [sonda reproduzível](evidence/2026-09-10/d2-d6-audit/probe.py) utiliza entradas sintéticas, mock HTTP para IBGE e catálogos descartáveis. Os [resultados completos](evidence/2026-09-10/d2-d6-audit/observations.json) registram:

- Payload IBGE vazio: retorno com `rows=0` e tabela criada, sem rejeição.
- Solicitação de 2022 com payload de 2021: parser aceita e devolve 2021.
- Inteiro antes de float: `1` seguido de `1.5` persiste como `1, 2` em BIGINT; ordem inversa preserva `1.0, 1.5` em DOUBLE.
- CNES janeiro com tipo `05`, fevereiro com tipo NULL: visão apresenta `05`, município de fevereiro e competência `202402`. Essa combinação não corresponde à última linha inteira.
- Duas ingestões iguais: duas linhas. Confirma append, sem demonstrar idempotência na API de escopo.
- `optimize`: CatalogException, `ducklake_compact_files` inexistente. A CLI termina com código **0** apesar dessa falha real.
- `vacuum`: InvalidInputException por cast INTERVAL → TIMESTAMPTZ.
- URI de exemplo com `sslmode=require`: parser remove o parâmetro do catálogo.
- Diretório `D'Avila`: ParserException no ATTACH.
- Introspecção da extensão confirma `ducklake_merge_adjacent_files`, `ducklake_expire_snapshots` e `ducklake_cleanup_old_files`; as duas últimas recebem corte TIMESTAMPTZ e suportam `dry_run`.

A suíte selecionada passou em **90 testes, 9,57 s** ([log](evidence/2026-09-10/d2-d6-audit/pytest.log)). Comando:

```sh
.venv/bin/python -m pytest tests/unit/sources/ibge tests/integration/test_ibge_pop_e2e.py tests/unit/lake tests/unit/sources/cnes tests/unit/sources/datasus_ftp/test_runner_concurrency.py -q
```

Esses testes verdes não encerram D2–D6: os testes IBGE chegam a exigir aceitação de vazio e descarte de símbolos; o teste de integração usa mock da URL incorreta. Os testes CNES existentes cobrem mudanças de competência sem o NULL reproduzido aqui. Não houve benchmark nacional, teste multiprocesso, conexão cloud real ou nova execução integral da suíte. A ausência de coordenação é uma conclusão da inspeção de código, não de uma corrida reproduzida.

## Como executar

Recomendação: entregas pequenas sobre o contrato de D1. Os nomes de API abaixo são propostas, não interfaces já disponíveis. A ordem de execução sugerida é **D2 → D3 → D4 → D5 → D6**, permitindo antecipar a correção localizada da visão CNES e desenvolver partes de D3 independentemente de D2. D5 depende da validação de fontes e schemas; D6 deve medir a base antes de otimizar.

### D2 — Definir produto populacional e validar antes de publicar

Arquivos principais: `src/omnisus_db/sources/ibge/{fetch,parse}.py`, `sources/ibge/importers/pop.py`, API pública, dicionário IBGE e respectivos testes.

1. Introduzir uma seleção explícita de produto, com fonte, variável, categorias, nível territorial e períodos permitidos. Proposta inicial: `estimativa` e `censo`, sem fallback silencioso entre produtos. A compatibilidade de `import_ibge_pop(years=...)` deve ter regra documentada; chamadas antigas sem produto não podem continuar tratando todos os anos como a mesma série.
2. Usar como candidatos os produtos da pesquisa anterior: estimativa 6579/9324; Censo 2010 202/93, com categorias Total explícitas; Censo 2022 4714/93. Validar esses contratos em metadados e períodos oficiais antes de implementar os endpoints. A contagem 2007 e a publicação territorial de 2023 precisam de produtos próprios ou indisponibilidade explícita no primeiro ciclo.
3. Separar referência populacional, referência territorial, ano de publicação e revisão. Persistir código municipal textual, produto e identidade da fonte. Recomendo tabela versionada com proveniência associada; manter visão de compatibilidade somente se a seleção de produto tornar seu significado inequívoco.
4. Rejeitar payload vazio inesperado, ano divergente, variável/categoria/nível incorreto, duplicatas e estrutura incompleta. Comparar a cobertura com o universo territorial da edição. Definir tratamento dos símbolos estatísticos, contabilizando ausências/rejeições; não usar descarte silencioso nem converter em zero.
5. Guardar URL, coleta, hash dos bytes, versão do contrato e contagens; publicar dados e proveniência na mesma transação. Manter identificação de proveniência compatível com a futura D5, sem esperar por todo seu controlador.

Aceite: fixtures oficiais versionadas com URL/hash; testes de cada produto e lacuna; HTTP 200 vazio não publica; fonte incompatível preserva dados anteriores; valores e quantidade de municípios conferidos contra a edição. Um teste ao vivo separado confirma a fonte; testes determinísticos não dependem da rede. Inventariar dados IBGE legados antes de migrar e não lhes atribuir proveniência retroativamente.

### D3 — Separar manutenção e corrigir composição de entradas

Arquivos principais: `lake/{catalog,connection,operations}.py`, `cli/main.py`, testes de conexão, catálogo, operações e CLI.

1. Fazer `Lake.cloud(catalog=..., storage=...)` construir `CatalogURI` diretamente. No parser de compatibilidade, remover apenas o parâmetro próprio de storage, preservando os demais parâmetros do catálogo e seus valores escapados; testar senha e storage com caracteres reservados e parâmetros repetidos. Mensagens devem ocultar credenciais.
2. Centralizar composição SQL: binding para valores onde suportado, escape próprio para literais em DDL e delimitação de identificadores. Aplicar também em ingestão, staging, auxiliares, alias e particionamento. Testar caminho com apóstrofo/espaço, palavra reservada e aspas internas; corrigir fechamento se a construção da conexão falhar.
3. Trocar compactação pelo wrapper de `ducklake_merge_adjacent_files`. Separar `expire_snapshots` de `cleanup_files`, com corte temporal explícito. Um intervalo de usuário deve ser convertido em instante de corte, nunca passado diretamente como INTERVAL ao parâmetro TIMESTAMPTZ.
4. Expor simulação nas operações destrutivas que a suportam, com resultado estruturado. Definir retenção histórica e margem para leitores separadamente. Não prometer dry-run nativo para compactação: ele não aparece na assinatura local inspecionada.
5. Falha real de manutenção deve encerrar CLI com código não zero. Corrigir a mensagem de vacuum: limpeza de arquivos não equivale a expiração de snapshots. Definir compatibilidade/depreciação do wrapper legado antes de mudar seu efeito.

Aceite: operação real em lake temporário com arquivos Parquet, além de tabelas pequenas com inlining; compactação preserva linhas e histórico; simulação de expiração/cleanup não muda snapshots/arquivos; retenção preserva versões esperadas; erro da API resulta em falha da CLI. Manutenção deve respeitar a exclusividade operacional de D1 e, depois, o lock de D5.

As operações distintas e o uso de corte temporal estão documentados em [Merge Adjacent Files](https://ducklake.select/docs/stable/duckdb/maintenance/merge_adjacent_files), [Expire Snapshots](https://ducklake.select/docs/stable/duckdb/maintenance/expire_snapshots) e [Cleanup of Files](https://ducklake.select/docs/stable/duckdb/maintenance/cleanup_of_files), consultados nesta avaliação. A introspecção local confirma disponibilidade/assinaturas, mas não substitui os testes funcionais de cada operação.

### D4 — Preservar valores e escolher a última linha CNES

Recomendo dois conjuntos de mudanças separadamente revisáveis: correção temporal e contrato de tipos.

- Na visão, selecionar a linha inteira por CNES e competência, preservando NULL. `ROW_NUMBER` com ordenação pela competência resolve a seleção quando não há empates; **não basta** para desempatar versões sem uma chave confiável. Rejeitar empates conflitantes até existir versão de publicação explícita. Testar ingestão fora de ordem e duas linhas na mesma competência. O nome vindo de `cnes_master` também deve ter sua referência de coleta identificada; não apresentá-lo como nome histórico daquela competência.
- Na ingestão, comparar nomes **e tipos** antes do INSERT. Definir contrato por dataset e regras conservadoras de promoção sem perda; recusar mudanças sem regra comprovada. Não promover int64 automaticamente para double. Tratar reconciliação entre batches do parser e entre escopos: `diagonal_relaxed` também exige validação de valores. Decidir se os YAML descrevem bruto ou canônico e não ativar transformações de domínio implicitamente.
- Para lakes antigos, inventariar schemas e valores potencialmente já arredondados. Mudar o dtype não recupera informação perdida; a correção pode exigir reconstrução da fonte.

Aceite: valores finais iguais nas duas ordens de ingestão ou rejeição explícita antes de mutar; inteiros acima de 2^53, decimais, nulos, overflow e códigos com zeros iniciais; falha preserva dados/schema anteriores. CNES mais recente com NULL deve continuar NULL e todos os atributos operacionais devem pertencer à mesma linha.

### D5 — Exclusividade verificável e publicação por escopo

Dividir em D5a (escritor local) e D5b (manifesto/reprocessamento). D5a pode avançar antes, preservando o contrato de um escritor.

1. Proteger a identidade canônica do catálogo com lock entre processos da biblioteca, evitando concorrência entre handles; cobrir toda escrita e leitura do recibo após commit. Definir aquisição, timeout, encerramento e recuperação após morte do processo. Testar caminhos equivalentes/symlinks. SQL externo que ignora o protocolo continua fora da garantia; cloud precisa de desenho próprio se houver demanda por vários escritores.
2. Manter `Lake.ingest` como append. Na API de importação por escopo, propor políticas explícitas `append`, `skip_same`, `error_if_exists` e `replace`. Introduzir sem troca silenciosa do padrão atual; recomendar `skip_same` nos novos fluxos gerenciados, recusando versão diferente sem pedido de substituição.
3. Manifesto com identidade do dataset/escopo, hash da fonte, versões de parser/transformações, `run_id`/`batch_id`, contagens e publicação. Dados e registro confirmado compartilham transação. Registrar tentativas fracassadas depois do rollback. Capturar snapshot como recibo e usar identidade persistida para reconciliação, sem depender apenas de um objeto Python.
4. Validar toda a entrada antes do DELETE e substituir somente o escopo lógico. CNES-ST inclui UF, embora sua partição física seja apenas ano/mês: substituir SP não pode apagar RJ. Validar identidade real das linhas, não apenas as colunas ano/UF injetadas pelo runner.
5. Em confirmação perdida, reabrir e consultar identidade persistida antes de decidir retry. Manifesto sozinho, sem exclusividade, não oferece proteção contra corrida. Lakes legados sem manifesto exigem inventário/reconstrução; não executar DISTINCT indiscriminado.

Aceite: dois processos disputando publicação; repetição idêntica; fonte revisada; parser revisado; substituição preservando outras UFs; vazio/truncamento/escopo errado preservando versão anterior; morte antes/depois do commit; confirmação perdida reconciliada sem duplicação. Os testes multiprocesso devem testar o protocolo da biblioteca, distinguindo-o dos bloqueios que o backend já fornece.

### D6 — Medir recursos e depois reduzir materialização

1. Definir máquina de referência, arquivos/hash, volume pretendido e limites de RSS e disco temporário. Criar baseline em processos isolados, medindo download, descompressão, parsing, staging e ingestão, concorrência 1 e configuração atual. Registrar linhas/s, pico de RSS, bytes em trânsito, disco temporário e versões. Os benchmarks mini atuais são controles úteis, mas não demonstram capacidade nacional.
2. Evoluir download para arquivo temporário com hash incremental e fila de referências a arquivos, ou outro mecanismo que limite bytes antes de acumulá-los. Adquirir orçamento só depois de baixar o payload não limita o pico de download. Definir política para arquivo individual maior que o orçamento.
3. Escrever batches em staging Parquet com schema validado, sem acumular todos os frames em lista. Integrar ingestão de staging existente para evitar regravação redundante. Preservar os gates de integridade DBF e a atomicidade de D1; publicar apenas após conclusão da validação.
4. A descompressão atual retorna DBF completo: o primeiro ganho não pode ser anunciado como memória constante. Mudança incremental nessa etapa depende de capacidade comprovada da biblioteca de DBC. Testar limpeza de temporários também em cancelamento/falha.

Aceite: equivalência de dados, schemas e resultados transacionais no mesmo corpus; respeito ao orçamento definido ou falha controlada; medição comparativa reproduzível demonstrando redução do recurso limitante, sem meta percentual inventada.

## Próxima entrega recomendada

Começar por **D2**, pois hoje a API permite uma população sem contrato de fonte/período verificável. O primeiro incremento deve definir os produtos suportados, rejeitar entradas inválidas e publicar proveniência junto dos dados. A escolha de incluir a publicação de 2023, o padrão futuro de repetição e o orçamento de memória ainda são decisões de produto; as propostas acima permitem preparar suas especificações sem assumir essas decisões como aprovadas.

Para a fonte IBGE, foram reutilizados os [payloads oficiais arquivados em 09/09](evidence/2026-09-09/ibge-responses.json) e a [pesquisa anterior](2026-09-09-pesquisa-e-diretrizes-de-correcao.md). A ferramenta web não conseguiu abrir diretamente os dois endpoints JSON nesta avaliação; não se afirma nova validação ao vivo de seus períodos. O [Plano de Dados Abertos do IBGE](https://www.ibge.gov.br/np_download/novoportal/documentos_institucionais/Plano_de_Dados_Abertos_IBGE_2024_2025.pdf) consultado confirma a associação da tabela 793 à Contagem da População.
