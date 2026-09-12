# SINAN — Chagas aguda

`sinan_chagas` importa notificações nacionais do diretório
`/dissemin/publicos/SINAN/DADOS/PRELIM`, arquivos `CHAGBRYY.dbc`.
O inventário consultado em 10/09/2026 continha 2023, 2024 e 2025.
Disponibilidade deve ser consultada novamente antes de cada estudo.
Arquivos finais de 2000–2022 existem em outro diretório e **não são parte deste
contrato**. A modalidade preliminar não é convertida silenciosamente em final.

## Descobrir, selecionar e publicar

```python
import omnisus_db as odb

scopes = odb.available("sinan_chagas", years=[2023], refresh=True)
if not scopes:
    raise ValueError("O arquivo solicitado não foi listado pela fonte")
report = odb.import_dataset(
    "sinan_chagas", scopes=scopes,
    target="ducklake:./chagas.ducklake", policy="skip_same",
    run_id="chagas-2023-estudo-01", concurrency=1, batch_size=1,
)
print(report.rows, report.failed)
```

```bash
omnisus-db inventory sinan_chagas
omnisus-db import sinan_chagas --years 2023 --plan inventory --policy skip_same
```

O recorte nacional é `ScopeKey(uf=None, ano=2023)`. Não aceita filtros de UF ou
mês na aquisição. Use `sg_uf_not` (notificação) ou os campos de residência
originais na consulta, conforme a pergunta científica.

## Contrato de integridade e publicação

- O arquivo inteiro passa pela verificação de tamanho e contagem DBF, pelo
  staging Arrow/Parquet e pela mesma transação dos importadores estaduais.
- Exige as colunas `id_agravo`, `nu_ano`, `sg_uf_not`; cada registro precisa
  informar `id_agravo=B571` e `nu_ano` igual ao ano pedido. Erros rejeitam o
  arquivo inteiro; não há descarte silencioso de linhas.
- `_source_ano` identifica o ano do arquivo e é reservado à biblioteca. Não
  sobrescreve `ano`, `uf` nem os campos originais, se estiverem presentes.
- `replace` valida antes de substituir exatamente o ano nacional; dados e
  manifesto são publicados atomicamente. Misturar publicação nacional e
  estadual na mesma tabela é rejeitado.
- `skip_same` verifica novamente a fonte. Se hash ou parser/dicionário mudou,
  exige uma decisão explícita de substituição. O padrão geral da API continua
  `append`; para pesquisadores, os exemplos escolhem `skip_same`.
- O manifesto mantém SHA-256, versão, URL de origem, IDs de execução/publicação
  e situação ativa. Manifestos antigos recebem URL nula, sem inventar origem.
  A URL não é um identificador imutável: o hash identifica os bytes adquiridos.

Uma falha de commit pode ter resultado desconhecido. Reabra o lake, consulte
`lake.publications(run_id=...)` e reconcilie antes de repetir a escrita. O lock
continua local/cooperativo; isso não estabelece recuperação distribuída.

## Interpretação e reprodução

Os 108 campos do YAML são um inventário físico observado em CHAGBR23.dbc,
**não uma auditoria semântica integral**. Campos adicionais são preservados;
incompatibilidades de tipo seguem a política geral de esquema. A validação
da identidade da fonte não comprova qualidade clínica, completitude da
vigilância nem classificação final do caso.

Não confundir notificações com casos confirmados, indivíduos únicos ou
incidência. Não confundir doença de Chagas aguda com os registros de doença
de Chagas crônica do e-SUS Notifica. A edição preliminar pode ser revisada ou
retirada do diretório; a existência de arquivos é distinta de encerramento
epidemiológico dos registros.

Fontes: [página oficial do agravo](https://www.portalsinan.saude.gov.br/doenca-de-chagas-aguda)
e [dicionário SINAN NET v5](https://portalsinan.saude.gov.br/images/documentos/Agravos/Chagas/DIC_DADOS_Chagas_v5.pdf).

O notebook `notebooks/sinan_chagas.py` apresenta descoberta, contrato, plano
salvo, importação explícita, recuperação e análise agregada com exportação da
proveniência. Execute na raiz do checkout:

```bash
uv run --locked --extra notebooks marimo edit notebooks/sinan_chagas.py
```

Abrir/exportar o notebook não inicia rede nem publicação. Interromper uma
célula não garante cancelar a thread do importador; aguarde sua conclusão
antes de reabrir o mesmo destino.
