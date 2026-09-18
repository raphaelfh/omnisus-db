# SIA · produção ambulatorial (`sia_*`)

## Em uma frase

Sete tabelas do Sistema de Informações Ambulatoriais do SUS (SIASUS): o boletim
individualizado (BPA-I), cinco tipos de laudo de APAC e o registro de atenção
psicossocial (RAAS), publicados pelo DATASUS um arquivo por tabela, UF e mês.

## O que um registro representa

Cada tabela vem de um instrumento ou laudo diferente:

- `sia_bpa_individualizado` (prefixo `BI`): Boletim de Produção Ambulatorial
  Individualizado (BPA-I), instituído pela Portaria SAS/MS nº 709/2007 para registrar
  informações sobre os usuários do SUS e sua situação de saúde pela CID
  (Informe SIASUS 2019-07, p. 17).
- `sia_apac_medicamentos` (prefixo `AM`): Laudo de Medicamentos da APAC
  (Informe SIASUS 2019-07, p. 5), com peso, altura, transplante e gestante do paciente
  (p. 7).
- `sia_apac_quimioterapia` (prefixo `AQ`): Laudo de Quimioterapia da APAC
  (Informe SIASUS 2019-07, p. 5), com CID de topografia, estádio, esquema e meses de
  tratamento planejados e autorizados (p. 9–10).
- `sia_apac_tratamento_dialitico` (prefixo `ATD`): Laudo de Tratamento Dialítico da APAC
  (Informe SIASUS 2019-07, p. 5), com a data de início da primeira diálise e a data de
  início da diálise na clínica (p. 15).
- `sia_apac_laudos_diversos` (prefixo `AD`): Laudos Diversos da APAC
  (Informe SIASUS 2019-07, p. 5), com o layout comum da APAC e nenhum campo próprio
  (p. 6).
- `sia_apac_cirurgia_bariatrica` (prefixo `ABO` no catálogo): Laudo de Acompanhamento à
  Cirurgia Bariátrica da APAC (Informe SIASUS 2019-07, p. 5), com número da AIH, data
  da cirurgia e número de meses de acompanhamento (p. 12).
- `sia_psicossocial` (prefixo `PS`): Registro das Ações Ambulatoriais de Saúde (RAAS) –
  Psicossocial (Informe SIASUS 2019-07, p. 15–16).

Sobre as linhas:

- As informações dos arquivos de APAC referem-se aos atendimentos ambulatoriais
  realizados em pacientes submetidos à APAC, nas respectivas competências (ano e mês),
  a partir de janeiro de 2008 (Informe SIASUS 2019-07, p. 5).
- `ap_autoriz` é o número da APAC, com a lei de formação UF, ano, tipo, sequencial e
  dígito (Informe SIASUS 2019-07, p. 6).
- O valor aprovado dos arquivos de APAC refere-se ao valor total da APAC
  (Informe SIASUS 2019-07, p. 5).
- Nos arquivos de APAC, o procedimento contido no arquivo refere-se ao procedimento
  principal (Informe SIASUS 2019-07, p. 5), em `ap_pripal` (p. 6).
- Na RAAS psicossocial, cada linha traz a quantidade de atendimentos (`qtdate`) e a
  quantidade de pacientes (`qtdpcn`) (Informe SIASUS 2019-07, p. 16–17).
- Nenhum dos sete dicionários declara chave primária
  (`src/omnisus_db/data/dicionarios/sia_*.yaml`, sem `primaryKey`).
- A importação grava as colunas do arquivo com nomes em minúsculas e acrescenta `ano`,
  `uf`, `mes` e `_source_release` a cada linha
  (`src/omnisus_db/sources/datasus_ftp/staging.py`, `dbc_bytes_to_parquet`;
  `src/omnisus_db/sources/datasus_ftp/_runner.py`, `ingest_raw`).

## Datas e geografia

- O documento diz que o `aamm` do nome do arquivo é o ano e o mês da competência
  (Informe SIASUS 2019-07, p. 5 para APAC e p. 17 para BPA-I).
