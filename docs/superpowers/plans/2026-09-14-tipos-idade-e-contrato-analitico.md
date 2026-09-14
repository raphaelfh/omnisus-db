# Tipos, idade e contrato analítico — plano de implementação

> **For agentic workers:** Use `superpowers:executing-plans` para executar uma entrega por vez. As caixas abaixo registram execução, não aprovação. Este documento registra o plano e sua execução; não autoriza por si só publicação, alteração do lake ou criação de tarefas externas.

**Goal:** disponibilizar metadados e valores analíticos confiáveis para SIM e SIH, corrigir o consumo no Omnisus e retirar caminhos obsoletos na mesma sequência de entregas.

**Architecture:** conservar a ingestão física de origem e acrescentar projeções SQL calculadas na leitura. A biblioteca será responsável pelas regras DATASUS, sua evidência, aplicabilidade e versão; o app continuará responsável por consultas, faixas etárias e apresentação. Aproveitar o carregador e o contrato existentes, com uma única definição das regras e sem um framework genérico de transformações.

**Tech Stack:** Python >=3.12, DuckDB/DuckLake, PyArrow, YAML e ferramentas já presentes; backend Python e frontend TypeScript do Omnisus.

**Spec:** relato `../omnisus/docs/architecture/omnisus-db-report-2026-09-14-tipos-e-idade.md`, relativo à raiz deste checkout; contratos em `docs/dicionario/{contrato,consumo,estrutura}.md`; requisitos e decisões explicitados neste plano. O pedido do usuário exige estrutura limpa e ausência de código morto.

## Registro da execução

Implementação da biblioteca em `c51d08d`, branch local `codex/contrato-analitico`.
O wheel 0.3.0 é construído desse commit limpo e identificado por SHA-256.
A integração do app está em `d98a0c9`, branch homônima no outro repositório. As sete
entregas funcionais são registradas aqui; não foram abertas sete PRs remotas.
Recibos, verificações e pendências estão em
`reports/evidence/2026-09-14/contrato-analitico/progress.md`.

A auditoria mantém pendências documentais explícitas: campos sem evidência,
escopos ainda não auditados e os compostos SIH cuja idade exata não foi confirmada.
O aceite do recorte auditado não encerra essas pendências nem autoriza extrapolação.

## Restrições globais

- Planejamento baseado no checkout `ea6c33f` e no snapshot 5 do lake v2; revalidar o estado antes da execução.
- `omnisus-db`: `/Users/raphael/PycharmProjects/omnisus-db`.
- `Omnisus`: `/Users/raphael/PycharmProjects/omnisus`; mudanças nele constituem entrega própria.
- Python `requires-python = ">=3.12"`; preservar suporte existente a 3.12, 3.13 e 3.14 e instalação em Linux, macOS e Windows.
- Não alterar valores, tipos, snapshots nem arquivos do lake existente para resolver apresentação ou análise.
- Não executar coerção em massa guiada por `type` legado. Código categórico continua código, mesmo quando contém somente dígitos na amostra.
- Não introduzir dependências de execução, motor de regras, serviços remotos, UDF Python por registro ou views persistentes para estas entregas.
- Contrato e recursos funcionam offline no wheel instalado fora do checkout.
- Campo desconhecido, regra sem suporte e valor ignorado devem continuar distinguíveis. Ausência de metadados nunca autoriza um cast como idade em anos.
- Dados de produção são consultados somente para auditoria de aceitação; testes de CI usam pequenas fixtures determinísticas.
- Cada PR substitui e remove os caminhos antigos que deixa sem consumidores. Depreciação só quando houver consumidor e compromisso de compatibilidade identificados, com condição concreta de remoção.
- `RELEASE.md` registra distribuição por wheel/tag e decisão de não publicar no PyPI. Preservar essa decisão; corrigir o workflow que tenta publicar por padrão.

## Evidência já obtida

Consultas somente leitura no snapshot 5 confirmaram:

