# Pesquisa técnica e proposta de evolução do omnisus-db

## Síntese executiva

A recomendação é evoluir a biblioteca por entregas pequenas, começando pela correspondência entre transação, dados persistidos e resultado comunicado ao usuário. Essa frente resolve falhas comprovadas sem exigir uma plataforma de orquestração. Em seguida, devem ser tratados o contrato populacional do IBGE, o reprocessamento e a preservação de tipos. A otimização de memória vem depois desses fundamentos, com medições representativas.

O diagnóstico revisado contém dez grupos de defeitos: quatro P1 e seis P2. A02 é uma decisão de contrato sobre repetição de cargas; A07 foi retirado por erro do relatório original. Implementar todos os itens como se fossem bugs equivalentes produziria mudanças desnecessárias e poderia alterar indevidamente a API de append. A referência local para essas distinções é a [revisão adversarial](/Users/raphael/PycharmProjects/omnisus-db/reports/2026-09-09-revisao-adversarial.md).

Esta pesquisa encontrou duas correções importantes para o desenho inicialmente sugerido. Primeiro, a função de último snapshot do DuckLake existe no commit auditado, mas seus testes mostram estado compartilhado entre conexões do mesmo catálogo: não basta presumir isolamento por conexão. Segundo, a publicação municipal de 2023 do IBGE utiliza resultados censitários de 2022 com atualização territorial; tratá-la como estimativa anual homogênea introduziria uma interpretação incorreta.[^snapshot-code][^snapshot-test][^ibge2023]

O documento oferece alternativas, prioridades, dependências e critérios de aceite. O usuário escolheu **evolução incremental da biblioteca, com um escritor por lake inicialmente**, e solicitou a atualização para as versões mais recentes compatíveis dos pacotes. Essa diretriz está aprovada; os contratos detalhados das entregas ainda serão especificados. Coordenação entre múltiplos escritores fica para uma etapa posterior.

A atualização de dependências e sua validação estão registradas em [Atualização de dependências e base de compatibilidade](/Users/raphael/PycharmProjects/omnisus-db/reports/2026-09-09-atualizacao-dependencias.md). As versões citadas na auditoria e nas evidências históricas abaixo continuam identificando o ambiente original; não foram substituídas retroativamente pelas versões novas.

## 1. Base de evidências e limites

A pesquisa foi realizada em 9 de setembro de 2026, tendo como referência do repositório o commit `011e77bdf14afcc3d72ebb666247d0968f92c165`. A revisão adversarial verificou que código e testes não mudaram entre essa referência e `e681aceb869004dc192c4aaa588a51adc6d54ac7`; as alterações intermediárias atingiram configuração e documentação. Os resultados históricos são reutilizados com essa delimitação, sem anunciar nova execução integral de testes.

Há três classes de evidência. Os defeitos locais estão apoiados nos diagnósticos e controles arquivados. As capacidades de dependências foram investigadas na documentação oficial e, no ponto mais sensível, no código e nos testes do commit exato do DuckLake. As decisões de arquitetura e os critérios de aceite são recomendações desta análise, não garantias já oferecidas pela biblioteca.

O ambiente da auditoria usava DuckDB 1.5.2, extensão DuckLake `415a9ebd`, Polars 1.40.1 e PyArrow 24.0.0. A API pública do GitHub resolveu o hash da extensão para `415a9ebdbd73db50a8c6ba703eb733ed16bcf33a`, cujo commit integra trabalho da versão 1.0. O calendário oficial associa DuckDB 1.5.2 à extensão 1.0. Isso melhora a correspondência documental, mas não substitui testes dos binários e das assinaturas efetivamente instalados.[^ducklake-commit][^versions]

A documentação consultada de Arrow identifica versão 25.0.1; o ambiente auditado utiliza 24.0.0. As recomendações relativas a casts e escrita por lotes precisam, portanto, de testes na versão suportada pelo pacote. Não há motivo demonstrado para atualizar todas as dependências em conjunto.

Não foram validados nesta pesquisa um ambiente Postgres remoto, armazenamento de objetos, instalação limpa, desempenho nacional ou recuperação real após queda de máquina. Também não foi estabelecida incidência de A05 em layouts históricos reais de um mesmo dataset DATASUS. Essas lacunas limitam as garantias da primeira entrega e orientam experimentos futuros; não justificam afirmar que todo uso atual do projeto é inviável.

## 2. Alternativas de arquitetura

