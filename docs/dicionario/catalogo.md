# Catálogo da auditoria

Projeção gerada da auditoria `2026-09-10-mapa-datasus`, consultada em **2026-09-10**.
Regenerar este arquivo não faz nova consulta nem renova a checagem.

As contagens abaixo representam a amostra de cada categoria, não todos os produtos
existentes. Colunas são ocorrências por tabela. Rótulos locais e nomes encontrados
em PDFs não são confirmações de significado, códigos ou vigência.

| Categoria | Subtipo amostrado | Tabelas | Colunas | Rótulos locais | Mapas locais | PDFs obtidos |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| DATASUS | TABWIN | 0 | 0 | 0 | 0 | 0 |
| IBGE | POPT | 28 | 84 | 0 | 0 | 1 |
| Base Territorial | TER | 22 | 111 | 0 | 0 | 1 |
| CIH | CR | 1 | 27 | 0 | 0 | 0 |
| CIHA | CIHA | 1 | 30 | 0 | 0 | 1 |
| CNES | ST | 1 | 208 | 9 | 2 | 1 |
| ESUSNOTIFICA | DCCR | 1 | 109 | 0 | 0 | 1 |
| PCE | PCE | 1 | 35 | 0 | 0 | 1 |
| PO | PO | 1 | 23 | 0 | 0 | 1 |
| RESP | RESP | 1 | 78 | 0 | 0 | 1 |
| SIASUS | PA | 1 | 60 | 0 | 0 | 1 |
| SIHSUS | RD | 1 | 113 | 95 | 21 | 2 |
| SIM | DO | 1 | 87 | 87 | 38 | 3 |
| SINAN | CHAG | 1 | 108 | 0 | 0 | 2 |
| SINASC | DN | 1 | 61 | 61 | 26 | 1 |
| SISCOLO | CC | 1 | 102 | 0 | 0 | 0 |
| SISMAMA | CM | 1 | 54 | 0 | 0 | 0 |
| SISPRENATAL | PN | 1 | 36 | 0 | 0 | 0 |

## Interpretação e prioridades

- **SIM, SINASC e SIH/RD:** começar pela revisão dos campos já presentes nos YAMLs,
  identificando diferenças de edição e colunas ainda sem definição.
- **CNES/ST:** ampliar a cobertura do produto exato; o rótulo da categoria não cobre os demais subtipos.
- **SIA/PA e IBGE/POPT:** não reutilizar automaticamente o dicionário de outro produto/API da mesma base.
- **CIH, SISCOLO, SISMAMA e SISPRENATAL:** documentação não obtida nos locais consultados;
  manter busca pendente. Isso não comprova inexistência de dicionários.
- **SINAN:** os documentos específicos e de notificação geral se complementam; conferir a edição.
- **DATASUS/TABWIN:** aplicativo amostrado, sem tabela de registros; não contar como falha de dicionário de coluna.

## Evidências recuperáveis

O [registro JSON](fontes/registro.json) fornece ID, URL oficial, hash e datas de cada PDF.
Campos editoriais desconhecidos permanecem `null`; nomes de arquivo não são usados para inventar datas.
O [CSV de cobertura](cobertura.csv) relaciona os IDs das fontes às categorias.
O [inventário por campo](campos.csv) reúne as colunas físicas, rótulos/códigos locais
e IDs das fontes com menção textual, mantendo a validação semântica como pendente.

