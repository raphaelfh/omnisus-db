# CNES · estabelecimentos (`cnes_estabelecimentos`)

## Em uma frase

Arquivo de estabelecimentos (ST) do Cadastro Nacional de Estabelecimentos de Saúde
(CNES), que o DATASUS publica por UF e mês de competência.

## O que um registro representa

- Os arquivos do CNES trazem os dados cadastrais dos estabelecimentos de saúde
  cadastrados no Sistema de Cadastro Nacional de Estabelecimentos do SUS
  (Informe CNES 2017-06, p. 1).
- O ST é o arquivo de estabelecimentos; o mesmo documento descreve outros arquivos,
  como dados complementares (DC), profissionais (PF), leitos (LT) e equipamentos (EQ)
  (Informe CNES 2017-06, p. 1–2).
- `cnes` é o número nacional do estabelecimento de saúde, com 7 caracteres
  (Informe CNES 2017-06, p. 3).
- `competen` é o ano e o mês de competência da informação, no formato AAAAMM
  (Informe CNES 2017-06, p. 11).
- O layout ST numera os campos de 1 a 203 (Informe CNES 2017-06, p. 3–11) e não traz
  o nome do estabelecimento (p. 3–11).
- O dicionário da biblioteca descreve a base como "CNES — Estabelecimentos (ST)", não
  declara chave primária e declara 12 colunas
  (`src/omnisus_db/data/dicionarios/cnes_estabelecimentos.yaml`, `title` e
  `schema.fields`, sem `primaryKey`).
- A importação grava as colunas do arquivo com nomes em minúsculas e acrescenta `ano`,
  `uf`, `mes` e `_source_release` a cada linha, então a tabela guarda também as
  colunas que o dicionário não declara
  (`src/omnisus_db/sources/datasus_ftp/staging.py`, `dbc_bytes_to_parquet`;
  `src/omnisus_db/sources/datasus_ftp/_runner.py`, `ingest_raw`).
- `cpf_cnpj` traz o CPF do estabelecimento, se pessoa física, ou o CNPJ, se pessoa
  jurídica; `pf_pj` indica 1 = física e 3 = jurídica; `cnpj_man` é o CNPJ da
  mantenedora (Informe CNES 2017-06, p. 3).
- `vinc_sus` indica o vínculo com o SUS: 1 = sim, 0 = não
  (Informe CNES 2017-06, p. 3).

## Datas e geografia

- O arquivo se chama `STufaamm`: `uf` é a Unidade da Federação, `aa` o ano e `mm` o
  mês da competência (Informe CNES 2017-06, p. 2).
- `competen` é o ano e o mês de competência da informação, e o documento grafa
  `DT_ATUA` o ano e o mês de competência da atualização da informação pelo
  estabelecimento, ambos no formato AAAAMM (Informe CNES 2017-06, p. 11).
- As colunas `ano`, `uf` e `mes` vêm do nome do arquivo (`STRR2401.dbc` → RR, 2024,
  mês 1) (`tests/unit/sources/datasus_ftp/test_filenames_golden.py`;
  `src/omnisus_db/sources/datasus_ftp/staging.py`).
- `codufmun` é o código do município do estabelecimento, "UF + MUNIC (sem dígito)",
  declarado com 7 caracteres (Informe CNES 2017-06, p. 3).
- `regsaude` é o código da região de saúde NOAS, e `micr_reg` o da micro-região de
  saúde NOAS (Informe CNES 2017-06, p. 3).
- O dicionário marca `codufmun` com `lpad_6` e o liga a `aux_municipios`
  (`src/omnisus_db/data/dicionarios/cnes_estabelecimentos.yaml`), mas a importação não
  ajusta o comprimento dos códigos: `lpad_6` está definido em
  `src/omnisus_db/transforms/codes.py`, e o caminho de importação (`staging.py`) não o
  chama.
- O código de município da população do IBGE tem 7 dígitos
  (`src/omnisus_db/data/dicionarios/ibge_populacao.yaml`, `codigo_ibge`), e o notebook
  da população junta municípios pelos 6 primeiros dígitos
  (`notebooks/bases/ibge_populacao.py`, consulta `obitos_por_100_mil`).

## Cobertura e modalidade

Arquivos mensais por UF, de agosto de 2005 em diante, no diretório
`/dissemin/publicos/CNES/200508_/Dados/ST`, sem diretório preliminar; veja o
[catálogo de datasets](../datasets.md). A biblioteca importa só os arquivos de prefixo
`ST`; os demais arquivos que o mesmo documento descreve (Informe CNES 2017-06,
p. 1–2) não estão no catálogo.

## Armadilhas

