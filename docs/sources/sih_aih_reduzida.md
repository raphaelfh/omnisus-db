# SIH · AIH reduzida (`sih_aih_reduzida`)

## Em uma frase

Autorizações de Internação Hospitalar (AIH) do Sistema de Informações Hospitalares do
SUS (SIH/SUS), nos arquivos RD que o DATASUS publica um por UF e mês de processamento.

## O que um registro representa

- O dicionário da biblioteca descreve a base como "SIHSUS — AIH Reduzida (RD)" e não
  declara chave primária (`src/omnisus_db/data/dicionarios/sih_aih_reduzida.yaml`,
  `title`, sem `primaryKey`).
- O documento oficial descreve o layout dos arquivos `RD*.dbf` para janeiro de 2008 em
  diante (Informe SIH 2016-03, p. 1).
- Cada linha traz o número da AIH em `n_aih`, com 13 caracteres, e o tipo da AIH em
  `ident` (Informe SIH 2016-03, p. 1).
- O documento não lista os códigos de `ident` (Informe SIH 2016-03, p. 1); o
  dicionário os decodifica como 1 = AIH principal, 3 = AIH de continuação e 5 = AIH de
  longa permanência (`src/omnisus_db/data/dicionarios/sih_aih_reduzida.yaml`).
- `seq_aih5` é o sequencial de longa permanência, da AIH tipo 5
  (Informe SIH 2016-03, p. 3).
- O layout RD não traz o número do Cartão Nacional de Saúde do paciente
  (Informe SIH 2016-03, p. 1–4); `aud_just` e `sis_just` guardam a justificativa para
  aceitar a AIH sem esse número (p. 3).
- `homonimo` indica se o paciente da AIH é homônimo do paciente de outra AIH
  (Informe SIH 2016-03, p. 3).
- `diag_princ` é o código do diagnóstico principal pela CID-10, com 4 caracteres
  (Informe SIH 2016-03, p. 2), e o dicionário o liga à tabela `aux_cid10`
  (`src/omnisus_db/data/dicionarios/sih_aih_reduzida.yaml`).
- `val_tot` é o valor total da AIH (Informe SIH 2016-03, p. 2).
- A importação grava as colunas do arquivo com nomes em minúsculas e acrescenta `ano`,
  `uf`, `mes` e `_source_release` a cada linha
  (`src/omnisus_db/sources/datasus_ftp/staging.py`, `dbc_bytes_to_parquet`;
  `src/omnisus_db/sources/datasus_ftp/_runner.py`, `ingest_raw`).

## Datas e geografia

- `ano_cmpt` e `mes_cmpt` são o ano e o mês de processamento da AIH
  (Informe SIH 2016-03, p. 1), e a data de internação é outro campo (p. 2).
- A data de internação está em `dt_inter` e a data de saída em `dt_saida`, ambas no
  formato aaaammdd (Informe SIH 2016-03, p. 2; o documento grafa o primeiro campo como
  `DI_INTER`).
- `nasc` é a data de nascimento do paciente, no formato aaaammdd
  (Informe SIH 2016-03, p. 1).
- `gestor_dt` é a data da autorização dada pelo gestor, no formato aaaammdd
  (Informe SIH 2016-03, p. 3).
- As colunas `ano`, `uf` e `mes` vêm do nome do arquivo (`RDSP2401.dbc` → SP, 2024,
  mês 1) (`tests/unit/sources/datasus_ftp/test_filenames_golden.py`;
  `src/omnisus_db/sources/datasus_ftp/staging.py`).
- `munic_res` é o município de residência do paciente, com 6 caracteres
  (Informe SIH 2016-03, p. 1).
- `munic_mov` é o município do estabelecimento, com 6 caracteres
  (Informe SIH 2016-03, p. 2).
- `uf_zi` é o município gestor, com 6 caracteres (Informe SIH 2016-03, p. 1), embora o
  dicionário o rotule "UF do gestor"
  (`src/omnisus_db/data/dicionarios/sih_aih_reduzida.yaml`).