- SIM: 361.228 registros; SIH: 1.646.463 registros.
- As faixas etárias brutas e decodificadas do relato foram reproduzidas.
- SIM: 7.359 registros em 0–4, 159.568 em 75+ e 351 desconhecidos pela regra avaliada. Não há `000` nem `400` nesse snapshot; ambos exigem fixtures próprias.
- SIH: 121.427 registros em 0–4 e 192.798 em 75+; 913.968 registros com `sexo = '3'`, atualmente ignorados na série feminina da pirâmide.
- Listas de campos ausentes e extras conferem. Tipos das partições (`USMALLINT`, `UTINYINT`) são refinamentos físicos de inteiros, não o mesmo problema de `VARCHAR` versus data/número.
- `Dicionario.arrow_schema` não tem consumidor em produção no código examinado; seus consumidores encontrados são testes.
- `transforms/codes.py` contém funções com consumidores encontrados apenas em testes. Antes de remover, ampliar a busca ao app, scripts, notebooks e documentação.
- A biblioteca já guarda hash e URI da origem no manifesto de publicação. Ausência de `_hash_arquivo` na linha não equivale a ausência de proveniência.
- `docs/dicionario/` já propõe o contrato, mas o resolvedor público ainda não existe.

Essas observações identificam um recorte; não validam automaticamente todos os anos, UFs e layouts.

## Decisões de desenho

### Uma fonte de autoria e duas representações

Conservar os YAMLs empacotados como ponto de autoria. Acrescentar somente os metadados necessários ao contrato existente e aos campos tratados. Fontes documentais compartilhadas ficam em um registro empacotado; documentos e CSVs de `docs/dicionario/` são projeções geradas dele. Não manter uma segunda tabela manual de códigos no app ou em JSON de produção.

Separar três informações:

1. Tipo físico declarado no documento/DBF de origem.
2. Tipo lógico descrito pelo dicionário, com estado de revisão.
3. Tipo SQL observado na relação consultada, vinculado ao snapshot.

Não reutilizar `field.physical_type` do protótipo para significar ora o manual, ora o lake. Evoluir a versão do contrato se mudar esse significado.

### Superfície pública pequena

Interfaces implementadas na edição 0.3.0:

```python
def describe_dataset(dataset: str) -> dict[str, object]:
    """Metadados resolvidos, offline, em cópia independente, com versões e hash."""

def display_row(dataset: str, row: Mapping[str, object]) -> dict[str, object]:
    """Apresentação dos valores, preservando bruto sem interpretação conhecida."""

def analytical_projection(
    dataset: str,
    *,
    observed_schema: Mapping[str, str],
    scopes: Sequence[SourceContext],
    rule_version: str | None = None,
) -> AnalyticalProjection:
    """Expressões DuckDB para os campos suportados e motivos de indisponibilidade."""
```

`AnalyticalProjection` será um valor imutável com `columns`, `unavailable`, `rule_version` e `metadata_hash`. Cada coluna terá `name`, `sql_type` e `expression`; cada indisponibilidade terá `field` e `reason`. Não recebe SQL arbitrário do usuário: resolve identificadores contra `observed_schema` e usa `lake/sql.py` para escapá-los. A consulta, os filtros e a conexão continuam pertencendo ao chamador.

`SourceContext` é um valor imutável com `scope: ScopeKey`, `release: str | None` e `source_sha256: str | None`, obtidos do manifesto do snapshot. Reaproveita a identidade de escopo existente, que só contém UF/ano/mês; modalidade e hash não devem ser inferidos desses três campos. `scopes` descreve o conjunto realmente selecionado. Contexto desconhecido permanece desconhecido; nenhuma regra que exija modalidade, origem ou layout confirmado pode ser aplicada sem essa informação.

Escopo vazio, incompleto ou parcialmente não suportado não ganha regra por suposição. A projeção retorna indisponibilidade para o campo afetado. O app pode reduzir o recorte explicitamente e solicitar outra projeção; não pode excluir registros silenciosamente.

`rule_version=None` seleciona a edição empacotada atual e devolve seu identificador efetivo. Versão explicitamente solicitada e ausente falha com erro claro; não cai na versão atual. Inicialmente distribuir somente edições reais, sem criar um resolvedor de versões históricas inexistentes.

### Responsabilidades dos arquivos