| Abordagem | Benefício principal | Custo e limite | Quando escolher |
|---|---|---|---|
| **Evolução incremental da biblioteca, com um escritor inicialmente — escolhida** | Corrige os defeitos reproduzidos, mantém CLI e reduz mudanças simultâneas | Exige declarar e aplicar a exclusividade; não entrega reprocessamento concorrente distribuído | Diretriz aprovada para a primeira etapa |
| **Biblioteca enxuta com controle externo** | Mantém append e delega agenda, histórico e exclusividade a um consumidor existente | CLI isolada depende de disciplina ou integração adicional; responsabilidade pode ficar fragmentada | Quando já existe um orquestrador durável com responsável definido |
| **Coordenação cloud desde o início** | Permite projetar disputas e retomada entre processos como requisitos centrais | Acrescenta integração, falhas de rede, credenciais, recuperação e testes de concorrência | Quando vários processos precisam gravar desde a primeira entrega |

As três alternativas precisam corrigir A01, A03, A04 e A06. Um orquestrador não conserta resultado omitido, fonte incorreta ou DELETE não atômico dentro da biblioteca. A diferença está em quem controla a identidade de uma carga e decide se ela pode ser reaplicada.

O DuckLake documenta alternativas de catálogo para usos locais e remotos, incluindo SQLite e Postgres. A escolha não deve ser reduzida a desempenho: ela define quem pode coordenar acesso e como o sistema se recupera de indisponibilidade. Preservar o catálogo local existente evita acrescentar uma migração sem relação direta com os defeitos confirmados.[^catalog]

Não se recomenda introduzir Airflow, Kafka, Spark ou outro formato de lake apenas para resolver os achados atuais. Essa é uma decisão de escopo: as evidências identificam problemas nas fronteiras existentes, e não demonstram necessidade de substituir a arquitetura inteira.

## 3. Primeiro subprojeto: transações e resultados confiáveis

### 3.1 Contratos observáveis

O primeiro ciclo deve abranger A01, A04, A06 e A08. O contrato proposto é que cada posição de entrada de uma execução concluída produza exatamente um resultado terminal. A identidade por posição importa porque o usuário pode fornecer o mesmo escopo duas vezes; usar somente o escopo como chave esconderia uma das solicitações.

Um resultado `ok` representa dados confirmados. Um escopo revertido pelo lote é `failed`, com causa distinguível da falha que provocou o rollback. `skipped` fica reservado a ausência esperada ou política explícita, como fonte comprovadamente não publicada. Falha de parsing, erro de rede e vazio inesperado não devem ser convertidos em ausência normal.

A soma de linhas bem-sucedidas precisa corresponder às linhas efetivamente confirmadas naquela execução, não à quantidade tentada antes do rollback. Na CLI, qualquer falha comunicada deve produzir saída diferente de zero. Uma execução sem entradas continua diferente de uma execução cujas entradas falharam.

Para interrupção ou perda de confirmação de commit, a API deve distinguir uma exceção com progresso parcial de um relatório completo. Não se deve inventar sucesso ou rollback para um resultado desconhecido. O esquema atual de três estados pode ser mantido inicialmente, usando erro explícito e contexto de progresso; a necessidade de um estado público adicional deve ser decidida na especificação.

### 3.2 Fronteira transacional

O DuckLake oferece transações que abrangem dados e alterações de schema. Essa capacidade permite que alterações relacionadas sejam confirmadas ou revertidas juntas. Ela não inclui automaticamente objetos Python, mensagens da CLI ou arquivos externos de controle.[^transactions]

No runner, a participação do escopo no lote deve ser registrada antes da operação que pode falhar. Os resultados só devem ser publicados como confirmados depois do COMMIT. A solução precisa tratar erro no corpo da transação e no próprio COMMIT, preservando a exceção original caso a tentativa de rollback também falhe.

No cache de schema, a opção inicial recomendada é invalidar entradas ao terminar uma transação com erro, em vez de manter uma réplica transacional complexa do catálogo. Ao iniciar uma nova fronteira de escrita, consultar o estado confirmado evita depender de alterações feitas por outro handle. O custo de leituras adicionais deve ser medido depois; A04 já demonstra o custo de correção de um cache inconsistente.

Para refresh CNES, buscar e validar a resposta antes da mutação. Preparar os registros em staging, verificar repetição de códigos e executar remoção e inserção dentro de uma única transação. Se o chamador já possui a transação, o método deve participar dela; transações aninhadas não devem ser presumidas. A responsabilidade de abrir e fechar a transação precisa ficar em uma camada definida.

### 3.3 Snapshot: a documentação não basta

A documentação estável descreve `last_committed_snapshot` como recurso útil quando várias conexões atualizam o destino. No commit auditado, a função consulta `DuckLakeCatalog::GetLastCommittedSnapshotId()`, cujo campo pertence ao catálogo. O teste oficial confirma que um COMMIT em `con1` altera o valor observado na conexão padrão. Portanto, esse recurso não é, por si só, um comprovante exclusivo de uma transação em todas as topologias.[^snapshots][^snapshot-code][^snapshot-test][^snapshot-state]