- `cnes` é o código CNES do hospital, com 7 caracteres (Informe SIH 2016-03, p. 3).
- O dicionário marca `munic_res` e `munic_mov` com `lpad_6` e os liga a
  `aux_municipios` (`src/omnisus_db/data/dicionarios/sih_aih_reduzida.yaml`), mas a
  importação não ajusta o comprimento dos códigos: `lpad_6` está definido em
  `src/omnisus_db/transforms/codes.py`, e o caminho de importação (`staging.py`) não o
  chama.

## Cobertura e modalidade

Arquivos mensais por UF, de janeiro de 2008 em diante, no diretório
`/dissemin/publicos/SIHSUS/200801_/Dados`, sem diretório preliminar; veja o
[catálogo de datasets](../datasets.md). A biblioteca importa só os arquivos de prefixo
`RD`; os arquivos `SP*.dbf`, que o mesmo documento descreve (Informe SIH 2016-03,
p. 4–5), não estão no catálogo.

## Armadilhas

- Há AIH de tipos diferentes em `ident` (Informe SIH 2016-03, p. 1) e um sequencial
  próprio para a AIH de longa permanência (p. 3).
- A consulta `aih_distintas` do notebook compara o número de linhas com o número de
  valores distintos de `n_aih` antes de qualquer contagem
  (`notebooks/bases/sih_aih_reduzida.py`).
- Agregar por `mes_cmpt` conta AIH processadas no mês (Informe SIH 2016-03, p. 1); para
  contar internações por mês de ocorrência, use `dt_inter` (p. 2).
- `morte` "indica óbito", com 1 algarismo, e o documento não lista os códigos
  (Informe SIH 2016-03, p. 2); o dicionário decodifica 0 = não e 1 = sim
  (`src/omnisus_db/data/dicionarios/sih_aih_reduzida.yaml`).
- `cid_morte` é a CID da morte (Informe SIH 2016-03, p. 3), e `cobranca` é o motivo de
  saída ou permanência (p. 2); o dicionário decodifica em `cobranca` códigos de alta,
  permanência, transferência e óbito
  (`src/omnisus_db/data/dicionarios/sih_aih_reduzida.yaml`).
- Os complementos federal e do gestor de serviços hospitalares e profissionais
  (`val_sh_fed`, `val_sp_fed`, `val_sh_ges`, `val_sp_ges`) estão incluídos no valor
  total da AIH (Informe SIH 2016-03, p. 4).
- `us_tot` é o valor total em dólar, não em reais (Informe SIH 2016-03, p. 2).
- Vários campos de valor vêm zerados: `val_sadt`, `val_rn`, `val_acomp`, `val_ortp`,
  `val_sangue`, `val_sadtsr`, `val_transp`, `val_obsang` e `val_ped1ac`
  (Informe SIH 2016-03, p. 2).
- Também vêm zerados `uti_mes_in`, `uti_mes_an`, `uti_mes_al`, `uti_int_in`,
  `uti_int_an` e `uti_int_al` (Informe SIH 2016-03, p. 1); a quantidade de dias de UTI
  no mês está em `uti_mes_to` (p. 1).
- `diag_secun` vem preenchido com zeros a partir de 201501
  (Informe SIH 2016-03, p. 2); os diagnósticos secundários estão em `diagsec1` a
  `diagsec9` (p. 4).
- `natureza` tem conteúdo só até maio de 2012; a natureza jurídica pela CONCLA está em
  `nat_jur` (Informe SIH 2016-03, p. 2).
- `idade` depende da unidade em `cod_idade` (Informe SIH 2016-03, p. 2); o documento
  não lista os códigos da unidade, e o dicionário decodifica 0 = ignorada, 2 = dias,
  3 = meses, 4 = anos e 5 = mais de 100 anos
  (`src/omnisus_db/data/dicionarios/sih_aih_reduzida.yaml`).
- `sexo` tem 1 caractere e o documento não lista os códigos
  (Informe SIH 2016-03, p. 1); os rótulos do dicionário não têm apoio neste documento
  (`src/omnisus_db/data/dicionarios/sih_aih_reduzida.yaml`).
- Os códigos ficam no lake como publicados: o dicionário decodifica rótulos, datas e
  idade na exibição, não na importação (`src/omnisus_db/transforms/dictionaries.py`,
  docstring do módulo; `src/omnisus_db/sources/datasus_ftp/staging.py`, que não
  decodifica).