| Arquivo | Responsabilidade após a mudança |
| --- | --- |
| `src/omnisus_db/transforms/dictionaries.py` | Carregamento interno, consulta de campos e apresentação; sem schema Arrow hipotético nem regras etárias duplicadas |
| `src/omnisus_db/metadata.py` — novo | Resolver e disponibilizar o contrato público a partir dos recursos empacotados |
| `src/omnisus_db/transforms/age.py` — novo | Semântica etária, resultado estruturado e tradução da mesma definição para cálculo escalar e SQL |
| `src/omnisus_db/transforms/analytics.py` — novo | Montar projeções SQL finitas de idade, sexo e datas, verificar campos e aplicabilidade |
| `src/omnisus_db/data/dicionarios/*.yaml` | Autoria das definições e vínculos com evidências |
| `src/omnisus_db/data/dicionarios/sources/registry.json` — novo | Registro canônico empacotado de fontes, páginas, hashes e revisões |
| `src/omnisus_db/lake/sql.py` | Únicas funções compartilhadas de escape/composição de identificadores |
| `scripts/metadados/{consultar,atualizar_catalogo}.py` | Usar o contrato da biblioteca e gerar documentação; retirar implementação concorrente ao migrar |
| `backend/app/integrations/omnisus_db/metadata.py` no app | Adaptar a interface pública da biblioteca ao contrato do app |
| `backend/app/services/reports.py` no app | Agregar campos analíticos; sem códigos DATASUS nem detecção por `x-display` |

Não criar um arquivo por campo. Só extrair outro módulo quando existir uma responsabilidade independente e um consumidor real.

## Entrega 1 — fechar as regras e reconciliar o inventário

**Arquivos:** YAMLs SIM/SIH; `docs/dicionario/{contrato,consumo,estrutura}.md`; `docs/sources/{sim_obitos,sih_aih_reduzida}.md`; `docs/dicionario/fontes/registro.json`; `scripts/metadados/atualizar_catalogo.py`; criar `scripts/metadados/auditar_contrato.py` e `reports/evidence/2026-09-14/contrato-analitico/`.

**Consome:** relato, documentos oficiais, DBFs/layouts e manifesto do snapshot. **Produz:** regras com evidência e aplicabilidade explícitas; auditoria reproduzível.

- [x] Implementar um comando de auditoria `python scripts/metadados/auditar_contrato.py --target <target> --snapshot-id 5 --out <diretorio>`, usando exclusivamente `LakeReader`. Registrar snapshot, revisão da biblioteca, hashes das publicações, schemas, SQL executado e agregados; não exportar registros individuais.
- [x] Conferir os PDFs SIM anterior/2025, registrando página, trecho, hash e divergência. Verificar separadamente unidades 0–5, `000`, `400`, `9xx` e valores terminados em `99`.
- [x] Buscar fonte oficial SIH para `cod_idade` 0/2/3/4/5/9, regra `100 + valor` e `idade=999`. Comparar unidades e idade com nascimento/internação no recorte sem tratar consistência empírica como autoridade documental universal.
- [x] Para `idade=999`, registrar uma decisão por unidade: ignorada quando sustentado; valor fora do domínio ou regra não suportada quando não sustentado. Não manter silenciosamente a sentinela global só porque o decoder atual a usa.
- [x] Auditar códigos de sexo SIM/SIH e sua vigência. SIM e SIH não compartilham um mapa por terem o mesmo nome de campo. Registrar códigos não binários, ignorados e desconhecidos sem os colapsar indevidamente.
- [x] Classificar cada campo ausente como histórico, não disseminado, metadado da biblioteca ou pendência sem evidência. Listar expressamente os sete campos SIM citados no relato e as cinco colunas de proveniência legadas.
- [x] Incluir `_source_release`, `diagsec1..9` e `tpdisec1..9` no inventário resolvido, com origem e aplicabilidade. Campos sem significado confirmado recebem estado desconhecido, não uma descrição presumida.
- [x] Documentar como obter hash, URI e publicação pelo manifesto e escopo. Não replicar essa informação em toda linha nem prometer linhagem por registro que o manifesto não fornece.
- [x] Corrigir a afirmação “o parser aplica o dicionário” nos dois perfis e a docstring que sugere tipos de ingestão controlados pelo YAML. Distinguir decodificação de apresentação e conversão de dados.
- [x] Salvar o SQL e os números completos da tabela de aceitação abaixo; substituir “igual” pelos valores efetivos.

**Aceite:** todo ponto documental tem evidência identificada ou pendência explícita. Regras sem evidência/aplicabilidade suficiente continuam indisponíveis; sua resolução permanece trabalho aberto, não é marcada como concluída por haver um fallback.

**Limpeza:** remover declarações comprovadamente obsoletas da autoria ativa, preservando histórico/evidências quando pertinentes. Não apagar campos históricos apenas porque não existem no snapshot 5.