Para um escritor exclusivo, a recomendação é obter o snapshot depois do COMMIT, mantendo exclusividade até concluir a captura do resultado. Se houver várias conexões compartilhando catálogo, a seção protegida deve abranger ambas as operações. Uma trava apenas em uma instância `Lake` não protege outros handles ou processos.

Para múltiplos escritores independentes, o desenho precisa de uma identidade persistida da operação, como `run_id` e `batch_id`, vinculada à confirmação. Metadados de commit são uma possibilidade documentada; devem ser testados quanto à disponibilidade e à recuperação. Uma falha depois do COMMIT e antes da resposta exige reconciliação, não reexecução automática de append.[^snapshots]

### 3.4 Cancelamento e progresso parcial

O runner combina produtores assíncronos com um consumidor que grava. A especificação deve exigir encerramento dos produtores quando o consumidor falha, inclusive com fila cheia. A documentação de Python recomenda limpeza em `finally` e propagação de `CancelledError`; a adoção de `TaskGroup` não deve converter indiscriminadamente falhas recuperáveis de escopo em cancelamento de toda a importação.[^asyncio]

O teste precisa observar término dentro de um limite, ausência de tarefas pendentes e preservação dos lotes já confirmados. Isso é uma exigência preventiva para a correção do runner, não um novo defeito de cancelamento confirmado nesta pesquisa.

## 4. População IBGE: fonte e significado temporal

### 4.1 O que deve mudar

A03 resulta de usar agregado 793, variável 93, para anos que a fonte não oferece. As respostas oficiais arquivadas identificam Contagem da População de 2007; a consulta de 2022 retornou HTTP 200 com lista vazia. O contrato de sucesso precisa validar cobertura e conteúdo, além do status HTTP.[^ibge793]

O agregado 6579, variável 9324, é candidato para estimativas municipais. A lista de períodos arquivada contém 2001–2006, 2008–2009, 2011–2021 e 2024–2026. Ela não cobre todos os anos entre o primeiro e o último. A aplicação deve consultar períodos publicados ou usar uma configuração versionada e verificável, sem preencher lacunas por inferência.[^ibge6579]

| Produto | Fonte investigada | Tratamento proposto |
|---|---|---|
| Estimativa municipal | Agregado 6579, variável 9324 | Aceitar somente períodos publicados e preservar revisão da fonte |
| Censo 2010 | Agregado 202, variável 93 | Selecionar explicitamente Total de sexo e Total de situação do domicílio |
| Censo 2022 | Agregado 4714, variável 93 | Importar como produto censitário, separado de estimativa |
| Relação municipal publicada em 2023 | Nota metodológica e arquivos oficiais próprios | Produto separado, ou indisponível no primeiro ciclo; não renomear Censo 2022 como estimativa 2023 |
| Contagem 2007 | Agregado 793, variável 93 | Manter somente se houver requisito explícito para esse produto |

Os metadados de 202 e 4714 foram consultados diretamente nesta pesquisa. A tabela 202 possui classificações de sexo e situação do domicílio; em ambas, a categoria de total é 0. A tabela 4714 oferece população, área e densidade, não possui classificações e identifica somente 2022. Essas verificações sustentam os candidatos, mas a seleção de uma série municipal completa ainda precisa de testes de contrato com respostas reais.[^ibge202][^ibge4714]

### 4.2 A exceção de 2023

A nota metodológica oficial explica que a população municipal publicada em 2023 deriva da segunda apuração do Censo 2022, com malha territorial de 30 de abril de 2023. Sua capa registra referência populacional em 31 de julho de 2022. A descrição pública do produto usa também a formulação de 1º de agosto de 2022; a importação deve preservar a referência expressa da edição selecionada, sem normalização temporal silenciosa.[^ibge2023][^ibge2023-page]

O desenho recomendado separa ano de publicação, data de referência populacional e referência territorial. Assim, um usuário que calcule taxas pode saber qual denominador está usando. Se a primeira entrega não incluir o produto de 2023, a resposta deve declarar a indisponibilidade para a série solicitada.

### 4.3 Validação e compatibilidade

Cada carga populacional deve validar agregado, variável, período, nível municipal, categorias e unicidade da chave esperada. A completude deve ser comparada ao universo territorial da edição, sem impor uma quantidade fixa de municípios para toda a história. Códigos geográficos permanecem identificadores textuais, com conversão explícita quando o consumidor utiliza outra representação.