### Em aberto

- O que uma linha representa: o documento traz o número da AIH (`n_aih`,
  Informe SIH 2016-03, p. 1), mas não diz que cada linha é uma AIH distinta, e o layout
  RD não traz o número do Cartão Nacional de Saúde do paciente (p. 1–4). Não trate
  linhas como pacientes, e compare linhas com valores distintos de `n_aih` (consulta
  `aih_distintas`) antes de contar AIH.
- Se uma internação longa aparece em mais de uma linha: o documento traz o tipo da AIH
  e o sequencial de longa permanência (p. 1 e p. 3), mas não diz como uma internação se
  divide em AIH. Não conte internações como linhas sem olhar `ident`, `seq_aih5` e
  `n_aih` nos seus dados.
- Se o mês do arquivo (`mes`) é sempre igual a `mes_cmpt`: o documento não explica o
  nome do arquivo. Compare as duas colunas antes de supor.
- Os códigos de `morte`, `ident`, `cod_idade` e `sexo`: o documento não os lista, e os
  rótulos vêm do dicionário da biblioteca. A consulta `campo_morte` do notebook mostra
  os valores publicados.
- O comprimento do código de município nos dados: o documento declara 6 caracteres
  (p. 1–2), e o dicionário indica `lpad_6`. Confira nos seus dados antes de juntar com
  outra base.
- Se o layout vale para arquivos processados depois de 2016-03: o documento é o informe
  desse processamento (p. 1).

## Como usar

```python
import omnisus_db as odb

alvo = "ducklake:./data/lake/pesquisa/dados.ducklake"
escopos = odb.available("sih_aih_reduzida", years=[2024], ufs=["RR"], months=[1], refresh=True)
relatorio = odb.import_dataset(
    "sih_aih_reduzida", scopes=escopos, target=alvo, policy="skip_same", run_id="sih-rr-2024-01"
)
with odb.LakeReader(alvo) as leitor:
    print(leitor.connect().sql("SELECT ano, mes, count(*) AS aih FROM lake.sih_aih_reduzida GROUP BY ALL").pl())
```

Passo a passo com análise e proveniência:
[notebooks/bases/sih_aih_reduzida.py](https://github.com/raphaelfh/omnisus-db/blob/main/notebooks/bases/sih_aih_reduzida.py)
[![Open in molab](https://molab.marimo.io/molab-shield.svg)](https://molab.marimo.io/github/raphaelfh/omnisus-db/blob/main/notebooks/bases/sih_aih_reduzida.py).

## Fontes

- Disseminação de Informações do Sistema de Informações Hospitalares (SIH), Informe
  Técnico referente ao processamento 2016-03 (`IT_SIHSUS_1603.pdf`), Ministério da
  Saúde / Secretaria de Gestão Estratégica e Participativa / DATASUS:
  <ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Doc/IT_SIHSUS_1603.pdf>
  — consultado em 2026-09-10; SHA-256
  `1e89d5f2cc41420385d7e30ba5541a387912ab3a0efb167d39def74502076220`, conferido de novo
  em 2026-09-13. Registro: `docs/dicionario/fontes/registro.json`.
- Catálogo gerado do registro da biblioteca: [Datasets](../datasets.md).

## Detalhes técnicos

### Linha de comando

```bash
omnisus-db inventory sih_aih_reduzida --refresh
omnisus-db import sih_aih_reduzida --plan inventory --years 2020-2024 --ufs RR
```

As importações acrescentam linhas a `lake.sih_aih_reduzida`. Ao terminar, a importação
devolve um `ImportReport`; o estado de uma transação interrompida aparece em
`ImportAbortedError`. Veja
[resultados e transações](../guides/inventory.md#transactions-and-interrupted-imports).

### Dicionário

As definições de campo, os metadados de chave estrangeira e as regras de decodificação
ficam em `src/omnisus_db/data/dicionarios/sih_aih_reduzida.yaml`. O parser aplica o
dicionário e preserva os campos não listados; por isso as colunas físicas da tabela
podem ser mais numerosas que as do dicionário. A validação do dicionário, sozinha, não
certifica todos os registros recebidos.