## Entrega 2 — contrato público utilizável e remoção do schema fictício

**Arquivos:** criar `src/omnisus_db/metadata.py`, `src/omnisus_db/data/dicionarios/sources/registry.json` e `tests/unit/test_metadata.py`; modificar `transforms/dictionaries.py`, `__init__.py`, YAMLs, scripts e contrato existente; adaptar `tests/unit/transforms/test_dictionaries.py`.

**Consome:** inventário e evidências da entrega 1. **Produz:** `describe_dataset()` público, versão do contrato e hash determinístico.

- [x] Migrar o registro de fontes para o pacote e fazer `docs/dicionario/fontes/registro.json` ser gerado dele. Resolver referências sem acesso à rede; incluir os recursos no wheel.
- [x] Implementar o contrato existente com tipos físicos documentais, tipos lógicos, domínio, ausência, derivação, fontes e aplicabilidade. Preservar os demais campos legados como não revisados. Não exigir curadoria integral de todas as bases para entregar SIM/SIH.
- [x] Corrigir os tipos lógicos sabidamente errados por evidência. Não transformar automaticamente todo `integer` categórico nem alinhar todo YAML ao schema de uma amostra.
- [x] Exportar `describe_dataset` em `omnisus_db.__init__`. Devolver cópias independentes ou valores realmente imutáveis; o `dataclass(frozen=True)` atual não protege listas e dicionários internos.
- [x] Exportar `display_row` a partir da implementação existente em `transforms/dictionaries.py`. Ela encapsula `load_dicionario(dataset).decode_row(dict(row))`; não acrescenta uma segunda implementação de apresentação. Testar ausência de mutação da entrada, contexto SIH completo e pass-through de campo desconhecido. Consumidor que só precisa de rótulo enum passa uma linha com aquele campo; idade SIH exige também sua unidade.
- [x] Exercitar isolamento, empacotamento e preservação de códigos pela interface pública:

```python
def test_metadata_does_not_share_mutable_state():
    import omnisus_db as odb
    original = odb.describe_dataset("sim_obitos")
    changed = odb.describe_dataset("sim_obitos")
    changed.clear()
    assert odb.describe_dataset("sim_obitos") == original
```

- [x] Verificar também que `"01"` e `"1"` continuam distintos, que hashes são estáveis, referências inexistentes falham e que o contrato não declara tipo físico observado sem schema/snapshot.
- [x] Buscar consumidores de `Dicionario.arrow_schema` no pacote, app, notebooks, scripts e documentação. Remover a propriedade, `_TYPE_MAP` e o import de PyArrow se nenhum outro uso restar nesse módulo. Substituir testes que só exercitam a propriedade por testes do contrato real.
- [x] Migrar scripts de consulta ao resolvedor público. Preservar o JSON draft como exemplo histórico identificado; remover validadores/compiladores duplicados que a migração tornar sem uso.
- [x] Rodar `uv run pytest tests/unit/test_metadata.py tests/unit/transforms/test_dictionaries.py` e validar o wheel fora do checkout.

**Aceite:** consumidor consulta os metadados sem caminhos internos ou arquivos em `docs`; nenhuma execução de cast é inferida do `type` legado. Schema físico de ingestão permanece sob `dbf_batches.py`/staging.

## Entrega 3 — idade estruturada e cálculo SQL

**Arquivos:** criar `transforms/age.py`, `transforms/analytics.py`, `tests/unit/transforms/test_age.py` e `tests/unit/transforms/test_analytics.py`; modificar `dictionaries.py`, YAMLs e `__init__.py`.

**Consome:** regras auditadas, metadados públicos e schema observado. **Produz:** `analytical_projection()` e idade calculável em SQL; apresentação derivada da mesma semântica.

- [x] Definir resultado etário estruturado com valor/unidade de origem interpretados, `years_completed` anulável e estado `valid`, `ignored`, `missing`, `invalid` ou `unsupported`. Preservar o bruto no chamador; não converter meses em dias exatos nem usar datas para substituir silenciosamente a idade publicada.
- [x] Modelar regras finitas por produto em uma definição compartilhada. O executor escalar atende à apresentação existente; o SQL atende a milhões de registros. Ambos usam as mesmas unidades, sentinelas e offsets; testes de equivalência detectam divergências entre os dois executores.
- [x] Incorporar ao executor os casos abaixo e os limites efetivamente estabelecidos na entrega 1. Valor não coberto pela evidência recebe `unsupported`, sem inventar um limite clínico:

| Base | Entrada | Anos completos / estado |
| --- | --- | --- |
| SIM | `000` | `NULL / ignored` |
| SIM | `045`, `122`, `229`, `310` | `0 / valid`, preservando unidade |
| SIM | `400` | `0 / valid`, precisão “menor de 1 ano” |
| SIM | `401`, `499`, `500`, `501` | `1`, `99`, `100`, `101`, conforme aplicabilidade |
| SIM | `999` | `NULL / ignored` |
| SIM | vazio, nulo | `NULL / missing` |
| SIM | negativo, caracteres não numéricos, comprimento inválido | `NULL / invalid` |
| SIH | unidade 2 + 30; unidade 3 + 11 | `0 / valid` |
| SIH | unidade 4 + 35; unidade 5 + 2 | `35`, `102`, se regra aplicável |
| SIH | unidade ausente/desconhecida | `NULL`, com motivo explícito |
| SIH | `idade=999` em cada unidade | decisão auditada na entrega 1, sem sentinela presumida |

- [x] Produzir `idade_anos_completos` e `idade_status` como colunas derivadas; incluir a referência à unidade original na derivação. Nome derivado que colide com coluna existente deve gerar erro explícito.
- [x] Reutilizar `lake/sql.py` e validar nomes contra `observed_schema`. Campo obrigatório ausente, versão inexistente e escopo sem aplicabilidade não podem resultar em `TRY_CAST(idade AS INTEGER)` como fallback.
- [x] Migrar `_decode_idade_sim` e `_decode_idade_sih` para apresentação do resultado estruturado e retirar as regras antigas. Preservar pass-through de exibição para bruto não interpretável quando esse for o comportamento contratado; não reutilizá-lo como resultado analítico.
- [x] Testar equivalência escalar/SQL com casos tabelados, limites e entradas malformadas; executar SQL real em DuckDB. Incluir regressão para números fracionários, whitespace, zeros à esquerda e unidades desconhecidas.
- [x] Rodar `uv run pytest tests/unit/transforms/test_age.py tests/unit/transforms/test_analytics.py tests/unit/transforms/test_dictionaries.py`.

**Aceite:** agregação SQL sem UDF por registro, com política de nulos/ignorados explícita; códigos brutos preservados; resultado reproduzível por versão/hash e snapshot. Remover os dois decoders antigos como fontes independentes de regras.

## Entrega 4 — sexo e datas analíticas

**Arquivos:** `transforms/analytics.py`, YAMLs SIM/SIH, `tests/unit/transforms/test_analytics.py`, `docs/sources/{sim_obitos,sih_aih_reduzida}.md` e documentação do contrato.

**Consome:** resolvedor e mecanismo de projeção existentes. **Produz:** `sexo_categoria`, `sexo_status`, `<campo>_data` e `<campo>_data_status` para datas suportadas.

- [x] Acrescentar mapa categórico de sexo por produto/edição, derivado da autoria auditada. Não adicionar outro mapa global SIM/SIH em Python ou no app. Preservar categorias distintas documentadas e estados de ignorado/desconhecido.
- [x] Cobrir `SIM sexo=2` e `SIH sexo=3` como feminino nas regras aplicáveis, e casos masculinos, ignorados, não mapeados e ausentes. Ausência de categoria binária não autoriza descartar o registro da qualidade/denominador.
- [x] Para todos os 11 campos de data SIM e quatro SIH listados no relato, compor conversão por formato declarado e verificado. Exigir oito dígitos e data calendárica válida; usar `TRY_STRPTIME(..., '%d%m%Y' ou '%Y%m%d')::DATE`, com guarda de formato. Fonte já tipada como `DATE` segue caminho compatível sem reinterpretação como string.
- [x] Vazio/nulo produz `missing`; calendário impossível produz `invalid`; sentinela documentada produz `ignored`. Preservar valor bruto e registrar as contagens de conversão não válida.
- [x] Testar ano bissexto válido, `31022024`, zeros, whitespace, texto inesperado, ordenação cronológica e tratamento explícito de `NULL`. Validar o formato de cada campo, incluindo `gestor_dt`, antes de liberar a regra.
- [x] Auditar `transforms/codes.py`. Remover helpers usados somente por seus próprios testes e retirar esses testes, se a busca completa confirmar ausência de consumidores. Não adicionar uma implementação Polars só para justificar sua sobrevivência. Retirar/reclassificar `x-transform` que aparenta execução inexistente, preservando a anotação descritiva pertinente.
- [x] Rodar `uv run pytest tests/unit/transforms/test_analytics.py tests/unit/transforms/test_dictionaries.py tests/unit/sources/datasus_ftp/test_staging.py`.