Vazio inesperado deve bloquear uma carga e, sobretudo, impedir substituição de dados já válidos. Símbolos estatísticos devem ter interpretação definida a partir da fonte; valores suprimidos ou indisponíveis não podem virar zero ou desaparecer sem contagem. A validação deve registrar quantidades recebidas, aceitas, rejeitadas e ausentes.

Metadados mínimos propostos: produto, agregado, variável, referência populacional, referência territorial quando aplicável, publicação/revisão, URL, instante de coleta e hash dos bytes. Esses campos podem residir em tabela de proveniência associada ao escopo; não precisam ser repetidos em cada linha. A escolha entre manter a tabela atual com uma visão compatível ou criar uma tabela versionada depende dos consumidores existentes.

## 5. Reprocessamento e proveniência

### 5.1 Preservar append e explicitar a política

A02 não deve gerar uma troca silenciosa do comportamento de `Lake.ingest`. A proposta é manter a primitiva de append e definir a política de repetição na API de importação por escopo, ou num controlador externo. A documentação deve indicar claramente qual camada oferece a garantia.

As opções são: rejeitar escopo já publicado; pular a mesma versão; substituir um escopo completo; ou acrescentar sob controle do consumidor. Para uma primeira política conservadora, recomenda-se pular apenas uma versão cuja identidade tenha sido comprovada e rejeitar alterações que exijam substituição não solicitada. O comportamento padrão ainda requer decisão de produto e estratégia de compatibilidade.

A identidade deve incluir dataset, escopo lógico, versão ou hash da fonte, versão do parser e versão das transformações relevantes. Dois arquivos iguais processados por transformações diferentes não são necessariamente a mesma publicação. Hash de bytes demonstra igualdade do conteúdo coletado; não demonstra completude ou equivalência estatística.

### 5.2 Substituição segura

Uma substituição deve primeiro materializar e validar a entrada completa. Somente depois pode remover as linhas do escopo e inserir a nova versão numa mesma transação. Para CNES-ST, escopo inclui UF mesmo quando a partição física contém apenas ano e mês. Apagar a partição física inteira não é uma implementação aceitável de substituição de uma UF.

A validação deve cobrir identidade de todas as linhas, integridade do arquivo, contagens disponíveis e política para vazio legítimo. Se a fonte estiver vazia de forma inesperada, incompleta ou fora do escopo, preservar o estado anterior. Uma queda expressiva de contagem pode gerar revisão, mas um limiar arbitrário de variação não substitui a definição de completude da fonte.

Lakes existentes sem proveniência não devem ser declarados idempotentes retroativamente. Precisam de inventário: quais escopos podem ser identificados, quais foram repetidos e quais podem ser reconstruídos. Não se deve aplicar `DISTINCT` indiscriminado para remover supostas duplicatas de dados de saúde; registros iguais nas colunas disponíveis podem representar eventos distintos.

### 5.3 Concorrência e estado durável

As tabelas de usuário do DuckLake não oferecem PRIMARY KEY ou UNIQUE. A documentação de conflitos também permite que inserções concorrentes em tabela existente sejam confirmadas. Logo, consultar um manifesto e inserir se não houver registro permite corrida entre escritores; isolamento por snapshot não equivale a exclusividade de escopo.[^constraints][^conflicts]

No cenário local, a política inicial pode exigir exclusividade de escrita por lake, com detecção de uma segunda execução antes de mutar dados. Essa garantia tem alcance definido: clientes que usam a biblioteca. SQL externo e ferramentas que ignoram o protocolo ficam fora dela. Para cloud, é necessário desenhar coordenação durável e recuperação de posse; apenas adicionar um lease com expiração deixa o problema do escritor atrasado sem solução.

Se o manifesto for interno, publicações confirmadas e dados podem compartilhar a transação DuckLake. Tentativas fracassadas precisam de registro posterior ao rollback, pois desapareceriam se registradas somente na transação abortada. Se o controlador for externo, seu estado e o commit do lake não formam automaticamente uma transação única; é obrigatória uma estratégia de reconciliação de confirmação perdida.

## 6. Schemas e visão CNES

### 6.1 Evolução sem perda de valores

A05 demonstrou que a ordem de chegada pode determinar schema e arredondamento na API. A correção deve definir tipos aceitos por dataset e regras de compatibilidade antes de inserir. A ausência de erro de SQL não é prova de preservação numérica.

O DuckLake documenta promoções sem perda, como ampliação de inteiros e de float32 para float64. Essa lista não autoriza qualquer conversão entre famílias. Promover automaticamente inteiros de 64 bits para double também pode perder exatidão. A alternativa conservadora é rejeitar mudanças sem regra comprovada e encaminhá-las a migração explícita ou representação canônica definida pelo domínio.[^schema]

