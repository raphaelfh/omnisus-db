# Consumo dos metadados

A biblioteca fornece `describe_dataset`, `display_row` e `analytical_projection`.
Elas funcionam offline com os recursos do wheel. Consultar metadados não abre um
lake nem baixa documentos. O contrato resolvido é `1.0.0`; a versão editorial do
dicionário e a versão da regra analítica são informações separadas.

## Definições e apresentação

```python
import omnisus_db as odb

metadata = odb.describe_dataset("sim_obitos")
sexo = next(item for item in metadata["fields"] if item["field"]["name"] == "sexo")
print(sexo["field"]["logical_type"])
print(sexo["claims"])
print(metadata["metadata_hash"])
print(odb.display_row("sim_obitos", {"idade": "469", "sexo": "2"}))
```

Cada chamada devolve dados independentes. `fields` contém documentos por coluna,
com referências resolvidas e estados de revisão; `schema.fields` preserva as
definições de autoria para consumidores de apresentação. Tipos legados são
**descritivos**: nenhum deles autoriza cast ou recodificação automática.
`display_row` retorna rótulos e preserva valores não interpretáveis; não usar seu
texto para calcular idades. SIH exige `cod_idade` e `idade` na mesma linha.

`physical_type` descreve o documento de origem, com comprimento desconhecido como
`null`. O tipo SQL efetivo vem de `DESCRIBE` no snapshot da consulta. Os valores
originais do lake continuam preservados.

## Projeções para análise

A edição inicial confirma apenas os arquivos SIM/SIH identificados por escopo,
modalidade e SHA-256 em `metadata["analytics"]["validated_sources"]`. Outro arquivo,
mesmo da mesma UF/ano, não herda automaticamente a interpretação. A função não
consulta o lake: o chamador deve fornecer schema e identidades do mesmo snapshot,
verificando que as publicações representam todas as linhas dos escopos selecionados.

```python
import omnisus_db as odb

target = "ducklake:./data/omnisus-v2.ducklake"
with odb.LakeReader(target, snapshot_id=5) as reader:
    con = reader.connect()
    schema = {row[0]: row[1] for row in con.sql("DESCRIBE lake.sim_obitos").fetchall()}
    publications = [row for row in reader.publications()
                    if row["dataset"] == "sim_obitos" and row["active"] and row["managed"]]
    contexts = [odb.SourceContext.from_publication(row) for row in publications]
    projection = odb.analytical_projection("sim_obitos", observed_schema=schema, scopes=contexts)
    print(projection.rule_version, projection.metadata_hash)
    print(projection.unavailable)
```

Depois de verificar a cobertura do manifesto, o consumidor compõe uma subconsulta
com `DerivedColumn.expression AS DerivedColumn.name`. Os nomes de origem são
resolvidos/escapados pela biblioteca. Filtros de usuário continuam vinculados por
parâmetros na consulta do consumidor. As expressões executam em SQL nativo, sem
UDF Python por registro e sem criar views persistentes.

As colunas disponíveis são `idade_anos_completos`, `idade_status`, `sexo_categoria`,
`sexo_status`, `<campo>_data` e `<campo>_data_status`. Estados distinguem `valid`,
`missing`, `ignored`, `invalid` e `unsupported`; nenhum deles deve virar zero por
conveniência. `SIM 400` significa zero anos completos com precisão menor de um ano,
não zero dias. Faixas etárias pertencem ao relatório.

Versão analítica solicitada e ausente gera erro. Colisão de nome derivado também.
Campo obrigatório ausente, dataset sem regra e contexto não confirmado retornam
indisponibilidade. `x-display` não indica capacidade analítica. Para reproduzir
resultados, fixar snapshot, versão do pacote/artefato, `rule_version` e
`metadata_hash`. Metadata hash deve ser conferido antes de reaplicar um preset.

## Fontes, limitação e auditoria

O registro canônico está em `src/omnisus_db/data/dicionarios/sources/registry.json`.
`docs/dicionario/fontes/registro.json` é gerado dele. Definições e revisões de campo
ficam nos YAMLs. Uma alteração de valor revisado exige atualizar sua evidência e
hash; referências inexistentes geram erro. Campo sem revisão não ganha aprovação
por estar no pacote.

A auditoria do snapshot 5, com SQL e agregados, está em
`reports/evidence/2026-09-14/contrato-analitico/`. A referência SIH `DT_INTER` possui
grafia/formato inconsistente no manual; o contrato registra o conflito e restringe
a interpretação ao recorte conferido. Idades SIH fora do domínio explicitamente
suportado ficam `unsupported`, incluindo `IDADE=999` sob unidade válida.

```bash
python scripts/metadados/consultar.py --dataset sim_obitos --field sexo --json
python scripts/metadados/consultar.py --dataset sih_aih_reduzida --field dt_inter --arrow
python scripts/metadados/auditar_contrato.py --target ducklake:./data/omnisus-v2.ducklake --snapshot-id 5 --out ./reports/audit --acceptance-only
```

O script de consulta valida o documento e pode demonstrar transporte Arrow/Parquet
em tabela vazia. `--metadata arquivo.json` valida um exemplo arquivado. O exemplo
histórico `0.1.0-draft` permanece legível; não é fonte de produção. Não há transporte
automático de metadados em toda consulta/exportação: para SQL/CSV guardar o JSON e a
identidade da regra no contrato da consulta.

## Migração e limpeza

Use a interface pública em vez de importar o carregador interno. `Dicionario`
continua interno para ingestão/apresentação; `Dicionario.arrow_schema` foi removido,
pois não descrevia o lake e não tinha consumidor de produção. Helpers Polars de
`transforms.codes` usados apenas por testes também foram removidos.
`x-normalization-hint` substitui a antiga anotação `x-transform: lpad_6` e não executa
normalização. A ingestão física e seu schema Arrow continuam implementados.

A ampliação da aplicabilidade a outros arquivos e a curadoria dos demais campos
permanecem trabalho explícito. O contrato não declara validadas todas as bases.