**Aceite:** datas ordenam corretamente quando o consumidor seleciona a representação tipada; sexo SIH não usa o mapa do SIM; ingestão e bruto não mudaram. Nada é convertido por ter apenas um tipo lógico legado.

## Entrega 5 — integrar o Omnisus e remover heurísticas

**Arquivos no Omnisus:** `backend/app/integrations/omnisus_db/{__init__,metadata}.py`, `backend/app/services/reports.py`, `backend/tests/contract/test_metadata_adapter.py`, `backend/tests/integration/test_reports_queries.py`, `backend/tests/unit/test_reports_service.py`, `backend/tests/contract/test_reports_api.py`; frontend em `src/features/reports/ageAvailability.ts` e `src/features/reports/ReportStates.test.tsx`; contrato de resposta em `backend/app/schemas/` conforme os tipos já existentes.

**Consome:** wheel da biblioteca com metadados e projeções, schema real e escopos selecionados. **Produz:** relatórios corretos e integração por interface pública.

- [x] Usar o wheel candidato durante validação; na entrega final fixar versão/artefato/hash distribuído. Não depender de importação editable de outro checkout.
- [x] Migrar o adaptador de metadados para `describe_dataset`. Remover o acesso interno ao carregador onde substituído e atualizar os testes de contrato do adaptador.
- [x] Migrar consumidores legítimos de `decode_row`/`decode` para `display_row`. Em `_decode_label`, passar o valor bruto e o campo à biblioteca uma vez; remover as tentativas locais com inteiro/string e `_maybe_int` após a busca confirmar seu último uso. Não retirar `Dicionario` interno da biblioteca enquanto a ingestão/apresentação o usam; retirar os imports e reexports internos do app após a migração de todos os seus consumidores.
- [x] Obter projeções no adaptador a partir de schema/escopos reais. Compor subconsulta/CTE com as colunas calculadas e deixar filtros vinculados por parâmetros. Guardar snapshot, versão da regra e hash nos metadados reprodutíveis da consulta/relatório.
- [x] Fazer `_age_group_distribution`, `_age_pyramid` e idade no drill-down usarem `idade_anos_completos`; extrair a definição duplicada das faixas para um único helper local consumido pelos três caminhos. Faixas são política do relatório, não do DATASUS.
- [x] Substituir o mapa binário da pirâmide por `sexo_categoria`. Explicitar contagens excluídas das séries masculina/feminina por outras categorias ou ausência e reconciliá-las com o total filtrado.
- [x] Remover a classificação por `x-display`, os casts diretos de idade codificada e `AGE_CODED_PENDING_UPSTREAM` quando todos os consumidores da versão suportada tiverem migrado. Preservar indisponibilidade funcional com motivos reais: campo ausente, regra não suportada ou escopo não confirmado.
- [x] Impedir regressão em SINASC/`IDADEMAE` e outras bases: idade em anos também exige declaração explícita adequada; ausência de `x-display` não serve como confirmação. Não aplicar regras de SIM/SIH a outros produtos.
- [x] Reativar faixa etária e drill-down quando a regra de idade estiver disponível; reativar pirâmide somente quando idade e sexo estiverem disponíveis. Não deixar um recurso independente bloqueado pela ausência de outro.
- [x] Ajustar schemas e frontend para motivos atuais; gerar tipos pelo mecanismo do projeto e remover textos/branches exclusivos da espera upstream já encerrada.
- [x] Rodar, no backend, `uv run pytest tests/contract/test_metadata_adapter.py tests/integration/test_reports_queries.py tests/unit/test_reports_service.py tests/contract/test_reports_api.py`; no frontend, `npm exec vitest run src/features/reports/ReportStates.test.tsx` e os testes dos componentes modificados.

**Aceite:** todos os números da tabela de aceitação conferem e os 913.968 registros SIH `sexo=3` participam da contabilidade feminina no recorte. Campos ignorados/desconhecidos são contabilizados. Não existe fallback que produz gráfico aparentemente válido por tratar código como anos.