Arrow oferece opções de cast que controlam overflow e truncamento. Elas são candidatas para validar conversões antes da escrita, com testes na versão 24 instalada. A implementação deve verificar o valor final armazenado, incluindo inteiros grandes, decimais, nulos e códigos com zeros iniciais; conferir apenas o dtype não basta.[^arrowcast]

Os dicionários YAML precisam declarar o seu papel: descrição de dados brutos, contrato canônico ou ambos em estruturas separadas. Ativar todas as transformações descritas no YAML durante ingestão alteraria o produto de dados. A primeira entrega deve estabelecer a fronteira e corrigir discrepâncias relevantes, preservando dados brutos quando esse for o contrato escolhido.

### 6.2 Última linha ou último valor não nulo

A11 mistura atributos de competências distintas porque calcula máximos por coluna. Se a visão representa o último snapshot, a seleção deve escolher uma linha inteira da competência mais recente e preservar seus nulos. Um empate na mesma competência precisa de regra determinística de versão ou de rejeição, não de ordenação incidental.

Se o produto desejado for “último valor conhecido de cada atributo”, essa é outra visão, com referência temporal por atributo. A documentação atual favorece a primeira interpretação. O aceite deve incluir um registro mais recente com NULL e confirmar que nenhum atributo antigo foi apresentado como pertencente à última competência.

## 7. Manutenção, URIs e SQL

A09 deve ser dividido em compactação, expiração de snapshots, remoção física e resultado da CLI. A documentação oferece `ducklake_merge_adjacent_files` para unir arquivos. Expirar snapshots altera o histórico disponível; remover arquivos posteriormente libera armazenamento. Essas operações não são equivalentes e não devem ser escondidas sob uma descrição genérica de vacuum.[^merge][^expire]

A limpeza utiliza um instante de corte, como o resultado de subtrair uma duração de `now()`, e oferece simulação. Arquivos deixam de ser necessários para snapshots retidos antes de serem removidos; consultas ainda ativas precisam ser consideradas. A política deve definir separadamente retenção histórica e margem para leitores. Não se recomenda um prazo universal nem remoção irrestrita como padrão.[^cleanup]

Os testes devem verificar assinatura na extensão suportada, preservação de dados atuais, histórico retido e saída não zero quando a manutenção falha. Simulação não pode alterar o lake. Backup e restauração precisam ser verificados antes de qualquer migração ou limpeza irreversível em dados reais; aqui isso é critério operacional futuro, não ação executada.

Para A10, separar a configuração do catálogo da configuração do armazenamento evita reconstruir uma URI composta de forma ambígua. A compatibilidade com o formato atual pode ser mantida por um parser de borda. Parâmetros originais do catálogo, incluindo valores escapados, devem sobreviver; mensagens e erros precisam ocultar credenciais.

Para A12, centralizar composição de SQL: parâmetros para valores quando suportados; escape de identificadores e literais nas posições que não aceitam binding. DuckDB documenta identificadores entre aspas duplas e duplicação de aspas internas. Não se deve presumir que placeholders resolvam identificadores ou toda instrução ATTACH.[^identifiers][^parameters]

O aceite deve incluir caminho `D'Avila`, espaços, identificador reservado, aspas e URI com query preexistente. A evidência original demonstra quebra com entrada legítima, não exploração remota; a prioridade não deve ser inflada por uma ameaça não demonstrada.

## 8. Memória e desempenho

O fluxo atual mantém bytes DBC, materializa DBF e acumula frames antes de produzir o LazyFrame. A fila limita quantidade de itens; a documentação de `asyncio.Queue` não atribui a esse limite um orçamento de bytes. Por isso, aumentar concorrência pode elevar bastante o pico de memória.[^queue]

A evolução candidata é gravar batches de registros em staging Parquet sem acumular todos os frames. `ParquetWriter` oferece escrita de RecordBatch; o schema precisa estar determinado ou reconciliado antes de finalizar os arquivos. Essa mudança reduz uma parcela da memória, mas não torna a descompressão DBC incremental se a dependência continuar devolvendo DBF completo.[^parquet]

O benchmark deve separar download, descompressão, parsing, staging e inserção. Medir pico de RSS, bytes em trânsito, espaço temporário e linhas por segundo em arquivos pequenos, grandes e de famílias distintas. Comparar com concorrência 1 e com a configuração atual, usando o mesmo conjunto de arquivos e hashes.