- As colunas `ano`, `uf` e `mes` vêm do nome do arquivo (`AMRR2401.dbc` → RR, 2024,
  mês 1) (`tests/unit/sources/datasus_ftp/test_filenames_golden.py`;
  `src/omnisus_db/sources/datasus_ftp/staging.py`).
- Na APAC, `ap_mvm` é a data de processamento ou movimento e `ap_cmp` a data de
  atendimento ao paciente ou competência, ambas AAAAMM (Informe SIASUS 2019-07, p. 6).
- A APAC tem validade: `ap_dtinic` e `ap_dtfim` são as datas de início e de fim da
  validade, AAAAMMDD, e `ap_dtocor` é a data de ocorrência que substitui a data de fim
  (Informe SIASUS 2019-07, p. 6).
- `ap_tpapac` indica se a APAC é 1 = inicial, 2 = continuidade ou 3 = única, e
  `ap_apacant` guarda o número da APAC anterior (Informe SIASUS 2019-07, p. 6).
- No BPA-I, `dt_process` é o ano e mês de processamento da produção e `dt_atend` o ano e
  mês do atendimento (Informe SIASUS 2019-07, p. 17).
- Na RAAS psicossocial, `dt_process` é a data de processamento e `dt_atend` a data do
  atendimento, AAAAMM, e `inicio` e `fim` são as datas de início e fim do atendimento
  (Informe SIASUS 2019-07, p. 16).
- Na APAC, `ap_munpcn` é UF + município de residência do paciente, com 6 caracteres, e
  `ap_ufmun` é UF + município do estabelecimento (Informe SIASUS 2019-07, p. 6).
- No BPA-I, `munpac` é UF + município de residência do paciente ou do estabelecimento,
  quando não há identificação do paciente, o que ocorre no BPA
  (Informe SIASUS 2019-07, p. 17).
- Na RAAS psicossocial, `munpac` é UF + município de residência do paciente, e `ufmun`
  o do estabelecimento (Informe SIASUS 2019-07, p. 16).
- `ap_ufdif` e `ap_mndif` (APAC) e `ufdif` e `mndif` (BPA-I) indicam se a UF ou o
  município de residência do paciente difere do local do estabelecimento
  (Informe SIASUS 2019-07, p. 6 e p. 18).

## Cobertura e modalidade

Arquivos mensais por UF, todos no diretório `/dissemin/publicos/SIASUS/200801_/Dados`,
sem diretório preliminar. O início difere por tabela: 2008-01 para BPA-I, medicamentos,
quimioterapia e laudos diversos; 2012-11 para a RAAS psicossocial; 2014-01 para
cirurgia bariátrica; 2014-08 para tratamento dialítico. Veja o
[catálogo de datasets](../datasets.md).

## Armadilhas

- Os códigos de `ap_ufdif` e `ap_mndif` mudam entre layouts: 0 e 1 em laudos diversos
  (Informe SIASUS 2019-07, p. 6), N e S em quimioterapia (p. 9), cirurgia bariátrica
  (p. 12) e tratamento dialítico (p. 14), e nenhum código, com 2 caracteres, em
  medicamentos (p. 7).
- Os cinco dicionários de APAC decodificam `ap_ufdif` e `ap_mndif` só como 0 e 1
  (`src/omnisus_db/data/dicionarios/sia_apac_*.yaml`).
- O documento nomeia o arquivo de cirurgia bariátrica `ABufaamm.dbf` (p. 5) e
  `ABUFMM.DBF` (p. 11); a biblioteca usa o prefixo `ABO` ([catálogo](../datasets.md);
  `tests/unit/sources/datasus_ftp/test_filenames_golden.py`).
- No arquivo real de cirurgia bariátrica, o cabeçalho tem 86 campos, 8 sem nome, que o
  parser descarta, e nomes variantes como `AP_TPPRE`, `AP_APACAN`, `AP_DTOOCOR` e
  `CO_CIDPRIM` (`tests/unit/sources/datasus_ftp/test_sia_apac.py`, docstring do
  módulo), enquanto o layout do documento lista 58 campos com `AP_TIPPRE`,
  `AP_APACANT`, `AP_DTOCOR` e `AP_CIDPRI` (Informe SIASUS 2019-07, p. 11–12).
