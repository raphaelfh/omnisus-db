# Auditoria de subtipos e dicionários

Conferência em 2026-09-10T17:22:28.049716+00:00.

## O que é um subtipo

O portal usa o campo **Tipo de Arquivo**. Neste acervo, subtipo é o conjunto de registros/assunto dentro de uma categoria: CNES tem ST (estabelecimentos), LT (leitos), PF (profissionais); SIHSUS tem RD (AIH reduzida), RJ (AIH rejeitadas), SP (serviços profissionais); SIASUS tem PA (produção ambulatorial), AM (medicamentos), AQ (quimioterapia); SINAN tem CHAG (Chagas aguda), DENG (dengue), HANS (hanseníase). UF, ano e mês são recortes; DBC/ZIP/DBF são formatos. Nenhum desses dois conceitos equivale ao subtipo.

As definições foram conferidas no [JavaScript oficial do seletor](https://datasus.saude.gov.br/wp-content/transferencia.js), salvo no acervo, e na documentação específica consultada.

## Conclusão

**Não existe neste notebook um dicionário semântico completo, validado coluna por coluna, para as 1.326 ocorrências de campos.** O mapa anterior cobre os descritores físicos observados nos arquivos. Há documentação oficial para muitas fontes, e há rótulos/decodificações locais para parte dos campos; essas coberturas são diferentes.

Uma descrição explica o significado de uma variável. Um domínio enumera seus códigos permitidos. Um layout define posição, tipo e tamanho. Para códigos como CID-10, CBO, CNES, IBGE e SIGTAP, também pode ser necessária uma tabela externa com edição compatível. Um campo de texto livre, data ou quantidade não necessariamente possui uma lista de códigos.

## Conferência 1: campos observados versus YAMLs locais

Correspondência por nome exato, ignorando maiúsculas/minúsculas, entre o arquivo amostrado e o YAML do mesmo subtipo. Rótulo local não é certificação de exatidão e uma lista x-decode pode não abranger todo o domínio. Não aplicamos o YAML SIA-BI à amostra PA, nem o YAML da API populacional ao arquivo IBGE POPT.

| categoria | campos_amostrados | rotulos_locais | mapas_de_codigos_locais | pdfs_oficiais_lidos | nomes_mencionados_em_pdf |
| --- | --- | --- | --- | --- | --- |
| Base Territorial | 111 | 0 | 0 | 1 | 106 |
| CIH | 27 | 0 | 0 | 0 | 0 |
| CIHA | 30 | 0 | 0 | 1 | 29 |
| CNES | 208 | 9 | 2 | 1 | 199 |
| ESUSNOTIFICA | 109 | 0 | 0 | 1 | 88 |
| IBGE | 84 | 0 | 0 | 1 | 28 |
| PCE | 35 | 0 | 0 | 1 | 35 |
| PO | 23 | 0 | 0 | 1 | 23 |
| RESP | 78 | 0 | 0 | 1 | 78 |
| SIASUS | 60 | 0 | 0 | 1 | 59 |
| SIHSUS | 113 | 95 | 21 | 1 | 110 |
| SIM | 87 | 87 | 38 | 1 | 81 |
| SINAN | 108 | 0 | 0 | 2 | 107 |
| SINASC | 61 | 61 | 26 | 1 | 22 |
| SISCOLO | 102 | 0 | 0 | 0 | 0 |
| SISMAMA | 54 | 0 | 0 | 0 | 0 |
| SISPRENATAL | 36 | 0 | 0 | 0 | 0 |

As colunas "nomes_mencionados_em_pdf" indicam somente presença textual no documento lido. Não garantem definição completa, aplicabilidade à edição ou associação à mesma tabela; falhas de extração de PDF podem reduzir a contagem.

Total local: 252 campos com rótulo e 87 com mapa de códigos, entre 1326 ocorrências.

## Conferência 2: documentação oficial obtida e exemplos revisados

- Foram baixados e lidos 14 PDFs oficiais: 12 do FTP DATASUS e 2 do Portal SINAN, com SHA-256 registrado. Eles cobrem 13 categorias com tabelas; isso não significa cobertura semântica integral dessas categorias.
- SIM: a página 2 de Estrutura_do_SIM_2025.pdf foi conferida também visualmente. SEXO admite M/1 para masculino, F/2 para feminino e I/0/9 para ignorado. RACACOR descreve 1 branca, 2 preta, 3 amarela, 4 parda e 5 indígena. O documento informa atualização 07/2025; a amostra é de 2023, então não se presume equivalência de todos os campos entre edições.
- SIHSUS: IT_SIHSUS_1603.pdf descreve DIAGSEC1–DIAGSEC9 e TPDISEC1–TPDISEC9. Esses 18 campos existem na amostra, mas não no YAML local sih_rd. Nesse informe, SEXO tem descrição, mas a linha correspondente não enumera seus códigos.
- SINAN/CHAG: o dicionário específico declara que parte dos campos gerais depende do dicionário de Notificação Individual. Os dois foram consultados. A revisão do documento Chagas v5 é de julho/2010; os arquivos amostrados são de 2023.
- SINASC: o PDF do FTP define campos e códigos, mas é uma estrutura histórica. Sua existência não valida automaticamente todos os 61 campos da edição 2023.
- Base Territorial: há o manual bases_territoriais.pdf, além de arquivos *_layout.txt dentro do ZIP amostrado. Layouts físicos não constituem, por si só, uma explicação completa de cada classificação territorial.
- CIH: a chamada do portal expirou; o diretório /dissemin/publicos/CIH/200801_201012/Doc foi consultado diretamente e estava vazio.
- SISCOLO, SISMAMA e SISPRENATAL: a modalidade Documentação do portal retornou lista vazia e os diretórios Doc examinados também estavam vazios. **Isso significa não localizado nesses caminhos; não prova inexistência de documentação em outros canais.**
- DATASUS/TABWIN é um pacote de aplicativo, não uma tabela clínica. O portal oferece documentação de uso do tabulador.
- O ZIP Docs_TAB_SINAN.zip excedeu o limite de 30 MiB desta conferência e não foi baixado. Os dois PDFs específicos do agravo/notificação foram obtidos diretamente do Portal SINAN.

## Fontes verificadas

- IBGE: [Pop_Residente_TCU_ate_2023.pdf](ftp://ftp.datasus.gov.br/dissemin/publicos/IBGE/DOC/Pop_Residente_TCU_ate_2023.pdf) · SHA-256 `ae71f4736dcebed703ac4b50b7b1b496d4dded1c3f726e57005ec5f216b6d817`.
- Base Territorial: [bases_territoriais.pdf](ftp://ftp.datasus.gov.br/territorio/doc/bases_territoriais.pdf) · SHA-256 `98a2c740720bf6fb5be6db01d8c80452de9d8735058cca675714ea34cf5f2e34`.
- CIHA: [Layout_Arquivos_CIHA.pdf](ftp://ftp.datasus.gov.br/dissemin/publicos/CIHA/201101_/Doc/Layout_Arquivos_CIHA.pdf) · SHA-256 `c326559e8d8d75afc3c115fa33f29efc1d74621064d53bb4cde129e4f88b9f1a`.
- CNES: [IT_CNES_1706.pdf](ftp://ftp.datasus.gov.br/dissemin/publicos/CNES/200508_/doc/IT_CNES_1706.pdf) · SHA-256 `71af7438a8cd77ed3fd7af03f7594b94aecf7eaa71082e28fa85c23c5524a1bb`.
- ESUSNOTIFICA: [Dicionario_de_Dados_Doenca_de_Chagas_Cronica.pdf](ftp://ftp.datasus.gov.br/dissemin/publicos/ESUSNOTIFICA/DOCS/Dicionario_de_Dados_Doenca_de_Chagas_Cronica.pdf) · SHA-256 `5b081513ff3d2b85679a0f5436393a14eec27258b6cd0eeda04ca166324be9e6`.
- PCE: [DIC_DADOS_SISPCE_PCE-DG.pdf](ftp://ftp.datasus.gov.br/dissemin/publicos/PCE/DOCS/DIC_DADOS_SISPCE_PCE-DG.pdf) · SHA-256 `9f83353e4e10e35c23aff26c888851985545086b3263930f0029c46b931dcf45`.
- PO: [Dicionario_Painel_Oncologia.pdf](ftp://ftp.datasus.gov.br/dissemin/publicos/PAINEL_ONCOLOGIA/DOC/Dicionario_Painel_Oncologia.pdf) · SHA-256 `5503556badd2c7b03ed669fc26622ca8e29c2e6342ac0bbab69e49718ecc309e`.
- RESP: [DIC_DADOS_RESP.pdf](ftp://ftp.datasus.gov.br/dissemin/publicos/RESP/DOCS/DIC_DADOS_RESP.pdf) · SHA-256 `c6e3fda1713d9932b6b3cca4a4838882ef66de30b356b47a7653cab1d4966ee5`.
- SIASUS: [Informe_Tecnico_SIASUS_2019_07.pdf](ftp://ftp.datasus.gov.br/dissemin/publicos/SIASUS/200801_/Doc/Informe_Tecnico_SIASUS_2019_07.pdf) · SHA-256 `70fe69dbd4cf0827452e3c265d8d83ebeabe145f63a7e054e57c7848d070c8dc`.
- SIHSUS: [IT_SIHSUS_1603.pdf](ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Doc/IT_SIHSUS_1603.pdf) · SHA-256 `1e89d5f2cc41420385d7e30ba5541a387912ab3a0efb167d39def74502076220`.
- SIM: [Estrutura_do_SIM_2025.pdf](ftp://ftp.datasus.gov.br/dissemin/publicos/SIM/CID10/DOCS/Estrutura_do_SIM_2025.pdf) · SHA-256 `b4195ac8e0f825a794cb487df93db41601a2f430a708172f494f1251b55eeeb1`.
- SINASC: [Estrutura_SINASC_para_CD.pdf](ftp://ftp.datasus.gov.br/dissemin/publicos/SINASC/NOV/DOCS/Estrutura_SINASC_para_CD.pdf) · SHA-256 `24e0d4388ea1d5fbe58a328136f1cb464e461985d3ed737210e0ecda5000cb08`.
- SINAN: [DIC_DADOS_Chagas_v5.pdf](https://portalsinan.saude.gov.br/images/documentos/Agravos/Chagas/DIC_DADOS_Chagas_v5.pdf) · SHA-256 `16c598f86fbfedd8040ebb34ad03c3351ff25c9bf1558354fe86ccb8b4bf8bd1`.
- SINAN: [DIC_DADOS_Notificacao_Individual_v5.pdf](https://portalsinan.saude.gov.br/images/documentos/Agravos/NINDIV/DIC_DADOS_Notificacao_Individual_v5.pdf) · SHA-256 `b3e0561c7a2d0a83d717286e07d01ca75b0d4499a38d3b3ba2b602a4fc983004`.

## Arquivos da auditoria

- [Cobertura por categoria](auditoria_cobertura.csv)
- [Situação de cada coluna, rótulos e códigos locais](auditoria_colunas.csv)
- [Consultas ao portal, fontes, hashes e limitações](auditoria_fontes.json)

Próxima etapa para um dicionário validado: associar cada coluna ao trecho/página e edição aplicável; conferir códigos observados versus domínio; registrar tabelas externas necessárias; marcar campos sem definição como pendentes, sem deduzir seu significado apenas pelo nome.