O critério de sucesso é preservar dados e reduzir o recurso limitante no cenário escolhido. Sem volume alvo, orçamento de memória e máquina de referência, não é responsável prometer capacidade nacional ou ganho percentual. Essa frente deve gerar seu próprio desenho depois que as garantias de correção estiverem estáveis.

## 9. Sequenciamento proposto

| Entrega | Escopo e arquivos candidatos | Dependência | Evidência para encerrar |
|---|---|---|---|
| D0 — Contratos e compatibilidade | Tipos de resultado, política de writer, matriz DuckDB/extensão e consumidores existentes | Decisão de cenário | Contratos aprovados e capacidades necessárias identificadas |
| D1 — Transações e resultados | `sources/datasus_ftp/_runner.py`, `sources/_base.py`, `lake/operations.py`, `sources/cnes/importers/master.py`, CLI | D0 | A01/A04/A06/A08 com regressões e controles de commit |
| D2 — Produto populacional | `sources/ibge/`, dicionário IBGE, documentação | Contrato de produto; D1 para publicação confiável | Fonte e período corretos, vazio rejeitado, proveniência verificável |
| D3 — Entradas e manutenção | `lake/catalog.py`, `lake/connection.py`, manutenção em `operations.py`, CLI | Matriz de capacidades; D1 quando compartilhar fronteira transacional | A09/A10/A12 e simulação sem mutação |
| D4 — Tipos e visão CNES | Reconciliação de schema, transformações pertinentes e `ensure_aux_cnes_view` | D1 e decisões de dados brutos/canônicos | Valores preservados nas duas ordens; última linha coerente |
| D5 — Reprocessamento | API de escopo e controlador/proveniência na camada escolhida | D1, validação de fontes e schemas | Repetição, substituição, isolamento e recuperação demonstrados |
| D6 — Escala | Fetch, parser e staging | Base funcional estabilizada | Benchmark reproduzível e orçamento de recursos documentado |

D2 e partes de D3 podem avançar independentemente depois que seus contratos forem definidos. D5 não deve anteceder a validação de entrada: substituir dados antes de corrigir vazios e schemas aumenta o risco de perda. D6 não deve atrasar as correções P1.

Não há estimativa de calendário confiável sem cenário operacional e responsáveis. A sequência utiliza condições de entrada e saída para evitar precisão artificial. Cada entrega arquitetural deve ter especificação própria; concentrar todos os assuntos em uma única implementação dificultaria revisão, reversão e atribuição de falhas.

## 10. Matriz de verificação adversarial

| Cenário | Resultado exigido |
|---|---|
| Um DBC inválido | Um resultado failed; nenhuma linha; CLI não zero |
| Válido, inválido e válido com lote de dois | Nenhum escopo omitido; lote revertido claramente identificado; progresso posterior coerente |
| Erro depois de ADD COLUMN | Rollback confirmado; novo uso do mesmo handle funciona com catálogo real |
| Erro no COMMIT | Sem publicação de sucesso; erro original preservado; estado desconhecido explicitado quando necessário |
| Refresh CNES falha entre remoção e inserção | Registro anterior permanece |
| Snapshot em transação externa | Comprovante capturado após commit, sem atribuir snapshot anterior |
| Outra conexão confirma entre commit e leitura do recibo | Exclusividade impede a corrida, ou identificação persistida permite reconciliar |
| Cancelamento com fila cheia | Encerramento limitado e sem perda de lotes já confirmados |
| Ano ausente no produto IBGE | Indisponibilidade explícita; nenhum sucesso vazio |
| Censo 2010 com categorias extras | Somente totais solicitados; duplicação de município detectada |
| Produto publicado em 2023 | Origem censitária e referências temporal/territorial preservadas |
| Substituição com entrada vazia ou incompleta | Dados anteriores intactos |
| Substituição de uma UF em partição compartilhada | Outras UFs intactas |
| Mesma versão processada duas vezes | Resultado conforme política aprovada; contagem estável se modo idempotente |
| Dois escritores no mesmo escopo | Exclusão ou resolução demonstrada; manifesto sem duplicidade lógica |
| Commit confirmado e resposta perdida | Reconciliação evita append duplicado |
| Inteiros/fracionários nas duas ordens | Sem arredondamento silencioso; conversão recusada quando não segura |
| Inteiro além da representação exata de double | Exatidão preservada ou rejeição explícita |
| Última competência CNES com NULL | Atributos pertencem à mesma linha temporal |
| URI com parâmetros e caminho com apóstrofo | Conexão preserva configuração e aceita caminho válido |
| Manutenção em dry-run | Inventário sem alteração; execução posterior preserva dados e histórico contratados |

