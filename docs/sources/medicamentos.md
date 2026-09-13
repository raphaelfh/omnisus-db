# Medicamentos: cobertura, acesso e interpretação

Verificação das fontes públicas: **10 de setembro de 2026**. A necessidade inclui
componente especializado e assistência farmacêutica básica. Nesta entrega, há
ingestão SIA-AM já existente, uma trilha Marimo dedicada e acesso HTTP novo para
observar estoque BNAFAR/Hórus. **Dispensações da assistência básica não estão
integradas.** Nenhuma fonte abaixo deve ser apresentada como substituta equivalente.

| Produto | Unidade observada | Acesso implementado | Limite |
|---|---|---|---|
| SIA-AM / APAC medicamentos | Registro administrativo de APAC | Importação FTP → pipeline comum → DuckLake | Não equivale a dose, retirada efetiva ou pessoa única |
| BNAFAR/Hórus público | Item/lote em posição de estoque | Uma página HTTP filtrada, com bytes e proveniência | Não é dispensação; sem garantia de completude ou cobertura do CBAF |
| Farmácia Popular / MGDI | Indicadores de pessoas atendidas | Fonte identificada e documentada | Sem importador nesta entrega; não representa farmácias municipais |
| BNAFAR/RNDS dispensação | Evento de dispensação descrito nos sistemas | Extração pública não confirmada | API de envio/interoperabilidade não comprova acesso público de leitura |

## Componente especializado: usar o núcleo existente

```python
import omnisus_db as odb

scopes = odb.scopes_for("sia_apac_medicamentos", years=[2024], ufs=["RR"], months=[1])
report = odb.import_dataset(
    "sia_apac_medicamentos", scopes=scopes, target="ducklake:medicamentos.ducklake",
    policy="skip_same", run_id="pesquisa-medicamentos-rr-202401-v1",
)
assert not report.failed  # Examine também skipped; ausência não é publicação.
with odb.Lake.local("ducklake:medicamentos.ducklake") as lake:
    publications = lake.publications(run_id=report.run_id)
```

O exemplo usa o mesmo parser/dicionário, validação, manifesto e publicação das
demais bases. Não introduz outro importador para SIA-AM. Guarde um `run_id` antes
da execução e consulte o manifesto se houver resultado de commit desconhecido.
Ao ampliar períodos, respeite alterações de layout e SIGTAP por competência.

`ap_pripal` identifica o procedimento principal; `ap_vl_ap` é valor aprovado.
Contar linhas mede registros, não pessoas únicas. Somar valores não mede quantidade
dispensada. O arquivo AM e o dicionário atual não sustentam inferir doses ou adesão.
O componente e o procedimento precisam ser classificados com terminologia válida
na competência, sem presumir que qualquer arquivo AM seja uma população CEAF completa.

