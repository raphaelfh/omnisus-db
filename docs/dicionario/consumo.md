# Consumo dos metadados

## O que funciona atualmente

O carregador interno já permite consultar as definições existentes:

```python
from omnisus_db.transforms.dictionaries import load_dicionario

dictionary = load_dicionario("sim_do")
field = dictionary.field_def("sexo")
print(field.get("description"))  # pode não estar preenchida
print(field.get("x-decode", {}))
```

Esse caminho é interno e retorna o conteúdo legado, sem garantia de revisão
oficial por campo. Atualmente `Dicionario.arrow_schema` constrói os tipos sem
anexar a proveniência proposta às colunas.

Para explorar todas as colunas amostradas, o [inventário CSV](campos.csv) traz
categoria/tabela/coluna, tipo físico, largura, rótulos e códigos locais, fontes
com menção textual e data da auditoria. `codigos_locais_json` é JSON dentro da
célula CSV; célula vazia significa informação não mapeada. Esses dados legados
continuam identificados como não auditados semanticamente e não satisfazem,
por si só, o contrato de evidência verificada.

## Protótipo executável

O [exemplo JSON](exemplos/sim_do.sexo.json) pode ser lido diretamente por qualquer
consumidor JSON. O [script](exemplos/consumir.py) valida contrato, referências e
hash das afirmações. Também permite anexar o objeto a uma coluna Arrow e
conferir o transporte por Parquet, usando uma tabela vazia: não fabrica dados
de saúde para demonstrar metadados.

Na raiz do repositório, em ambiente com `jsonschema` e `pyarrow`:

```bash
python docs/dicionario/exemplos/consumir.py
python docs/dicionario/exemplos/consumir.py --metadata docs/dicionario/exemplos/sim_do.sexo.json --json
python docs/dicionario/exemplos/consumir.py --arrow
```

`--json` emite exclusivamente o documento validado no stdout, para consumo por
pipes ou outros programas. Falhas de validação retornam código diferente de zero
e diagnóstico no stderr. `--json` e `--arrow` são modos mutuamente exclusivos.
O notebook `notebooks/metadados_cli.py`, no checkout, executa esses comandos e
consultas Python aos CSVs do catálogo, exibindo as saídas reais e filtros por
categoria/tabela/coluna. Não há ainda um comando nativo `omnisus-db metadata`.

Leitura direta, sem depender da API futura:

```python
import json
from pathlib import Path

metadata = json.loads(
    Path("docs/dicionario/exemplos/sim_do.sexo.json").read_text(encoding="utf-8")
)
print(metadata["field"]["description"])
print(metadata["field"]["codes"])
print(metadata["claims"][0]["checked_at"])
print(metadata["sources"][0]["url"])
print(metadata["applicability"]["status"])  # unknown: não confirmar vigência
```

O protótipo só demonstra leitura e transporte. Não recodifica dados nem escolhe
automaticamente uma edição aplicável.

## Contrato de distribuição recomendado

Distribuir um JSON resolvido por dataset/edição com índice por coluna, além de
um arquivo acompanhante `*.metadata.json` junto à exportação de dados. Incluir
versões do contrato e dicionário, identidade do produto e hash dos metadados.
Cada coluna deve poder ser obtida isoladamente no formato deste exemplo.

Para Arrow, usar uma chave de metadado com namespace, `omnisus:column`, cujo
valor é JSON UTF-8. A API oficial aceita metadados em
[campos Arrow](https://arrow.apache.org/docs/python/generated/pyarrow.field.html)
e no [schema](https://arrow.apache.org/docs/python/generated/pyarrow.Schema.html).
Em domínios grandes, anexar uma referência versionada e distribuir a lista
separadamente para evitar repetir milhares de códigos em cada arquivo.

Não presumir preservação em toda transformação. Testar as rotas usadas pela lib
(Arrow → Parquet → Arrow, Polars, DuckDB/DuckLake e consultas SQL). Projeções,
aliases e colunas derivadas precisam de associação explícita à coluna original
ou de metadados de derivação. Para SQL e CSV, o JSON acompanhante e um catálogo
consultável são a referência de transporte; um CSV não carrega metadados por
coluna por si só.

## API pública proposta, ainda não implementada

O formato desejado é uma consulta equivalente a
`describe_dataset(dataset, period=..., dictionary_version=...)`, retornando os
campos, seus estados de revisão e fontes. O nome e a assinatura finais devem
ser definidos na integração. O consumidor deve conseguir:

- consultar metadados offline, sem precisar baixar PDFs;
- fixar uma versão para reproduzir uma análise;
- buscar um campo pelo nome exposto ou físico, sem ambiguidade;
- distinguir informação desconhecida de informação confirmada;
- exigir aplicabilidade confirmada antes de interpretar códigos;
- receber códigos desconhecidos preservados e relatórios de divergência.

Não apresentar `describe_dataset` como função disponível até haver implementação,
exportação pública e testes. A consulta deve devolver cópias ou objetos imutáveis,
evitando que um consumidor altere os dicionários compartilhados pelo cache atual.

## Roteiro de implantação

| Etapa | Entrega | Critério de conclusão |
| --- | --- | --- |
| 1. Contrato e catálogo | Estes documentos, schema, exemplo e inventário | Validação documental e exemplo executável |
| 2. Autoria versionada | Extensões YAML, fontes e domínios empacotados | Migração preserva comportamento legado; nenhuma validação presumida |
| 3. Compilador e resolvedor | JSON determinístico, seleção por produto/edição/período | Referências resolvidas, conflito temporal explícito, recursos no wheel |
| 4. API de consulta | Consulta de dataset/campo e relatório de cobertura | Funciona offline e com versão fixada |
| 5. Transporte | Arrow/Parquet, JSON acompanhante e catálogo SQL | Proveniência preservada ou ausência explicitamente reportada em cada rota |
| 6. Ampliação editorial | Checagem campo a campo, começando pelos produtos já suportados | Cobertura publicada por afirmação e por aplicabilidade |

A etapa 1 está materializada nesta pasta. As demais são trabalho de integração
e curadoria; a existência deste contrato não significa que as 1.326 ocorrências
de colunas já tenham descrição e códigos oficialmente validados.