Os testes devem comparar valores persistidos, resultados públicos e estado após falha. Mocks ajudam a provocar falhas de rede, mas não substituem integração real com DuckLake para DDL, COMMIT, snapshot e manutenção. Fixtures HTTP versionadas tornam os testes IBGE determinísticos; consultas oficiais periódicas podem verificar mudanças de contrato sem tornar toda a suíte dependente da internet.

Os 386 testes históricos e a cobertura de 91,28% são contexto, não critério suficiente de aceite dessas entregas. A suíte deve ganhar regressões para os comportamentos comprovados; após cada alteração, executar os testes relacionados e os checks exigidos pelo projeto. Novas medições precisam registrar commit, hashes dos arquivos envolvidos, versões e seleção de testes, corrigindo a falha de proveniência do relatório inicial.

## 11. Compatibilidade, migração e reversão

Mudanças aditivas no resultado e nos metadados devem preservar os consumidores existentes quando possível. Alterar o significado de `snapshot_id`, trocar o produto populacional ou modificar a política padrão de repetição exige notas de migração claras. Não atribuir automaticamente proveniência a cargas antigas cuja origem não possa ser reconstruída.

Para schemas incompatíveis ou novo produto populacional, preferir criar e validar o destino novo antes de trocar a visão de consumo. Conferir contagens, chaves e valores com o destino anterior, reconhecendo que mudanças legítimas de fonte podem impedir igualdade simples. A reversão consiste em restabelecer o caminho de leitura anterior enquanto os dados antigos ainda estiverem disponíveis.

Mudanças de extensão ou formato de catálogo devem ter teste de abertura, leitura e restauração em cópia. Reverter o pacote Python não garante que uma versão anterior da extensão consiga abrir um catálogo migrado. Expiração e limpeza física só entram depois da janela de validação acordada.

## 12. Decisões necessárias para a especificação

O cenário foi decidido: evolução incremental, com um escritor por lake na primeira etapa. Essa escolha determina o alcance de exclusividade, os testes de snapshot e o mecanismo de retomada. A fronteira deve permitir coordenação externa no futuro, sem prometer agora reprocessamento concorrente distribuído.

Na sequência, a especificação deve decidir o comportamento de erro/continuação de lotes e a compatibilidade dos resultados públicos. Em subprojetos posteriores, decidir o produto populacional desejado, o padrão de repetição, a responsabilidade pela proveniência e a política de tipos. Retenção histórica e orçamento de memória devem ser definidos antes das respectivas entregas, sem bloquear os reparos transacionais.

O primeiro desenho a revisar é, portanto, D1: preservar a API de ingestão de baixo nível, contabilizar todos os escopos, confirmar resultados somente após commit, invalidar cache após rollback e tornar refresh CNES atômico. Sua aprovação permite escrever uma especificação pequena e verificável; as outras frentes continuam como propostas independentes.

## Fontes

As fontes externas abaixo são primárias. Foram consultadas em 9 de setembro de 2026; links `stable` podem evoluir. Metadados de 793 e 6579 estão preservados na evidência da auditoria; metadados de 202 e 4714 foram consultados diretamente nesta pesquisa e arquivados em [research-sources.json](/Users/raphael/PycharmProjects/omnisus-db/reports/evidence/2026-09-09/research-sources.json), junto às referências adicionais verificadas. Os links imutáveis do DuckLake identificam o código da extensão auditada.

