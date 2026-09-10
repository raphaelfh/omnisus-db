# Mapa do acervo didático DATASUS

Coleta iniciada em **2026-09-10T16:23:22.600941+00:00** e encerrada em **2026-09-10T16:25:53.791920+00:00**.

**18 categorias**, **17 com amostras tabulares**, **1 de aplicativo**, **0 falhas**. Foram extraídas **65 tabelas**, **1326 ocorrências de colunas** e **9,784 linhas de amostra**. Os arquivos escolhidos somam **42.84 MiB**.

## Alcance e leitura correta

- Uma amostra por categoria do seletor. Isso **não cobre todos os subtipos, agravos, anos ou UFs** do DATASUS.
- Cada DBC/ZIP escolhido foi baixado inteiro. As tabelas exportadas contêm somente as primeiras 200 linhas ativas de cada tabela, ou todas quando há menos registros.
- O inventário se refere ao diretório listado e os descritores de colunas se referem ao arquivo amostrado. Não extrapole esse esquema para todos os arquivos da categoria.
- Campos são mantidos como texto bruto (Latin-1 nos DBFs), preservando zeros à esquerda, datas e códigos. Tipo DBF, largura e casas decimais são descritores físicos; String é o tipo da amostra.
- Nulos e valores distintos são calculados somente na amostra. Os totais de registros ativos/excluídos vêm da geometria e dos marcadores físicos do DBF, cuja integridade foi conferida.
- Arquivos nacionais e estaduais do IBGE se sobrepõem. Linhas de tabelas diferentes não são somáveis como pessoas únicas; códigos homônimos não comprovam que uma junção é válida.
- Documentação e descritores físicos não equivalem a um dicionário semântico validado. Significados, unidades e categorias clínicas exigem a documentação específica.
- ZIPs são inspecionados sem executar seus programas. Na Base Territorial, DBF é preferido às cópias CSV/XML/TXT da mesma tabela. Todos os membros permanecem no inventário do ZIP.