| Categoria | Documento | ID |
| --- | --- | --- |
| IBGE | [Pop_Residente_TCU_ate_2023.pdf](ftp://ftp.datasus.gov.br/dissemin/publicos/IBGE/DOC/Pop_Residente_TCU_ate_2023.pdf) | `ibge-ae71f4736dce` |
| Base Territorial | [bases_territoriais.pdf](ftp://ftp.datasus.gov.br/territorio/doc/bases_territoriais.pdf) | `base-territorial-98a2c740720b` |
| CIHA | [Layout_Arquivos_CIHA.pdf](ftp://ftp.datasus.gov.br/dissemin/publicos/CIHA/201101_/Doc/Layout_Arquivos_CIHA.pdf) | `ciha-c326559e8d8d` |
| CNES | [IT_CNES_1706.pdf](ftp://ftp.datasus.gov.br/dissemin/publicos/CNES/200508_/doc/IT_CNES_1706.pdf) | `cnes-71af7438a8cd` |
| ESUSNOTIFICA | [Dicionario_de_Dados_Doenca_de_Chagas_Cronica.pdf](ftp://ftp.datasus.gov.br/dissemin/publicos/ESUSNOTIFICA/DOCS/Dicionario_de_Dados_Doenca_de_Chagas_Cronica.pdf) | `esusnotifica-5b081513ff3d` |
| PCE | [DIC_DADOS_SISPCE_PCE-DG.pdf](ftp://ftp.datasus.gov.br/dissemin/publicos/PCE/DOCS/DIC_DADOS_SISPCE_PCE-DG.pdf) | `pce-9f83353e4e10` |
| PO | [Dicionario_Painel_Oncologia.pdf](ftp://ftp.datasus.gov.br/dissemin/publicos/PAINEL_ONCOLOGIA/DOC/Dicionario_Painel_Oncologia.pdf) | `po-5503556badd2` |
| RESP | [DIC_DADOS_RESP.pdf](ftp://ftp.datasus.gov.br/dissemin/publicos/RESP/DOCS/DIC_DADOS_RESP.pdf) | `resp-c6e3fda1713d` |
| SIASUS | [Informe_Tecnico_SIASUS_2019_07.pdf](ftp://ftp.datasus.gov.br/dissemin/publicos/SIASUS/200801_/Doc/Informe_Tecnico_SIASUS_2019_07.pdf) | `siasus-70fe69dbd4cf` |
| SIHSUS | [IT_SIHSUS_1603.pdf](ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Doc/IT_SIHSUS_1603.pdf) | `sihsus-1e89d5f2cc41` |
| SIM | [Estrutura_do_SIM_2025.pdf](ftp://ftp.datasus.gov.br/dissemin/publicos/SIM/CID10/DOCS/Estrutura_do_SIM_2025.pdf) | `sim-b4195ac8e0f8` |
| SINASC | [Estrutura_SINASC_para_CD.pdf](ftp://ftp.datasus.gov.br/dissemin/publicos/SINASC/NOV/DOCS/Estrutura_SINASC_para_CD.pdf) | `sinasc-24e0d4388ea1` |
| SINAN | [DIC_DADOS_Chagas_v5.pdf](https://portalsinan.saude.gov.br/images/documentos/Agravos/Chagas/DIC_DADOS_Chagas_v5.pdf) | `sinan-16c598f86fbf` |
| SINAN | [DIC_DADOS_Notificacao_Individual_v5.pdf](https://portalsinan.saude.gov.br/images/documentos/Agravos/NINDIV/DIC_DADOS_Notificacao_Individual_v5.pdf) | `sinan-b3e0561c7a2d` |
| SIHSUS | [TAB_SIH.zip](ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Auxiliar/TAB_SIH.zip) | `sih-tab-714ed980d483` |
| SIM | [Dicionário DOM (+ investigação materna)](https://svs.aids.gov.br/daent/cgiae/coesv/sistemas-informacao/sim/documentacao/dicionario-de-dados-SIM-tabela-DOM.pdf) | `sim-dom-fb396a277981` |
| SIM | [Estrutura SIM anterior — Mortalidade 2006](ftp://ftp.datasus.gov.br/dissemin/publicos/SIM/CID10/DOCS/Estrutura_SIM_Anterior.pdf) | `sim-anterior-13cabba0b9a1` |

## Rastreamento no repositório

As tabelas e todas as colunas estão em `reports/2026-09-10-mapa-datasus/tabelas.csv` e `colunas.csv`.
A auditoria detalhada está em `auditoria_colunas.csv`, `auditoria_fontes.json` e
`AUDITORIA_DICIONARIOS.md` na mesma pasta. Esses relatórios são o retrato histórico
usado nesta projeção; não são regenerados aqui.

O [exemplo de contrato](exemplos/sim_obitos.sexo.json) acrescenta uma checagem pontual
do campo SEXO no documento SIM de 2025, com aplicabilidade histórica pendente.
Ele não promove os demais campos a revisados nem muda as contagens da auditoria.