[^transactions]: DuckLake, [Transactions](https://ducklake.select/docs/stable/duckdb/advanced_features/transactions). Atomicidade de DDL e dados, isolamento e fronteira de commit.
[^catalog]: DuckLake, [Choosing a Catalog Database](https://ducklake.select/docs/stable/duckdb/usage/choosing_a_catalog_database). Catálogos locais e remotos.
[^versions]: DuckLake, [Release Calendar e matriz de compatibilidade](https://www.ducklake.select/release_calendar). Associação documentada de DuckDB 1.5.2, extensão e especificação 1.0.
[^ducklake-commit]: DuckLake, [commit 415a9ebdbd73db50a8c6ba703eb733ed16bcf33a](https://github.com/duckdb/ducklake/commit/415a9ebdbd73db50a8c6ba703eb733ed16bcf33a). Identidade resolvida pela API pública oficial do GitHub.
[^snapshots]: DuckLake, [Snapshots](https://ducklake.select/docs/stable/duckdb/usage/snapshots). Funções de snapshot e metadados de commit; semântica refinada pelos testes do commit abaixo.
[^snapshot-code]: DuckLake, [implementação de last_committed_snapshot no commit auditado](https://github.com/duckdb/ducklake/blob/415a9ebdbd73db50a8c6ba703eb733ed16bcf33a/src/functions/ducklake_last_committed_snapshot.cpp).
[^snapshot-test]: DuckLake, [teste oficial ducklake_last_commit.test](https://github.com/duckdb/ducklake/blob/415a9ebdbd73db50a8c6ba703eb733ed16bcf33a/test/sql/snapshot_info/ducklake_last_commit.test). Demonstra leitura do valor alterado por outra conexão do mesmo catálogo.
[^snapshot-state]: DuckLake, [estado e acesso ao último snapshot em DuckLakeCatalog](https://github.com/duckdb/ducklake/blob/415a9ebdbd73db50a8c6ba703eb733ed16bcf33a/src/include/storage/ducklake_catalog.hpp).
[^constraints]: DuckLake, [Constraints](https://ducklake.select/docs/stable/duckdb/advanced_features/constraints). Restrições disponíveis para tabelas de usuário.
[^conflicts]: DuckLake, [Conflict Resolution](https://ducklake.select/docs/stable/duckdb/advanced_features/conflict_resolution). Conflitos lógicos e repetição de commits concorrentes.
[^schema]: DuckLake, [Schema Evolution, documentação estável 1.0](https://ducklake.select/docs/stable/duckdb/usage/schema_evolution). Promoções sem perda; a entrega deve verificar a matriz na extensão alvo.
[^merge]: DuckLake, [Merge Adjacent Files](https://ducklake.select/docs/stable/duckdb/maintenance/merge_adjacent_files). Função de compactação e preservação de histórico.
[^expire]: DuckLake, [Expire Snapshots](https://ducklake.select/docs/stable/duckdb/maintenance/expire_snapshots). Expiração do histórico, simulação e relação com limpeza.
[^cleanup]: DuckLake, [Cleanup of Files](https://ducklake.select/docs/stable/duckdb/maintenance/cleanup_of_files). Instante de corte, leitores ativos e remoção de arquivos.
[^identifiers]: DuckDB, [Keywords and Identifiers](https://duckdb.org/docs/stable/sql/dialect/keywords_and_identifiers). Identificadores delimitados e escape.
[^parameters]: DuckDB, [Prepared Statements](https://www.duckdb.org/docs/current/sql/query_syntax/prepared_statements). Parâmetros de valores; não fundamenta binding de identificadores ou de toda DDL.
[^asyncio]: Python 3.12, [Coroutines and Tasks](https://docs.python.org/3.12/library/asyncio-task.html). Cancelamento, limpeza e TaskGroup.
[^queue]: Python 3.12, [Queues](https://docs.python.org/3.12/library/asyncio-queue.html). `maxsize` limita quantidade de itens.
[^arrowcast]: Apache Arrow, [CastOptions](https://arrow.apache.org/docs/python/generated/pyarrow.compute.CastOptions.html). Controle de overflow e truncamento; documentação consultada 25.0.1.
[^parquet]: Apache Arrow, [ParquetWriter](https://arrow.apache.org/docs/python/generated/pyarrow.parquet.ParquetWriter.html). Escrita de batches; documentação consultada 25.0.1.
[^ibge793]: IBGE, [metadados do agregado 793](https://servicodados.ibge.gov.br/api/v3/agregados/793/metadados) e [períodos](https://servicodados.ibge.gov.br/api/v3/agregados/793/periodos). Respostas preservadas em [ibge-responses.json](/Users/raphael/PycharmProjects/omnisus-db/reports/evidence/2026-09-09/ibge-responses.json).
[^ibge6579]: IBGE, [metadados do agregado 6579](https://servicodados.ibge.gov.br/api/v3/agregados/6579/metadados) e [períodos](https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos). Mesma evidência arquivada, incluindo lacunas na série.
[^ibge202]: IBGE, [metadados do agregado 202](https://servicodados.ibge.gov.br/api/v3/agregados/202/metadados). Censo, variável 93, classificações 1 e 2 com total 0.
[^ibge4714]: IBGE, [metadados do agregado 4714](https://servicodados.ibge.gov.br/api/v3/agregados/4714/metadados). Censo 2022, nível municipal e variável 93.
[^ibge2023]: IBGE, [Relação da População dos Municípios para publicação no DOU em 2023 — Nota metodológica n. 01](https://www.ibge.gov.br/biblioteca/visualizacao/livros/liv102024.pdf), capa e páginas 6–7. Origem censitária, segunda apuração e referência territorial.
[^ibge2023-page]: IBGE, [Relação da População dos Municípios para publicação no TCU](https://www.ibge.gov.br/estatisticas/sociais/populacao/37734-relacao-da-populacao-dos-municipios-para-publicacao-no-tcu.html). Contexto da publicação e formulação da referência populacional; a nota metodológica é a referência específica da edição analisada.