Fontes: [seletor de transferência DATASUS](https://datasus.saude.gov.br/transferencia-de-arquivos/) e [definições de categorias e subtipos do portal](https://datasus.saude.gov.br/wp-content/transferencia.js). O manifesto registra URLs exatas de cada arquivo e SHA-256.

## Visão geral

| categoria | subtipo_amostrado | status | arquivo | bytes | tabelas | colunas | linhas_amostradas |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DATASUS | TABWIN | artefato | TAB415.zip | 15670769 | 0 | 0 | 0 |
| IBGE | POPT | amostra | POPTBR23.zip | 77027 | 28 | 84 | 3754 |
| Base Territorial | TER | amostra | 04-base_territorial_abr26.zip | 1730744 | 22 | 111 | 3394 |
| CIH | CR | amostra | CRCE1103.dbc | 10001 | 1 | 27 | 200 |
| CIHA | CIHA | amostra | CIHADF2211.dbc | 10006 | 1 | 30 | 200 |
| CNES | ST | amostra | STRR2301.dbc | 40745 | 1 | 208 | 200 |
| ESUSNOTIFICA | DCCR | amostra | DCCRBR23.dbc | 705678 | 1 | 109 | 200 |
| PCE | PCE | amostra | PCEAL23.dbc | 9622 | 1 | 35 | 200 |
| PO | PO | amostra | POBR2023.dbc | 23767771 | 1 | 23 | 200 |
| RESP | RESP | amostra | RESPRR23.dbc | 2879 | 1 | 78 | 3 |
| SIASUS | PA | amostra | PARR2301.dbc | 1156052 | 1 | 60 | 200 |
| SIHSUS | RD | amostra | RDRR2301.dbc | 349244 | 1 | 113 | 200 |
| SIM | DO | amostra | DORR2023.dbc | 288798 | 1 | 87 | 200 |
| SINAN | CHAG | amostra | CHAGBR23.dbc | 411945 | 1 | 108 | 200 |
| SINASC | DN | amostra | DNRR2023.dbc | 627526 | 1 | 61 | 200 |
| SISCOLO | CC | amostra | CCRR1301.dbc | 53230 | 1 | 102 | 200 |
| SISMAMA | CM | amostra | CMSP1409.dbc | 10292 | 1 | 54 | 200 |
| SISPRENATAL | PN | amostra | PNRR1301.dbc | 2551 | 1 | 36 | 33 |

## Arquivos para consulta

- [Fontes e arquivos](fontes.csv)
- [Mapa de tabelas](tabelas.csv)
- [Todas as colunas e descritores](colunas.csv)
- [Membros dos ZIPs](membros_zip.csv)
- [Mapa estruturado completo](mapa.json)
- [Subtipos descritos pelo portal, incluindo não amostrados](subtipos_portal.csv)

## Como escolher o próximo estudo

Use o esquema para formular uma pergunta, examine o dicionário específico e só então decida o recorte a importar por inteiro. Comece pela unidade de observação: cadastro, exame, notificação, produção, população e território possuem denominadores distintos. Amostras de conveniência servem para aprender a estrutura, não para inferência populacional.

## DATASUS — Aplicativos TABWIN/TABNET

**Natureza:** aplicativo · **Subtipo escolhido:** `TABWIN` · **Status:** artefato.

**Pergunta de estudo:** Quais mapas, documentos e programas acompanham o tabulador?

**Limitação:** O pacote TABWIN representa esta categoria; não é uma base de pacientes. Executáveis não são executados.

**Inventário:** `/tabwin/tabwin`; 5 arquivos no diretório, 2 candidatos do subtipo dentro do limite de tamanho.

**Arquivo:** [TAB415.zip](ftp://ftp.datasus.gov.br/tabwin/tabwin/TAB415.zip) · 15,670,769 bytes.

**Coleta UTC:** `2026-09-10T16:23:27.111386+00:00` · **Modificação informada pelo FTP (sem fuso):** `2018-08-08T13:28:00`.

**SHA-256:** `a7371b19292f368212575d9bb59e261c95b3135c46a1294bc370f04ba21192e6`

**Original local:** `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/DATASUS/TAB415.zip`

**Rótulos retornados pelo portal:** DATASUS / Programas.

### Conteúdo do ZIP

| arquivo | bytes | comprimidos | diretorio |
| --- | --- | --- | --- |
| MAPAS/ | 0 | 0 | True |
| MAPAS/ac_municip.MAP | 39458 | 25029 | False |
| MAPAS/al_municip.MAP | 39986 | 23510 | False |
| MAPAS/am_municip.MAP | 210506 | 168366 | False |
| MAPAS/ap_municip.MAP | 49242 | 33491 | False |
| MAPAS/ba_municip.MAP | 363874 | 284509 | False |
| MAPAS/br_divadm.MAP | 878058 | 601985 | False |
| MAPAS/br_frontfaixa.MAP | 725570 | 509094 | False |
| MAPAS/br_frontzona.MAP | 254498 | 190006 | False |
| MAPAS/br_macsaud.MAP | 849578 | 608926 | False |
| MAPAS/br_micibge.MAP | 1910218 | 1187114 | False |
| MAPAS/br_municip.MAP | 4987642 | 3796680 | False |
| MAPAS/br_regiao.MAP | 232610 | 196831 | False |
| MAPAS/br_regmetr.MAP | 790170 | 600321 | False |
| MAPAS/br_regsaud.MAP | 1756490 | 1205838 | False |
| MAPAS/br_semiarido.MAP | 757866 | 529678 | False |
| MAPAS/br_uf.MAP | 443058 | 317318 | False |
| MAPAS/br_ufsigla.MAP | 443058 | 317093 | False |
| MAPAS/ce_municip.MAP | 138250 | 101969 | False |
| MAPAS/df_municip.MAP | 1554 | 1171 | False |
| MAPAS/es_municip.MAP | 69714 | 45066 | False |
| MAPAS/go_municip.MAP | 276522 | 213895 | False |
| MAPAS/ma_municip.MAP | 195210 | 149861 | False |
| MAPAS/mg_municip.MAP | 818850 | 651488 | False |
| MAPAS/ms_municip.MAP | 146866 | 109442 | False |
| MAPAS/mt_municip.MAP | 315738 | 252896 | False |
| MAPAS/pa_municip.MAP | 290146 | 237585 | False |
| MAPAS/pb_municip.MAP | 93962 | 62402 | False |
| MAPAS/pe_municip.MAP | 100266 | 69516 | False |
| MAPAS/pi_municip.MAP | 121378 | 86825 | False |
| MAPAS/pr_municip.MAP | 291194 | 218603 | False |
| MAPAS/rj_municip.MAP | 71834 | 48393 | False |
| MAPAS/rn_municip.MAP | 59690 | 36421 | False |
| MAPAS/ro_municip.MAP | 79994 | 55238 | False |
| MAPAS/rr_municip.MAP | 48610 | 33357 | False |
| MAPAS/rs_municip.MAP | 332266 | 255204 | False |
| MAPAS/sc_municip.MAP | 186866 | 136171 | False |
| MAPAS/se_municip.MAP | 36250 | 20162 | False |
| MAPAS/sp_municip.MAP | 432250 | 334689 | False |
| MAPAS/to_municip.MAP | 177634 | 139526 | False |
| autoexec.r | 276 | 175 | False |
| CarregaWayPoint.xsl | 1148 | 577 | False |
| dbf2dbc.exe | 46592 | 26824 | False |
| defcnv.htm | 16176 | 5381 | False |
| DocTabWin.htm | 60305 | 20503 | False |
| HISTORIA.TXT | 42265 | 14960 | False |
| IMPBORL.DLL | 12288 | 5022 | False |
| menu.r | 2813 | 916 | False |
| modelo.rx | 301 | 157 | False |
| msxsl.exe | 24896 | 13599 | False |
| sql2.gif | 20466 | 20040 | False |
| TabWin.ini | 317 | 208 | False |
| TABWIN32.CNT | 8660 | 2642 | False |
| Tabwin32.GID | 37615 | 5056 | False |
| Tabwin32.hlp | 4021986 | 817480 | False |
| TabWin415.exe | 1927680 | 873340 | False |

### Documentos textuais encontrados

| arquivo | bytes |
| --- | --- |
| HISTORIA.TXT | 42265 |

## IBGE — Base Populacional

**Natureza:** população · **Subtipo escolhido:** `POPT` · **Status:** amostra.

**Pergunta de estudo:** Quais códigos municipais e valores populacionais estão publicados?

**Limitação:** POPT é o produto distribuído pelo DATASUS. Tabelas BR e por UF se sobrepõem; não some as duas coberturas.

**Inventário:** `/dissemin/publicos/IBGE/POPTCU`; 33 arquivos no diretório, 33 candidatos do subtipo dentro do limite de tamanho.

**Arquivo:** [POPTBR23.zip](ftp://ftp.datasus.gov.br/dissemin/publicos/IBGE/POPTCU/POPTBR23.zip) · 77,027 bytes.

**Coleta UTC:** `2026-09-10T16:23:27.912522+00:00` · **Modificação informada pelo FTP (sem fuso):** `2025-01-07T09:38:00`.

**SHA-256:** `cd19b3aea860af8e4397cbb33d9b444b7ae40ee52d4a2bf7506779fba627b8f7`

**Original local:** `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip`

### Subtipos descritos no portal (nem todos foram amostrados)

| fonte | sigla_arquivo | desc_arquivo | abrangencia |
| --- | --- | --- | --- |
| IBGE | POP | POP - Censo e Estimativas - 1980 até 2012 | BR |
| IBGE | POPS | POPS - Estimativas por sexo e idade - 2000 até 2025 | BR |
| IBGE | POPT | POPT - Estimativas TCU - 1992 até 2025 | BR |

**Rótulos retornados pelo portal:** IBGE / Dados.

### Conteúdo do ZIP

| arquivo | bytes | comprimidos | diretorio |
| --- | --- | --- | --- |
| POPTRN23.dbf | 3469 | 1139 | False |
| POPTRO23.dbf | 1169 | 426 | False |
| POPTRR23.dbf | 429 | 191 | False |
| POPTRS23.dbf | 10069 | 3182 | False |
| POPTSC23.dbf | 6029 | 1970 | False |
| POPTSE23.dbf | 1629 | 579 | False |
| POPTSP23.dbf | 13029 | 4301 | False |
| POPTTO23.dbf | 2909 | 958 | False |
| POPTAC23.dbf | 569 | 238 | False |
| POPTAL23.dbf | 2169 | 744 | False |
| POPTAM23.dbf | 1369 | 498 | False |
| POPTAP23.dbf | 449 | 199 | False |
| POPTBA23.dbf | 8469 | 2758 | False |
| POPTBR23.dbf | 111529 | 35291 | False |
| POPTCE23.dbf | 3809 | 1276 | False |
| POPTDF23.dbf | 150 | 83 | False |
| POPTES23.dbf | 1689 | 605 | False |
| POPTGO23.dbf | 5049 | 1654 | False |
| POPTMA23.dbf | 4469 | 1472 | False |
| POPTMG23.dbf | 17189 | 5422 | False |
| POPTMS23.dbf | 1709 | 609 | False |
| POPTMT23.dbf | 2949 | 988 | False |
| POPTPA23.dbf | 3009 | 1037 | False |
| POPTPB23.dbf | 4589 | 1479 | False |
| POPTPE23.dbf | 3829 | 1303 | False |
| POPTPI23.dbf | 4609 | 1455 | False |
| POPTPR23.dbf | 8109 | 2629 | False |
| POPTRJ23.dbf | 1969 | 711 | False |

### Tabela `POPTRN23.dbf`

**Identificador:** `t000_POPTRN23` · **Campos:** 3 · **Linhas na amostra:** 167.

Registros declarados: **167**; ativos: **167**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t000_POPTRN23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 167 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 166 |

### Tabela `POPTRO23.dbf`

**Identificador:** `t001_POPTRO23` · **Campos:** 3 · **Linhas na amostra:** 52.

Registros declarados: **52**; ativos: **52**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t001_POPTRO23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 52 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 52 |

### Tabela `POPTRR23.dbf`

**Identificador:** `t002_POPTRR23` · **Campos:** 3 · **Linhas na amostra:** 15.

Registros declarados: **15**; ativos: **15**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t002_POPTRR23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 15 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 15 |

### Tabela `POPTRS23.dbf`

**Identificador:** `t003_POPTRS23` · **Campos:** 3 · **Linhas na amostra:** 200.

Registros declarados: **497**; ativos: **497**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t003_POPTRS23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 200 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 200 |

### Tabela `POPTSC23.dbf`

**Identificador:** `t004_POPTSC23` · **Campos:** 3 · **Linhas na amostra:** 200.

Registros declarados: **295**; ativos: **295**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t004_POPTSC23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 200 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 199 |

### Tabela `POPTSE23.dbf`

**Identificador:** `t005_POPTSE23` · **Campos:** 3 · **Linhas na amostra:** 75.

Registros declarados: **75**; ativos: **75**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t005_POPTSE23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 75 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 75 |

### Tabela `POPTSP23.dbf`

**Identificador:** `t006_POPTSP23` · **Campos:** 3 · **Linhas na amostra:** 200.

Registros declarados: **645**; ativos: **645**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t006_POPTSP23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 200 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 200 |

### Tabela `POPTTO23.dbf`

**Identificador:** `t007_POPTTO23` · **Campos:** 3 · **Linhas na amostra:** 139.

Registros declarados: **139**; ativos: **139**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t007_POPTTO23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 139 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 139 |

### Tabela `POPTAC23.dbf`

**Identificador:** `t008_POPTAC23` · **Campos:** 3 · **Linhas na amostra:** 22.

Registros declarados: **22**; ativos: **22**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t008_POPTAC23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 22 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 22 |

### Tabela `POPTAL23.dbf`

**Identificador:** `t009_POPTAL23` · **Campos:** 3 · **Linhas na amostra:** 102.

Registros declarados: **102**; ativos: **102**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t009_POPTAL23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 102 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 102 |

### Tabela `POPTAM23.dbf`

**Identificador:** `t010_POPTAM23` · **Campos:** 3 · **Linhas na amostra:** 62.

Registros declarados: **62**; ativos: **62**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t010_POPTAM23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 62 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 62 |

### Tabela `POPTAP23.dbf`

**Identificador:** `t011_POPTAP23` · **Campos:** 3 · **Linhas na amostra:** 16.

Registros declarados: **16**; ativos: **16**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t011_POPTAP23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 16 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 16 |

### Tabela `POPTBA23.dbf`

**Identificador:** `t012_POPTBA23` · **Campos:** 3 · **Linhas na amostra:** 200.

Registros declarados: **417**; ativos: **417**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t012_POPTBA23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 200 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 199 |

### Tabela `POPTBR23.dbf`

**Identificador:** `t013_POPTBR23` · **Campos:** 3 · **Linhas na amostra:** 200.

Registros declarados: **5570**; ativos: **5570**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t013_POPTBR23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 200 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 199 |

### Tabela `POPTCE23.dbf`

**Identificador:** `t014_POPTCE23` · **Campos:** 3 · **Linhas na amostra:** 184.

Registros declarados: **184**; ativos: **184**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t014_POPTCE23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 184 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 184 |

### Tabela `POPTDF23.dbf`

**Identificador:** `t015_POPTDF23` · **Campos:** 3 · **Linhas na amostra:** 1.

Registros declarados: **1**; ativos: **1**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t015_POPTDF23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 1 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 1 |

### Tabela `POPTES23.dbf`

**Identificador:** `t016_POPTES23` · **Campos:** 3 · **Linhas na amostra:** 78.

Registros declarados: **78**; ativos: **78**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t016_POPTES23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 78 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 78 |

### Tabela `POPTGO23.dbf`

**Identificador:** `t017_POPTGO23` · **Campos:** 3 · **Linhas na amostra:** 200.

Registros declarados: **246**; ativos: **246**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t017_POPTGO23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 200 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 200 |

### Tabela `POPTMA23.dbf`

**Identificador:** `t018_POPTMA23` · **Campos:** 3 · **Linhas na amostra:** 200.

Registros declarados: **217**; ativos: **217**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t018_POPTMA23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 200 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 199 |

### Tabela `POPTMG23.dbf`

**Identificador:** `t019_POPTMG23` · **Campos:** 3 · **Linhas na amostra:** 200.

Registros declarados: **853**; ativos: **853**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t019_POPTMG23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 200 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 200 |

### Tabela `POPTMS23.dbf`

**Identificador:** `t020_POPTMS23` · **Campos:** 3 · **Linhas na amostra:** 79.

Registros declarados: **79**; ativos: **79**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t020_POPTMS23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 79 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 79 |

### Tabela `POPTMT23.dbf`

**Identificador:** `t021_POPTMT23` · **Campos:** 3 · **Linhas na amostra:** 141.

Registros declarados: **141**; ativos: **141**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t021_POPTMT23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 141 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 141 |

### Tabela `POPTPA23.dbf`

**Identificador:** `t022_POPTPA23` · **Campos:** 3 · **Linhas na amostra:** 144.

Registros declarados: **144**; ativos: **144**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t022_POPTPA23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 144 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 144 |

### Tabela `POPTPB23.dbf`

**Identificador:** `t023_POPTPB23` · **Campos:** 3 · **Linhas na amostra:** 200.

Registros declarados: **223**; ativos: **223**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t023_POPTPB23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 200 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 198 |

### Tabela `POPTPE23.dbf`

**Identificador:** `t024_POPTPE23` · **Campos:** 3 · **Linhas na amostra:** 185.

Registros declarados: **185**; ativos: **185**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t024_POPTPE23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 185 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 185 |

### Tabela `POPTPI23.dbf`

**Identificador:** `t025_POPTPI23` · **Campos:** 3 · **Linhas na amostra:** 200.

Registros declarados: **224**; ativos: **224**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t025_POPTPI23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 200 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 198 |

### Tabela `POPTPR23.dbf`

**Identificador:** `t026_POPTPR23` · **Campos:** 3 · **Linhas na amostra:** 200.

Registros declarados: **399**; ativos: **399**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t026_POPTPR23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 200 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 198 |

### Tabela `POPTRJ23.dbf`

**Identificador:** `t027_POPTRJ23` · **Campos:** 3 · **Linhas na amostra:** 92.

Registros declarados: **92**; ativos: **92**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/IBGE/POPTBR23.zip_amostras/t027_POPTRJ23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| MUNIC_RES | C | 7 | 0 | String | 0 | 92 |
| ANO | C | 4 | 0 | String | 0 | 1 |
| POPULACAO | N | 8 | 0 | String | 0 | 92 |

## Base Territorial — Mapas e conversões para tabulação

**Natureza:** território · **Subtipo escolhido:** `TER` · **Status:** amostra.

**Pergunta de estudo:** Que tabelas relacionam municípios, UFs e regiões?

**Limitação:** A edição territorial da amostra é explícita; códigos mudam entre edições. O ZIP de tabelas não cobre todos os mapas.

**Inventário:** `/territorio/tabelas/2026`; 3 arquivos no diretório, 3 candidatos do subtipo dentro do limite de tamanho.

**Arquivo:** [04-base_territorial_abr26.zip](ftp://ftp.datasus.gov.br/territorio/tabelas/2026/04-base_territorial_abr26.zip) · 1,730,744 bytes.

**Coleta UTC:** `2026-09-10T16:23:59.645407+00:00` · **Modificação informada pelo FTP (sem fuso):** `2026-04-27T16:34:00`.

**SHA-256:** `91274730129b8dff5e0afe485b01698da74ab5cee080cf3c3b123b31664a5489`

**Original local:** `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip`

**Falha de consulta ao portal:** HTTPStatusError: Server error '503 Service Unavailable' for url 'https://datasus.saude.gov.br/wp-content/ftp.php'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/503. Listagem FTP usada explicitamente.

### Conteúdo do ZIP

| arquivo | bytes | comprimidos | diretorio |
| --- | --- | --- | --- |
| tb_uf.csv | 3236 | 927 | False |
| tb_terrcid_layout.txt | 161 | 124 | False |
| tb_terrcid.xml | 30023 | 3348 | False |
| tb_terrcid.txt | 14208 | 3085 | False |
| tb_terrcid.dbf | 14517 | 3177 | False |
| tb_terrcid.csv | 9298 | 2962 | False |
| tb_regsaud_layout.txt | 189 | 133 | False |
| tb_regsaud.xml | 112719 | 12283 | False |
| tb_regsaud.txt | 33496 | 10389 | False |
| tb_regsaud.dbf | 80844 | 11792 | False |
| tb_regsaud.csv | 34125 | 10502 | False |
| tb_regmetr_layout.txt | 213 | 144 | False |
| tb_regmetr.xml | 32895 | 2590 | False |
| tb_regmetr.txt | 11008 | 2148 | False |
| tb_regmetr.dbf | 18270 | 2374 | False |
| tb_regmetr.csv | 11008 | 2148 | False |
| tb_regiao_layout.txt | 186 | 129 | False |
| tb_regiao.xml | 1369 | 301 | False |
| tb_regiao.txt | 353 | 189 | False |
| tb_regiao.dbf | 550 | 244 | False |
| tb_regiao.csv | 353 | 189 | False |
| tb_pndr_layout.txt | 158 | 121 | False |
| tb_pndr.xml | 8429 | 891 | False |
| tb_pndr.txt | 4032 | 747 | False |
| tb_pndr.dbf | 4184 | 827 | False |
| tb_pndr.csv | 2793 | 742 | False |
| tb_municip_layout.txt | 728 | 340 | False |
| tb_municip.xml | 4352329 | 329454 | False |
| tb_municip.txt | 722850 | 266201 | False |
| tb_municip.dbf | 1151527 | 292414 | False |
| tb_municip.csv | 722850 | 266214 | False |
| tb_mis.xml | 12097 | 414 | False |
| tb_mis.txt | 6026 | 314 | False |
| tb_mis.dbf | 5939 | 349 | False |
| tb_mis.csv | 6241 | 325 | False |
| tb_micibge_layout.txt | 189 | 133 | False |
| tb_micibge.xml | 135419 | 14550 | False |
| tb_micibge.txt | 36132 | 12209 | False |
| tb_micibge.dbf | 65050 | 13672 | False |
| tb_micibge.csv | 36439 | 12350 | False |
| tb_macsaud_layout.txt | 189 | 134 | False |
| tb_macsaud.xml | 38990 | 3249 | False |
| tb_macsaud.txt | 10423 | 2477 | False |
| tb_macsaud.dbf | 20050 | 2929 | False |
| tb_macsaud.csv | 10533 | 2512 | False |
| tb_dsei_layout.txt | 130 | 103 | False |
| tb_dsei.xml | 5672 | 1181 | False |
| tb_dsei.txt | 3230 | 1001 | False |
| tb_dsei.dbf | 3358 | 1076 | False |
| tb_dsei.csv | 2114 | 993 | False |
| tb_divadmant.dbf | 31546 | 5671 | False |
| tb_divadm_layout.txt | 188 | 133 | False |
| tb_divadm.xml | 59209 | 6055 | False |
| tb_divadm.txt | 31581 | 5570 | False |
| tb_divadm.dbf | 31546 | 5671 | False |
| tb_divadm.csv | 18427 | 5017 | False |
| rl_regsaud_macsaud_layout.txt | 78 | 69 | False |
| rl_regsaud_macsaud.xml | 37906 | 1667 | False |
| rl_regsaud_macsaud.txt | 5303 | 1169 | False |
| rl_regsaud_macsaud.dbf | 4498 | 1154 | False |
| rl_regsaud_macsaud.csv | 5310 | 1178 | False |
| rl_municip_terrcid_layout.txt | 78 | 72 | False |
| rl_municip_terrcid.xml | 159252 | 6763 | False |
| rl_municip_terrcid.txt | 62249 | 14504 | False |
| rl_municip_terrcid.dbf | 18608 | 5010 | False |
| rl_municip_terrcid.csv | 29643 | 5332 | False |
| rl_municip_regsaud_layout.txt | 79 | 73 | False |
| rl_municip_regsaud.xml | 490402 | 19946 | False |
| rl_municip_regsaud.txt | 78031 | 15636 | False |
| rl_municip_regsaud.dbf | 66962 | 15372 | False |
| rl_municip_regsaud.csv | 78031 | 15637 | False |
| rl_municip_regmetr_layout.txt | 79 | 73 | False |
| rl_municip_regmetr.xml | 475726 | 17212 | False |
| rl_municip_regmetr.txt | 72770 | 13552 | False |
| rl_municip_regmetr.dbf | 61654 | 12978 | False |
| rl_municip_regmetr.csv | 72770 | 13553 | False |
| rl_municip_pndr_layout.txt | 75 | 69 | False |
| rl_municip_pndr.xml | 93186 | 3837 | False |
| rl_municip_pndr.txt | 62249 | 12789 | False |
| rl_municip_pndr.dbf | 11738 | 2844 | False |
| rl_municip_pndr.csv | 18648 | 2986 | False |
| rl_municip_micibge_layout.txt | 79 | 71 | False |
| rl_municip_micibge.xml | 492602 | 19505 | False |
| rl_municip_micibge.txt | 78381 | 15463 | False |
| rl_municip_micibge.dbf | 67262 | 15257 | False |
| rl_municip_micibge.csv | 78381 | 15462 | False |
| rl_municip_macsaud_layout.txt | 79 | 72 | False |
| rl_municip_macsaud.xml | 487005 | 18556 | False |
| rl_municip_macsaud.txt | 72784 | 14705 | False |
| rl_municip_macsaud.dbf | 61665 | 14479 | False |
| rl_municip_macsaud.csv | 72784 | 14704 | False |
| rl_municip_dsei_layout.txt | 75 | 69 | False |
| rl_municip_dsei.xml | 18466 | 1040 | False |
| rl_municip_dsei.txt | 2530 | 686 | False |
| rl_municip_dsei.dbf | 2398 | 743 | False |
| rl_municip_dsei.csv | 3704 | 758 | False |
| rl_municip_divadm_layout.txt | 82 | 74 | False |
| rl_municip_divadm.xml | 480996 | 20115 | False |
| rl_municip_divadm.txt | 67896 | 16004 | False |
| rl_municip_divadm.dbf | 62336 | 15699 | False |
| rl_municip_divadm.csv | 96186 | 16335 | False |
| tb_uf_layout.txt | 268 | 170 | False |
| tb_uf.xml | 7537 | 1071 | False |
| tb_uf.txt | 1454 | 804 | False |
| tb_uf.dbf | 3277 | 936 | False |

### Tabela `tb_terrcid.dbf`

**Identificador:** `t000_tb_terrcid` · **Campos:** 5 · **Linhas na amostra:** 148.

Registros declarados: **148**; ativos: **148**; excluídos: **0**. Reparo do terminador DBF: **True**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip_amostras/t000_tb_terrcid.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_TERRCID | C | 3 | 0 | String | 0 | 148 |
| DS_NOME | C | 42 | 0 | String | 0 | 148 |
| DS_NOMEPAD | C | 42 | 0 | String | 0 | 148 |
| CO_STATUS | C | 6 | 0 | String | 0 | 2 |
| NU_ORDMAP | N | 1 | 0 | String | 0 | 2 |

### Tabela `tb_regsaud.dbf`

**Identificador:** `t001_tb_regsaud` · **Campos:** 6 · **Linhas na amostra:** 200.

Registros declarados: **466**; ativos: **466**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip_amostras/t001_tb_regsaud.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_REGSAUD | C | 5 | 0 | String | 0 | 200 |
| CO_STATUS | C | 1 | 0 | String | 0 | 1 |
| DS_NOME | C | 55 | 0 | String | 0 | 200 |
| DS_NOMEPAD | C | 55 | 0 | String | 0 | 200 |
| DS_ABREV | C | 55 | 0 | String | 0 | 200 |
| NU_ORDEM | N | 1 | 0 | String | 0 | 1 |

### Tabela `tb_regmetr.dbf`

**Identificador:** `t002_tb_regmetr` · **Campos:** 7 · **Linhas na amostra:** 114.

Registros declarados: **114**; ativos: **114**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip_amostras/t002_tb_regmetr.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_REGMETR | C | 4 | 0 | String | 0 | 114 |
| CO_STATUS | C | 1 | 0 | String | 0 | 2 |
| CO_TIPO | C | 1 | 0 | String | 0 | 2 |
| DS_NOME | C | 50 | 0 | String | 0 | 114 |
| DS_NOMEPAD | C | 50 | 0 | String | 0 | 114 |
| DS_ABREV | C | 50 | 0 | String | 0 | 114 |
| NU_ORDEM | N | 1 | 0 | String | 0 | 2 |

### Tabela `tb_regiao.dbf`

**Identificador:** `t003_tb_regiao` · **Campos:** 6 · **Linhas na amostra:** 6.

Registros declarados: **6**; ativos: **6**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip_amostras/t003_tb_regiao.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_REGIAO | N | 1 | 0 | String | 0 | 6 |
| CO_STATUS | C | 5 | 0 | String | 0 | 2 |
| DS_NOME | C | 19 | 0 | String | 0 | 6 |
| DS_NOMEPAD | C | 19 | 0 | String | 0 | 6 |
| DS_ABREV | C | 8 | 0 | String | 0 | 6 |
| NU_ORDEM | N | 1 | 0 | String | 0 | 2 |

### Tabela `tb_pndr.dbf`

**Identificador:** `t004_tb_pndr` · **Campos:** 5 · **Linhas na amostra:** 42.

Registros declarados: **42**; ativos: **42**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip_amostras/t004_tb_pndr.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_PNDR | C | 3 | 0 | String | 0 | 42 |
| DS_NOME | C | 42 | 0 | String | 0 | 42 |
| DS_NOMEPAD | C | 42 | 0 | String | 0 | 42 |
| CO_STATUS | C | 6 | 0 | String | 0 | 2 |
| NU_ORDMAP | N | 1 | 0 | String | 0 | 2 |

### Tabela `tb_municip.dbf`

**Identificador:** `t005_tb_municip` · **Campos:** 24 · **Linhas na amostra:** 200.

Registros declarados: **5725**; ativos: **5725**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip_amostras/t005_tb_municip.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_MUNICIP | C | 6 | 0 | String | 0 | 200 |
| CO_MUNICDV | C | 7 | 0 | String | 0 | 200 |
| CO_STATUS | C | 7 | 0 | String | 0 | 2 |
| CO_TIPO | C | 7 | 0 | String | 0 | 2 |
| DS_NOME | C | 48 | 0 | String | 0 | 200 |
| DS_NOMEPAD | C | 48 | 0 | String | 0 | 200 |
| DS_OBSERV | C | 1 | 0 | String | 0 | 2 |
| CO_REGIAO | C | 1 | 0 | String | 0 | 1 |
| CO_UF | C | 2 | 0 | String | 0 | 5 |
| CO_ALTER | C | 1 | 0 | String | 200 | 1 |
| CO_ALTERDV | C | 1 | 0 | String | 200 | 1 |
| IN_CAPITAL | C | 1 | 0 | String | 0 | 2 |
| IN_AMAZLEG | C | 1 | 0 | String | 0 | 1 |
| IN_SEMIAR | C | 1 | 0 | String | 0 | 1 |
| IN_FRONTZN | C | 1 | 0 | String | 0 | 2 |
| DT_INSTAL | C | 4 | 0 | String | 5 | 46 |
| DT_EXTIN | C | 4 | 0 | String | 200 | 1 |
| CO_SUCESS | C | 6 | 0 | String | 200 | 1 |
| NU_ORDEM | C | 1 | 0 | String | 200 | 1 |
| NU_ORDMAP | C | 1 | 0 | String | 200 | 1 |
| NU_LATITUD | C | 19 | 0 | String | 5 | 196 |
| NU_LONGIT | C | 18 | 0 | String | 5 | 196 |
| NU_ALTITUD | C | 4 | 0 | String | 5 | 107 |
| NU_AREA | C | 10 | 0 | String | 5 | 196 |

### Tabela `tb_mis.dbf`

**Identificador:** `t006_tb_mis` · **Campos:** 4 · **Linhas na amostra:** 53.

Registros declarados: **53**; ativos: **53**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip_amostras/t006_tb_mis.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_MIS | C | 3 | 0 | String | 0 | 1 |
| NOME_MIS | C | 98 | 0 | String | 0 | 1 |
| CO_MUNIC_I | C | 6 | 0 | String | 0 | 53 |
| NU_ORDEM | C | 1 | 0 | String | 0 | 1 |

### Tabela `tb_micibge.dbf`

**Identificador:** `t007_tb_micibge` · **Campos:** 6 · **Linhas na amostra:** 200.

Registros declarados: **584**; ativos: **584**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip_amostras/t007_tb_micibge.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_MICIBGE | C | 5 | 0 | String | 0 | 200 |
| CO_STATUS | C | 1 | 0 | String | 0 | 2 |
| DS_NOME | C | 41 | 0 | String | 0 | 200 |
| DS_NOMEPAD | C | 41 | 0 | String | 0 | 200 |
| DS_ABREV | C | 21 | 0 | String | 0 | 188 |
| NU_ORDEM | N | 1 | 0 | String | 0 | 2 |

### Tabela `tb_macsaud.dbf`

**Identificador:** `t008_tb_macsaud` · **Campos:** 6 · **Linhas na amostra:** 168.

Registros declarados: **168**; ativos: **168**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip_amostras/t008_tb_macsaud.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_MACSAUD | C | 4 | 0 | String | 0 | 168 |
| CO_STATUS | C | 1 | 0 | String | 0 | 2 |
| DS_NOME | C | 37 | 0 | String | 0 | 153 |
| DS_NOMEPAD | C | 37 | 0 | String | 0 | 153 |
| DS_ABREV | C | 37 | 0 | String | 0 | 154 |
| NU_ORDEM | N | 1 | 0 | String | 0 | 2 |

### Tabela `tb_dsei.dbf`

**Identificador:** `t009_tb_dsei` · **Campos:** 4 · **Linhas na amostra:** 34.

Registros declarados: **34**; ativos: **34**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip_amostras/t009_tb_dsei.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_DSEI | C | 3 | 0 | String | 0 | 34 |
| DS_NOME | C | 42 | 0 | String | 0 | 34 |
| DS_NOMEPAD | C | 42 | 0 | String | 0 | 34 |
| CO_SEDE | C | 6 | 0 | String | 0 | 33 |

### Tabela `tb_divadmant.dbf`

**Identificador:** `t010_tb_divadmant` · **Campos:** 6 · **Linhas na amostra:** 200.

Registros declarados: **261**; ativos: **261**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip_amostras/t010_tb_divadmant.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_DIVADM | C | 4 | 0 | String | 0 | 200 |
| CO_STATUS | C | 6 | 0 | String | 0 | 3 |
| DS_NOME | C | 42 | 0 | String | 0 | 200 |
| DS_NOMEPAD | C | 42 | 0 | String | 0 | 200 |
| DS_ABREV | C | 24 | 0 | String | 0 | 200 |
| NU_ORDEM | C | 1 | 0 | String | 0 | 3 |

### Tabela `tb_divadm.dbf`

**Identificador:** `t011_tb_divadm` · **Campos:** 6 · **Linhas na amostra:** 200.

Registros declarados: **261**; ativos: **261**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip_amostras/t011_tb_divadm.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_DIVADM | C | 4 | 0 | String | 0 | 200 |
| CO_STATUS | C | 6 | 0 | String | 0 | 3 |
| DS_NOME | C | 42 | 0 | String | 0 | 200 |
| DS_NOMEPAD | C | 42 | 0 | String | 0 | 200 |
| DS_ABREV | C | 24 | 0 | String | 0 | 200 |
| NU_ORDEM | C | 1 | 0 | String | 0 | 3 |

### Tabela `rl_regsaud_macsaud.dbf`

**Identificador:** `t012_rl_regsaud_macsaud` · **Campos:** 2 · **Linhas na amostra:** 200.

Registros declarados: **440**; ativos: **440**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip_amostras/t012_rl_regsaud_macsaud.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_REGSAUD | C | 5 | 0 | String | 0 | 199 |
| CO_MACRORR | C | 4 | 0 | String | 0 | 57 |

### Tabela `rl_municip_terrcid.dbf`

**Identificador:** `t013_rl_municip_terrcid` · **Campos:** 2 · **Linhas na amostra:** 200.

Registros declarados: **1851**; ativos: **1851**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip_amostras/t013_rl_municip_terrcid.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_MUNICIP | C | 6 | 0 | String | 0 | 200 |
| CO_TERRCID | C | 3 | 0 | String | 0 | 15 |

### Tabela `rl_municip_regsaud.dbf`

**Identificador:** `t014_rl_municip_regsaud` · **Campos:** 2 · **Linhas na amostra:** 200.

Registros declarados: **5572**; ativos: **5572**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip_amostras/t014_rl_municip_regsaud.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_MUNICIP | C | 6 | 0 | String | 0 | 200 |
| CO_REGSAUD | C | 5 | 0 | String | 0 | 25 |

### Tabela `rl_municip_regmetr.dbf`

**Identificador:** `t015_rl_municip_regmetr` · **Campos:** 2 · **Linhas na amostra:** 200.

Registros declarados: **5596**; ativos: **5596**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip_amostras/t015_rl_municip_regmetr.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_MUNICIP | C | 6 | 0 | String | 0 | 200 |
| CO_REGMET | C | 4 | 0 | String | 0 | 15 |

### Tabela `rl_municip_pndr.dbf`

**Identificador:** `t016_rl_municip_pndr` · **Campos:** 2 · **Linhas na amostra:** 200.

Registros declarados: **1164**; ativos: **1164**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip_amostras/t016_rl_municip_pndr.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_MUNICIP | C | 6 | 0 | String | 0 | 200 |
| CO_PNDR | C | 3 | 0 | String | 0 | 1 |

### Tabela `rl_municip_micibge.dbf`

**Identificador:** `t017_rl_municip_micibge` · **Campos:** 2 · **Linhas na amostra:** 200.

Registros declarados: **5597**; ativos: **5597**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip_amostras/t017_rl_municip_micibge.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_MUNICIP | C | 6 | 0 | String | 0 | 200 |
| CO_MICIBGE | C | 5 | 0 | String | 0 | 27 |

### Tabela `rl_municip_macsaud.dbf`

**Identificador:** `t018_rl_municip_macsaud` · **Campos:** 2 · **Linhas na amostra:** 200.

Registros declarados: **5597**; ativos: **5597**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip_amostras/t018_rl_municip_macsaud.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_MUNICIP | C | 6 | 0 | String | 0 | 200 |
| CO_MACSAUD | C | 4 | 0 | String | 0 | 16 |

### Tabela `rl_municip_dsei.dbf`

**Identificador:** `t019_rl_municip_dsei` · **Campos:** 2 · **Linhas na amostra:** 200.

Registros declarados: **230**; ativos: **230**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip_amostras/t019_rl_municip_dsei.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_MUNICIP | C | 6 | 0 | String | 0 | 191 |
| CO_DSEI | C | 3 | 0 | String | 0 | 29 |

### Tabela `rl_municip_divadm.dbf`

**Identificador:** `t020_rl_municip_divadm` · **Campos:** 2 · **Linhas na amostra:** 200.

Registros declarados: **5658**; ativos: **5658**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip_amostras/t020_rl_municip_divadm.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_MUNICIP | C | 6 | 0 | String | 0 | 200 |
| CO_DIVADM | C | 4 | 0 | String | 0 | 14 |

### Tabela `tb_uf.dbf`

**Identificador:** `t021_tb_uf` · **Campos:** 8 · **Linhas na amostra:** 29.

Registros declarados: **29**; ativos: **29**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/Base_Territorial/04-base_territorial_abr26.zip_amostras/t021_tb_uf.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_UF | N | 2 | 0 | String | 0 | 29 |
| DS_SIGLA | C | 2 | 0 | String | 0 | 29 |
| CO_STATUS | C | 6 | 0 | String | 0 | 3 |
| DS_NOME | C | 41 | 0 | String | 0 | 29 |
| DS_NOMEPAD | C | 41 | 0 | String | 0 | 29 |
| CO_SUCESS | N | 1 | 0 | String | 0 | 6 |
| CO_REGIAO | N | 8 | 0 | String | 0 | 28 |
| NU_AREA | N | 1 | 0 | String | 0 | 3 |

### Documentos textuais encontrados

| arquivo | bytes |
| --- | --- |
| tb_terrcid_layout.txt | 161 |
| tb_terrcid.txt | 14208 |
| tb_regsaud_layout.txt | 189 |
| tb_regsaud.txt | 33496 |
| tb_regmetr_layout.txt | 213 |
| tb_regmetr.txt | 11008 |
| tb_regiao_layout.txt | 186 |
| tb_regiao.txt | 353 |
| tb_pndr_layout.txt | 158 |
| tb_pndr.txt | 4032 |
| tb_municip_layout.txt | 728 |
| tb_municip.txt | 722850 |
| tb_mis.txt | 6026 |
| tb_micibge_layout.txt | 189 |
| tb_micibge.txt | 36132 |
| tb_macsaud_layout.txt | 189 |
| tb_macsaud.txt | 10423 |
| tb_dsei_layout.txt | 130 |
| tb_dsei.txt | 3230 |
| tb_divadm_layout.txt | 188 |
| tb_divadm.txt | 31581 |
| rl_regsaud_macsaud_layout.txt | 78 |
| rl_regsaud_macsaud.txt | 5303 |
| rl_municip_terrcid_layout.txt | 78 |
| rl_municip_terrcid.txt | 62249 |
| rl_municip_regsaud_layout.txt | 79 |
| rl_municip_regsaud.txt | 78031 |
| rl_municip_regmetr_layout.txt | 79 |
| rl_municip_regmetr.txt | 72770 |
| rl_municip_pndr_layout.txt | 75 |
| rl_municip_pndr.txt | 62249 |
| rl_municip_micibge_layout.txt | 79 |
| rl_municip_micibge.txt | 78381 |
| rl_municip_macsaud_layout.txt | 79 |
| rl_municip_macsaud.txt | 72784 |
| rl_municip_dsei_layout.txt | 75 |
| rl_municip_dsei.txt | 2530 |
| rl_municip_divadm_layout.txt | 82 |
| rl_municip_divadm.txt | 67896 |
| tb_uf_layout.txt | 268 |
| tb_uf.txt | 1454 |

## CIH — Comunicação de Informação Hospitalar

**Natureza:** registros · **Subtipo escolhido:** `CR` · **Status:** amostra.

**Pergunta de estudo:** Como são descritas as comunicações hospitalares históricas?

**Limitação:** Acervo histórico. Ausência de RR no recorte não significa ausência da base.

**Inventário:** `/dissemin/publicos/CIH/200801_201012/Dados`; 869 arquivos no diretório, 868 candidatos do subtipo dentro do limite de tamanho.

**Arquivo:** [CRCE1103.dbc](ftp://ftp.datasus.gov.br/dissemin/publicos/CIH/200801_201012/Dados/CRCE1103.dbc) · 10,001 bytes.

**Coleta UTC:** `2026-09-10T16:24:00.554175+00:00` · **Modificação informada pelo FTP (sem fuso):** `2016-11-04T11:06:00`.

**SHA-256:** `e2cf9fc1fc664f01b81e1e8930c9691e5b5df403af2c0d050d4110270f4dd068`

**Original local:** `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/CIH/CRCE1103.dbc`

### Subtipos descritos no portal (nem todos foram amostrados)

| fonte | sigla_arquivo | desc_arquivo | abrangencia |
| --- | --- | --- | --- |
| CIH | CR | CR - Comunicação de Internação Hospitalar - A partir de Jan/2008 | UF |

### Tabela `CRCE1103.dbc`

**Identificador:** `t000_CRCE1103` · **Campos:** 27 · **Linhas na amostra:** 200.

Registros declarados: **396**; ativos: **396**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/CIH/CRCE1103.dbc_amostras/t000_CRCE1103.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| ANO_CMPT | C | 4 | 0 | String | 0 | 1 |
| MES_CMPT | C | 2 | 0 | String | 0 | 1 |
| ESPEC | C | 2 | 0 | String | 200 | 1 |
| CGC_HOSP | C | 14 | 0 | String | 26 | 6 |
| MUNIC_RES | C | 6 | 0 | String | 0 | 29 |
| NASC | C | 8 | 0 | String | 0 | 192 |
| SEXO | C | 1 | 0 | String | 0 | 2 |
| UTI_MES_TO | C | 3 | 0 | String | 0 | 1 |
| UTI_INT_TO | C | 3 | 0 | String | 106 | 3 |
| PROC_REA | C | 10 | 0 | String | 0 | 55 |
| DT_INTER | C | 8 | 0 | String | 0 | 35 |
| DT_SAIDA | C | 8 | 0 | String | 0 | 31 |
| DIAG_PRINC | C | 4 | 0 | String | 0 | 96 |
| DIAG_SECUN | C | 4 | 0 | String | 197 | 3 |
| COBRANCA | C | 2 | 0 | String | 0 | 6 |
| NATUREZA | C | 2 | 0 | String | 0 | 1 |
| GESTAO | C | 1 | 0 | String | 0 | 1 |
| MUNIC_MOV | C | 6 | 0 | String | 0 | 4 |
| COD_IDADE | C | 1 | 0 | String | 0 | 3 |
| IDADE | C | 2 | 0 | String | 0 | 73 |
| DIAS_PERM | C | 5 | 0 | String | 0 | 12 |
| MORTE | C | 1 | 0 | String | 0 | 1 |
| NACIONAL | C | 3 | 0 | String | 200 | 1 |
| CAR_INT | C | 2 | 0 | String | 200 | 1 |
| HOMONIMO | C | 1 | 0 | String | 200 | 1 |
| CNES | C | 7 | 0 | String | 0 | 6 |
| FONTE | C | 2 | 0 | String | 0 | 3 |

## CIHA — Comunicação Hospitalar e Ambulatorial

**Natureza:** registros · **Subtipo escolhido:** `CIHA` · **Status:** amostra.

**Pergunta de estudo:** Que campos distinguem os atendimentos comunicados?

**Limitação:** Disponibilidade varia por UF e competência. Não equiparar a cobertura à do SIH.

**Inventário:** `/dissemin/publicos/CIHA/201101_/Dados`; 4798 arquivos no diretório, 4798 candidatos do subtipo dentro do limite de tamanho.

**Arquivo:** [CIHADF2211.dbc](ftp://ftp.datasus.gov.br/dissemin/publicos/CIHA/201101_/Dados/CIHADF2211.dbc) · 10,006 bytes.

**Coleta UTC:** `2026-09-10T16:24:01.415903+00:00` · **Modificação informada pelo FTP (sem fuso):** `2026-09-08T16:25:00`.

**SHA-256:** `599e2aaf1cf1e3c42adee9945a76ab6cd563681d3cc061ac6d8db61b873b2e8d`

**Original local:** `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/CIHA/CIHADF2211.dbc`

### Subtipos descritos no portal (nem todos foram amostrados)

| fonte | sigla_arquivo | desc_arquivo | abrangencia |
| --- | --- | --- | --- |
| CIHA | CIHA | CIHA - Comunicação de Internação Hospitalar e Ambulatorial - A partir de Jan/2011 | UF |

### Tabela `CIHADF2211.dbc`

**Identificador:** `t000_CIHADF2211` · **Campos:** 30 · **Linhas na amostra:** 200.

Registros declarados: **473**; ativos: **473**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/CIHA/CIHADF2211.dbc_amostras/t000_CIHADF2211.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| ANO_CMPT | C | 4 | 0 | String | 0 | 1 |
| MES_CMPT | C | 2 | 0 | String | 0 | 1 |
| ESPEC | C | 2 | 0 | String | 200 | 1 |
| CGC_HOSP | C | 14 | 0 | String | 0 | 3 |
| MUNIC_RES | C | 6 | 0 | String | 70 | 2 |
| NASC | C | 8 | 0 | String | 70 | 112 |
| SEXO | C | 1 | 0 | String | 70 | 3 |
| UTI_MES_TO | C | 3 | 0 | String | 0 | 1 |
| UTI_INT_TO | C | 3 | 0 | String | 0 | 24 |
| PROC_REA | C | 10 | 0 | String | 0 | 69 |
| QT_PROC | C | 6 | 0 | String | 0 | 20 |
| DT_ATEND | C | 8 | 0 | String | 70 | 39 |
| DT_SAIDA | C | 8 | 0 | String | 70 | 30 |
| DIAG_PRINC | C | 4 | 0 | String | 91 | 53 |
| DIAG_SECUN | C | 4 | 0 | String | 200 | 1 |
| COBRANCA | C | 2 | 0 | String | 117 | 8 |
| NATUREZA | C | 2 | 0 | String | 200 | 1 |
| GESTAO | C | 1 | 0 | String | 0 | 1 |
| MUNIC_MOV | C | 6 | 0 | String | 0 | 1 |
| COD_IDADE | C | 1 | 0 | String | 70 | 3 |
| IDADE | C | 2 | 0 | String | 70 | 57 |
| DIAS_PERM | C | 5 | 0 | String | 70 | 25 |
| MORTE | C | 1 | 0 | String | 70 | 3 |
| NACIONAL | C | 3 | 0 | String | 200 | 1 |
| CAR_INT | C | 2 | 0 | String | 200 | 1 |
| HOMONIMO | C | 1 | 0 | String | 200 | 1 |
| CNES | C | 7 | 0 | String | 0 | 3 |
| FONTE | C | 2 | 0 | String | 0 | 6 |
| CGC_CONSOR | C | 14 | 0 | String | 70 | 7 |
| MODALIDADE | C | 2 | 0 | String | 0 | 3 |

## CNES — Cadastro Nacional de Estabelecimentos de Saúde

**Natureza:** cadastro · **Subtipo escolhido:** `ST` · **Status:** amostra.

**Pergunta de estudo:** Que atributos descrevem um estabelecimento na competência?

**Limitação:** A amostra ST cobre estabelecimentos; outros subtipos, como equipes e leitos, não são amostrados.

**Inventário:** `/dissemin/publicos/CNES/200508_/Dados/ST`; 6804 arquivos no diretório, 6804 candidatos do subtipo dentro do limite de tamanho.

**Arquivo:** [STRR2301.dbc](ftp://ftp.datasus.gov.br/dissemin/publicos/CNES/200508_/Dados/ST/STRR2301.dbc) · 40,745 bytes.

**Coleta UTC:** `2026-09-10T16:24:02.368171+00:00` · **Modificação informada pelo FTP (sem fuso):** `2023-02-17T07:31:00`.

**SHA-256:** `21317fb046d6790d4143b39e1b300caff5b151d7cde368b62175871f8091d03a`

**Original local:** `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/CNES/STRR2301.dbc`

### Subtipos descritos no portal (nem todos foram amostrados)

| fonte | sigla_arquivo | desc_arquivo | abrangencia |
| --- | --- | --- | --- |
| CNES | LT | LT - Leitos - A partir de Out/2005 | UF |
| CNES | ST | ST - Estabelecimentos - A partir de Ago/2005 | UF |
| CNES | DC | DC - Dados Complementares - A partir de Ago/2005 | UF |
| CNES | EQ | EQ - Equipamentos - A partir de Ago/2005 | UF |
| CNES | SR | SR - Serviço Especializado - A partir de Ago/2005 | UF |
| CNES | HB | HB - Habilitação - A partir de Mar/2007 | UF |
| CNES | PF | PF - Profissional - A partir de Ago/2005 | UF |
| CNES | EP | EP - Equipes - A partir de Abr/2007 | UF |
| CNES | RC | RC - Regra Contratual - A partir de Mar/2007 | UF |
| CNES | IN | IN - Incentivos - A partir de Nov/2007 | UF |
| CNES | EE | EE - Estabelecimento de Ensino - A partir de Mar/2007 | UF |
| CNES | EF | EF - Estabelecimento Filantrópico - A partir de Mar/2007 | UF |
| CNES | GM | GM - Gestão e Metas - A partir de Jun/2007 | UF |

**Rótulos retornados pelo portal:** CNES / Dados.

### Tabela `STRR2301.dbc`

**Identificador:** `t000_STRR2301` · **Campos:** 208 · **Linhas na amostra:** 200.

Registros declarados: **886**; ativos: **886**; excluídos: **0**. Reparo do terminador DBF: **True**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/CNES/STRR2301.dbc_amostras/t000_STRR2301.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CNES | C | 7 | 0 | String | 0 | 200 |
| CODUFMUN | C | 6 | 0 | String | 0 | 3 |
| COD_CEP | C | 8 | 0 | String | 0 | 70 |
| CPF_CNPJ | C | 14 | 0 | String | 0 | 68 |
| PF_PJ | C | 1 | 0 | String | 0 | 2 |
| NIV_DEP | C | 1 | 0 | String | 0 | 2 |
| CNPJ_MAN | C | 14 | 0 | String | 0 | 8 |
| COD_IR | C | 2 | 0 | String | 200 | 1 |
| REGSAUDE | C | 4 | 0 | String | 199 | 2 |
| MICR_REG | C | 6 | 0 | String | 200 | 1 |
| DISTRSAN | C | 4 | 0 | String | 200 | 1 |
| DISTRADM | C | 4 | 0 | String | 200 | 1 |
| VINC_SUS | C | 1 | 0 | String | 0 | 2 |
| TPGESTAO | C | 1 | 0 | String | 0 | 3 |
| ESFERA_A | C | 2 | 0 | String | 200 | 1 |
| RETENCAO | C | 2 | 0 | String | 200 | 1 |
| ATIVIDAD | C | 2 | 0 | String | 0 | 1 |
| NATUREZA | C | 2 | 0 | String | 200 | 1 |
| CLIENTEL | C | 2 | 0 | String | 0 | 3 |
| TP_UNID | C | 2 | 0 | String | 0 | 22 |
| TURNO_AT | C | 2 | 0 | String | 0 | 6 |
| NIV_HIER | C | 2 | 0 | String | 200 | 1 |
| TP_PREST | C | 2 | 0 | String | 0 | 1 |
| CO_BANCO | C | 4 | 0 | String | 191 | 6 |
| CO_AGENC | C | 5 | 0 | String | 191 | 8 |
| C_CORREN | C | 14 | 0 | String | 191 | 10 |
| CONTRATM | C | 11 | 0 | String | 200 | 1 |
| DT_PUBLM | C | 8 | 0 | String | 200 | 1 |
| CONTRATE | C | 11 | 0 | String | 200 | 1 |
| DT_PUBLE | C | 8 | 0 | String | 200 | 1 |
| ALVARA | C | 25 | 0 | String | 159 | 42 |
| DT_EXPED | C | 8 | 0 | String | 161 | 37 |
| ORGEXPED | C | 2 | 0 | String | 152 | 3 |
| AV_ACRED | C | 1 | 0 | String | 200 | 1 |
| CLASAVAL | C | 1 | 0 | String | 200 | 1 |
| DT_ACRED | C | 6 | 0 | String | 200 | 1 |
| AV_PNASS | C | 1 | 0 | String | 200 | 1 |
| DT_PNASS | C | 6 | 0 | String | 200 | 1 |
| GESPRG1E | C | 1 | 0 | String | 0 | 2 |
| GESPRG1M | C | 1 | 0 | String | 0 | 2 |
| GESPRG2E | C | 1 | 0 | String | 0 | 2 |
| GESPRG2M | C | 1 | 0 | String | 0 | 2 |
| GESPRG4E | C | 1 | 0 | String | 0 | 2 |
| GESPRG4M | C | 1 | 0 | String | 0 | 1 |
| NIVATE_A | C | 1 | 0 | String | 0 | 2 |
| GESPRG3E | C | 1 | 0 | String | 0 | 1 |
| GESPRG3M | C | 1 | 0 | String | 0 | 1 |
| GESPRG5E | C | 1 | 0 | String | 0 | 2 |
| GESPRG5M | C | 1 | 0 | String | 0 | 2 |
| GESPRG6E | C | 1 | 0 | String | 0 | 2 |
| GESPRG6M | C | 1 | 0 | String | 0 | 2 |
| NIVATE_H | C | 1 | 0 | String | 0 | 2 |
| QTLEITP1 | N | 4 | 0 | String | 0 | 5 |
| QTLEITP2 | N | 4 | 0 | String | 0 | 7 |
| QTLEITP3 | N | 4 | 0 | String | 0 | 6 |
| LEITHOSP | C | 1 | 0 | String | 0 | 2 |
| QTINST01 | N | 3 | 0 | String | 0 | 2 |
| QTINST02 | N | 3 | 0 | String | 0 | 1 |
| QTINST03 | N | 3 | 0 | String | 0 | 1 |
| QTINST04 | N | 3 | 0 | String | 0 | 3 |
| QTINST05 | N | 3 | 0 | String | 0 | 2 |
| QTINST06 | N | 3 | 0 | String | 0 | 1 |
| QTINST07 | N | 3 | 0 | String | 0 | 1 |
| QTINST08 | N | 3 | 0 | String | 0 | 4 |
| QTINST09 | N | 3 | 0 | String | 0 | 2 |
| QTINST10 | N | 3 | 0 | String | 0 | 2 |
| QTINST11 | N | 3 | 0 | String | 0 | 2 |
| QTINST12 | N | 3 | 0 | String | 0 | 2 |
| QTINST13 | N | 3 | 0 | String | 0 | 3 |
| QTINST14 | N | 3 | 0 | String | 0 | 6 |
| URGEMERG | C | 1 | 0 | String | 0 | 2 |
| QTINST15 | N | 3 | 0 | String | 0 | 7 |
| QTINST16 | N | 3 | 0 | String | 0 | 9 |
| QTINST17 | N | 3 | 0 | String | 0 | 6 |
| QTINST18 | N | 3 | 0 | String | 0 | 8 |
| QTINST19 | N | 3 | 0 | String | 0 | 2 |
| QTINST20 | N | 3 | 0 | String | 0 | 2 |
| QTINST21 | N | 3 | 0 | String | 0 | 2 |
| QTINST22 | N | 3 | 0 | String | 0 | 2 |
| QTINST23 | N | 3 | 0 | String | 0 | 5 |
| QTINST24 | N | 3 | 0 | String | 0 | 3 |
| QTINST25 | N | 3 | 0 | String | 0 | 5 |
| QTINST26 | N | 3 | 0 | String | 0 | 2 |
| QTINST27 | N | 3 | 0 | String | 0 | 3 |
| QTINST28 | N | 3 | 0 | String | 0 | 2 |
| QTINST29 | N | 3 | 0 | String | 0 | 3 |
| QTINST30 | N | 3 | 0 | String | 0 | 2 |
| ATENDAMB | C | 1 | 0 | String | 0 | 2 |
| QTINST31 | N | 3 | 0 | String | 0 | 4 |
| QTINST32 | N | 3 | 0 | String | 0 | 2 |
| QTINST33 | N | 3 | 0 | String | 0 | 1 |
| CENTRCIR | C | 1 | 0 | String | 0 | 2 |
| QTINST34 | N | 3 | 0 | String | 0 | 3 |
| QTINST35 | N | 3 | 0 | String | 0 | 3 |
| QTINST36 | N | 3 | 0 | String | 0 | 2 |
| QTINST37 | N | 3 | 0 | String | 0 | 1 |
| CENTROBS | C | 1 | 0 | String | 0 | 2 |
| QTLEIT05 | N | 3 | 0 | String | 0 | 5 |
| QTLEIT06 | N | 3 | 0 | String | 0 | 4 |
| QTLEIT07 | N | 3 | 0 | String | 0 | 3 |
| QTLEIT08 | N | 3 | 0 | String | 0 | 5 |
| QTLEIT09 | N | 3 | 0 | String | 0 | 1 |
| QTLEIT19 | N | 3 | 0 | String | 0 | 1 |
| QTLEIT20 | N | 3 | 0 | String | 0 | 1 |
| QTLEIT21 | N | 3 | 0 | String | 0 | 2 |
| QTLEIT22 | N | 3 | 0 | String | 0 | 3 |
| QTLEIT23 | N | 3 | 0 | String | 0 | 2 |
| QTLEIT32 | N | 3 | 0 | String | 0 | 5 |
| QTLEIT34 | N | 3 | 0 | String | 0 | 2 |
| QTLEIT38 | N | 3 | 0 | String | 0 | 2 |
| QTLEIT39 | N | 3 | 0 | String | 0 | 2 |
| QTLEIT40 | N | 3 | 0 | String | 0 | 2 |
| CENTRNEO | C | 1 | 0 | String | 0 | 2 |
| ATENDHOS | C | 1 | 0 | String | 0 | 2 |
| SERAP01P | C | 1 | 0 | String | 0 | 2 |
| SERAP01T | C | 1 | 0 | String | 0 | 2 |
| SERAP02P | C | 1 | 0 | String | 0 | 2 |
| SERAP02T | C | 1 | 0 | String | 0 | 2 |
| SERAP03P | C | 1 | 0 | String | 0 | 2 |
| SERAP03T | C | 1 | 0 | String | 0 | 1 |
| SERAP04P | C | 1 | 0 | String | 0 | 2 |
| SERAP04T | C | 1 | 0 | String | 0 | 2 |
| SERAP05P | C | 1 | 0 | String | 0 | 2 |
| SERAP05T | C | 1 | 0 | String | 0 | 2 |
| SERAP06P | C | 1 | 0 | String | 0 | 2 |
| SERAP06T | C | 1 | 0 | String | 0 | 2 |
| SERAP07P | C | 1 | 0 | String | 0 | 2 |
| SERAP07T | C | 1 | 0 | String | 0 | 1 |
| SERAP08P | C | 1 | 0 | String | 0 | 2 |
| SERAP08T | C | 1 | 0 | String | 0 | 2 |
| SERAP09P | C | 1 | 0 | String | 0 | 2 |
| SERAP09T | C | 1 | 0 | String | 0 | 2 |
| SERAP10P | C | 1 | 0 | String | 0 | 2 |
| SERAP10T | C | 1 | 0 | String | 0 | 1 |
| SERAP11P | C | 1 | 0 | String | 0 | 2 |
| SERAP11T | C | 1 | 0 | String | 0 | 1 |
| SERAPOIO | C | 1 | 0 | String | 0 | 2 |
| RES_BIOL | C | 1 | 0 | String | 0 | 2 |
| RES_QUIM | C | 1 | 0 | String | 0 | 2 |
| RES_RADI | C | 1 | 0 | String | 0 | 2 |
| RES_COMU | C | 1 | 0 | String | 0 | 2 |
| COLETRES | C | 1 | 0 | String | 0 | 2 |
| COMISS01 | C | 1 | 0 | String | 0 | 2 |
| COMISS02 | C | 1 | 0 | String | 0 | 2 |
| COMISS03 | C | 1 | 0 | String | 0 | 2 |
| COMISS04 | C | 1 | 0 | String | 0 | 2 |
| COMISS05 | C | 1 | 0 | String | 0 | 2 |
| COMISS06 | C | 1 | 0 | String | 0 | 2 |
| COMISS07 | C | 1 | 0 | String | 0 | 2 |
| COMISS08 | C | 1 | 0 | String | 0 | 2 |
| COMISS09 | C | 1 | 0 | String | 0 | 1 |
| COMISS10 | C | 1 | 0 | String | 0 | 2 |
| COMISS11 | C | 1 | 0 | String | 0 | 2 |
| COMISS12 | C | 1 | 0 | String | 0 | 2 |
| COMISSAO | C | 1 | 0 | String | 0 | 2 |
| AP01CV01 | C | 1 | 0 | String | 0 | 2 |
| AP01CV02 | C | 1 | 0 | String | 0 | 2 |
| AP01CV03 | C | 1 | 0 | String | 0 | 1 |
| AP01CV04 | C | 1 | 0 | String | 0 | 1 |
| AP01CV05 | C | 1 | 0 | String | 0 | 1 |
| AP01CV06 | C | 1 | 0 | String | 0 | 1 |
| AP01CV07 | C | 1 | 0 | String | 0 | 1 |
| AP02CV01 | C | 1 | 0 | String | 0 | 2 |
| AP02CV02 | C | 1 | 0 | String | 0 | 2 |
| AP02CV03 | C | 1 | 0 | String | 0 | 1 |
| AP02CV04 | C | 1 | 0 | String | 0 | 1 |
| AP02CV05 | C | 1 | 0 | String | 0 | 2 |
| AP02CV06 | C | 1 | 0 | String | 0 | 2 |
| AP02CV07 | C | 1 | 0 | String | 0 | 2 |
| AP03CV01 | C | 1 | 0 | String | 0 | 2 |
| AP03CV02 | C | 1 | 0 | String | 0 | 2 |
| AP03CV03 | C | 1 | 0 | String | 0 | 1 |
| AP03CV04 | C | 1 | 0 | String | 0 | 1 |
| AP03CV05 | C | 1 | 0 | String | 0 | 2 |
| AP03CV06 | C | 1 | 0 | String | 0 | 2 |
| AP03CV07 | C | 1 | 0 | String | 0 | 1 |
| AP04CV01 | C | 1 | 0 | String | 0 | 2 |
| AP04CV02 | C | 1 | 0 | String | 0 | 2 |
| AP04CV03 | C | 1 | 0 | String | 0 | 1 |
| AP04CV04 | C | 1 | 0 | String | 0 | 1 |
| AP04CV05 | C | 1 | 0 | String | 0 | 1 |
| AP04CV06 | C | 1 | 0 | String | 0 | 1 |
| AP04CV07 | C | 1 | 0 | String | 0 | 1 |
| AP05CV01 | C | 1 | 0 | String | 0 | 2 |
| AP05CV02 | C | 1 | 0 | String | 0 | 2 |
| AP05CV03 | C | 1 | 0 | String | 0 | 1 |
| AP05CV04 | C | 1 | 0 | String | 0 | 1 |
| AP05CV05 | C | 1 | 0 | String | 0 | 1 |
| AP05CV06 | C | 1 | 0 | String | 0 | 1 |
| AP05CV07 | C | 1 | 0 | String | 0 | 1 |
| AP06CV01 | C | 1 | 0 | String | 0 | 2 |
| AP06CV02 | C | 1 | 0 | String | 0 | 2 |
| AP06CV03 | C | 1 | 0 | String | 0 | 1 |
| AP06CV04 | C | 1 | 0 | String | 0 | 1 |
| AP06CV05 | C | 1 | 0 | String | 0 | 1 |
| AP06CV06 | C | 1 | 0 | String | 0 | 1 |
| AP06CV07 | C | 1 | 0 | String | 0 | 2 |
| AP07CV01 | C | 1 | 0 | String | 0 | 1 |
| AP07CV02 | C | 1 | 0 | String | 0 | 1 |
| AP07CV03 | C | 1 | 0 | String | 0 | 1 |
| AP07CV04 | C | 1 | 0 | String | 0 | 1 |
| AP07CV05 | C | 1 | 0 | String | 0 | 1 |
| AP07CV06 | C | 1 | 0 | String | 0 | 1 |
| AP07CV07 | C | 1 | 0 | String | 0 | 1 |
| ATEND_PR | C | 1 | 0 | String | 0 | 1 |
| DT_ATUAL | C | 6 | 0 | String | 0 | 38 |
| COMPETEN | C | 6 | 0 | String | 0 | 1 |
| NAT_JUR | C | 4 | 0 | String | 0 | 12 |

## ESUSNOTIFICA — e-SUS Notifica: Doença de Chagas Crônica

**Natureza:** notificações · **Subtipo escolhido:** `DCCR` · **Status:** amostra.

**Pergunta de estudo:** Como o arquivo representa as notificações de DCC?

**Limitação:** Preservar a modalidade informada pelo portal; não confundir Chagas crônica com Chagas aguda do SINAN.

**Inventário:** `/dissemin/publicos/ESUSNOTIFICA/DADOS/FINAIS`; 1 arquivos no diretório, 1 candidatos do subtipo dentro do limite de tamanho.

**Arquivo:** [DCCRBR23.dbc](ftp://ftp.datasus.gov.br/dissemin/publicos/ESUSNOTIFICA/DADOS/FINAIS/DCCRBR23.dbc) · 705,678 bytes.

**Coleta UTC:** `2026-09-10T16:24:39.451735+00:00` · **Modificação informada pelo FTP (sem fuso):** `2026-07-31T14:26:00`.

**SHA-256:** `5008178b914b4087006d30a0da4149b070616354e6ee8b292cfb4e2e3cd1161f`

**Original local:** `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/ESUSNOTIFICA/DCCRBR23.dbc`

### Subtipos descritos no portal (nem todos foram amostrados)

| fonte | sigla_arquivo | desc_arquivo | abrangencia |
| --- | --- | --- | --- |
| ESUSNOTIFICA | DCCR | DCCR - Doença de Chagas Crônica | BR |
| ESUSNOTIFICA_p | DCCR | DCCR - Doença de Chagas Crônica | BR |

**Falha de consulta ao portal:** HTTPStatusError: Server error '503 Service Unavailable' for url 'https://datasus.saude.gov.br/wp-content/ftp.php'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/503. Listagem FTP usada explicitamente.

### Tabela `DCCRBR23.dbc`

**Identificador:** `t000_DCCRBR23` · **Campos:** 109 · **Linhas na amostra:** 200.

Registros declarados: **5455**; ativos: **5455**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/ESUSNOTIFICA/DCCRBR23.dbc_amostras/t000_DCCRBR23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| SG_UF_NOT | C | 19 | 0 | String | 0 | 18 |
| ID_MUNICIP | C | 25 | 0 | String | 0 | 77 |
| ID_ESTRANG | C | 3 | 0 | String | 170 | 2 |
| ID_OCUPA_N | C | 88 | 0 | String | 178 | 15 |
| ID_PAIS | C | 9 | 0 | String | 200 | 1 |
| NU_IDADE_N | C | 4 | 0 | String | 0 | 59 |
| CS_SEXO | C | 9 | 0 | String | 0 | 2 |
| CS_RACA | C | 8 | 0 | String | 0 | 6 |
| CS_ESCOL_N | C | 13 | 0 | String | 22 | 8 |
| SG_UF | C | 19 | 0 | String | 0 | 18 |
| ID_MN_RESI | C | 27 | 0 | String | 0 | 99 |
| SG_PAIS | C | 9 | 0 | String | 200 | 1 |
| DT_NOTIFIC | C | 10 | 0 | String | 0 | 53 |
| ANO_DIAG | C | 4 | 0 | String | 1 | 30 |
| MO_SUSPEIT | C | 53 | 0 | String | 0 | 9 |
| CS_GESTANT | C | 26 | 0 | String | 0 | 5 |
| UF_NASC | C | 19 | 0 | String | 37 | 16 |
| MUN_NASC | C | 27 | 0 | String | 47 | 95 |
| COUFINF | C | 19 | 0 | String | 53 | 19 |
| COMUNINF | C | 23 | 0 | String | 181 | 15 |
| EIE_IGG | C | 14 | 0 | String | 0 | 5 |
| IFI_IGG | C | 14 | 0 | String | 0 | 5 |
| HAI_IGG | C | 14 | 0 | String | 0 | 4 |
| QUIMIO_IGG | C | 14 | 0 | String | 0 | 4 |
| PCR | C | 13 | 0 | String | 5 | 3 |
| OUTRO_POSI | C | 3 | 0 | String | 11 | 3 |
| AC_NOT | C | 3 | 0 | String | 124 | 3 |
| UF_UBS_AC | C | 19 | 0 | String | 179 | 10 |
| MUN_UBS_AC | C | 25 | 0 | String | 179 | 11 |
| HOSP_ESP | C | 3 | 0 | String | 162 | 3 |
| UF_HOSPESP | C | 19 | 0 | String | 187 | 11 |
| MUN_ESP | C | 25 | 0 | String | 187 | 11 |
| ELETROCARD | C | 13 | 0 | String | 134 | 4 |
| RX_TORAX | C | 13 | 0 | String | 137 | 4 |
| RX_COLON | C | 13 | 0 | String | 135 | 4 |
| RX_ESOFAGO | C | 13 | 0 | String | 135 | 4 |
| ECOCARDIO | C | 13 | 0 | String | 135 | 4 |
| OUTRO_EXAM | C | 13 | 0 | String | 135 | 4 |
| EXAME_DESC | C | 254 | 0 | String | 187 | 14 |
| COMORBID | C | 109 | 0 | String | 157 | 10 |
| HIV | C | 3 | 0 | String | 0 | 2 |
| HIPERTEN | C | 3 | 0 | String | 0 | 2 |
| HEPATITE | C | 3 | 0 | String | 0 | 1 |
| DIABETES | C | 3 | 0 | String | 0 | 2 |
| CARDIOPAT | C | 3 | 0 | String | 0 | 2 |
| NEOPLASIA | C | 3 | 0 | String | 0 | 2 |
| LEISHMANIA | C | 3 | 0 | String | 0 | 1 |
| OUT_COMORB | C | 3 | 0 | String | 0 | 2 |
| FORMA | C | 22 | 0 | String | 124 | 7 |
| REATIVACAO | C | 3 | 0 | String | 139 | 3 |
| HIST_BNZ | C | 3 | 0 | String | 132 | 3 |
| TRAT_BNZ | C | 3 | 0 | String | 124 | 3 |
| BNZ_TOT_CP | C | 3 | 0 | String | 182 | 8 |
| BNZ_DIAS | C | 3 | 0 | String | 183 | 7 |
| TRAT_NFX | C | 3 | 0 | String | 136 | 2 |
| NFX_TOT_CP | C | 3 | 0 | String | 200 | 1 |
| NFX_DIAS | C | 2 | 0 | String | 200 | 1 |
| ADVERS_BNZ | C | 11 | 0 | String | 161 | 2 |
| BNZ_LEVE | C | 24 | 0 | String | 198 | 2 |
| BNZ_GRAVE | C | 16 | 0 | String | 200 | 1 |
| BNZ_AUGESI | C | 7 | 0 | String | 200 | 1 |
| BNZ_PAREST | C | 11 | 0 | String | 200 | 1 |
| BNZ_DEPRE | C | 22 | 0 | String | 200 | 1 |
| BNZ_GASTRO | C | 29 | 0 | String | 200 | 1 |
| BNZ_ARTRAL | C | 10 | 0 | String | 200 | 1 |
| REAC_BNZ | C | 6 | 0 | String | 200 | 1 |
| BNZ_OUTRAS | C | 105 | 0 | String | 200 | 1 |
| ADVERS_NFX | C | 11 | 0 | String | 183 | 2 |
| NFX_LEVE | C | 24 | 0 | String | 200 | 1 |
| NFX_GRAVE | N | 1 | 0 | String | 0 | 1 |
| NFX_AGEUSI | N | 1 | 0 | String | 0 | 1 |
| NFX_PAREST | C | 11 | 0 | String | 200 | 1 |
| NFX_MEDULA | N | 1 | 0 | String | 0 | 1 |
| NFX_GASTRO | C | 29 | 0 | String | 200 | 1 |
| NFX_ARTRAL | C | 10 | 0 | String | 200 | 1 |
| REAC_NFX | C | 6 | 0 | String | 200 | 1 |
| NFX_OUTRAS | C | 49 | 0 | String | 200 | 1 |
| HIST_EPID | C | 14 | 0 | String | 131 | 6 |
| BUSCAATIVA | C | 3 | 0 | String | 124 | 3 |
| DIAG_FAMIL | C | 14 | 0 | String | 163 | 8 |
| EXAM_FAMIL | C | 14 | 0 | String | 163 | 7 |
| CONF_FAMIL | C | 14 | 0 | String | 163 | 3 |
| TF_RESIDEN | C | 3 | 0 | String | 136 | 3 |
| UF_RESI_TF | C | 18 | 0 | String | 199 | 2 |
| MN_RESI_TF | C | 23 | 0 | String | 199 | 2 |
| MUD_UBS_AC | C | 3 | 0 | String | 166 | 2 |
| UF_NOV_AC | C | 12 | 0 | String | 200 | 1 |
| MUN_NOV_AC | C | 21 | 0 | String | 200 | 1 |
| NOVO_ESPEC | C | 3 | 0 | String | 138 | 2 |
| ANT_UF_ESP | C | 17 | 0 | String | 200 | 1 |
| ANT_MUN | C | 14 | 0 | String | 200 | 1 |
| ST_ENCERRA | C | 35 | 0 | String | 154 | 6 |
| DT_OBITO | C | 10 | 0 | String | 189 | 12 |
| DT_ENCERRA | C | 10 | 0 | String | 154 | 40 |
| SITUACAO | N | 1 | 0 | String | 0 | 1 |
| DT_CRIACAO | C | 10 | 0 | String | 0 | 100 |
| DT_DIGITAC | C | 10 | 0 | String | 0 | 100 |
| LAB_CNES | N | 1 | 0 | String | 0 | 1 |
| CNES | C | 37 | 0 | String | 63 | 76 |
| CD_MUNICIP | C | 6 | 0 | String | 0 | 77 |
| CD_MN_RESI | C | 6 | 0 | String | 0 | 99 |
| CD_MUN_NAS | C | 6 | 0 | String | 47 | 95 |
| CD_COMUNIN | C | 6 | 0 | String | 181 | 15 |
| CD_MUN_UBS | C | 6 | 0 | String | 179 | 11 |
| CD_MUN_ESP | C | 6 | 0 | String | 187 | 11 |
| CD_MN_RES0 | C | 6 | 0 | String | 199 | 2 |
| CD_MUN_NOV | C | 6 | 0 | String | 200 | 1 |
| CD_ANT_MUN | C | 6 | 0 | String | 200 | 1 |
| ANO_NASC | C | 4 | 0 | String | 0 | 59 |

## PCE — Controle da Esquistossomose

**Natureza:** registros · **Subtipo escolhido:** `PCE` · **Status:** amostra.

**Pergunta de estudo:** Quais campos descrevem as atividades de controle?

**Limitação:** Amostra AL; a unidade de registro e os denominadores exigem o dicionário do programa.

**Inventário:** `/dissemin/publicos/PCE/DADOS`; 460 arquivos no diretório, 460 candidatos do subtipo dentro do limite de tamanho.

**Arquivo:** [PCEAL23.dbc](ftp://ftp.datasus.gov.br/dissemin/publicos/PCE/DADOS/PCEAL23.dbc) · 9,622 bytes.

**Coleta UTC:** `2026-09-10T16:24:40.123028+00:00` · **Modificação informada pelo FTP (sem fuso):** `2025-11-11T12:07:00`.

**SHA-256:** `3ed318070267601164f13435c705b681601795071f1bcb5a5074851d3f56707c`

**Original local:** `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/PCE/PCEAL23.dbc`

### Subtipos descritos no portal (nem todos foram amostrados)

| fonte | sigla_arquivo | desc_arquivo | abrangencia |
| --- | --- | --- | --- |
| PCE | PCE | PCE - Programa de Controle da Esquistossomose | TT |

**Rótulos retornados pelo portal:** PCE / Dados.

### Tabela `PCEAL23.dbc`

**Identificador:** `t000_PCEAL23` · **Campos:** 35 · **Linhas na amostra:** 200.

Registros declarados: **469**; ativos: **469**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/PCE/PCEAL23.dbc_amostras/t000_PCEAL23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| ID_UF | C | 2 | 0 | String | 0 | 1 |
| SG_UF | C | 2 | 0 | String | 0 | 1 |
| ID_LOC | C | 12 | 0 | String | 0 | 126 |
| DT_COMP | C | 6 | 0 | String | 0 | 5 |
| QT_POP | C | 4 | 0 | String | 0 | 133 |
| QT_PRED | C | 1 | 0 | String | 0 | 1 |
| QT_EXAM | C | 4 | 0 | String | 0 | 124 |
| QT_NRECOL | C | 4 | 0 | String | 0 | 96 |
| QT_1A4 | C | 2 | 0 | String | 0 | 16 |
| QT_5A16 | C | 2 | 0 | String | 0 | 7 |
| QT_17 | C | 2 | 0 | String | 0 | 5 |
| QT_POS | C | 3 | 0 | String | 0 | 22 |
| QT_ATRAT | C | 3 | 0 | String | 0 | 22 |
| QT_TRAT | C | 3 | 0 | String | 0 | 16 |
| QT_CI | C | 3 | 0 | String | 0 | 3 |
| QT_REC | C | 1 | 0 | String | 0 | 1 |
| QT_AUS | C | 3 | 0 | String | 0 | 15 |
| QT_ASC | C | 3 | 0 | String | 0 | 24 |
| QT_ANC | C | 3 | 0 | String | 0 | 29 |
| QT_TAE | C | 2 | 0 | String | 0 | 6 |
| QT_TT | C | 2 | 0 | String | 0 | 9 |
| QT_EV | C | 2 | 0 | String | 0 | 7 |
| QT_SE | C | 2 | 0 | String | 0 | 2 |
| QT_HN | C | 3 | 0 | String | 0 | 3 |
| QT_OUT | C | 2 | 0 | String | 0 | 4 |
| QT_CAP | C | 3 | 0 | String | 0 | 1 |
| QT_PESQ | C | 3 | 0 | String | 0 | 1 |
| QT_BGLA | C | 2 | 0 | String | 0 | 1 |
| QT_BSTR | C | 3 | 0 | String | 0 | 1 |
| QT_BTEN | C | 1 | 0 | String | 0 | 1 |
| QT_OUT1 | C | 3 | 0 | String | 0 | 1 |
| QT_POSBGLA | C | 1 | 0 | String | 0 | 1 |
| QT_POSBTEN | C | 1 | 0 | String | 0 | 1 |
| QT_POSBSTR | C | 2 | 0 | String | 0 | 1 |
| QT_POSOUT | C | 1 | 0 | String | 0 | 1 |

## PO — Painel de Oncologia

**Natureza:** registros · **Subtipo escolhido:** `PO` · **Status:** amostra.

**Pergunta de estudo:** Que variáveis permitem estudar diagnóstico e tratamento?

**Limitação:** Recorte nacional; contagens de registros não devem ser interpretadas automaticamente como pessoas únicas.

**Inventário:** `/dissemin/publicos/PAINEL_ONCOLOGIA/DADOS`; 14 arquivos no diretório, 14 candidatos do subtipo dentro do limite de tamanho.

**Arquivo:** [POBR2023.dbc](ftp://ftp.datasus.gov.br/dissemin/publicos/PAINEL_ONCOLOGIA/DADOS/POBR2023.dbc) · 23,767,771 bytes.

**Coleta UTC:** `2026-09-10T16:24:44.984856+00:00` · **Modificação informada pelo FTP (sem fuso):** `2026-08-05T17:33:00`.

**SHA-256:** `8cfce74e3ca265076e5983aac4caae73375e05bfd992c44675dbf43b4fe4d0da`

**Original local:** `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/PO/POBR2023.dbc`

### Subtipos descritos no portal (nem todos foram amostrados)

| fonte | sigla_arquivo | desc_arquivo | abrangencia |
| --- | --- | --- | --- |
| PO | PO | PO - Painel de Oncologia – desde 2013 | BR |

**Rótulos retornados pelo portal:** PO / Dados.

### Tabela `POBR2023.dbc`

**Identificador:** `t000_POBR2023` · **Campos:** 23 · **Linhas na amostra:** 200.

Registros declarados: **679408**; ativos: **679408**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/PO/POBR2023.dbc_amostras/t000_POBR2023.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| ANO_DIAGN | C | 4 | 0 | String | 0 | 1 |
| ANOMES_DIA | C | 6 | 0 | String | 0 | 12 |
| ANO_TRATAM | C | 4 | 0 | String | 126 | 4 |
| ANOMES_TRA | C | 6 | 0 | String | 126 | 21 |
| UF_RESID | C | 2 | 0 | String | 0 | 24 |
| MUN_RESID | C | 6 | 0 | String | 0 | 156 |
| UF_TRATAM | C | 2 | 0 | String | 126 | 20 |
| MUN_TRATAM | C | 6 | 0 | String | 126 | 51 |
| UF_DIAGN | C | 2 | 0 | String | 0 | 23 |
| MUN_DIAG | C | 6 | 0 | String | 0 | 98 |
| TRATAMENTO | C | 1 | 0 | String | 0 | 5 |
| DIAGNOSTIC | C | 2 | 0 | String | 0 | 4 |
| IDADE | C | 3 | 0 | String | 0 | 64 |
| SEXO | C | 1 | 0 | String | 0 | 2 |
| ESTADIAM | C | 1 | 0 | String | 5 | 8 |
| CNES_DIAG | C | 7 | 0 | String | 0 | 142 |
| CNES_TRAT | C | 7 | 0 | String | 126 | 61 |
| TEMPO_TRAT | C | 5 | 0 | String | 5 | 48 |
| CNS_PAC | C | 15 | 0 | String | 200 | 1 |
| DIAG_DETH | C | 3 | 0 | String | 0 | 54 |
| DT_DIAG | C | 10 | 0 | String | 0 | 140 |
| DT_TRAT | C | 10 | 0 | String | 126 | 64 |
| DT_NASC | C | 10 | 0 | String | 0 | 200 |

## RESP — Notificações de casos suspeitos de SCZ

**Natureza:** notificações · **Subtipo escolhido:** `RESP` · **Status:** amostra.

**Pergunta de estudo:** Que campos constam da notificação e da investigação?

**Limitação:** Amostras estaduais podem ter pouquíssimas linhas. Suspeita não equivale a caso confirmado.

**Inventário:** `/dissemin/publicos/RESP/DADOS`; 281 arquivos no diretório, 281 candidatos do subtipo dentro do limite de tamanho.

**Arquivo:** [RESPRR23.dbc](ftp://ftp.datasus.gov.br/dissemin/publicos/RESP/DADOS/RESPRR23.dbc) · 2,879 bytes.

**Coleta UTC:** `2026-09-10T16:24:45.608333+00:00` · **Modificação informada pelo FTP (sem fuso):** `2024-07-01T17:33:00`.

**SHA-256:** `92c37aa544e88b705262ffd1e318927b6b3ce00fe9bc523522e3163ea0ced9f6`

**Original local:** `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/RESP/RESPRR23.dbc`

### Subtipos descritos no portal (nem todos foram amostrados)

| fonte | sigla_arquivo | desc_arquivo | abrangencia |
| --- | --- | --- | --- |
| RESP | RESP | RESP - Notificações de casos suspeitos de SCZ – desde 2015 | UF |

**Rótulos retornados pelo portal:** RESP / Dados.

### Tabela `RESPRR23.dbc`

**Identificador:** `t000_RESPRR23` · **Campos:** 78 · **Linhas na amostra:** 3.

Registros declarados: **3**; ativos: **3**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/RESP/RESPRR23.dbc_amostras/t000_RESPRR23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_SEQ | C | 6 | 0 | String | 0 | 1 |
| DT_NOTIFIC | C | 10 | 0 | String | 0 | 2 |
| ANO_NOT | C | 7 | 0 | String | 0 | 1 |
| TP_NOTIFIC | C | 10 | 0 | String | 0 | 1 |
| DT_NASCMAE | C | 10 | 0 | String | 1 | 3 |
| IDADEGES | C | 8 | 0 | String | 0 | 3 |
| RACACOR | C | 7 | 0 | String | 0 | 2 |
| REGIAORES | C | 9 | 0 | String | 0 | 1 |
| UFRES | C | 5 | 0 | String | 0 | 1 |
| CODMUNRES | C | 9 | 0 | String | 0 | 1 |
| SEXO | C | 4 | 0 | String | 0 | 2 |
| DT_NASC | C | 8 | 0 | String | 0 | 3 |
| ANO_NASC | C | 8 | 0 | String | 0 | 2 |
| PESO | C | 4 | 0 | String | 0 | 3 |
| COMPRIMENT | C | 10 | 0 | String | 0 | 3 |
| PERIMCEFAL | C | 10 | 0 | String | 0 | 3 |
| DIAMCEFAL | C | 9 | 0 | String | 3 | 1 |
| MICROCEFAL | C | 10 | 0 | String | 0 | 2 |
| DEF_NEURO | C | 9 | 0 | String | 0 | 1 |
| DEF_AUDIT | C | 9 | 0 | String | 0 | 1 |
| DEF_VISUAL | C | 10 | 0 | String | 0 | 1 |
| TPDETECCAO | C | 10 | 0 | String | 0 | 2 |
| GEST_DIAG | C | 9 | 0 | String | 0 | 2 |
| GRAVIDEZ | C | 8 | 0 | String | 0 | 1 |
| CLASS_FETO | C | 10 | 0 | String | 0 | 1 |
| DT_SINTOMA | C | 10 | 0 | String | 2 | 2 |
| FEBRE_GES | C | 9 | 0 | String | 0 | 2 |
| EXANT_GES | C | 9 | 0 | String | 0 | 2 |
| PRURIDO | C | 7 | 0 | String | 0 | 1 |
| CONJUNTIV | C | 9 | 0 | String | 0 | 1 |
| DOR_ARTIC | C | 9 | 0 | String | 0 | 1 |
| DOR_MUSC | C | 8 | 0 | String | 0 | 1 |
| EDEMA | C | 5 | 0 | String | 0 | 1 |
| CEFALEIA | C | 8 | 0 | String | 0 | 1 |
| HIPERT_GAN | C | 10 | 0 | String | 0 | 1 |
| NEUROLOG | C | 8 | 0 | String | 0 | 1 |
| EXA_TORSCH | C | 10 | 0 | String | 0 | 2 |
| RESUL_S | C | 7 | 0 | String | 0 | 3 |
| RESUL_TO | C | 8 | 0 | String | 0 | 2 |
| RESUL_C | C | 7 | 0 | String | 0 | 1 |
| RESUL_H | C | 7 | 0 | String | 0 | 1 |
| RESUL_Z | C | 7 | 0 | String | 0 | 2 |
| SO_IGG_Z | C | 8 | 0 | String | 0 | 2 |
| SO_IGM_Z | C | 8 | 0 | String | 0 | 2 |
| TR_IGG_Z | C | 8 | 0 | String | 0 | 1 |
| TR_IGM_Z | C | 8 | 0 | String | 0 | 1 |
| PCR_Z | C | 5 | 0 | String | 0 | 2 |
| HIST_ARBOV | C | 10 | 0 | String | 0 | 1 |
| HIST_MALFO | C | 10 | 0 | String | 0 | 1 |
| RNEXA_TORS | C | 10 | 0 | String | 0 | 1 |
| RNRESUL_S | C | 9 | 0 | String | 0 | 1 |
| RNRESUL_TO | C | 10 | 0 | String | 0 | 1 |
| RNRESUL_C | C | 9 | 0 | String | 0 | 1 |
| RNRESUL_H | C | 9 | 0 | String | 0 | 1 |
| RNRESUL_Z | C | 9 | 0 | String | 0 | 2 |
| RNSO_IGG_Z | C | 10 | 0 | String | 0 | 2 |
| RNSO_IGM_Z | C | 10 | 0 | String | 0 | 2 |
| RNTR_IGG_Z | C | 10 | 0 | String | 0 | 1 |
| RNTR_IGM_Z | C | 10 | 0 | String | 0 | 1 |
| RNPCR_Z | C | 7 | 0 | String | 0 | 2 |
| EXAME_USS | C | 9 | 0 | String | 0 | 2 |
| DT_USS | C | 8 | 0 | String | 2 | 2 |
| EXA_TRANSF | C | 10 | 0 | String | 0 | 2 |
| DT_TRANSF | C | 9 | 0 | String | 1 | 3 |
| EXAME_TC | C | 8 | 0 | String | 0 | 2 |
| DT_TC | C | 8 | 0 | String | 2 | 2 |
| EXAME_RS | C | 8 | 0 | String | 0 | 1 |
| DT_RS | C | 5 | 0 | String | 3 | 1 |
| REGIAONOT | C | 9 | 0 | String | 0 | 1 |
| UFNOT | C | 5 | 0 | String | 0 | 1 |
| CODMUNNOT | C | 9 | 0 | String | 0 | 1 |
| ST_OBITO | C | 8 | 0 | String | 0 | 2 |
| DT_OBITO | C | 8 | 0 | String | 2 | 2 |
| CLASSIFIN | C | 9 | 0 | String | 0 | 2 |
| ETIOLOGIA | C | 9 | 0 | String | 0 | 2 |
| CRITERIO | C | 8 | 0 | String | 0 | 1 |
| STATUS_NOT | C | 10 | 0 | String | 0 | 1 |
| DT_ULT_ALT | C | 10 | 0 | String | 0 | 2 |

## SIASUS — Informações Ambulatoriais do SUS

**Natureza:** produção · **Subtipo escolhido:** `PA` · **Status:** amostra.

**Pergunta de estudo:** Como os registros de produção ambulatorial são estruturados?

**Limitação:** PA é um subtipo da família SIA. Quantidade aprovada, registros e pessoas são medidas distintas.

**Inventário:** `/dissemin/publicos/SIASUS/200801_/Dados`; 54199 arquivos no diretório, 5419 candidatos do subtipo dentro do limite de tamanho.

**Arquivo:** [PARR2301.dbc](ftp://ftp.datasus.gov.br/dissemin/publicos/SIASUS/200801_/Dados/PARR2301.dbc) · 1,156,052 bytes.

**Coleta UTC:** `2026-09-10T16:24:47.614660+00:00` · **Modificação informada pelo FTP (sem fuso):** `2024-03-06T22:44:00`.

**SHA-256:** `9c25984b133e750dcf23f39363154c04738161bb56f4bc9b79143642af549d3b`

**Original local:** `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/SIASUS/PARR2301.dbc`

### Subtipos descritos no portal (nem todos foram amostrados)

| fonte | sigla_arquivo | desc_arquivo | abrangencia |
| --- | --- | --- | --- |
| SIASUS | AB | AB - APAC de Acompanhamento a Cirurgia Bariátrica - A Partir de Jan/2008 até Mar/2013 | UF |
| SIASUS | ABO | ABO - APAC Acompanhamento Pós Cirurgia Bariátrica - A Partir de Abr/2013 | UF |
| SIASUS | ACF | ACF - APAC Confeção de Fístula Arteriovenosa - A Partir de Jun/2014 | UF |
| SIASUS | AD | AD - APAC de Laudos Diversos - A Partir de Jan/2008 | UF |
| SIASUS | AM | AM - APAC de Medicamentos - A Partir de Jan/2008 | UF |
| SIASUS | AN | AN - APAC de Nefrologia - A Partir de Jan/2008 até Out/2014 | UF |
| SIASUS | AQ | AQ - APAC de Quimioterapia - A Partir de Jan/2008 | UF |
| SIASUS | AR | AR - APAC de Radioterapia - A Partir de Jan/2008 | UF |
| SIASUS | ATD | ATD - APAC Tratamento Dialítico - A Partir de Jun/2014 | UF |
| SIASUS | PA | PA - Produção Ambulatorial - A Partir de Jul/1994 | UF |
| SIASUS | PS | PS - Psicossocial - A Partir de Jan/2013 | UF |
| SIASUS | SAD | SAD - Atenção Domiciliar - A Partir de Nov/2012 | — |

**Rótulos retornados pelo portal:** SIASUS / Dados.

### Tabela `PARR2301.dbc`

**Identificador:** `t000_PARR2301` · **Campos:** 60 · **Linhas na amostra:** 200.

Registros declarados: **32400**; ativos: **32400**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/SIASUS/PARR2301.dbc_amostras/t000_PARR2301.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| PA_CODUNI | C | 7 | 0 | String | 0 | 5 |
| PA_GESTAO | C | 6 | 0 | String | 0 | 1 |
| PA_CONDIC | C | 2 | 0 | String | 0 | 1 |
| PA_UFMUN | C | 6 | 0 | String | 0 | 4 |
| PA_REGCT | C | 4 | 0 | String | 0 | 1 |
| PA_INCOUT | C | 4 | 0 | String | 0 | 1 |
| PA_INCURG | C | 4 | 0 | String | 0 | 1 |
| PA_TPUPS | C | 2 | 0 | String | 0 | 3 |
| PA_TIPPRE | C | 2 | 0 | String | 0 | 1 |
| PA_MN_IND | C | 1 | 0 | String | 0 | 1 |
| PA_CNPJCPF | C | 14 | 0 | String | 0 | 1 |
| PA_CNPJMNT | C | 14 | 0 | String | 0 | 1 |
| PA_CNPJ_CC | C | 14 | 0 | String | 0 | 1 |
| PA_MVM | C | 6 | 0 | String | 0 | 1 |
| PA_CMP | C | 6 | 0 | String | 0 | 1 |
| PA_PROC_ID | C | 10 | 0 | String | 0 | 45 |
| PA_TPFIN | C | 2 | 0 | String | 0 | 2 |
| PA_SUBFIN | C | 4 | 0 | String | 0 | 1 |
| PA_NIVCPL | C | 1 | 0 | String | 0 | 2 |
| PA_DOCORIG | C | 1 | 0 | String | 0 | 1 |
| PA_AUTORIZ | C | 13 | 0 | String | 0 | 1 |
| PA_CNSMED | C | 15 | 0 | String | 0 | 1 |
| PA_CBOCOD | C | 6 | 0 | String | 0 | 32 |
| PA_MOTSAI | C | 2 | 0 | String | 0 | 1 |
| PA_OBITO | C | 1 | 0 | String | 0 | 1 |
| PA_ENCERR | C | 1 | 0 | String | 0 | 1 |
| PA_PERMAN | C | 1 | 0 | String | 0 | 1 |
| PA_ALTA | C | 1 | 0 | String | 0 | 1 |
| PA_TRANSF | C | 1 | 0 | String | 0 | 1 |
| PA_CIDPRI | C | 4 | 0 | String | 0 | 1 |
| PA_CIDSEC | C | 4 | 0 | String | 0 | 1 |
| PA_CIDCAS | C | 4 | 0 | String | 0 | 1 |
| PA_CATEND | C | 2 | 0 | String | 0 | 1 |
| PA_IDADE | C | 3 | 0 | String | 0 | 24 |
| IDADEMIN | C | 3 | 0 | String | 0 | 2 |
| IDADEMAX | C | 3 | 0 | String | 0 | 2 |
| PA_FLIDADE | C | 1 | 0 | String | 0 | 2 |
| PA_SEXO | C | 1 | 0 | String | 0 | 1 |
| PA_RACACOR | C | 2 | 0 | String | 0 | 1 |
| PA_MUNPCN | C | 6 | 0 | String | 0 | 1 |
| PA_QTDPRO | N | 11 | 0 | String | 0 | 74 |
| PA_QTDAPR | N | 11 | 0 | String | 0 | 74 |
| PA_VALPRO | N | 20 | 2 | String | 0 | 106 |
| PA_VALAPR | N | 20 | 2 | String | 0 | 106 |
| PA_UFDIF | C | 1 | 0 | String | 0 | 1 |
| PA_MNDIF | C | 1 | 0 | String | 0 | 1 |
| PA_DIF_VAL | N | 20 | 2 | String | 0 | 1 |
| NU_VPA_TOT | N | 20 | 2 | String | 0 | 1 |
| NU_PA_TOT | N | 20 | 2 | String | 0 | 22 |
| PA_INDICA | C | 1 | 0 | String | 0 | 1 |
| PA_CODOCO | C | 1 | 0 | String | 0 | 1 |
| PA_FLQT | C | 1 | 0 | String | 0 | 1 |
| PA_FLER | C | 1 | 0 | String | 0 | 1 |
| PA_ETNIA | C | 4 | 0 | String | 200 | 1 |
| PA_VL_CF | N | 20 | 2 | String | 0 | 1 |
| PA_VL_CL | N | 20 | 2 | String | 0 | 1 |
| PA_VL_INC | N | 20 | 2 | String | 0 | 1 |
| PA_SRV_C | C | 6 | 0 | String | 200 | 1 |
| PA_INE | C | 10 | 0 | String | 200 | 1 |
| PA_NAT_JUR | C | 4 | 0 | String | 0 | 1 |

## SIHSUS — Informações Hospitalares do SUS

**Natureza:** produção · **Subtipo escolhido:** `RD` · **Status:** amostra.

**Pergunta de estudo:** Quais campos descrevem uma AIH reduzida?

**Limitação:** RD é um subtipo; uma AIH não deve ser tratada automaticamente como uma pessoa única.

**Inventário:** `/dissemin/publicos/SIHSUS/200801_/Dados`; 22915 arquivos no diretório, 6020 candidatos do subtipo dentro do limite de tamanho.

**Arquivo:** [RDRR2301.dbc](ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados/RDRR2301.dbc) · 349,244 bytes.

**Coleta UTC:** `2026-09-10T16:24:49.054134+00:00` · **Modificação informada pelo FTP (sem fuso):** `2024-02-05T23:00:00`.

**SHA-256:** `e9f717ff378477a883d19f733efe8409aee7f7795a027584b9f383364264d8e4`

**Original local:** `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/SIHSUS/RDRR2301.dbc`

### Subtipos descritos no portal (nem todos foram amostrados)

| fonte | sigla_arquivo | desc_arquivo | abrangencia |
| --- | --- | --- | --- |
| SIHSUS | RD | RD - AIH Reduzida | UF |
| SIHSUS | RJ | RJ - AIH Rejeitadas | UF |
| SIHSUS | SP | SP - Serviços Profissionais | UF |
| SIHSUS | ER | ER - AIH Rejeitadas com código de erro | UF |

**Rótulos retornados pelo portal:** SIHSUS / Dados.

### Tabela `RDRR2301.dbc`

**Identificador:** `t000_RDRR2301` · **Campos:** 113 · **Linhas na amostra:** 200.

Registros declarados: **4734**; ativos: **4734**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/SIHSUS/RDRR2301.dbc_amostras/t000_RDRR2301.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| UF_ZI | C | 6 | 0 | String | 0 | 1 |
| ANO_CMPT | C | 4 | 0 | String | 0 | 1 |
| MES_CMPT | C | 2 | 0 | String | 0 | 1 |
| ESPEC | C | 2 | 0 | String | 0 | 4 |
| CGC_HOSP | C | 14 | 0 | String | 173 | 2 |
| N_AIH | C | 13 | 0 | String | 0 | 200 |
| IDENT | C | 1 | 0 | String | 0 | 1 |
| CEP | C | 8 | 0 | String | 0 | 91 |
| MUNIC_RES | C | 6 | 0 | String | 0 | 14 |
| NASC | C | 8 | 0 | String | 0 | 193 |
| SEXO | C | 1 | 0 | String | 0 | 2 |
| UTI_MES_IN | N | 2 | 0 | String | 0 | 1 |
| UTI_MES_AN | N | 2 | 0 | String | 0 | 1 |
| UTI_MES_AL | N | 2 | 0 | String | 0 | 1 |
| UTI_MES_TO | N | 3 | 0 | String | 0 | 12 |
| MARCA_UTI | C | 2 | 0 | String | 0 | 3 |
| UTI_INT_IN | N | 2 | 0 | String | 0 | 1 |
| UTI_INT_AN | N | 2 | 0 | String | 0 | 1 |
| UTI_INT_AL | N | 2 | 0 | String | 0 | 1 |
| UTI_INT_TO | N | 3 | 0 | String | 0 | 2 |
| DIAR_ACOM | N | 3 | 0 | String | 0 | 34 |
| QT_DIARIAS | N | 3 | 0 | String | 0 | 34 |
| PROC_SOLIC | C | 10 | 0 | String | 0 | 72 |
| PROC_REA | C | 10 | 0 | String | 0 | 72 |
| VAL_SH | N | 13 | 2 | String | 0 | 165 |
| VAL_SP | N | 13 | 2 | String | 0 | 116 |
| VAL_SADT | N | 13 | 2 | String | 0 | 1 |
| VAL_RN | N | 13 | 2 | String | 0 | 1 |
| VAL_ACOMP | N | 13 | 2 | String | 0 | 1 |
| VAL_ORTP | N | 13 | 2 | String | 0 | 1 |
| VAL_SANGUE | N | 13 | 2 | String | 0 | 1 |
| VAL_SADTSR | N | 11 | 2 | String | 0 | 1 |
| VAL_TRANSP | N | 13 | 2 | String | 0 | 1 |
| VAL_OBSANG | N | 11 | 2 | String | 0 | 1 |
| VAL_PED1AC | N | 11 | 2 | String | 0 | 1 |
| VAL_TOT | N | 14 | 2 | String | 0 | 167 |
| VAL_UTI | N | 8 | 2 | String | 0 | 13 |
| US_TOT | N | 10 | 2 | String | 0 | 167 |
| DT_INTER | C | 8 | 0 | String | 0 | 97 |
| DT_SAIDA | C | 8 | 0 | String | 0 | 86 |
| DIAG_PRINC | C | 4 | 0 | String | 0 | 102 |
| DIAG_SECUN | C | 4 | 0 | String | 0 | 1 |
| COBRANCA | C | 2 | 0 | String | 0 | 12 |
| NATUREZA | C | 2 | 0 | String | 0 | 1 |
| NAT_JUR | C | 4 | 0 | String | 0 | 2 |
| GESTAO | C | 1 | 0 | String | 0 | 1 |
| RUBRICA | N | 5 | 0 | String | 0 | 1 |
| IND_VDRL | C | 1 | 0 | String | 0 | 2 |
| MUNIC_MOV | C | 6 | 0 | String | 0 | 3 |
| COD_IDADE | C | 1 | 0 | String | 0 | 3 |
| IDADE | N | 2 | 0 | String | 0 | 70 |
| DIAS_PERM | N | 5 | 0 | String | 0 | 37 |
| MORTE | N | 1 | 0 | String | 0 | 2 |
| NACIONAL | C | 3 | 0 | String | 0 | 3 |
| NUM_PROC | C | 4 | 0 | String | 200 | 1 |
| CAR_INT | C | 2 | 0 | String | 0 | 2 |
| TOT_PT_SP | N | 6 | 0 | String | 0 | 1 |
| CPF_AUT | C | 11 | 0 | String | 200 | 1 |
| HOMONIMO | C | 1 | 0 | String | 0 | 2 |
| NUM_FILHOS | N | 2 | 0 | String | 0 | 3 |
| INSTRU | C | 1 | 0 | String | 0 | 2 |
| CID_NOTIF | C | 4 | 0 | String | 198 | 2 |
| CONTRACEP1 | C | 2 | 0 | String | 0 | 3 |
| CONTRACEP2 | C | 2 | 0 | String | 0 | 3 |
| GESTRISCO | C | 1 | 0 | String | 0 | 1 |
| INSC_PN | C | 12 | 0 | String | 0 | 1 |
| SEQ_AIH5 | C | 3 | 0 | String | 0 | 1 |
| CBOR | C | 6 | 0 | String | 0 | 1 |
| CNAER | C | 3 | 0 | String | 0 | 1 |
| VINCPREV | C | 1 | 0 | String | 0 | 1 |
| GESTOR_COD | C | 5 | 0 | String | 0 | 5 |
| GESTOR_TP | C | 1 | 0 | String | 0 | 2 |
| GESTOR_CPF | C | 15 | 0 | String | 0 | 2 |
| GESTOR_DT | C | 8 | 0 | String | 200 | 1 |
| CNES | C | 7 | 0 | String | 0 | 6 |
| CNPJ_MANT | C | 14 | 0 | String | 27 | 2 |
| INFEHOSP | C | 1 | 0 | String | 200 | 1 |
| CID_ASSO | C | 4 | 0 | String | 0 | 1 |
| CID_MORTE | C | 4 | 0 | String | 0 | 1 |
| COMPLEX | C | 2 | 0 | String | 0 | 2 |
| FINANC | C | 2 | 0 | String | 0 | 1 |
| FAEC_TP | C | 6 | 0 | String | 200 | 1 |
| REGCT | C | 4 | 0 | String | 0 | 1 |
| RACA_COR | C | 2 | 0 | String | 0 | 5 |
| ETNIA | C | 4 | 0 | String | 0 | 6 |
| SEQUENCIA | N | 9 | 0 | String | 0 | 200 |
| REMESSA | C | 21 | 0 | String | 0 | 1 |
| AUD_JUST | C | 50 | 0 | String | 193 | 2 |
| SIS_JUST | C | 50 | 0 | String | 193 | 6 |
| VAL_SH_FED | N | 10 | 2 | String | 0 | 1 |
| VAL_SP_FED | N | 10 | 2 | String | 0 | 1 |
| VAL_SH_GES | N | 10 | 2 | String | 0 | 1 |
| VAL_SP_GES | N | 10 | 2 | String | 0 | 1 |
| VAL_UCI | N | 10 | 2 | String | 0 | 2 |
| MARCA_UCI | C | 2 | 0 | String | 0 | 2 |
| DIAGSEC1 | C | 4 | 0 | String | 172 | 25 |
| DIAGSEC2 | C | 4 | 0 | String | 200 | 1 |
| DIAGSEC3 | C | 4 | 0 | String | 200 | 1 |
| DIAGSEC4 | C | 4 | 0 | String | 200 | 1 |
| DIAGSEC5 | C | 4 | 0 | String | 200 | 1 |
| DIAGSEC6 | C | 4 | 0 | String | 200 | 1 |
| DIAGSEC7 | C | 4 | 0 | String | 200 | 1 |
| DIAGSEC8 | C | 4 | 0 | String | 200 | 1 |
| DIAGSEC9 | C | 1 | 0 | String | 200 | 1 |
| TPDISEC1 | C | 1 | 0 | String | 0 | 2 |
| TPDISEC2 | C | 1 | 0 | String | 0 | 1 |
| TPDISEC3 | C | 1 | 0 | String | 0 | 1 |
| TPDISEC4 | C | 1 | 0 | String | 0 | 1 |
| TPDISEC5 | C | 1 | 0 | String | 0 | 1 |
| TPDISEC6 | C | 1 | 0 | String | 0 | 1 |
| TPDISEC7 | C | 1 | 0 | String | 0 | 1 |
| TPDISEC8 | C | 1 | 0 | String | 0 | 1 |
| TPDISEC9 | C | 1 | 0 | String | 0 | 1 |

## SIM — Informações de Mortalidade

**Natureza:** registros · **Subtipo escolhido:** `DO` · **Status:** amostra.

**Pergunta de estudo:** Como inspecionar campos de data, residência e causas?

**Limitação:** Amostra DORES. As primeiras linhas não representam a população e não permitem estimar taxas.

**Inventário:** `/dissemin/publicos/SIM/CID10/DORES`; 812 arquivos no diretório, 794 candidatos do subtipo dentro do limite de tamanho.

**Arquivo:** [DORR2023.dbc](ftp://ftp.datasus.gov.br/dissemin/publicos/SIM/CID10/DORES/DORR2023.dbc) · 288,798 bytes.

**Coleta UTC:** `2026-09-10T16:24:49.970472+00:00` · **Modificação informada pelo FTP (sem fuso):** `2024-12-19T11:56:00`.

**SHA-256:** `15b5203507161b7c35f9c69a52c955bdac133629549099b85a88e03a9a45baf0`

**Original local:** `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/SIM/DORR2023.dbc`

### Subtipos descritos no portal (nem todos foram amostrados)

| fonte | sigla_arquivo | desc_arquivo | abrangencia |
| --- | --- | --- | --- |
| SIM | DO | DO - Declarações de Óbito - 1979 a 2026 | TT |
| SIM | DOREXT | DOREXT - Mortalidade de residentes no exterior - 2013 a 2026 | BR |
| SIM | DOFET | DOFET - Declarações de Óbitos fetais - 1979 a 2026 | BR |
| SIM | DOEXT | DOEXT - Declarações de Óbitos por causas externas - 1979 a 2026 | BR |
| SIM | DOINF | DOINF - Declarações de Óbitos infantis - 1979 a 2026 | BR |
| SIM | DOMAT | DOMAT - Declarações de Óbitos maternos - 1996 a 2026 | BR |

**Rótulos retornados pelo portal:** SIM / Dados - Finais.

### Tabela `DORR2023.dbc`

**Identificador:** `t000_DORR2023` · **Campos:** 87 · **Linhas na amostra:** 200.

Registros declarados: **3311**; ativos: **3311**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/SIM/DORR2023.dbc_amostras/t000_DORR2023.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| ORIGEM | C | 1 | 0 | String | 0 | 1 |
| TIPOBITO | C | 1 | 0 | String | 0 | 1 |
| DTOBITO | C | 8 | 0 | String | 0 | 23 |
| HORAOBITO | C | 5 | 0 | String | 15 | 143 |
| NATURAL | C | 3 | 0 | String | 3 | 25 |
| CODMUNNATU | C | 7 | 0 | String | 27 | 79 |
| DTNASC | C | 8 | 0 | String | 3 | 196 |
| IDADE | C | 3 | 0 | String | 0 | 99 |
| SEXO | C | 1 | 0 | String | 0 | 3 |
| RACACOR | C | 1 | 0 | String | 6 | 5 |
| ESTCIV | C | 1 | 0 | String | 28 | 7 |
| ESC | C | 1 | 0 | String | 25 | 7 |
| ESC2010 | C | 1 | 0 | String | 26 | 8 |
| SERIESCFAL | C | 1 | 0 | String | 114 | 8 |
| OCUP | C | 6 | 0 | String | 37 | 50 |
| CODMUNRES | C | 7 | 0 | String | 0 | 14 |
| LOCOCOR | C | 1 | 0 | String | 0 | 5 |
| CODESTAB | C | 8 | 0 | String | 88 | 16 |
| ESTABDESCR | C | 40 | 0 | String | 200 | 1 |
| CODMUNOCOR | C | 7 | 0 | String | 0 | 15 |
| IDADEMAE | C | 2 | 0 | String | 181 | 14 |
| ESCMAE | C | 1 | 0 | String | 181 | 6 |
| ESCMAE2010 | C | 1 | 0 | String | 181 | 7 |
| SERIESCMAE | C | 1 | 0 | String | 187 | 4 |
| OCUPMAE | C | 6 | 0 | String | 182 | 8 |
| QTDFILVIVO | C | 2 | 0 | String | 181 | 7 |
| QTDFILMORT | C | 2 | 0 | String | 181 | 5 |
| GRAVIDEZ | C | 1 | 0 | String | 181 | 2 |
| SEMAGESTAC | C | 3 | 0 | String | 181 | 17 |
| GESTACAO | C | 1 | 0 | String | 181 | 7 |
| PARTO | C | 1 | 0 | String | 181 | 3 |
| OBITOPARTO | C | 1 | 0 | String | 181 | 2 |
| PESO | C | 4 | 0 | String | 181 | 20 |
| TPMORTEOCO | C | 1 | 0 | String | 179 | 4 |
| OBITOGRAV | C | 1 | 0 | String | 179 | 3 |
| OBITOPUERP | C | 1 | 0 | String | 179 | 4 |
| ASSISTMED | C | 1 | 0 | String | 28 | 4 |
| EXAME | C | 1 | 0 | String | 200 | 1 |
| CIRURGIA | C | 1 | 0 | String | 200 | 1 |
| NECROPSIA | C | 1 | 0 | String | 27 | 4 |
| LINHAA | C | 20 | 0 | String | 16 | 66 |
| LINHAB | C | 20 | 0 | String | 50 | 93 |
| LINHAC | C | 20 | 0 | String | 92 | 81 |
| LINHAD | C | 20 | 0 | String | 147 | 48 |
| LINHAII | C | 30 | 0 | String | 122 | 53 |
| CAUSABAS | C | 4 | 0 | String | 0 | 130 |
| CB_PRE | C | 4 | 0 | String | 200 | 1 |
| COMUNSVOIM | C | 7 | 0 | String | 158 | 3 |
| DTATESTADO | C | 8 | 0 | String | 0 | 41 |
| CIRCOBITO | C | 1 | 0 | String | 153 | 5 |
| ACIDTRAB | C | 1 | 0 | String | 176 | 4 |
| FONTE | C | 1 | 0 | String | 160 | 6 |
| NUMEROLOTE | C | 8 | 0 | String | 0 | 47 |
| TPPOS | C | 1 | 0 | String | 28 | 3 |
| DTINVESTIG | C | 8 | 0 | String | 178 | 14 |
| CAUSABAS_O | C | 4 | 0 | String | 0 | 127 |
| DTCADASTRO | C | 8 | 0 | String | 0 | 52 |
| ATESTANTE | C | 1 | 0 | String | 8 | 5 |
| STCODIFICA | C | 1 | 0 | String | 0 | 1 |
| CODIFICADO | C | 1 | 0 | String | 0 | 1 |
| VERSAOSIST | C | 7 | 0 | String | 0 | 1 |
| VERSAOSCB | C | 7 | 0 | String | 0 | 1 |
| FONTEINV | C | 8 | 0 | String | 178 | 4 |
| DTRECEBIM | C | 8 | 0 | String | 0 | 52 |
| ATESTADO | C | 50 | 0 | String | 0 | 192 |
| DTRECORIGA | C | 8 | 0 | String | 0 | 46 |
| CAUSAMAT | C | 4 | 0 | String | 200 | 1 |
| ESCMAEAGR1 | C | 2 | 0 | String | 181 | 7 |
| ESCFALAGR1 | C | 2 | 0 | String | 26 | 13 |
| STDOEPIDEM | C | 1 | 0 | String | 0 | 1 |
| STDONOVA | C | 1 | 0 | String | 0 | 1 |
| DIFDATA | C | 8 | 0 | String | 0 | 94 |
| NUDIASOBCO | C | 4 | 0 | String | 183 | 17 |
| NUDIASOBIN | C | 4 | 0 | String | 200 | 1 |
| DTCADINV | C | 8 | 0 | String | 183 | 15 |
| TPOBITOCOR | C | 1 | 0 | String | 183 | 5 |
| DTCONINV | C | 8 | 0 | String | 183 | 15 |
| FONTES | C | 6 | 0 | String | 175 | 10 |
| TPRESGINFO | C | 2 | 0 | String | 198 | 2 |
| TPNIVELINV | C | 1 | 0 | String | 183 | 3 |
| NUDIASINF | C | 4 | 0 | String | 200 | 1 |
| DTCADINF | C | 8 | 0 | String | 175 | 14 |
| MORTEPARTO | C | 1 | 0 | String | 175 | 3 |
| DTCONCASO | C | 8 | 0 | String | 178 | 12 |
| FONTESINF | C | 7 | 0 | String | 200 | 1 |
| ALTCAUSA | C | 1 | 0 | String | 178 | 2 |
| CONTADOR | C | 8 | 0 | String | 0 | 200 |

## SINAN — Agravos de Notificação

**Natureza:** notificações · **Subtipo escolhido:** `CHAG` · **Status:** amostra.

**Pergunta de estudo:** Como se organiza uma ficha de Chagas aguda?

**Limitação:** Uma amostra de CHAG não cobre os demais agravos. A modalidade preliminar/final acompanha a origem.

**Inventário:** `/dissemin/publicos/SINAN/DADOS/PRELIM`; 357 arquivos no diretório, 3 candidatos do subtipo dentro do limite de tamanho.

**Arquivo:** [CHAGBR23.dbc](ftp://ftp.datasus.gov.br/dissemin/publicos/SINAN/DADOS/PRELIM/CHAGBR23.dbc) · 411,945 bytes.

**Coleta UTC:** `2026-09-10T16:24:51.338779+00:00` · **Modificação informada pelo FTP (sem fuso):** `2024-12-02T14:39:00`.

**SHA-256:** `a0ab9f568b52c565819466eba2cf312e40549cec707f28e5001de1532f79a10f`

**Original local:** `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/SINAN/CHAGBR23.dbc`

### Subtipos descritos no portal (nem todos foram amostrados)

| fonte | sigla_arquivo | desc_arquivo | abrangencia |
| --- | --- | --- | --- |
| SINAN | ANIM | ANIM - Acidente por Animais Peçonhentos | BR |
| SINAN | ANTR | ANTR - Atendimento Antirrabico | BR |
| SINAN | AIDA | AIDA - AIDS em adultos | BR |
| SINAN | AIDC | AIDC - AIDS em crianças | BR |
| SINAN | BOTU | BOTU - Botulismo | BR |
| SINAN | COLE | COLE - Cólera | BR |
| SINAN | COQU | COQU - Coqueluche | BR |
| SINAN | DENG | DENG - Dengue | BR |
| SINAN | DIFT | DIFT - Difteria | BR |
| SINAN | DCRJ | DCRJ - Doença de Creutzfeldt-Jakob (DCJ) | BR |
| SINAN | CHAG | CHAG - Doença de Chagas Aguda | BR |
| SINAN | EXAN | EXAN - Doença exantemáticas | BR |
| SINAN | ESQU | ESQU - Esquistossomose | BR |
| SINAN | ESPO | ESPO - Esporotricose (Epizootia) | BR |
| SINAN | CHIK | CHIK - Febre de Chikungunya | BR |
| SINAN | FMAC | FMAC - Febre Maculosa | BR |
| SINAN | FTIF | FTIF - Febre Tifóide | BR |
| SINAN | HANS | HANS - Hanseníase | BR |
| SINAN | HANT | HANT - Hantavirose | BR |
| SINAN | HEPA | HEPA - Hepatites Virais | BR |
| SINAN | HIVA | HIVA - HIV em adultos | BR |
| SINAN | HIVC | HIVC - HIV em crianças | BR |
| SINAN | HIVE | HIVE - HIV em crianças expostas | BR |
| SINAN | HIVG | HIVG - HIV em gestante | BR |
| SINAN | INFL | INFL - Influenza Pandêmica | BR |
| SINAN | IEXO | IEXO - Intoxicação Exógena | BR |
| SINAN | LEIV | LEIV - Leishmaniose Visceral | BR |
| SINAN | LTAN | LTAN - Leishmaniose Tegumentar Americana | BR |
| SINAN | LEPT | LEPT - Leptospirose | BR |
| SINAN | MALA | MALA - Malária | BR |
| SINAN | MENI | MENI - Meningite | BR |
| SINAN | PFAN | PFAN - Paralisia Flácida Aguda | BR |
| SINAN | PEST | PEST - Peste | BR |
| SINAN | RAIV | RAIV - Raiva | BR |
| SINAN | ROTA | ROTA - Rotavírus | BR |
| SINAN | SIFA | SIFA - Sífilis Adquirida | BR |
| SINAN | SIFC | SIFC - Sífilis Congênita | BR |
| SINAN | SIFG | SIFG - Sífilis em Gestante | BR |
| SINAN | SRC | SRC - Síndrome da Rubéola Congênia | BR |
| SINAN | SDTA | SDTA - Surto Doenças Transmitidas por Alimentos | BR |
| SINAN | TETA | TETA - Tétano Acidental | BR |
| SINAN | TETN | TETN - Tétano Neonatal | BR |
| SINAN | TOXC | TOXC - Toxoplasmose Congênita | BR |
| SINAN | TOXG | TOXG - Toxoplasmose Gestacional | BR |
| SINAN | NTRA | NTRA - Notificação de Tracoma | BR |
| SINAN | TRAC | TRAC - Inquérito de Tracoma | BR |
| SINAN | TUBE | TUBE - Tuberculose | BR |
| SINAN | VARC | VARC - Varicela | BR |
| SINAN | VIOL | VIOL - Violência doméstica, sexual e/ou outras violências | BR |
| SINAN | ZIKA | ZIKA - Zika Vírus | BR |
| SINAN | ACBI | ACBI - Acidente de trabalho com material biológico | BR |
| SINAN | ACGR | ACGR - Acidente de trabalho | BR |
| SINAN | CANC | CANC - Cancêr relacionado ao trabalho | BR |
| SINAN | DERM | DERM - Dermatoses ocupacionais | BR |
| SINAN | LERD | LERD - LER/Dort | BR |
| SINAN | PAIR | PAIR - Perda auditiva por ruído relacionado ao trabalho | BR |
| SINAN | PNEU | PNEU - Pneumoconioses realacionadas ao trabalho | BR |
| SINAN | MENT | MENT - Transtornos mentais relacionados ao trabalho | BR |
| SINAN_P | ANIM | ANIM - Acidente por Animais Peçonhentos | BR |
| SINAN_P | ANTR | ANTR - Atendimento Antirrabico | BR |
| SINAN_P | AIDA | AIDA - AIDS em adultos | BR |
| SINAN_P | AIDC | AIDC - AIDS em crianças | BR |
| SINAN_P | BOTU | BOTU - Botulismo | BR |
| SINAN_P | COLE | COLE - Cólera | BR |
| SINAN_P | COQU | COQU - Coqueluche | BR |
| SINAN_P | DENG | DENG - Dengue | BR |
| SINAN_P | DIFT | DIFT - Difteria | BR |
| SINAN_P | DCRJ | DCRJ - Doença de Creutzfeldt-Jakob (DCJ) | BR |
| SINAN_P | CHAG | CHAG - Doença de Chagas Aguda | BR |
| SINAN_P | EXAN | EXAN - Doença exantemáticas | BR |
| SINAN_P | ESQU | ESQU - Esquistossomose | BR |
| SINAN_P | ESPO | ESPO - Esporotricose (Epizootia) | BR |
| SINAN_P | CHIK | CHIK - Febre de Chikungunya | BR |
| SINAN_P | FMAC | FMAC - Febre Maculosa | BR |
| SINAN_P | FTIF | FTIF - Febre Tifóide | BR |
| SINAN_P | HANS | HANS - Hanseníase | BR |
| SINAN_P | HANT | HANT - Hantavirose | BR |
| SINAN_P | HEPA | HEPA - Hepatites Virais | BR |
| SINAN_P | HIVA | HIVA - HIV em adultos | BR |
| SINAN_P | HIVC | HIVC - HIV em crianças | BR |
| SINAN_P | HIVE | HIVE - HIV em crianças expostas | BR |
| SINAN_P | HIVG | HIVG - HIV em gestantes | BR |
| SINAN_P | INFL | INFL - Influenza Pandêmica | BR |
| SINAN_P | IEXO | IEXO - Intoxicação Exógena | BR |
| SINAN_P | LEIV | LEIV - Leishmaniose Visceral | BR |
| SINAN_P | LTAN | LTAN - Leishmaniose Tegumentar Americana | BR |
| SINAN_P | LEPT | LEPT - Leptospirose | BR |
| SINAN_P | MALA | MALA - Malária | BR |
| SINAN_P | MENI | MENI - Meningite | BR |
| SINAN_P | PFAN | PFAN - Paralisia Flácida Aguda | BR |
| SINAN_P | PEST | PEST - Peste | BR |
| SINAN_P | SIFA | SIFA - Sífilis Adquirida | BR |
| SINAN_P | SIFC | SIFC - Sífilis Congênita | BR |
| SINAN_P | SIFG | SIFG - Sífilis em Gestante | BR |
| SINAN_P | SRC | SRC - Síndrome da Rubéola Congênia | BR |
| SINAN_P | SDTA | SDTA - Surto Doenças Transmitidas por Alimentos | BR |
| SINAN_P | RAIV | RAIV - Raiva | BR |
| SINAN_P | ROTA | ROTA - Rotavírus | BR |
| SINAN_P | TETA | TETA - Tétano Acidental | BR |
| SINAN_P | TETN | TETN - Tétano Neonatal | BR |
| SINAN_P | TOXC | TOXC - Toxoplasmose Congênita | BR |
| SINAN_P | TOXG | TOXG - Toxoplasmose Gestacional | BR |
| SINAN_P | NTRA | NTRA - Notificação de Tracoma | BR |
| SINAN_P | TRAC | TRAC - Inquérito de Tracoma | BR |
| SINAN_P | TUBE | TUBE - Tuberculose | BR |
| SINAN_P | VARC | VARC - Varicela | BR |
| SINAN_P | VIOL | VIOL - Violência doméstica, sexual e/ou outras violências | BR |
| SINAN_P | ZIKA | ZIKA - Zika Vírus | BR |
| SINAN_P | ACBI | ACBI - Acidente de trabalho com material biológico | BR |
| SINAN_P | ACGR | ACGR - Acidente de trabalho | BR |
| SINAN_P | CANC | CANC - Cancêr relacionado ao trabalho | BR |
| SINAN_P | DERM | DERM - Dermatoses ocupacionais | BR |
| SINAN_P | LERD | LERD - LER/Dort | BR |
| SINAN_P | PAIR | PAIR - Perda auditiva por ruído relacionado ao trabalho | BR |
| SINAN_P | PNEU | PNEU - Pneumoconioses realacionadas ao trabalho | BR |
| SINAN_P | MENT | MENT - Transtornos mentais relacionados ao trabalho | BR |

**Rótulos retornados pelo portal:** SINAN_p / Dados - Preliminares.

### Tabela `CHAGBR23.dbc`

**Identificador:** `t000_CHAGBR23` · **Campos:** 108 · **Linhas na amostra:** 200.

Registros declarados: **6253**; ativos: **6253**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/SINAN/CHAGBR23.dbc_amostras/t000_CHAGBR23.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| TP_NOT | C | 1 | 0 | String | 0 | 1 |
| ID_AGRAVO | C | 4 | 0 | String | 0 | 1 |
| DT_NOTIFIC | D | 8 | 0 | String | 0 | 122 |
| SEM_NOT | C | 6 | 0 | String | 0 | 48 |
| NU_ANO | C | 4 | 0 | String | 0 | 1 |
| SG_UF_NOT | C | 2 | 0 | String | 0 | 14 |
| ID_MUNICIP | C | 6 | 0 | String | 0 | 51 |
| ID_REGIONA | C | 8 | 0 | String | 25 | 25 |
| ID_UNIDADE | C | 7 | 0 | String | 0 | 78 |
| DT_SIN_PRI | D | 8 | 0 | String | 0 | 139 |
| SEM_PRI | C | 6 | 0 | String | 0 | 54 |
| ANO_NASC | C | 4 | 0 | String | 0 | 75 |
| NU_IDADE_N | N | 4 | 0 | String | 0 | 74 |
| CS_SEXO | C | 1 | 0 | String | 0 | 2 |
| CS_GESTANT | C | 1 | 0 | String | 0 | 3 |
| CS_RACA | C | 1 | 0 | String | 1 | 7 |
| CS_ESCOL_N | C | 2 | 0 | String | 17 | 12 |
| SG_UF | C | 2 | 0 | String | 0 | 15 |
| ID_MN_RESI | C | 6 | 0 | String | 0 | 54 |
| ID_RG_RESI | C | 8 | 0 | String | 23 | 28 |
| ID_PAIS | C | 4 | 0 | String | 0 | 1 |
| NDUPLIC_N | C | 1 | 0 | String | 200 | 1 |
| DT_INVEST | D | 8 | 0 | String | 0 | 120 |
| ID_OCUPA_N | C | 6 | 0 | String | 92 | 28 |
| ANT_UF_1 | C | 2 | 0 | String | 186 | 6 |
| MUN_1 | C | 6 | 0 | String | 186 | 12 |
| ANT_UF_2 | C | 2 | 0 | String | 199 | 2 |
| MUN_2 | C | 6 | 0 | String | 199 | 2 |
| ANT_UF_3 | C | 2 | 0 | String | 200 | 1 |
| MUN_3 | C | 6 | 0 | String | 200 | 1 |
| PRESENCA | C | 1 | 0 | String | 1 | 5 |
| PARASITO | D | 8 | 0 | String | 181 | 16 |
| HISTORIA | C | 1 | 0 | String | 1 | 4 |
| CONTROLE | C | 1 | 0 | String | 12 | 4 |
| MANIPULA | C | 1 | 0 | String | 9 | 5 |
| MAECHAGA | C | 1 | 0 | String | 7 | 4 |
| ORAL | C | 1 | 0 | String | 7 | 4 |
| ASSINTOMA | C | 1 | 0 | String | 5 | 4 |
| EDEMA | C | 1 | 0 | String | 16 | 4 |
| MENINGOE | C | 1 | 0 | String | 19 | 4 |
| POLIADENO | C | 1 | 0 | String | 20 | 4 |
| FEBRE | C | 1 | 0 | String | 17 | 4 |
| HEPATOME | C | 1 | 0 | String | 19 | 4 |
| SINAIS_ICC | C | 1 | 0 | String | 20 | 4 |
| ARRITMIAS | C | 1 | 0 | String | 21 | 4 |
| ASTENIA | C | 1 | 0 | String | 16 | 4 |
| ESPLENOM | C | 1 | 0 | String | 20 | 4 |
| CHAGOMA | C | 1 | 0 | String | 20 | 4 |
| OUTRO_SIN | C | 1 | 0 | String | 200 | 1 |
| OUTRO_ESP | C | 30 | 0 | String | 200 | 1 |
| DT_COL_DIR | D | 8 | 0 | String | 40 | 89 |
| EXAME | C | 1 | 0 | String | 28 | 4 |
| MICRO_HEMA | C | 1 | 0 | String | 44 | 4 |
| OUTRO | C | 1 | 0 | String | 54 | 4 |
| DT_COL_IND | D | 8 | 0 | String | 184 | 15 |
| XENODIAG | C | 1 | 0 | String | 141 | 3 |
| HEMOCULT | C | 1 | 0 | String | 140 | 4 |
| DT_COL_S1 | D | 8 | 0 | String | 116 | 67 |
| DT_COL_S2 | D | 8 | 0 | String | 195 | 6 |
| ELI_IGM_S1 | C | 1 | 0 | String | 146 | 4 |
| ELI_IGG_S1 | C | 1 | 0 | String | 139 | 5 |
| ELI_IGM_S2 | C | 1 | 0 | String | 175 | 3 |
| ELI_IGG_S2 | C | 1 | 0 | String | 173 | 4 |
| HEM_IGM_S1 | C | 1 | 0 | String | 148 | 3 |
| HEM_IGG_S1 | C | 1 | 0 | String | 143 | 4 |
| HEM_IGM_S2 | C | 1 | 0 | String | 174 | 3 |
| HEM_IGG_S2 | C | 1 | 0 | String | 175 | 3 |
| IMU_IGM_S1 | C | 1 | 0 | String | 149 | 5 |
| TIT_IGM_S1 | C | 5 | 0 | String | 185 | 7 |
| IMU_IGM_S2 | C | 1 | 0 | String | 176 | 3 |
| TIT_IGM_S2 | C | 5 | 0 | String | 197 | 2 |
| IMU_IGG_S1 | C | 1 | 0 | String | 154 | 5 |
| TIT_IGG_S1 | C | 5 | 0 | String | 191 | 5 |
| IMU_IGG_S2 | C | 1 | 0 | String | 178 | 3 |
| TIT_IGG_S2 | C | 5 | 0 | String | 198 | 3 |
| RESUL_HIS | D | 8 | 0 | String | 199 | 2 |
| RES_HIST | C | 1 | 0 | String | 152 | 5 |
| ESPECIFICO | C | 1 | 0 | String | 46 | 4 |
| SINTOMATIC | C | 1 | 0 | String | 52 | 4 |
| DROGA | C | 1 | 0 | String | 84 | 3 |
| TEMPO | N | 3 | 0 | String | 92 | 4 |
| CON_TRIAT | C | 1 | 0 | String | 54 | 5 |
| BIOSSEG | C | 1 | 0 | String | 60 | 5 |
| FISCALIZA | C | 1 | 0 | String | 58 | 5 |
| MED_OUTRO | C | 1 | 0 | String | 61 | 5 |
| OUTRO_DES | C | 30 | 0 | String | 127 | 25 |
| CLASSI_FIN | C | 1 | 0 | String | 0 | 2 |
| CRITERIO | C | 1 | 0 | String | 5 | 4 |
| EVOLUCAO | C | 1 | 0 | String | 4 | 4 |
| DT_OBITO | D | 8 | 0 | String | 124 | 72 |
| CON_PROVAV | C | 1 | 0 | String | 64 | 4 |
| CON_OUTRA | C | 30 | 0 | String | 200 | 1 |
| CON_LOCAL | C | 1 | 0 | String | 66 | 5 |
| TPAUTOCTO | C | 1 | 0 | String | 64 | 4 |
| COUFINF | C | 2 | 0 | String | 65 | 8 |
| COPAISINF | C | 4 | 0 | String | 0 | 2 |
| COMUNINF | C | 6 | 0 | String | 65 | 30 |
| DOENCA_TRA | C | 1 | 0 | String | 90 | 3 |
| DT_ENCERRA | D | 8 | 0 | String | 0 | 107 |
| DT_DIGITA | D | 8 | 0 | String | 0 | 108 |
| DT_TRANSUS | D | 8 | 0 | String | 181 | 20 |
| DT_TRANSDM | D | 8 | 0 | String | 199 | 2 |
| DT_TRANSSM | D | 8 | 0 | String | 111 | 61 |
| DT_TRANSRM | D | 8 | 0 | String | 200 | 1 |
| DT_TRANSRS | D | 8 | 0 | String | 195 | 6 |
| DT_TRANSSE | D | 8 | 0 | String | 198 | 3 |
| NU_LOTE_V | C | 7 | 0 | String | 200 | 1 |
| NU_LOTE_H | C | 7 | 0 | String | 200 | 1 |

## SINASC — Nascidos Vivos

**Natureza:** registros · **Subtipo escolhido:** `DN` · **Status:** amostra.

**Pergunta de estudo:** Quais campos descrevem nascimento e características maternas?

**Limitação:** Amostra DNRES; comparar edições exige verificar alterações do esquema.

**Inventário:** `/dissemin/publicos/SINASC/1996_/Dados/DNRES`; 823 arquivos no diretório, 799 candidatos do subtipo dentro do limite de tamanho.

**Arquivo:** [DNRR2023.dbc](ftp://ftp.datasus.gov.br/dissemin/publicos/SINASC/1996_/Dados/DNRES/DNRR2023.dbc) · 627,526 bytes.

**Coleta UTC:** `2026-09-10T16:24:52.299792+00:00` · **Modificação informada pelo FTP (sem fuso):** `2024-12-20T11:41:00`.

**SHA-256:** `3b9c5cb07b3981e735bea9bc9c7967906af13047b202cc85550b92c885e82a3c`

**Original local:** `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/SINASC/DNRR2023.dbc`

### Subtipos descritos no portal (nem todos foram amostrados)

| fonte | sigla_arquivo | desc_arquivo | abrangencia |
| --- | --- | --- | --- |
| SINASC | DN | DN - Declarações de nascidos vivos 1994 a 2026 | TT |
| SINASC | DNEX | DNEX - Declarações de nascidos vivos residentes no exterior 2014 a 2026 | BR |

**Rótulos retornados pelo portal:** SINASC / Dados - Finais.

### Tabela `DNRR2023.dbc`

**Identificador:** `t000_DNRR2023` · **Campos:** 61 · **Linhas na amostra:** 200.

Registros declarados: **13105**; ativos: **13105**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/SINASC/DNRR2023.dbc_amostras/t000_DNRR2023.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| ORIGEM | C | 1 | 0 | String | 0 | 1 |
| CODESTAB | C | 7 | 0 | String | 172 | 9 |
| CODMUNNASC | C | 7 | 0 | String | 0 | 4 |
| LOCNASC | C | 1 | 0 | String | 0 | 4 |
| IDADEMAE | C | 2 | 0 | String | 0 | 31 |
| ESTCIVMAE | C | 1 | 0 | String | 0 | 5 |
| ESCMAE | C | 1 | 0 | String | 0 | 6 |
| CODOCUPMAE | C | 6 | 0 | String | 1 | 9 |
| QTDFILVIVO | C | 2 | 0 | String | 0 | 10 |
| QTDFILMORT | C | 2 | 0 | String | 6 | 5 |
| CODMUNRES | C | 7 | 0 | String | 0 | 5 |
| GESTACAO | C | 1 | 0 | String | 0 | 3 |
| GRAVIDEZ | C | 1 | 0 | String | 0 | 2 |
| PARTO | C | 1 | 0 | String | 0 | 2 |
| CONSULTAS | C | 1 | 0 | String | 0 | 4 |
| DTNASC | C | 8 | 0 | String | 0 | 115 |
| HORANASC | C | 5 | 0 | String | 0 | 118 |
| SEXO | C | 1 | 0 | String | 0 | 2 |
| APGAR1 | C | 2 | 0 | String | 173 | 4 |
| APGAR5 | C | 2 | 0 | String | 173 | 4 |
| RACACOR | C | 1 | 0 | String | 0 | 4 |
| PESO | C | 4 | 0 | String | 0 | 58 |
| IDANOMAL | C | 1 | 0 | String | 0 | 1 |
| DTCADASTRO | C | 8 | 0 | String | 0 | 54 |
| CODANOMAL | C | 20 | 0 | String | 200 | 1 |
| NUMEROLOTE | C | 8 | 0 | String | 168 | 20 |
| VERSAOSIST | C | 7 | 0 | String | 168 | 2 |
| DTRECEBIM | C | 8 | 0 | String | 168 | 22 |
| DIFDATA | C | 8 | 0 | String | 0 | 131 |
| DTRECORIGA | C | 8 | 0 | String | 200 | 1 |
| NATURALMAE | C | 3 | 0 | String | 6 | 4 |
| CODMUNNATU | C | 7 | 0 | String | 6 | 10 |
| CODUFNATU | C | 2 | 0 | String | 6 | 4 |
| ESCMAE2010 | C | 1 | 0 | String | 0 | 6 |
| SERIESCMAE | C | 1 | 0 | String | 174 | 8 |
| DTNASCMAE | C | 8 | 0 | String | 0 | 180 |
| RACACORMAE | C | 1 | 0 | String | 0 | 4 |
| QTDGESTANT | C | 2 | 0 | String | 0 | 10 |
| QTDPARTNOR | C | 2 | 0 | String | 0 | 10 |
| QTDPARTCES | C | 2 | 0 | String | 0 | 4 |
| IDADEPAI | C | 2 | 0 | String | 85 | 36 |
| DTULTMENST | C | 8 | 0 | String | 7 | 112 |
| SEMAGESTAC | C | 2 | 0 | String | 0 | 8 |
| TPMETESTIM | C | 2 | 0 | String | 0 | 3 |
| CONSPRENAT | C | 2 | 0 | String | 62 | 15 |
| MESPRENAT | C | 2 | 0 | String | 25 | 11 |
| TPAPRESENT | C | 2 | 0 | String | 0 | 1 |
| STTRABPART | C | 1 | 0 | String | 0 | 3 |
| STCESPARTO | C | 1 | 0 | String | 0 | 4 |
| TPNASCASSI | C | 2 | 0 | String | 0 | 5 |
| TPFUNCRESP | C | 1 | 0 | String | 2 | 4 |
| TPDOCRESP | C | 1 | 0 | String | 0 | 5 |
| DTDECLARAC | C | 8 | 0 | String | 3 | 62 |
| ESCMAEAGR1 | C | 2 | 0 | String | 0 | 9 |
| STDNEPIDEM | C | 1 | 0 | String | 0 | 2 |
| STDNNOVA | C | 1 | 0 | String | 0 | 1 |
| CODPAISRES | C | 3 | 0 | String | 2 | 2 |
| TPROBSON | C | 2 | 0 | String | 0 | 6 |
| PARIDADE | C | 10 | 0 | String | 0 | 2 |
| KOTELCHUCK | C | 1 | 0 | String | 0 | 6 |
| CONTADOR | C | 8 | 0 | String | 0 | 200 |

## SISCOLO — Câncer do Colo de Útero

**Natureza:** exames · **Subtipo escolhido:** `CC` · **Status:** amostra.

**Pergunta de estudo:** Que variáveis descrevem os exames citopatológicos?

**Limitação:** Acervo histórico CC. O portal pode rotular a fonte como SIASUS; mantemos também a categoria solicitada.

**Inventário:** `/dissemin/publicos/SISCAN/SISCOLO4/Dados`; 5716 arquivos no diretório, 2858 candidatos do subtipo dentro do limite de tamanho.

**Arquivo:** [CCRR1301.dbc](ftp://ftp.datasus.gov.br/dissemin/publicos/SISCAN/SISCOLO4/Dados/CCRR1301.dbc) · 53,230 bytes.

**Coleta UTC:** `2026-09-10T16:24:53.330181+00:00` · **Modificação informada pelo FTP (sem fuso):** `2022-08-17T12:15:00`.

**SHA-256:** `b77df19ea9b261d473c1adb4b3a0f9e44fd8f156444f09e10e50dabdbf15a815`

**Original local:** `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/SISCOLO/CCRR1301.dbc`

### Subtipos descritos no portal (nem todos foram amostrados)

| fonte | sigla_arquivo | desc_arquivo | abrangencia |
| --- | --- | --- | --- |
| SISCOLO | CC | CC - Citopatológico de Colo de Útero - 2006 a 2014 | UF |
| SISCOLO | HC | HC - Histopatológico de Colo de Útero - 2006 a 2014 | UF |

**Rótulos retornados pelo portal:** SIASUS / Dados.

### Tabela `CCRR1301.dbc`

**Identificador:** `t000_CCRR1301` · **Campos:** 102 · **Linhas na amostra:** 200.

Registros declarados: **1903**; ativos: **1903**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/SISCOLO/CCRR1301.dbc_amostras/t000_CCRR1301.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_US | C | 7 | 0 | String | 0 | 60 |
| CO_US_UF | C | 2 | 0 | String | 0 | 1 |
| CO_US_IBGE | C | 7 | 0 | String | 0 | 13 |
| REGUS | C | 1 | 0 | String | 0 | 1 |
| CO_PAC_IBG | C | 7 | 0 | String | 0 | 14 |
| CO_PAC_UF | C | 2 | 0 | String | 0 | 1 |
| CO_PAC_ESC | C | 1 | 0 | String | 0 | 4 |
| CO_RES_NOR | C | 1 | 0 | String | 0 | 1 |
| CO_PAC_IDA | C | 3 | 0 | String | 0 | 55 |
| REGRESID | C | 1 | 0 | String | 0 | 1 |
| CO_CNES | C | 7 | 0 | String | 0 | 2 |
| CLABIBGE | C | 7 | 0 | String | 0 | 1 |
| CLABUF | C | 2 | 0 | String | 0 | 1 |
| REGLAB | C | 1 | 0 | String | 0 | 1 |
| DT_ID_COMP | C | 6 | 0 | String | 0 | 1 |
| ANO_COMP | C | 4 | 0 | String | 0 | 1 |
| CO_FX_ETAR | C | 2 | 0 | String | 0 | 12 |
| CO_PAC_RAC | C | 2 | 0 | String | 0 | 1 |
| CO_ATI_ESC | C | 1 | 0 | String | 0 | 3 |
| CO_ATI_GLA | C | 1 | 0 | String | 0 | 2 |
| CO_ATI_IND | C | 1 | 0 | String | 0 | 1 |
| CO_CEL_ESC | C | 1 | 0 | String | 0 | 2 |
| CO_CEL_GLA | C | 1 | 0 | String | 0 | 1 |
| CO_NEO_MAL | C | 1 | 0 | String | 0 | 1 |
| CO_AMOSTRA | C | 1 | 0 | String | 0 | 1 |
| CO_ADEQ_MA | C | 1 | 0 | String | 0 | 2 |
| CO_BEN_INF | C | 1 | 0 | String | 0 | 2 |
| CO_BEN_MET | C | 1 | 0 | String | 0 | 2 |
| CO_BEN_REP | C | 1 | 0 | String | 0 | 1 |
| CO_BEN_ATR | C | 1 | 0 | String | 0 | 2 |
| CO_BEN_RAD | C | 1 | 0 | String | 0 | 2 |
| CO_BEN_OUT | C | 1 | 0 | String | 0 | 2 |
| CO_MIC_LAC | C | 1 | 0 | String | 0 | 2 |
| CO_MIC_COC | C | 1 | 0 | String | 0 | 2 |
| CO_MIC_CHL | C | 1 | 0 | String | 0 | 1 |
| CO_MIC_ACT | C | 1 | 0 | String | 0 | 1 |
| CO_MIC_BAC | C | 1 | 0 | String | 0 | 2 |
| CO_MIC_TRI | C | 1 | 0 | String | 0 | 2 |
| CO_MIC_HER | C | 1 | 0 | String | 0 | 1 |
| CO_MIC_CAN | C | 1 | 0 | String | 0 | 2 |
| CO_MIC_GAR | C | 1 | 0 | String | 0 | 2 |
| CO_MIC_OUT | C | 1 | 0 | String | 0 | 2 |
| CO_ANM_PRE | C | 1 | 0 | String | 0 | 4 |
| DT_ANM_PRE | C | 4 | 0 | String | 42 | 10 |
| ST_MON_EXT | C | 1 | 0 | String | 0 | 3 |
| TEMPCITANT | C | 8 | 0 | String | 42 | 7 |
| DINTCOLETA | C | 1 | 0 | String | 0 | 4 |
| DINTRESULT | C | 1 | 0 | String | 0 | 4 |
| DINTTEMPEX | C | 1 | 0 | String | 0 | 3 |
| QTDEXA | C | 8 | 0 | String | 0 | 3 |
| QUANTEXAME | C | 8 | 0 | String | 0 | 3 |
| REPREZT | C | 8 | 0 | String | 0 | 3 |
| RESNORM | C | 8 | 0 | String | 0 | 1 |
| POSNAONEO | C | 8 | 0 | String | 0 | 2 |
| LESALTGRA | C | 8 | 0 | String | 0 | 2 |
| PSNAONPLA | C | 8 | 0 | String | 0 | 2 |
| NLSALTGRA | C | 8 | 0 | String | 0 | 1 |
| PSNNPLA | C | 8 | 0 | String | 0 | 1 |
| NALTGRA | C | 8 | 0 | String | 0 | 1 |
| LBGRAU | C | 8 | 0 | String | 0 | 2 |
| LAGRAU | C | 8 | 0 | String | 0 | 1 |
| LAGRAUMI | C | 8 | 0 | String | 0 | 1 |
| CARCINO | C | 8 | 0 | String | 0 | 1 |
| C_EPI_ESCA | C | 8 | 0 | String | 0 | 4 |
| C_EPI_GLAN | C | 8 | 0 | String | 0 | 3 |
| CO_EPI_MET | C | 8 | 0 | String | 0 | 2 |
| ADENCARCIN | C | 8 | 0 | String | 0 | 1 |
| DENCARCINV | C | 8 | 0 | String | 0 | 1 |
| OUTNEO | C | 8 | 0 | String | 0 | 1 |
| ALTERADO | C | 8 | 0 | String | 0 | 2 |
| CVCIONAL | C | 8 | 0 | String | 0 | 1 |
| MEIOLIQU | C | 8 | 0 | String | 0 | 1 |
| AMOSREJAUS | C | 8 | 0 | String | 0 | 1 |
| AMOSREJDAN | C | 8 | 0 | String | 0 | 1 |
| AMOSREJALH | C | 8 | 0 | String | 0 | 1 |
| AMOSREJOUT | C | 8 | 0 | String | 0 | 1 |
| REJEITADA | C | 8 | 0 | String | 0 | 1 |
| SATISFACT | C | 8 | 0 | String | 0 | 4 |
| INSATSFAC | C | 8 | 0 | String | 0 | 2 |
| CO_INSA_AC | C | 8 | 0 | String | 0 | 2 |
| CO_INSA_SA | C | 8 | 0 | String | 0 | 1 |
| CO_INSA_PI | C | 8 | 0 | String | 0 | 1 |
| CO_INSA_AR | C | 8 | 0 | String | 0 | 2 |
| CO_INSA_CO | C | 8 | 0 | String | 0 | 1 |
| CO_INSA_SU | C | 8 | 0 | String | 0 | 1 |
| CO_INSA_OU | C | 8 | 0 | String | 0 | 1 |
| CBEMINFLA | C | 8 | 0 | String | 0 | 4 |
| CBEMMETAS | C | 8 | 0 | String | 0 | 2 |
| CBEMREPAR | C | 8 | 0 | String | 0 | 1 |
| CBEMATROF | C | 8 | 0 | String | 0 | 2 |
| CBEMRADI | C | 8 | 0 | String | 0 | 2 |
| CBEMOUT | C | 8 | 0 | String | 0 | 2 |
| CMICLACT | C | 8 | 0 | String | 0 | 3 |
| CMICCOCO | C | 8 | 0 | String | 0 | 2 |
| CMICCHLA | C | 8 | 0 | String | 0 | 1 |
| CMICACTI | C | 8 | 0 | String | 0 | 1 |
| CMICBACI | C | 8 | 0 | String | 0 | 3 |
| CMICTRICO | C | 8 | 0 | String | 0 | 2 |
| CMICHERP | C | 8 | 0 | String | 0 | 1 |
| CMICCAND | C | 8 | 0 | String | 0 | 2 |
| CMICGARD | C | 8 | 0 | String | 0 | 3 |
| CMICOUT | C | 8 | 0 | String | 0 | 2 |

## SISMAMA — Câncer de Mama

**Natureza:** exames · **Subtipo escolhido:** `CM` · **Status:** amostra.

**Pergunta de estudo:** Que campos descrevem a citopatologia de mama?

**Limitação:** Acervo histórico CM. Um arquivo existente pode estar vazio; tentativas sem linhas são registradas.

**Inventário:** `/dissemin/publicos/SISCAN/SISMAMA/Dados`; 5023 arquivos no diretório, 1675 candidatos do subtipo dentro do limite de tamanho.

**Arquivo:** [CMSP1409.dbc](ftp://ftp.datasus.gov.br/dissemin/publicos/SISCAN/SISMAMA/Dados/CMSP1409.dbc) · 10,292 bytes.

**Coleta UTC:** `2026-09-10T16:25:53.789467+00:00` · **Modificação informada pelo FTP (sem fuso):** `2022-08-31T17:05:00`.

**SHA-256:** `81fe1e7bd5494e7590cbc88a6489137a3615285872a1595442c95666ba426f51`

**Original local:** `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162552-sismama/SISMAMA/CMSP1409.dbc`

### Subtipos descritos no portal (nem todos foram amostrados)

| fonte | sigla_arquivo | desc_arquivo | abrangencia |
| --- | --- | --- | --- |
| SISMAMA | CM | CM - Citopatológico de Mama - 2006 a 2014 | UF |
| SISMAMA | HM | HC - Histopatológico de Mama - 2006 a 2014 | UF |

**Rótulos retornados pelo portal:** SIASUS / Dados.

### Tentativas de obtenção

| arquivo | status | motivo |
| --- | --- | --- |
| CMRR1301.dbc | vazio | Arquivo sem registros nas tabelas lidas. |
| CMRR0909.dbc | vazio | Arquivo sem registros nas tabelas lidas. |
| CMRR0910.dbc | vazio | Arquivo sem registros nas tabelas lidas. |
| CMRR0911.dbc | vazio | Arquivo sem registros nas tabelas lidas. |
| CMRR1301.dbc | vazio | Arquivo sem registros nas tabelas lidas. |
| CMSP1409.dbc | amostra | — |

### Tabela `CMSP1409.dbc`

**Identificador:** `t000_CMSP1409` · **Campos:** 54 · **Linhas na amostra:** 200.

Registros declarados: **428**; ativos: **428**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162552-sismama/SISMAMA/CMSP1409.dbc_amostras/t000_CMSP1409.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| CO_PAC_UF | C | 2 | 0 | String | 0 | 1 |
| CO_US_UF | C | 2 | 0 | String | 0 | 1 |
| CO_PAC_IBG | C | 7 | 0 | String | 0 | 52 |
| CO_US_IBGE | C | 7 | 0 | String | 0 | 32 |
| CO_US | C | 7 | 0 | String | 0 | 60 |
| CO_CNES | C | 7 | 0 | String | 0 | 23 |
| PRESTUF | C | 2 | 0 | String | 0 | 1 |
| REGUS | C | 1 | 0 | String | 0 | 1 |
| REGRESID | C | 1 | 0 | String | 0 | 1 |
| REGLAB | C | 1 | 0 | String | 0 | 1 |
| ANO_COMP | C | 4 | 0 | String | 0 | 2 |
| PRESTMUN | C | 7 | 0 | String | 0 | 18 |
| DT_ID_COMP | C | 6 | 0 | String | 0 | 1 |
| CO_FX_ETAR | C | 2 | 0 | String | 0 | 13 |
| CO_PAC_ESC | C | 1 | 0 | String | 0 | 6 |
| CO_PAC_SEX | C | 1 | 0 | String | 0 | 2 |
| CO_PAC_RAC | C | 2 | 0 | String | 0 | 5 |
| CANMPACANC | C | 1 | 0 | String | 0 | 4 |
| CO_CLI_DES | C | 1 | 0 | String | 0 | 4 |
| CO_CLI_NOD | C | 1 | 0 | String | 0 | 5 |
| CCLIMATMAM | C | 1 | 0 | String | 0 | 3 |
| CCLIMATDPC | C | 1 | 0 | String | 0 | 4 |
| DINTCOLETA | C | 1 | 0 | String | 0 | 5 |
| DINTRESULT | C | 1 | 0 | String | 0 | 5 |
| DINTTEMPEX | C | 1 | 0 | String | 0 | 4 |
| CO_RES_ADE | C | 1 | 0 | String | 0 | 3 |
| PRESULPAAF | C | 1 | 0 | String | 0 | 6 |
| CRESBENIG | C | 1 | 0 | String | 0 | 7 |
| CRESMALIIN | C | 1 | 0 | String | 0 | 3 |
| CRESSUSMAL | C | 1 | 0 | String | 0 | 4 |
| CRESPOSMAL | C | 1 | 0 | String | 0 | 4 |
| CRESDERPAP | C | 1 | 0 | String | 0 | 5 |
| QUANTEXAME | C | 8 | 0 | String | 0 | 5 |
| PBENMASTIT | C | 8 | 0 | String | 0 | 1 |
| PBENABSUBA | C | 8 | 0 | String | 0 | 2 |
| PBENFIBROA | C | 8 | 0 | String | 0 | 2 |
| PBENNECGOR | C | 8 | 0 | String | 0 | 1 |
| PBENCONDFI | C | 8 | 0 | String | 0 | 3 |
| PBENLESEPI | C | 8 | 0 | String | 0 | 3 |
| PBENOUTRAS | C | 8 | 0 | String | 0 | 5 |
| PMALINTUMP | C | 8 | 0 | String | 0 | 1 |
| PMALINTUMF | C | 8 | 0 | String | 0 | 1 |
| PMALINOUTR | C | 8 | 0 | String | 0 | 2 |
| PSUSLEJPCA | C | 8 | 0 | String | 0 | 2 |
| PSUSOUTROS | C | 8 | 0 | String | 0 | 2 |
| PPOSMACDUC | C | 8 | 0 | String | 0 | 2 |
| PPOSMACLOB | C | 8 | 0 | String | 0 | 1 |
| PPOSMACOUT | C | 8 | 0 | String | 0 | 2 |
| DEMATACELU | C | 8 | 0 | String | 0 | 2 |
| DENEGMALIG | C | 8 | 0 | String | 0 | 5 |
| DEMALIINDT | C | 8 | 0 | String | 0 | 1 |
| DEPOSMALIG | C | 8 | 0 | String | 0 | 1 |
| DELESMALIG | C | 8 | 0 | String | 0 | 1 |
| DEPROCINFL | C | 8 | 0 | String | 0 | 2 |

## SISPRENATAL — Monitoramento do Pré-Natal

**Natureza:** registros · **Subtipo escolhido:** `PN` · **Status:** amostra.

**Pergunta de estudo:** Quais variáveis descrevem o acompanhamento pré-natal?

**Limitação:** Recorte histórico PN; não deve ser interpretado como retrato da atenção pré-natal atual.

**Inventário:** `/dissemin/publicos/SISPRENATAL/201201_/Dados`; 944 arquivos no diretório, 944 candidatos do subtipo dentro do limite de tamanho.

**Arquivo:** [PNRR1301.dbc](ftp://ftp.datasus.gov.br/dissemin/publicos/SISPRENATAL/201201_/Dados/PNRR1301.dbc) · 2,551 bytes.

**Coleta UTC:** `2026-09-10T16:24:55.531324+00:00` · **Modificação informada pelo FTP (sem fuso):** `2014-05-22T10:23:00`.

**SHA-256:** `221be92d16ca8a4902f27ff2a954d4dd32261e3b0b786c1172347b44923a6465`

**Original local:** `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/SISPRENATAL/PNRR1301.dbc`

### Subtipos descritos no portal (nem todos foram amostrados)

| fonte | sigla_arquivo | desc_arquivo | abrangencia |
| --- | --- | --- | --- |
| SISPRENATAL | PN | PN - Pré-Natal - 2012 a 2014 | UF |

**Rótulos retornados pelo portal:** SISPRENATAL / Dados.

### Tabela `PNRR1301.dbc`

**Identificador:** `t000_PNRR1301` · **Campos:** 36 · **Linhas na amostra:** 33.

Registros declarados: **33**; ativos: **33**; excluídos: **0**. Reparo do terminador DBF: **False**.

Amostra Parquet: `/Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162322/SISPRENATAL/PNRR1301.dbc_amostras/t000_PNRR1301.parquet`

| nome | tipo_origem | largura | decimais | tipo_amostra | nulos_amostra | distintos_amostra |
| --- | --- | --- | --- | --- | --- | --- |
| NU_ANO_GES | C | 4 | 0 | String | 0 | 2 |
| DT_ATEND | C | 6 | 0 | String | 0 | 1 |
| CO_UF_IBGE | C | 2 | 0 | String | 0 | 1 |
| NU_GESTA | C | 6 | 0 | String | 0 | 33 |
| CO_GESTANT | C | 12 | 0 | String | 0 | 1 |
| CO_PAIS | C | 3 | 0 | String | 0 | 1 |
| NU_CNS | C | 15 | 0 | String | 0 | 33 |
| NU_IDADE | C | 15 | 0 | String | 0 | 15 |
| NU_NIS | C | 15 | 0 | String | 31 | 3 |
| NU_NIS_REP | C | 15 | 0 | String | 33 | 1 |
| DS_ZONA | C | 50 | 0 | String | 8 | 3 |
| QT_AB_ECT | C | 3 | 0 | String | 0 | 2 |
| QT_AB_GER | C | 3 | 0 | String | 0 | 1 |
| QT_AB_MOL | C | 3 | 0 | String | 0 | 3 |
| QT_MOR_APS | C | 3 | 0 | String | 0 | 1 |
| QT_MOR_PS | C | 3 | 0 | String | 0 | 1 |
| QT_NSC_MOR | C | 3 | 0 | String | 0 | 1 |
| QT_NSC_VIV | C | 3 | 0 | String | 0 | 5 |
| QT_PRT_CIR | C | 3 | 0 | String | 0 | 2 |
| QT_PRT_FOR | C | 3 | 0 | String | 0 | 1 |
| QT_PRT_VAG | C | 3 | 0 | String | 0 | 5 |
| ST_AUX_DSL | C | 1 | 0 | String | 0 | 1 |
| ST_GRA_ANT | C | 1 | 0 | String | 0 | 2 |
| ST_GRA_PLA | C | 1 | 0 | String | 0 | 2 |
| DT_DUM | C | 8 | 0 | String | 1 | 30 |
| DT_DPP | C | 8 | 0 | String | 1 | 30 |
| CO_TPO_GRA | C | 10 | 0 | String | 0 | 2 |
| CO_ESC_GP | C | 2 | 0 | String | 0 | 6 |
| CO_RAC_GP | C | 2 | 0 | String | 0 | 3 |
| CO_ETN_GP | C | 4 | 0 | String | 27 | 3 |
| CO_STF_GP | C | 2 | 0 | String | 0 | 6 |
| CO_MUN_UBS | C | 6 | 0 | String | 0 | 5 |
| QT_CONS | N | 3 | 0 | String | 0 | 3 |
| QT_CONSULT | C | 3 | 0 | String | 0 | 3 |
| ST_GESTAC | C | 1 | 0 | String | 0 | 2 |
| DT_INC | C | 8 | 0 | String | 0 | 18 |

## Recuperações após a coleta inicial

| categoria | manifesto | fim_utc |
| --- | --- | --- |
| SISMAMA | /Users/raphael/PycharmProjects/omnisus-db/data/lake/panorama-datasus/20260910T162552-sismama/manifesto.json | 2026-09-10T16:25:53.791914+00:00 |

## Conferência de dicionários e significados

Veja a [auditoria de documentação oficial e cobertura por coluna](AUDITORIA_DICIONARIOS.md). O esquema físico não equivale a um dicionário semântico validado.
