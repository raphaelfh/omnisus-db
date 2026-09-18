# Estrutura recomendada

## Escolha

| Alternativa | Manutenção | Consumo | Decisão |
| --- | --- | --- | --- |
| Markdown por campo | Fácil de ler; difícil validar e sincronizar | Exige extrair texto | Gerar apenas como documentação |
| YAMLs independentes em `docs` e `src` | Duas definições podem divergir | Consumidor precisa escolher | Evitar |
| YAML empacotado + registros de fontes/domínios + projeções geradas | Uma edição, validação e histórico Git | JSON resolvido e metadados por coluna | **Adotar** |
| Banco remoto obrigatório para consultar descrições | Exige serviço e disponibilidade | Acrescenta rede ao uso da lib | Não necessário nesta etapa |

O carregador atual já usa `src/omnisus_db/data/dicionarios/*.yaml` para tipos,
partições e decodificações, preservando propriedades adicionais em `raw` e
`fields`. Estender essa base evita um segundo catálogo manual. O
[Table Schema da Frictionless](https://specs.frictionlessdata.io/table-schema/)
permite propriedades adicionais e distingue representação física e lógica.
As extensões `x-*` abaixo são convenções propostas pelo omnisusdb, não campos
padronizados pela Frictionless.

## Organização atual destes documentos

```text
docs/dicionario/
  index.md                    # entrada e estado de implementação
  estrutura.md                # decisão e layout de destino
  contrato.md                  # semântica e regras do contrato
  manutencao.md                # atualização e double check
  consumo.md                  # exemplos e roteiro de integração
  catalogo.md                  # gerado a partir da auditoria
  cobertura.csv               # gerado a partir da auditoria
  campos.csv                  # colunas observadas + definições locais pendentes
  fontes/registro.json         # inventário gerado das evidências baixadas
  schemas/column-metadata.schema.json
  exemplos/sim_obitos.sexo.json    # exemplo do contrato, fora da produção

scripts/metadados/
  consultar.py                # CLI experimental de validação e consumo
  atualizar_catalogo.py       # geração das projeções da auditoria
  README.md                   # comandos e dependências

notebooks/
  metadados_cli.py             # demonstração interativa dos comandos
```

Scripts executáveis ficam em `scripts/metadados/`; `docs/dicionario/` contém
documentação, contratos e exemplos declarativos. Os caminhos internos dos
scripts são resolvidos a partir do repositório, sem depender do diretório atual.
As definições de produção continuam em `src/omnisus_db/data/dicionarios/`.

O registro inicial das fontes é uma projeção da auditoria. Não editar seus
números manualmente: o script preserva URLs e hashes e pode conferir os arquivos
locais. O exemplo JSON é um caso de referência para o contrato; não deve virar
uma segunda definição de produção de `sim_obitos`.

## Organização de destino na biblioteca

Este layout é proposto para a etapa de integração; os novos diretórios abaixo
ainda não são carregados pela biblioteca.

```text
src/omnisus_db/data/dicionarios/
  sim_obitos.yaml                 # seleção da edição padrão + schema atual
  ...                         # demais produtos existentes
  editions/sim_obitos/<versao>.yaml  # edições imutáveis quando houver diferenças
  sources/<source-id>.yaml    # uma revisão exata de documento oficial
  codelists/<dominio>/<versao>.yaml # listas grandes ou reutilizadas
  schemas/                    # contratos de autoria e exportação

docs/dicionario/gerado/
  datasets/<dataset-id>/<versao>.md
  fontes.md
  cobertura.csv
```

No destino, o registro canônico de fontes será empacotado em `sources/`; o
registro em `docs` será gerado dele. Ao migrar, importar as 14 evidências da
auditoria uma vez e mudar o gerador, em vez de manter os dois registros editáveis.
Validar a inclusão dos recursos no wheel e na instalação fora do checkout.

## Unidade de edição e identidade

Um YAML por produto e edição agrupa campos que mudam juntos e mantém revisões
legíveis. Não criar inicialmente 1.326 arquivos pequenos. Domínios e fontes
usados em vários campos ficam separados e são referenciados por IDs versionados.

| Identidade | Exemplo | Regra |
| --- | --- | --- |
| Categoria do portal | `SIM` | Serve para descoberta |
| Produto/tabela | `sim_obitos`, origem `SIM/DO/DORES` | Não confundir com outro produto da categoria |
| Campo | `sim_obitos.sexo` | Estável dentro do produto, não global por grafia |
| Nome físico | `SEXO` | Nome no arquivo de origem |
| Nome exposto | `sexo` | Nome usado pela lib; aliases explícitos |
| Edição dos metadados | `1.0.0` | Identifica conteúdo congelado, não o ano dos dados |
| Revisão da fonte | `sim-b4195ac8e0f8` | Identifica bytes pelo SHA-256 completo no registro |
| Recorte de dados | `RR`, 2023, arquivo e hash | Evidência observada, separada da regra documental |

IDs de novos produtos devem seguir o registro de datasets quando ele existir.
No catálogo exploratório, conservar categoria/subtipo/tabela física sem inventar
que há um importador da biblioteca para todos eles. SINASC/DN no portal, por
exemplo, corresponde ao dataset `sinasc_nascidos_vivos` já usado pela lib.

## Camadas de informação

1. **Fonte:** órgão, URL, edição declarada, data de obtenção e hash do documento.
2. **Definição:** significado do campo, tipo, unidade, formato e domínio de códigos.
3. **Evidência:** qual página/trecho sustenta cada afirmação e como foi conferida.
4. **Aplicabilidade:** produto, layout, período e condições em que a regra vale.
5. **Observação:** valores e tipos encontrados em um arquivo real identificado.
6. **Exportação:** JSON resolvido e projeções para docs, Arrow e catálogo SQL.

Valores observados ajudam a detectar divergências; não estabelecem sozinhos o
domínio completo. Um PDF encontrado também não basta para confirmar todos os
campos que ele menciona.

## Versionamento

Separar `schema_version` (formato do contrato), `dictionary_version` (conteúdo
editorial), revisão do documento oficial e período dos dados. Guardar edições
anteriores; uma URL pode permanecer igual enquanto seu PDF muda.

Para o resolvedor futuro, adotar intervalos de aplicabilidade com início inclusivo
e fim exclusivo. Limites `null` só significam intervalo aberto quando o status é
`confirmed`; em `unknown`, significam que a vigência não foi estabelecida.
Recortes sobrepostos com definições diferentes devem produzir conflito explícito,
nunca a seleção silenciosa do documento mais recente.

Mudanças de tipos, transformações ou códigos afetam interpretação e exigem revisão
de compatibilidade. Uma correção apenas bibliográfica pode ter versão editorial
nova sem reprocessar dados. Separar o hash da configuração efetiva de ingestão do
hash completo dos metadados na integração; conferir os hashes de linhagem atuais
antes de mudar a política. Não alterar o comportamento de reprocessamento apenas
por acrescentar uma descrição.