- Cada arquivo ST é de um mês da competência (Informe CNES 2017-06, p. 2), e o
  documento não declara chave nem diz quantas vezes um `cnes` aparece por arquivo
  (p. 3–11; veja Em aberto). Não some linhas de várias competências como se fossem
  estabelecimentos.
- A consulta `estabelecimentos_por_tipo` do notebook mostra, lado a lado, linhas e
  códigos CNES distintos por competência (`notebooks/bases/cnes_estabelecimentos.py`).
- `tp_unid` é o "Tipo de unidade (estabelecimento)", com 2 caracteres, e o documento
  não lista os códigos (Informe CNES 2017-06, p. 3); os rótulos vêm do dicionário da
  biblioteca (`src/omnisus_db/data/dicionarios/cnes_estabelecimentos.yaml`).
- `turno_at` é o código de turno de atendimento, sem lista de códigos no documento
  (Informe CNES 2017-06, p. 3); o dicionário decodifica de 1 a 7
  (`src/omnisus_db/data/dicionarios/cnes_estabelecimentos.yaml`).
- `nivate_a` indica se existe nível de atenção ambulatorial, de gestão municipal ou
  estadual, para o CNES, com 1 = sim e 0 = não (Informe CNES 2017-06, p. 4), embora o
  dicionário o rotule "Nível de atenção"
  (`src/omnisus_db/data/dicionarios/cnes_estabelecimentos.yaml`).
- Há dois campos de natureza: `natureza`, código da natureza da organização com 2
  caracteres (Informe CNES 2017-06, p. 3), e `nat_jur`, natureza jurídica com 4
  caracteres (p. 11).
- O dicionário rotula `nat_jur` "Natureza jurídica (CONCLA)", e o documento não cita
  a CONCLA nesse campo (Informe CNES 2017-06, p. 11;
  `src/omnisus_db/data/dicionarios/cnes_estabelecimentos.yaml`).
- O documento grafa `DT_ATUA` (Informe CNES 2017-06, p. 11), e o dicionário declara
  `dt_atual` com o rótulo "Data de atualização"
  (`src/omnisus_db/data/dicionarios/cnes_estabelecimentos.yaml`).
- `motdesab` é o código do motivo de desabilitação do estabelecimento
  (Informe CNES 2017-06, p. 11).
- As quantidades de leitos tipo 1 (cirúrgico), 2 (clínico) e 3 (complementar) estão em
  `qtleitp1` a `qtleitp3` (Informe CNES 2017-06, p. 5); o arquivo de leitos é o LT
  (p. 2), que a biblioteca não importa ([catálogo](../datasets.md)).
- O nome do estabelecimento não está no ST (Informe CNES 2017-06, p. 3–11):
  `odb.import_cnes_master` busca os nomes na API pública e os junta a `aux_cnes`
  (`src/omnisus_db/__init__.py`, docstring de `import_cnes_master`).
- `aux_cnes` mostra `tp_unid` e `codufmun` da competência mais recente de cada CNES,
  não os da competência que você analisa
  (`src/omnisus_db/lake/operations.py`, `ensure_aux_cnes_view`).
- `odb.import_dataset("cnes_estabelecimentos", ...)` carrega a tabela mas não atualiza
  `aux_cnes`; `odb.import_cnes_estabelecimentos` atualiza
  (`src/omnisus_db/__init__.py`, docstring de `import_cnes_estabelecimentos`).
- Os códigos ficam no lake como publicados: o dicionário decodifica rótulos na
  exibição, não na importação (`src/omnisus_db/transforms/dictionaries.py`, docstring
  do módulo; `src/omnisus_db/sources/datasus_ftp/staging.py`, que não decodifica).

### Em aberto

- Se um `cnes` aparece mais de uma vez no mesmo arquivo: o documento não declara chave
  (p. 3–11), o dicionário não declara chave primária, e `aux_cnes` recusa linhas
  conflitantes na competência mais recente
  (`src/omnisus_db/lake/operations.py`). Compare `count(*)` com
  `count(DISTINCT cnes)` antes de contar estabelecimentos.
- Se o ST inclui estabelecimentos desabilitados: o documento traz o código do motivo
  de desabilitação (p. 11), mas não diz quais estabelecimentos entram no arquivo.
  Olhe a distribuição de `motdesab` nos seus dados.
- Se `competen` é sempre igual ao ano e mês do nome do arquivo: o documento descreve os
  dois (p. 2 e p. 11), mas não afirma que coincidem. Compare `competen` com `ano` e
  `mes`.
- O comprimento do código de município nos dados: o documento declara 7 caracteres
  para "UF + MUNIC (sem dígito)" (p. 3), e o dicionário indica `lpad_6`. Confira nos
  seus dados antes de juntar com outra base.
- Os códigos de `tp_unid` e `turno_at`: o documento não os lista (p. 3), e os rótulos
  vêm do dicionário da biblioteca.