Referências oficiais: [SIA/SUS](https://wiki.saude.gov.br/sia/index.php/P%C3%A1gina_principal)
e [SABEIS/Conitec](https://www.gov.br/conitec/pt-br/assuntos/noticias/2026/fevereiro/sabeis-libera-acesso-publico-a-dados-do-sus/).
A descrição da SABEIS a vincula à produção SIA/APAC e distingue séries de medicamentos
especializados e quimioterápicos; isso não valida automaticamente cada inferência
possível a partir dos arquivos AM.

## BNAFAR/Hórus: leitura pública de estoque

A [especificação oficial Swagger](https://apidadosabertos.saude.gov.br/static/swagger.json)
consultada declara `/daf/estoque-medicamentos-bnafar-horus`, retorno JSON/CSV,
`limit <= 1000` e `offset` como **número da página**, começando em zero.
Uma consulta `codigo_uf=14&limit=1&offset=0` respondeu HTTP 200, envelope
`{"parametros": [...]}`, com posição de estoque datada de 2026-09-09.
Isso comprova somente aquela leitura, sem validar cobertura histórica/nacional.

```python
from pathlib import Path
import json
from omnisus_db.sources.medicamentos import fetch_stock_page

page = fetch_stock_page(filters={"codigo_uf": "14"}, limit=20, page=0)
Path("estoque-resposta.json").write_bytes(page.raw)
Path("estoque-proveniencia.json").write_text(json.dumps(page.provenance(), indent=2))
assert page.complete is False
```

Filtros aceitos são exatamente os nomes documentados: `codigo_uf`,
`codigo_municipio`, `codigo_cnes`, `anomes_posicao_estoque`, `data_posicao_estoque`,
`codigo_catmat`, `sigla_programa_saude`, `tipo_produto`, `sigla_sistema_origem`.
Use strings para preservar zeros dos identificadores. Não se presume que o servidor
aplicou corretamente cada filtro sem validação de domínio posterior.

O cliente limita bytes descomprimidos, rejeita envelopes inesperados e propaga
erros HTTP. Guarda URL com parâmetros, horário UTC, SHA-256 dos bytes recebidos,
página e limite. Uma resposta vazia/curta mantém `complete=False`. Não pagina
automaticamente nem publica no lake: falta contrato de snapshot e completude
para substituir um recorte sem risco. Repetir offset pode observar uma base alterada.

Estoque não pode ser somado entre datas como consumo. Programas, apresentações,
unidades de fornecimento e lotes precisam de interpretação antes de agregações.
Registro ausente não significa estoque zero ou falta de dispensação.

## Assistência básica: lacuna delimitada

A [página BNAFAR](https://www.gov.br/saude/pt-br/composicao/sectics/daf/bnafar)
descreve consolidação de estoques, movimentações e dispensações de múltiplos
sistemas. A [FAQ oficial](https://www.gov.br/saude/pt-br/composicao/sectics/daf/bnafar/faq/faq)
descreve SI-BNAFAR como serviço de **envio** pelos gestores. Não usar esse endereço
como se fosse endpoint de extração nacional para pesquisadores.

O [catálogo MGDI/Farmácia Popular](https://dadosabertos.saude.gov.br/dataset/mgdi-programa-farmacia-popular-do-brasil)
lista recursos de pessoas atendidas, incluindo recortes por condição e modalidade.
Esses indicadores são úteis para acesso, mas não constituem registros individuais
de dispensação nem cobrem toda a assistência básica municipal. Recursos identificados
no portal ainda precisam de aquisição, dicionário e granularidade verificados antes
de um importador. Um item previsto no Plano de Dados Abertos não prova que seu arquivo
esteja publicamente acessível hoje.

Próximo contrato para dispensação básica: identificar recurso oficial de leitura
(ou exportação fornecida pelo gestor), edição, abrangência, unidade observacional,
terminologia do medicamento e regras de completude. Somente então desenhar staging
e publicação sobre o núcleo do omnisus. Não preencher essa lacuna com estoque,
aquisições ou indicadores agregados apresentados como dispensação.

## Trilha Marimo e verificação

Execute `uv run --locked --extra notebooks marimo edit notebooks/bases/medicamentos.py`
a partir do repositório. Etapas: descobrir diferenças entre fontes; inspecionar
dicionário e fixar recorte; importar mediante botão; verificar e exportar resumo com
manifesto. A consulta de estoque tem formulário separado, sem escrita no lake.

As APAC vão para o lake de pesquisa compartilhado; cada execução guarda plano,
resultado e proveniência em `data/lake/pesquisa/execucoes/<run_id>/`, e
`policy="skip_same"` impede duplicar um arquivo já publicado.
O notebook usa uma thread para chamadas síncronas; interromper a célula não garante
cancelamento da importação. Consulte o `run_id` antes de repetir trabalho interrompido.

Testes HTTP usam transporte simulado: offset por página, preservação dos bytes e
identificadores, resposta vazia, alteração de envelope, limite de bytes, erros HTTP
e parâmetros inválidos. A leitura real pequena descrita acima complementa esses
testes, mas não valida ingestão integral do estoque nem dispensações básicas.