- Os dicionários de APAC e da RAAS psicossocial foram gerados do cabeçalho de arquivos
  DBF reais de 2024, não do informe técnico, e muitos rótulos só repetem o nome do campo
  (`src/omnisus_db/data/dicionarios/sia_apac_*.yaml` e `sia_psicossocial.yaml`,
  comentário inicial e `label`).
- Quantidade e valor aparecem apresentados e aprovados: `qt_apres` e `qt_aprov`,
  `vl_apres` e `vl_aprov` no BPA-I (Informe SIASUS 2019-07, p. 17–18).
- No BPA-I, o número de autorização `autoriz` não é obrigatório e não é criticado
  (Informe SIASUS 2019-07, p. 17).
- No BPA-I, `etnia` só é preenchida quando `racacor` é 05 (indígena), a partir da
  competência de outubro de 2010 (Informe SIASUS 2019-07, p. 18).
- O CNS do paciente vem cifrado (`cns_pac` na RAAS, "criptografia";
  Informe SIASUS 2019-07, p. 16), e os dicionários marcam os campos de CNS com
  `x-crypto: datasus-cns` (`src/omnisus_db/data/dicionarios/sia_*.yaml`).
- Depois de decifrado, o CNS liga pessoas entre tabelas do SIA: nos arquivos de teste de
  Roraima, janeiro de 2024, 312 pessoas estavam no BPA-I e na APAC de medicamentos, e 56
  no BPA-I e na RAAS psicossocial (`tests/unit/sources/datasus_ftp/test_sia_apac.py`,
  `test_cross_family_cns_intersection_rr`).
- Os códigos ficam no lake como publicados: o dicionário decodifica rótulos e datas na
  exibição, não na importação (`src/omnisus_db/transforms/dictionaries.py`, docstring do
  módulo; `src/omnisus_db/sources/datasus_ftp/staging.py`, que não decodifica).

### Em aberto

- O que uma linha de APAC representa: o documento diz que a APAC gera um registro por
  código de procedimento realizado, principal ou secundário, e, na frase seguinte, que
  nos arquivos de APAC o procedimento se refere ao principal (p. 5). Vale para
  `sia_apac_medicamentos`, `sia_apac_quimioterapia`, `sia_apac_tratamento_dialitico`,
  `sia_apac_laudos_diversos` e `sia_apac_cirurgia_bariatrica`. Compare o número de
  linhas com o de valores distintos de `ap_autoriz` antes de contar APAC.
- Se a mesma APAC reaparece em meses seguintes: o documento prevê APAC de continuidade e
  período de validade (p. 6), mas não diz se cada mês publica a APAC de novo. Não some
  meses sem conferir `ap_autoriz` e `ap_tpapac`.
- Qual mês o arquivo representa: o documento chama o `aamm` do nome de mês da
  competência (p. 5 e p. 17), mas separa processamento (`ap_mvm`, `dt_process`) de
  atendimento ou competência (`ap_cmp`, `dt_atend`) (p. 6, p. 16 e p. 17). Compare `mes`
  com esses campos nos seus dados.
- O que uma linha de `sia_bpa_individualizado` representa: o documento diz que o BPA-I
  gera um registro por atendimento no arquivo de procedimentos ambulatoriais (PA)
  (p. 3), mas não diz o mesmo do arquivo BI.
- O que uma linha de `sia_psicossocial` representa: cada linha traz quantidades de
  atendimentos e de pacientes (p. 16–17), e o documento não diz se ela é um atendimento,
  um paciente ou um período.
- O formato de `inicio` e `fim` na RAAS psicossocial: o documento dá DDMMAAAA (p. 16),
  e o dicionário lê `yyyyMMdd` (`src/omnisus_db/data/dicionarios/sia_psicossocial.yaml`).
  Confira nos seus dados antes de converter.
- Que procedimentos entram em `sia_apac_laudos_diversos`: o documento lista o laudo e
  seu layout (p. 5–6), sem dizer o que ele cobre.