- Se o layout vale para competências anteriores a 2017-06: o documento é o informe
  técnico dessa data (p. 1), e os arquivos começam em 2005-08.

## Como usar

```python
import omnisus_db as odb

alvo = "ducklake:./data/lake/pesquisa/dados.ducklake"
escopos = odb.available("cnes_estabelecimentos", years=[2024], ufs=["RR"], months=[1], refresh=True)
relatorio = odb.import_dataset(
    "cnes_estabelecimentos", scopes=escopos, target=alvo, policy="skip_same", run_id="cnes-rr-2024-01"
)
with odb.LakeReader(alvo) as leitor:
    print(leitor.connect().sql("SELECT competen, count(DISTINCT cnes) AS estabelecimentos FROM lake.cnes_estabelecimentos GROUP BY ALL").pl())
```

`odb.import_cnes_estabelecimentos` faz a mesma importação e, ao terminar, também
atualiza a visão `aux_cnes`.

Passo a passo com análise e proveniência:
[notebooks/bases/cnes_estabelecimentos.py](https://github.com/raphaelfh/omnisus-db/blob/main/notebooks/bases/cnes_estabelecimentos.py).

## Fontes

- Disseminação de Informações do Sistema de Cadastro Nacional de Estabelecimentos do
  SUS (CNES), CNES - Informe Técnico 2017-06 (`IT_CNES_1706.pdf`), Ministério da Saúde /
  Secretaria Executiva / DATASUS:
  <ftp://ftp.datasus.gov.br/dissemin/publicos/CNES/200508_/doc/IT_CNES_1706.pdf>
  — consultado em 2026-09-10; SHA-256
  `71af7438a8cd77ed3fd7af03f7594b94aecf7eaa71082e28fa85c23c5524a1bb`, conferido de novo
  em 2026-09-13. Registro: `docs/dicionario/fontes/registro.json`.
- Catálogo gerado do registro da biblioteca: [Datasets](../datasets.md).

## Detalhes técnicos

### Importação e `aux_cnes`

O CNES-ST usa o pipeline do FTP do DATASUS; o [catálogo](../datasets.md) define
cadência, cobertura e partições. `import_cnes_estabelecimentos()` devolve um
`ImportReport` e atualiza `aux_cnes` depois da carga:

```python
import omnisus_db as odb

relatorio = odb.import_cnes_estabelecimentos(years=[2023], ufs=["RR"], months=[1])
print(relatorio.rows, relatorio.failed)
```

A importação do CNES-ST acrescenta linhas por padrão e aceita as políticas explícitas
de reimportação descritas em
[reprocessamento](../guides/reprocessing-and-maintenance.md). A substituição sempre
casa UF, ano e mês, embora a UF não seja partição física.

`aux_cnes` tem uma linha por código CNES, com `cnes`, `nome`, `tp_unid`, `codufmun` e
`yyyymm_max`, tirados das linhas do maior `ano`/`mes` de cada código. NULLs dessa linha
continuam NULL; um valor mais antigo não é levado adiante. Linhas idênticas na
competência mais recente se fundem na visão; linhas conflitantes causam erro até que o
escopo de origem seja reconciliado. A tabela subjacente guarda o histórico. O nome,
coletado à parte, é enriquecimento atual e não estabelece um nome histórico para a
competência selecionada.

A função atualiza a visão depois da carga do FTP, numa operação separada. Um empate
conflitante pode, portanto, fazer a atualização da visão falhar depois que os lotes de
origem já foram gravados; examine os dados e o manifesto de publicação antes de tentar
de novo.

<a id="establishment-names"></a>

### Nomes dos estabelecimentos

Os nomes vêm à parte, por `import_cnes_master()`, da API pública do CNES. O valor
devolvido é o número de registros úteis obtidos, não um `ImportReport`.

```python
atualizados = odb.import_cnes_master()  # códigos ausentes, descobertos em cnes_estabelecimentos
```

A atualização valida os registros antes de alterar o lake e grava juntas a criação da
tabela, a substituição das linhas e a atualização da visão. Códigos explícitos
repetidos são buscados uma vez. Falhas HTTP individuais e respostas sem nome útil são
omitidas; o inteiro devolvido não identifica quais códigos falharam, e as linhas
antigas desses códigos permanecem. `only_missing=True` filtra os códigos descobertos no
lake quando `codes=None`; códigos explícitos são pedidos mesmo que já estejam
presentes.

### Dicionário

As definições de campo e os metadados de decodificação ficam em
`src/omnisus_db/data/dicionarios/cnes_estabelecimentos.yaml`. Veja
[o contrato de transações](../guides/inventory.md#transactions-and-interrupted-imports)
para a exigência de um único escritor e o tratamento de falhas.