## Entrega 6 — datas no explorador, filtros e exportações

**Arquivos no Omnisus:** `frontend/src/features/explorer/{querySpec,QueryParts,display,api}.ts*`, testes `display.test.ts` e `QueryState.test.tsx`, `backend/tests/integration/test_explorer_contract.py`; localizar o handler real com `rg -n 'ORDER BY|sort|query_spec' backend/app` antes da edição, reutilizando o compilador de consulta existente.

**Consome:** metadados e projeção de datas da biblioteca. **Produz:** seleção coerente de campos brutos e derivados no explorador.

- [x] Expor as datas derivadas como campos selecionáveis com rótulo claro e proveniência; manter a ordenação bruta do campo bruto, conforme o contrato atual do explorador.
- [x] Quando a coluna tipada for selecionada, aplicar ordenação, filtros, paginação e exportação sobre a mesma expressão no backend. Não ordenar somente a página no frontend nem reimplementar parse de data em TypeScript.
- [x] Definir `NULLS LAST` na ordenação das datas derivadas, desempate estável conforme a paginação existente e indicadores para valores inválidos/ignorados.
- [x] Incluir campo/representação, snapshot e identidade da regra no estado reproduzível; links e presets antigos continuam apontando à representação bruta. Não alterar silenciosamente seu significado.
- [x] Testar `02/01/2023` antes de `01/04/2023`, paginação com empates, inválidos e filtros; confirmar equivalência entre resultado exibido e CSV/Parquet exportado. Exportação bruta continua disponível.
- [x] Remover a limitação de ordenação textual somente dos fluxos que passaram a usar data tipada; manter descrição correta da representação bruta.

**Aceite:** usuário consegue ordenar cronologicamente e reproduzir a consulta, com semântica consistente em tela e exportação, sem alteração do snapshot.

## Entrega 7 — release, distribuição e encerramento

**Arquivos:** `CHANGELOG.md`, `RELEASE.md`, `src/omnisus_db/_version.py`, `.github/workflows/{test,release}.yml`, documentos de consumo/migração e dependências/lockfiles do app.

**Consome:** PRs funcionais com testes aprovados. **Produz:** artefato instalável identificado, documentação coerente e consumidor atualizado.