- Se o layout de 2019 vale para todos os anos: o documento diz que não houve mudanças
  nos arquivos de APAC (p. 6), sem data de referência.

## Como usar

```python
import omnisus_db as odb

alvo = "ducklake:./data/lake/pesquisa/dados.ducklake"
escopos = odb.available("sia_bpa_individualizado", years=[2024], ufs=["RR"], months=[1], refresh=True)
relatorio = odb.import_dataset(
    "sia_bpa_individualizado", scopes=escopos, target=alvo, policy="skip_same", run_id="sia-bpai-rr-2024-01"
)
with odb.LakeReader(alvo) as leitor:
    print(leitor.connect().sql("SELECT ano, mes, count(*) AS registros FROM lake.sia_bpa_individualizado GROUP BY ALL").pl())
```

Passo a passo com as sete tabelas, análise e proveniência:
[notebooks/bases/sia.py](https://github.com/raphaelfh/omnisus-db/blob/main/notebooks/bases/sia.py)
[![Open in molab](https://molab.marimo.io/molab-shield.svg)](https://molab.marimo.io/github/raphaelfh/omnisus-db/blob/main/notebooks/bases/sia.py).

## Fontes

- Disseminação de Dados em Saúde, Sistema de Informações Ambulatoriais do SUS
  (SIASUS), Informe Técnico (`Informe_Tecnico_SIASUS_2019_07.pdf`), Ministério da
  Saúde / Secretaria Executiva / DATASUS / CGGOV:
  <ftp://ftp.datasus.gov.br/dissemin/publicos/SIASUS/200801_/Doc/Informe_Tecnico_SIASUS_2019_07.pdf>
  — consultado em 2026-09-10; SHA-256
  `70fe69dbd4cf0827452e3c265d8d83ebeabe145f63a7e054e57c7848d070c8dc`, conferido de novo
  em 2026-09-13. Registro: `docs/dicionario/fontes/registro.json`. Em 2026-09-13, o
  diretório `/dissemin/publicos/SIASUS/200801_/Doc` só continha este informe.
- Catálogo gerado do registro da biblioteca: [Datasets](../datasets.md).

## Detalhes técnicos

### As sete tabelas

Todas usam o mesmo diretório do FTP, `/dissemin/publicos/SIASUS/200801_/Dados`, e se
distinguem pelo prefixo do arquivo ([catálogo](../datasets.md)):

| Dataset | Prefixo |
| --- | --- |
| `sia_bpa_individualizado` | `BI` |
| `sia_apac_medicamentos` | `AM` |
| `sia_apac_quimioterapia` | `AQ` |
| `sia_apac_tratamento_dialitico` | `ATD` |
| `sia_apac_laudos_diversos` | `AD` |
| `sia_apac_cirurgia_bariatrica` | `ABO` |
| `sia_psicossocial` | `PS` |

O informe técnico também cita arquivos que a biblioteca não importa: produção
ambulatorial (`PA`), APAC de nefrologia (`AN`), radioterapia (`AR`), confecção de
fístula (`ACF`) e acompanhamento multiprofissional (`AMP`), e atenção domiciliar
(`SAD`) (Informe SIASUS 2019-07, p. 1 e p. 5).

### Linha de comando

```bash
omnisusdb inventory sia_bpa_individualizado --refresh
omnisusdb import sia_bpa_individualizado --plan inventory --years 2020-2024 --ufs RR
```

As importações acrescentam linhas à tabela do dataset, por exemplo
`lake.sia_bpa_individualizado`. Ao terminar, a importação devolve um `ImportReport`; o
estado de uma transação interrompida aparece em `ImportAbortedError`. Veja
[resultados e transações](../guides/inventory.md#transactions-and-interrupted-imports).

### Dicionários

As definições de campo e as regras de decodificação ficam em
`src/omnisus_db/data/dicionarios/<dataset>.yaml`, um arquivo por tabela. Os sete usam a
codificação `latin-1`, porque o CNS cifrado usa bytes que o `cp1252` não define
(comentário inicial de cada dicionário). O parser aplica o dicionário e preserva os
campos não listados; por isso as colunas físicas da tabela podem ser mais numerosas que
as do dicionário.