- [x] Corrigir a contradição de `RELEASE.md`: o canal atual é wheel/tag. Alterar `release.yml` para produzir/publicar o artefato no canal adotado e só executar PyPI quando explicitamente habilitado. Não criar Trusted Publisher ou mudar o canal por conta própria.
- [x] Preparar uma versão que inclua a correção SIM já em `Unreleased`, a interface analítica e a migração de caminhos removidos. Documentar que a correção de exibição, isoladamente, não produz idade numérica.
- [x] Não foi necessária uma distribuição parcial: o candidato 0.3.0 inclui a interface analítica e a correção de exibição.
- [x] Construir wheel e sdist, conferir reconstrução byte a byte e testar instalação fora do checkout em Python 3.12/3.13/3.14 no macOS arm64; confirmar recursos de fontes/dicionários e hash do contrato.
- [ ] Executar a matriz remota Linux/macOS/Windows após autorização para push; workflows preparados, resultado remoto ainda não disponível.
- [x] Rodar os checks existentes de lint, tipos e testes para os módulos afetados; executar a suíte geral uma vez na integração final. Não ampliar benchmarks ou matriz Rust sem mudança no decoder/ingestão que justifique isso.

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest -m "not e2e and not perf" --cov=omnisus_db --cov-fail-under=85
```

- [x] Comparar resultado analítico contra a tabela abaixo via `LakeReader(snapshot_id=5)` e registrar SQL/versões. Conferir que contagens e schemas brutos permanecem iguais.
- [x] Revisar diff, imports, referências e exports após as remoções. Não considerar ausência de alerta de lint prova suficiente de ausência de deadcode.
- [x] Preparar versão, notas e artefato revisáveis; fixar app/notebooks no wheel definitivo local e repetir a instalação/relatórios.
- [ ] Criar/push da tag e publicar o candidato no canal adotado somente após autorização. PyPI permanece desabilitado por padrão.
- [x] Atualizar relato e handoff do app com os resultados e pendências reais; remover a frase “basta trocar a fonte” e só encerrar após idade, sexo, datas, metadados, distribuição e limpeza terem aceite.

## Tabela de aceitação no snapshot 5

| Faixa | SIM, anos completos | SIH, anos completos |
| --- | ---: | ---: |
| 0–4 | 7.359 | 121.427 |
| 5–14 | 1.528 | 78.113 |
| 15–24 | 5.807 | 169.855 |
| 25–34 | 10.088 | 236.400 |
| 35–44 | 17.730 | 204.829 |
| 45–54 | 28.934 | 190.941 |
| 55–64 | 51.691 | 226.190 |
| 65–74 | 78.172 | 225.910 |
| 75+ | 159.568 | 192.798 |
| Desconhecida | 351 | 0 |
| Total | 361.228 | 1.646.463 |

Esses números reproduzem as regras avaliadas, não dispensam sua auditoria. Se a evidência oficial exigir outra interpretação, registrar a diferença e sua razão antes de mudar a referência; não ajustar o código apenas para reproduzir o número antigo.

## Lista obrigatória de remoção/substituição

| Candidato | Decisão/condição de remoção |
| --- | --- |
| `Dicionario.arrow_schema`, `_TYPE_MAP`, import de PyArrow exclusivo | Remover na entrega 2 após busca completa por consumidores |
| `_decode_idade_sim`, `_decode_idade_sih` e mapas independentes | Substituir na entrega 3 pelo resultado estruturado e apresentação compartilhada |
| Helpers Polars de `codes.py` usados somente em testes | Remover na entrega 4 se a busca ampliada confirmar; não remover helpers usados por produto real |
| Declarações `x-transform` que prometem execução inexistente | Remover/reclassificar junto da documentação na entrega 4 |
| Carregador interno usado diretamente pelo app | Migrar para metadados/apresentação públicos na entrega 5; retirar imports/reexports internos após último consumidor |
| Cast de idade codificada e detecção por `x-display` | Remover na entrega 5; substituição por capacidades semânticas explícitas |
| Duas expressões CASE das mesmas faixas no app | Unificar no helper local de faixas na entrega 5 |
| Mapa global de sexo da pirâmide | Remover na entrega 5; consumir categoria por produto |
| Motivo `age_coded_pending_upstream` e mensagens correspondentes | Remover após versão mínima do app incorporar o contrato; manter indisponibilidades reais |
| Registros de fontes/compiladores manuais duplicados em `docs` e scripts | Converter em projeções/consumidores da fonte empacotada na entrega 2 |
| Tentativa de PyPI que falha por desenho | Desativar por padrão na entrega 7, coerente com o canal escolhido |

Testes de comportamento migram para a interface substituta. Testes que apenas dão sobrevida a uma função sem consumidor são removidos com ela. Não remover a leitura física Arrow, o carregador usado pela ingestão, o manifesto, o suporte a códigos desconhecidos ou a indisponibilidade legítima.

## Ordem e critério de conclusão

Executar `1 → 2 → 3 → 4 → 5 → 6 → 7`. Preparar o wheel candidato após a entrega 4 para integrar o app; a entrega 7 consolida distribuição definitiva e aceitação ponta a ponta. Cada entrega é um PR revisável; testes, documentação e remoções pertencem ao mesmo PR do comportamento correspondente.

- [x] Todos os itens do relato foram mapeados às entregas 1–7.
- [x] Regra não resolvida permanece explicitamente aberta e não é mascarada por um valor numérico.
- [x] App e notebooks consumidores não precisam importar internals para os caminhos migrados.
- [x] Dados brutos e snapshots preservados; interpretação e sua versão são visíveis.
- [x] Faixas e pirâmide reconciliam com totais incluindo desconhecidos/outras categorias.
- [x] Datas tipadas têm ordenação, filtro e exportação coerentes.
- [x] Wheel distribuído funciona offline fora do checkout; versão final usada pelo app está identificada.
- [x] Nenhum novo helper, wrapper, mapa de códigos, branch de compatibilidade ou recurso empacotado ficou sem consumidor ou finalidade documental explícita.
- [x] Não há implementação antiga ainda executável concorrendo com a nova no mesmo fluxo.

Estimativa de tamanho: sete entregas funcionais, em dois repositórios. O maior fator de incerteza é a evidência/aplicabilidade das regras SIH e a migração dos consumidores de apresentação; não prometer data de conclusão antes da entrega 1 e do inventário de consumidores da entrega 2.
