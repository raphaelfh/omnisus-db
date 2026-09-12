# SINAN além de Chagas e fontes públicas de dispensação

Investigação, não implementação. Nenhum código de ingestão foi escrito.
Sondagens ao vivo entre **2026-09-11T23:11Z** e **2026-09-12T03:58Z**; cada seção
registra o horário UTC. Arquivos baixados foram lidos e apagados (só hashes ficam
aqui). O relatório de 2026-09-10 (`reports/2026-09-10-mapa-datasus/`) é citado
apenas como observação anterior.

## Resumo

- **SINAN no FTP:** `FINAIS` tem 741 arquivos de 45 prefixos e `PRELIM` tem 357
  arquivos de 56 prefixos. Todos os arquivos são nacionais anuais `<PREFIXO>BR<AA>.dbc`,
  sem arquivos por UF. Nenhum par (agravo, ano) aparece nos dois diretórios.
- **"Preliminar" não quer dizer "ano recente".** 13 agravos (HIV/aids, sífilis,
  hepatites, varicela, exantemáticas, rubéola congênita) têm a série inteira, desde
  2007, só em `PRELIM`. Dengue, chikungunya e zika de 2025 já estão em `FINAIS`.
  Os dois diretórios são reescritos: arquivos "finais" de 2007 têm data de
  modificação de agosto de 2026.
- **O contrato do Chagas não pode ser copiado como está.** Em arquivos reais:
  - `TUBEBR19` (final) e `TUBEBR25` têm 3.193 e 1.513 registros com `nu_ano` diferente
    do ano do arquivo. O ano do arquivo de TB segue `DT_DIAG`.
  - `ZIKABR25` (final) tem 12 registros de outros anos.
  - `id_agravo` aparece truncado em parte dos registros (`A16.`, `A50.`).
  - Metade de `AIDABR24` não tem `id_agravo`.

  A validação estrita do Chagas rejeitaria esses arquivos publicados.
- **Contrato recomendado:** produtos separados `sinan_<agravo>_final` e
  `sinan_<agravo>_prelim`, com o sufixo espelhando o diretório do DATASUS. Antes do
  segundo produto SINAN, duas mudanças no núcleo são obrigatórias:
  - a decodificação de nomes precisa conhecer o diretório, porque hoje dois produtos
    com o mesmo prefixo colidem;
  - a validação precisa sair do `if` por nome e virar uma tabela por agravo.
- **Prioridade sugerida:** arboviroses (dengue, chikungunya, zika), tuberculose,
  sífilis (três arquivos), hanseníase, violência.
- **Dispensação:** **nenhuma fonte pública de eventos de dispensação foi
  confirmada**, nem em nível de registro nem agregada.
  - O que existe publicamente: estoque (BNAFAR/Hórus), entregas a DSEI (SasiSUS,
    2022) e indicadores de pessoas atendidas (Farmácia Popular/MGDI).
  - A dispensação da BNAFAR e da RNDS é de envio ou de acesso autenticado.

## Parte 1 — SINAN

### 1.1 Inventário observado

Listagem ao vivo com `omnisus_db.browse(path, depth=1, refresh=True)` em
2026-09-11T23:13Z:

- `/dissemin/publicos/SINAN` contém `AUXILIAR`, `DADOS` e `DOCS`.
- `/dissemin/publicos/SINAN/DADOS` contém `FINAIS` (modificado em 2026-08-01 18:11)
  e `PRELIM` (modificado em 2026-08-27 16:00).
- `FINAIS`: 741 arquivos, 45 prefixos, nenhum subdiretório.
- `PRELIM`: 357 arquivos, 56 prefixos, nenhum subdiretório. A contagem é igual à
  registrada em 2026-09-10.
- Todos os 1.098 nomes casam com `^[A-Z]{3,4}BR\d{2}\.dbc$`; não há arquivo por UF.
- A união tem 58 prefixos: 43 aparecem nos dois diretórios, 13 só em `PRELIM`,
  2 só em `FINAIS`.

| Prefixo | Agravo | FINAIS | PRELIM |
|---|---|---|---|
| ACBI | Acidente trabalho mat. biológico | 2006–2022 | 2023–2026 |
| ACGR | Acidente de trabalho | 2006–2022 | 2023–2026 |
| AIDA | AIDS adulto | — | 2007–2024 |
| AIDC | AIDS criança | — | 2007–2024 |
| ANIM | Animais peçonhentos | 2007–2022 | 2023–2026 |
| ANTR | Atendimento antirrábico | 2006–2024 | 2025–2026 |
| BOTU | Botulismo | 2007–2024 | 2025–2026 |
| CANC | Câncer relacionado ao trabalho | 2007–2022 | 2023–2026 |
| CHAG | Chagas aguda | 2000–2022 | 2023–2025 |
| CHIK | Chikungunya | 2014–2025 | 2026 |
| COLE | Cólera | 2007–2022 | 2024–2025 (2023 ausente nos dois) |
| COQU | Coqueluche | 2007–2022 | 2023–2026 |
| DCRJ | Creutzfeldt-Jakob | 2007–2022 | 2023–2024 |
| DENG | Dengue | 2000–2025 | 2026 |
| DERM | Dermatoses ocupacionais | 2006–2022 | 2023–2026 |
| DIFT | Difteria | 2007–2023 | 2024–2026 |
| ESPO | Esporotricose (epizootia) | 2013–2022 | — |
| ESQU | Esquistossomose | 2007–2022 | 2023–2026 |
| EXAN | Exantemáticas | — | 2007–2026 |
| FMAC | Febre maculosa | 2007–2021 | 2022–2026 |
| FTIF | Febre tifoide | 2007–2024 | 2025–2026 |
| HANS | Hanseníase | 2001–2023 | 2024–2026 |
| HANT | Hantavirose | 1999–2024 | 2025–2026 |
| HEPA | Hepatites virais | — | 2007–2023 |
| HIVA | HIV adulto | — | 2007–2024 |
| HIVC | HIV criança | — | 2007–2024 |
| HIVE | HIV criança exposta | — | 2015–2024 |
| HIVG | HIV gestante | — | 2007–2024 |
| IEXO | Intoxicação exógena | 2006–2022 | 2023–2026 |
| LEIV | Leishmaniose visceral | 2000–2024 | 2025 |
| LEPT | Leptospirose | 2000–2024 | 2025–2026 |
| LER | (só `LERBR19.dbc`) | 2019 | — |
| LERD | LER/Dort | 2006–2022 | 2023–2026 |
| LTAN | Leishmaniose tegumentar | 2000–2024 | 2025 |
| MALA | Malária | 2004–2022 | 2023–2024 |
| MENI | Meningite | 2007–2022 | 2023–2026 |
| MENT | Transtornos mentais trabalho | 2006–2022 | 2023–2026 |
| NTRA | Notificação de tracoma | 2010–2024 | 2025–2026 |
| PAIR | Perda auditiva por ruído | 2006–2022 | 2023–2026 |
| PEST | Peste | 2007–2024 | 2025 |
| PFAN | Paralisia flácida aguda | 2007–2022 | 2023–2026 |
| PNEU | Pneumoconioses | 2006–2022 | 2023–2026 |
| RAIV | Raiva | 2007–2024 | 2025–2026 |
| ROTA | Rotavírus | 2009–2024 | 2025–2026 |
| SDTA | Surto DTA | 2007–2018 (2014 ausente) | 2019–2024 |
| SIFA | Sífilis adquirida | — | 2010–2025 |
| SIFC | Sífilis congênita | — | 2007–2025 |
| SIFG | Sífilis em gestante | — | 2007–2025 |
| SRC | Rubéola congênita | — | 2007–2026 |
| TETA | Tétano acidental | 2007–2023 | 2024–2026 |
| TETN | Tétano neonatal | 2014–2021 | 2022–2026 |
| TOXC | Toxoplasmose congênita | 2019–2023 | 2024–2026 |
| TOXG | Toxoplasmose gestacional | 2019–2023 | 2024–2026 |
| TRAC | Inquérito de tracoma | 2009–2024 | 2025–2026 |
| TUBE | Tuberculose | 2001–2019 | 2020–2025 |
| VARC | Varicela | — | 2007–2025 |
| VIOL | Violências | 2009–2024 | 2025 |
| ZIKA | Zika | 2015–2025 | 2026 |

Notas sobre o inventário:

- **Descrições dos agravos.** Vêm da lista de subtipos do portal de transferência
  gravada em 2026-09-10 (`reports/2026-09-10-mapa-datasus/README.md`).
- **Prefixo `INFL`.** O portal lista `INFL` (influenza pandêmica), mas ele não aparece
  em nenhum dos dois diretórios hoje.
- **`LERBR19.dbc`.** Tem 403.871 bytes, o mesmo tamanho de `LERDBR19.dbc`: parece uma
  cópia com prefixo truncado. A identidade não foi verificada por hash.

Documentação no mesmo FTP:

- `SINAN/DOCS` tem `Docs_TAB_SINAN.zip` (65.650.628 B, não baixado), um POP de acesso
  a microdados e notas técnicas de DCJ, intoxicação exógena, rotavírus, surtos de DTA
  e toxoplasmose.
- `SINAN/AUXILIAR` tem `TAB_SINANNET.zip` (44.000.914 B, não baixado).
- O POP de acesso a microdados (`POP_I_Acesso_a_Microdados_5.pdf`, SHA-256 `e2a9f530…`)
  descreve só a navegação do portal. Não trata de preliminar × final.

Um diretório vizinho usa o mesmo desenho. `/dissemin/publicos/ESUSNOTIFICA`
(listado em 2026-09-12T03:21Z) contém:

- `DADOS/FINAIS/DCCRBR23.dbc` e `DADOS/PRELIM/DCCRBR24.dbc`, `DCCRBR25.dbc`
  (Chagas crônica);
- `DOCS/Dicionario_de_Dados_Doenca_de_Chagas_Cronica.pdf`.

### 1.2 Como `FINAIS` e `PRELIM` se relacionam

Fatos observados:

1. **Não há sobreposição.** Nenhum (agravo, ano) está nos dois diretórios.
   Nos 43 agravos com arquivos nos dois, `PRELIM` começa no ano seguinte ao último de
   `FINAIS`. As exceções são COLE (2023 ausente nos dois) e SDTA (2014 ausente em
   `FINAIS`).
2. **A fronteira varia por agravo.**
   - Arboviroses: 2025 já é final em setembro de 2026.
   - Agravos do trabalho, IEXO e MENI: o último ano final é 2022.
   - TUBE: o último ano final é 2019.
   - HIV/aids, sífilis e hepatites não têm nenhum arquivo final.
3. **A regra oficial de dois anos não se aplica a todos os agravos.** A nota
   "TABNET Doença de Chagas aguda – SINAN NET" (GT-Chagas/CGZV, datada de 24/09/2025,
   <http://tabnet.datasus.gov.br/cgi/sinannet/chagas/NT_doenca_de_Chagas_aguda.pdf>,
   baixada em 2026-09-12T03:54Z) diz que a base preliminar é exportada no segundo
   semestre do ano seguinte e considerada fechada após dois anos. A mesma nota lista
   UFs de 2024 cuja classificação final foi ajustada pela área técnica nacional.
   A regra descreve Chagas; o inventário do item 2 mostra que outras áreas técnicas
   não seguem o mesmo calendário.
4. **Os dois diretórios são reescritos.** Datas de modificação do FTP:
   - `DENGBR07`–`DENGBR25` (FINAIS): entre 2026-02-27 e 2026-09-10; `DENGBR21` às
     15:45 de 2026-09-10.
   - `VIOLBR09`–`VIOLBR24` (FINAIS): todos em 2026-07-24.
   - `LEPTBR07`–`LEPTBR24` (FINAIS): 2026-07-15.
   - `SIFGBR07`–`SIFGBR25` (PRELIM): 2026-06-30.
   - `HIV*`/`AID*` (PRELIM): sem alteração desde 2025-02-24/25.

   A data prova reescrita, não mudança de conteúdo. Não existe histórico de hashes,
   exceto `CHAGBR23`, gravado em 2026-09-10.
5. **Como a transição acontece.** Não foi observada nenhuma transição
   PRELIM → FINAIS em curso. Pela ausência de sobreposição, o provável é que o arquivo
   saia de `PRELIM` quando entra em `FINAIS`; isso é inferência, não observação.
6. **Mesmo layout nos dois diretórios.** Os campos são idênticos entre o arquivo final e
   o preliminar do mesmo agravo em 5 pares amostrados (seção 1.3).

Ferramentas de referência:

- **microdatasus** (`R/fetch_datasus.R`, baixado em 2026-09-12T03:54Z) funde os dois
  diretórios: dados definitivos ou atuais têm precedência sobre preliminares. Cobre
  8 sistemas SINAN (dengue, chikungunya, zika, malária, Chagas, LV, LTA, leptospirose).
- **PySUS** tem esquemas YAML para cerca de 30 agravos em
  `pysus/api/metadata/schemas/sinan/` (árvore do repositório, 2026-09-12). Não foi
  verificado como o PySUS trata as duas modalidades.

### 1.3 Amostragem de arquivos reais

Condições da amostra:

- 17 arquivos (57.774.064 B), baixados um de cada vez por FTP em 2026-09-12T03:54Z.
- Descompressão com `datasus_dbc.decompress_bytes` (a mesma do staging), leitura
  direta do cabeçalho e dos registros DBF, arquivo apagado em seguida.
- Uma segunda leitura, às 03:56Z, de `TUBEBR25`, `ZIKABR25`, `SIFCBR25` e `AIDABR24`
  (7.582.350 B) investigou as anomalias.

| Diretório | Arquivo | Registros | Campos | `id_agravo` observado | `nu_ano` ≠ ano do arquivo |
|---|---|---:|---:|---|---:|
| FINAIS | DENGBR17 | 239.395 | 121 | A90 (100%) | 0 |
| PRELIM | DENGBR26 | 453.398 | 121 | A90 (100%) | 0 |
| FINAIS | CHIKBR14 | 4.622 | 122 | A920 (100%) | 0 |
| FINAIS | ZIKABR25 | 25.764 | 38 | A928 (100%) | **12** (6 de 2024, 6 de 2026) |
| PRELIM | ZIKABR26 | 11.648 | 38 | A928 (100%) | 0 |
| FINAIS | TUBEBR19 | 95.849 | 94 | A169 (100%) | **3.193** (2020: 2.793; 2021: 161; …) |
| PRELIM | TUBEBR25 | 112.482 | 94 | A169 110.193; **`A16.` 2.289** | **1.513** (2026) |
| PRELIM | SIFABR25 | 133.759 | 27 | A539 (100%) | 0 |
| PRELIM | SIFGBR25 | 48.929 | 32 | O981 (100%) | 0 |
| PRELIM | SIFCBR25 | 12.630 | 64 | A509 12.279; **`A50.` 351** | 0 |
| FINAIS | VIOLBR09 | 39.976 | 159 | Y09 (100%) | 0 |
| FINAIS | HANSBR23 | 30.114 | 63 | A309 (100%) | 0 |
| PRELIM | HANSBR25 | 31.268 | 63 | A309 (100%) | 0 |
| FINAIS | LEIVBR24 | 8.537 | 76 | B550 (100%) | 0 |
| PRELIM | LEIVBR25 | 6.026 | 76 | B550 (100%) | 0 |
| PRELIM | HIVABR24 | 25.736 | 76 | B24 (100%) | 0 |
| PRELIM | AIDABR24 | 21.096 | 77 | B24 10.473; **vazio 10.623** | 0 |

Não houve registros marcados como apagados. `sg_uf_not` só aparece vazio nos 10.623
registros sem agravo de `AIDABR24`.

Os campos são idênticos entre final e preliminar em DENG 17/26, ZIKA 25/26,
TUBE 19/25, HANS 23/25 e LEIV 24/25. Entre dengue e chikungunya a diferença é um campo:
CHIK tem `NU_LOTE_I` a mais.

Diagnóstico das anomalias:

- **TUBE.** Em `TUBEBR25`, o ano de `DT_DIAG` é 2025 nos 112.482 registros (100%).
  Os 1.513 registros com `nu_ano` de 2026 têm `DT_NOTIFIC` em 2026 e `DT_DIAG` em 2025.
  O ano do arquivo de tuberculose segue o **diagnóstico**, não a notificação.
  Os 2.289 `A16.` têm `TP_NOT=2`.
- **ZIKA final.** Os 12 registros fora do ano também têm `DT_NOTIFIC` fora de 2025.
  O ano de `DT_SIN_PRI` também não explica todos (6 de 2024, 4 de 2025, 2 de 2026).
  Nenhum campo de data sozinho define esse arquivo.
- **AIDABR24.** Os 10.623 registros sem agravo:
  - têm `TP_NOT`, `SG_UF_NOT`, `ID_MUNICIP`, `SG_UF` e `EVOLUCAO` vazios;
  - têm `DT_NOTIFIC='********'` (10.622 deles);
  - têm `ORIGEM` 3 (9.042) ou 2 (1.580);
  - os registros normais têm `ORIGEM=1` em todos os 10.473.

  Não são notificações SINAN comuns. O significado de `ORIGEM` **não foi confirmado**:
  a extração de texto do dicionário `DIC_DADOS_Aids_adulto_v5.pdf` não encontrou
  `ORIGEM`, `TP_NOT` nem `ID_AGRAVO`.

Hashes SHA-256 dos arquivos amostrados:

```text
FINAIS DENGBR17.dbc ec341731d6bbae5a6c2bcc4c349b6e3ee4f66b34469663fa45c15214912afce0
PRELIM DENGBR26.dbc b3d593c88e86502b803239a5cfca6e8727149216a3fef8e22b647cbbcea4169e
FINAIS CHIKBR14.dbc 7ebc16fd79b6c1225c3b5929990f3975a18e6d0e662ff4eaca91cd548784cb42
FINAIS ZIKABR25.dbc 22089d257e02153fcd107730446275aa420448d460c0c65ce634ad3dda81cee6
PRELIM ZIKABR26.dbc 23619351afcced0a1164290e98e8f46b3abaa6260c2766d6201ddfc17c26a8dc
FINAIS TUBEBR19.dbc 7a00e29a5a309b794e21f1a650d3b04b9d3cb05fcc6ef8c9feefab3a961c9144
PRELIM TUBEBR25.dbc b5aa111e8dcd1d17ba89d021eb7d27514a33d586b2385c47dd21ca7414728236
PRELIM SIFABR25.dbc 340d9f9995c20ed0465960164efe390f32871d8de54f9277a29afa774f1d0c4c
PRELIM SIFGBR25.dbc de5b7d13b78b6a6ea2464711b93b4686bb8671ba1b01bb2a801a7b6317622b19
PRELIM SIFCBR25.dbc fad5ce28d891b4bf147f1f8a0e8f850e9f4808599766d347586378555a6652eb
FINAIS VIOLBR09.dbc 1eb7e17fcaba745f2cb90c1a4266d9148cd2a0b840fb54bcb5c9dbabc113c735
FINAIS HANSBR23.dbc 0d380ef55d243412799f640036d86e3fef1f4f5095f5e07de0ef70a153a26b29
PRELIM HANSBR25.dbc 2704ddb57f360b1c0f9a419d06722df245546143df9c58d9f62248bd646f4d9a
FINAIS LEIVBR24.dbc ad94f0be615fb5bc1946bbab99838a7341cbcecb88ae9cff0ccff6cbe8409672
PRELIM LEIVBR25.dbc 43d8a1d91ff00d6522732b295f861b20e09473e80f36826d35686536125f652f
PRELIM HIVABR24.dbc 3c944e6328818d5a78f0a5bfa5a5d3d84d996dd75120ade6bbcced86ab9e70b6
PRELIM AIDABR24.dbc 693beb166ce6fd1480ed4cc02786cea8fb95d5727500056bb18ef85789da309b
```

### 1.4 Contrato final × preliminar

Restrições verificadas no código atual:

- **`Dataset.ftp_dir` é uma `str`** (`datasets.py`): cada linha do registro aponta
  para um único diretório.
- **Decodificação global por prefixo.** `parse_filename` percorre o registro e, para
  produtos nacionais, devolve a primeira linha cujo prefixo casa
  (`filenames.py:35-39`). Depois, `available()` descarta os nomes de outro produto
  (`inventory.py:300-306`). Consequência: se `sinan_deng_final` e `sinan_deng_prelim`
  tiverem prefixo `DENG`, **a segunda linha nunca encontra arquivos**. O teste Tier 3
  (`test_registry_probe.py`) usa a mesma decodificação. Hoje isso já afetaria um
  `sinan_chagas_final` ao lado do `sinan_chagas_prelim` existente.
- **Um `Dataset` avulso não é descoberto.** O prefixo não está no registro, então
  `decode` devolve `None` e `available()` volta vazio.
- **A validação de identidade é escolhida por nome** (`_runner.py:144`).
- **Memória do staging.** O staging mantém o DBF descomprimido inteiro em memória
  (docstring de `dbc_bytes_to_parquet`). `DENGBR24.dbc` tem 287.558.389 B
  comprimidos, abaixo do limite de 512 MiB de `DEFAULT_MAX_PAYLOAD_BYTES`, mas o
  tamanho descomprimido não foi medido.

Opções:

| Opção | Descrição | Veredito |
|---|---|---|
| **A** | Duas linhas por agravo: `sinan_<agravo>_final` (FINAIS) e `sinan_<agravo>_prelim` (PRELIM). O sufixo é o rótulo do diretório do DATASUS. As duas linhas podem apontar para o mesmo YAML via `dictionary=`. | **Recomendada** |
| B | Uma linha por agravo cobrindo os dois diretórios. A modalidade é gravada por publicação (o `source_uri` já contém o diretório), com uma coluna de modalidade. | Alternativa viável |
| C | Um produto `sinan` com parâmetros de agravo e modalidade. | Rejeitada |
| D | Nenhuma linha nova; o pesquisador usa `browse` e um `Dataset` avulso. | Rejeitada como suficiente |
| E | Fusão com precedência final > preliminar (modelo microdatasus). | Rejeitada |

Por que **A**:

- Preserva as invariantes que já existem: um diretório por linha, uma tabela por
  linha, o contrato escrito em `docs/sources/sinan_chagas_prelim.md` e a regra de
  nunca converter preliminar em final em silêncio.
- Não exige lógica de precedência.
- Custo único: decodificação consciente do produto (decodificar o nome dentro do
  `Dataset` pedido, em vez de pelo mapa global de prefixos) e uma tabela de validação.

Custos de A que ficam na documentação:

- Quando um ano passa de `PRELIM` para `FINAIS`, o pesquisador importa em `_final` e
  remove o escopo antigo de `_prelim` com `delete_scope`. Nada disso é automático.
- Para HIV/aids, sífilis e hepatites, a tabela `_prelim` guarda a série inteira
  desde 2007. O nome segue o rótulo do DATASUS, não a idade do dado.
- Consultas que vão de 2000 a 2026 unem duas tabelas.

Por que as outras opções ficam de fora:

- **B** quer uma consulta contínua em uma tabela só. Em troca, `ftp_dir` passa a ser
  plural (reabre uma decisão de desenho) e é preciso definir o que acontece quando o
  mesmo ano existe nos dois diretórios; isso não foi observado hoje, mas precisaria de
  regra. A tabela passaria a misturar modalidades entre anos: correto só se a coluna de
  modalidade for sempre consultada.
- **C** quebra "uma linha = uma tabela = um YAML" (docstring de `datasets.py`) e o
  princípio "fatos, não formulários". Os layouts diferem demais: de 27 a 159 campos
  na amostra.
- **D** não tem descoberta (`available()` vazio), nem validação de identidade, nem
  dicionário empacotado. O pesquisador fica com planejamento às cegas.
- **E** converteria preliminar em final sem decisão explícita, o que contradiz o
  contrato atual.

Validação de staging generalizada (decisão do usuário):

- **Identidade.** Rejeitar o arquivo inteiro quando aparecer um `id_agravo` fora de
  um conjunto aceito por agravo, montado a partir de arquivos reais:
  - TUBE: {`A169`, `A16.`}
  - SIFC: {`A509`, `A50.`}
  - demais agravos da amostra: um único código.
- **Ano.** A regra estrita do Chagas (todo registro com `nu_ano` = ano) **rejeitaria**
  `ZIKABR25` e `TUBEBR19`, arquivos finais publicados. Duas saídas:
  - (i) estrita, com a coluna certa por agravo (`DT_DIAG` para TUBE): `ZIKABR25`
    continua rejeitado;
  - (ii) sem checagem de ano: `_source_ano` identifica o arquivo e `nu_ano` fica
    preservado como original.

  Recomendo (ii) para novos agravos. É menos mecanismo, e o DATASUS publicou esses
  registros naquele arquivo. O Chagas pode ficar como está: seus três arquivos passam.

### 1.5 Custo por agravo e lista priorizada

Custo por agravo, seguindo o precedente do Chagas:

- uma ou duas linhas de registro;
- um YAML de inventário físico lido de um arquivo real, compartilhado pelas duas linhas
  e citando o PDF oficial em `x-evidence`;
- um DBF sintético de teste, como em `test_sinan_chagas.py`;
- o probe Tier 3, que é automático para cada linha nova (mais um e2e opcional);
- uma entrada na tabela de validação (códigos aceitos).

Uso em pesquisa: contagem no PubMed (E-utilities, 2026-09-11T23:18Z) com
`("SINAN" OR "Sistema de Informação de Agravos de Notificação" OR "Notifiable Diseases
Information System" OR "Information System for Notifiable Diseases")[tiab] AND
<termo>[tiab]`. Total SINAN: 782.

| Agravo | Artigos |
|---|---:|
| tuberculose | 147 |
| HIV/aids | 119 |
| hanseníase | 75 |
| violência | 68 |
| dengue | 65 |
| leishmaniose | 59 |
| sífilis | 52 |
| animais peçonhentos | 44 |
| intoxicação | 28 |
| hepatite | 24 |
| chikungunya | 19 |
| meningite | 18 |
| zika, malária | 14 cada |
| Chagas | 12 |

É um indicador grosseiro: termos em inglês, só título e resumo. Não mede uso real.

Dicionários oficiais (links nas páginas do portalsinan, verificados por HEAD em
2026-09-11T23:20Z, base
`https://portalsinan.saude.gov.br/images/documentos/Agravos/`):

- **Dengue e chikungunya:** `Dengue/DIC_DADOS_ONLINE.pdf` (339.721 B, modificado em
  2016-06-03), linkado nas duas páginas.
- **Zika:** a página `/zika` linka só o dicionário genérico de notificação individual,
  `NINDIV/DIC_DADOS_NET_Not_Individual_rev.pdf`. Isso é coerente com os 38 campos.
- **Tuberculose:** `Tuberculose/DICI_DADOS_NET_Tuberculose_23_07_2020.pdf`.
- **Sífilis em gestante:** `Sifilis-Ges/DIC_DADOS_Gestante_Sifilis_v5.pdf`.
- **Sífilis congênita:** `Sifilis-Con/DIC_DADOS_Sifilis_Congenita_v5.pdf`.
- **Sífilis adquirida:** o slug `/sifilis-adquirida` respondeu 404; **dicionário não
  encontrado**.
- **Hanseníase:** `Hanseniase/DIC_DADOS_Hanseniase_v5.pdf`.
- **Violências:** link para `via/DIC_DADOS_NET_Violencias_v5.pdf` (sem HEAD).
- **Leishmaniose visceral:** `Leishmaniose Visceral/DIC_DADOS_LV_v5.pdf`.
- **Intoxicação exógena:** `iexog/DIC_DADOS_Intoxicacao_Exogena_v6_26.02.2026.pdf`.
- **Animais peçonhentos:** `AAP/DIC_DADOS_Animais_Pedonhentos_v5.pdf`.
- **Hepatites:** `Hepatites Virais/DIC_DADOS_Hepatite_v5.pdf`.

A maioria dos v5 tem data de 2016. Os arquivos atuais trazem campos que não foram
cruzados com esses PDFs, então o YAML deve continuar como inventário físico, não
semântico.

Lista priorizada:

1. **Arboviroses: dengue, chikungunya, zika.**
   - Linhas: até 6, com 3 YAMLs. Dengue e chikungunya diferem em 1 campo.
   - Por quê: DENG e CHIK têm um código único e `nu_ano` limpo na amostra; o layout
     da dengue é igual entre final e preliminar. O microdatasus cobre os três, e a API
     DEMAS tem endpoints para os três.
   - Risco: medir memória com `DENGBR24` (287 MB comprimidos) antes de registrar;
     ZIKA final tem registros fora do ano (decisão da §1.4).
2. **Tuberculose.**
   - Linhas: 2 (F 2001–2019, P 2020–2025).
   - Por quê: maior uso no PubMed.
   - Exige código `A16.` aceito e ano por `DT_DIAG` (ou nenhuma checagem de ano).
3. **Sífilis: adquirida, gestante, congênita.**
   - Linhas: 3, só `_prelim`.
   - Por quê: arquivos pequenos e códigos limpos, exceto `A50.`.
   - Pendência: falta o dicionário da sífilis adquirida.
4. **Hanseníase.**
   - Linhas: 2 (F 2001–2023, P 2024–2026).
   - Por quê: amostra totalmente limpa e layout igual entre final e preliminar.
5. **Violência interpessoal/autoprovocada.**
   - Linhas: 2 (F 2009–2024, P 2025).
   - Tem 159 campos. `VIOLBR25` (39 MB) não foi amostrado, então o layout preliminar
     não está verificado.
   - Alternativa mais barata para o 5º lugar: leishmaniose visceral (amostra limpa,
     arquivos < 1 MB).

Adiados:

- **HIV/aids.** Tem alto uso em pesquisa, mas metade de `AIDABR24` não é notificação
  comum (`ORIGEM` ≠ 1) e os arquivos estão parados desde 2025-02. Precisa de contrato
  próprio.
- **Hepatites.** Só `PRELIM` até 2023, sem atualização desde 2025-03.

## Parte 2 — Fonte pública de eventos de dispensação

| Fonte (acesso) | O que foi observado | Unidade / granularidade | Dispensação? |
|---|---|---|---|
| `apidadosabertos.saude.gov.br` Swagger v1.8.32 (<https://apidadosabertos.saude.gov.br/static/swagger.json>, 2026-09-11T23:11Z e 2026-09-12T03:58Z; licença declarada MIT; nenhuma operação declara `security`) | 100 caminhos, todos `GET`. Só dois tratam de medicamento: `/daf/estoque-medicamentos-bnafar-horus` e `/saude-indigena/sesai-assistencia-farmaceutica`. Não há endpoint de dispensação. | — | Não |
| `/daf/estoque-medicamentos-bnafar-horus?codigo_uf=14&limit=1&offset=0` (HTTP 200, 702 B, 2026-09-11T23:13Z) | Um registro: `data_posicao_estoque` 2026-09-10, `codigo_catmat` BR0370120-1, `quantidade_estoque` 2059.0, lote, validade, programa MAL. | Item/lote em estoque por estabelecimento | Não (estoque) |
| `/saude-indigena/sesai-assistencia-farmaceutica` (HTTP 200; sem autenticação) | 2.310 linhas (busca binária com `limit=1`, 23 requisições). Campos: `dsei`, `material`, `unidade_de_medida`, `qtd_entregue`. Sem data, município ou paciente. 476 de 1.000 linhas com mojibake (`Ã�CIDO…`). O resumo do Swagger cita "dispensação", mas o dicionário oficial define `Qtd Entregue` como quantidade entregue. | Material por DSEI | Não (entrega ou distribuição) |
| Catálogo "Assistência Farmacêutica no SasiSUS – Farmácia" (`dadosabertos.saude.gov.br/dataset/assistencia_farmaceutica_sasisus_farmacia`, 2026-09-12T03:54Z) | Descrição: entregas de medicamentos aos DSEI (Hórus Indígena). Atualização semestral. Um CSV "2022" (16.773 B). Licença não declarada nos metadados. | DSEI × material | Não |
| `dadosabertos.saude.gov.br` busca (2026-09-12T03:53Z; o CKAN legado `opendatasus.saude.gov.br` redireciona com 302; `ckan-dadosabertos.saude.gov.br` não resolve em DNS público) | "dispensação": **0** pacotes. "farmácia": MGDI Farmácia Popular e SasiSUS. "medicamentos": esses dois, mais MGDI RNDS e BPS. "BNAFAR": só "BNAFAR - Posição de Estoque" (CC-BY, quinzenal, nota "Em manutenção", último recurso de 06-06-2026). | — | Não |
| MGDI Farmácia Popular (`dataset/mgdi-programa-farmacia-popular-do-brasil`; arquivos em `demas-dados-abertos.s3.amazonaws.com`) | 14 recursos CSV de indicadores de **pessoas atendidas**. `sntpbih.csv.zip` (430.567 B, SHA-256 `7ed90244…`): 22.283 linhas, `co_anomes` ∈ {202312, 202412, 202512, 202607}, granularidade municipal. `pfpbben.csv.zip` (1.106.823 B): 61.273 linhas, 11 competências de 201612 a 202607 (dezembros e o último mês). `license_id` vazio nos metadados. | Número de pessoas por município e competência | Não (indicador agregado de acesso) |
| MGDI RNDS (`dataset/mgdi-rede-nacional-de-dados-em-saude-rnds`) | 7 indicadores de contagem de registros na RNDS. O de prescrição (RPM), `sdigi013rc`, tem 27 linhas por UF, só 202606. Não há indicador de dispensação. | Registros por UF | Não |
| Portal BNAFAR <https://bnafar.saude.gov.br/> (2026-09-11) | Página de login ("Acesso Restrito"). | — | Sem leitura pública |
| gov.br BNAFAR "Rol de dados" (2026-09-12T03:53Z) | A página exige autenticação ("Conteúdo Restrito"). | — | Sem leitura pública |
| gov.br BNAFAR FAQ (atualizada em 16/10/2025, lida em 2026-09-12) | Consolida posição de estoque, saídas e dispensação. A Portaria GM/MS nº 5.713/2024 tornou o **envio** diário obrigatório. A dispensação chega pelo REDFM via RNDS. | Evento de dispensação enviado pelos entes | Existe, mas não é público |
| RNDS: perfil `BRRegistroDispensacaoMedicamento` (simplifier.net, rascunho v01.00, 2023-07-07) e guia <https://rnds-guia.saude.gov.br/docs/publico-alvo/gestor/portal/> (2026-09-12T03:53Z) | Modelo de documento de dispensação. O acesso é pedido no Portal de Serviços DATASUS em etapas (Responsável, Sistema, Operação, Finalização). Busca na web: credencial por certificado digital vinculada a CNES. | Documento individual | Integração credenciada, não leitura pública |
| dados.gov.br API `/dados/api/publico/conjuntos-dados` (2026-09-12T03:21Z) | HTTP 401, `www-authenticate: Bearer`, sem token. | — | Não verificado (exige chave) |
| SICLOM / Painel Logístico HIV e hepatites | Pela notícia do gov.br/aids via busca (fev./2025): painel semanal de consumo, saldo e cobertura por UF, município e UDM. O artigo da Agência Gov estava indisponível em 2026-09-12 por restrição eleitoral. Não foi confirmado nenhum arquivo ou API para download. | Agregado em painel | Agregado não ingerível confirmado: não |
| `/atencao-primaria/siaps-atendimento-individual` | Sem filtros, e com `competencia_siaps=202601&co_uf_ibge=14`, a resposta foi `[]`. A descrição do Swagger não lista campo de medicamento. | Atendimento | Não |
| SIA-AM / APAC (já no pacote) | Registro de APAC. | APAC | Não (ver `docs/sources/medicamentos.md`) |

**Conclusão da Parte 2: nenhuma fonte pública de eventos de dispensação foi
confirmada.**

- Os eventos existem na BNAFAR/RNDS por força normativa (Portaria GM/MS nº 5.713/2024),
  mas o acesso observado é de envio, credenciado ou autenticado.
- As fontes públicas mais próximas medem outra coisa:
  - estoque (BNAFAR/Hórus);
  - entrega a DSEI, só 2022, sem data nem município (SasiSUS);
  - pessoas atendidas por município, em competências esparsas (Farmácia Popular/MGDI).
- Apresentar qualquer uma delas como dispensação violaria a regra já escrita em
  `docs/sources/medicamentos.md`.
- O caminho realista para pesquisa com dispensação é uma extração fornecida pelo gestor
  ou via LAI. Um contrato para isso só pode ser desenhado quando houver um arquivo real.

## Limites desta investigação

- **Histórico do FTP.** Datas de modificação indicam reescrita, não mudança de
  conteúdo. Não há histórico de hashes além de `CHAGBR23`, de 2026-09-10.
- **Tamanho da amostra.** Um ou dois arquivos por agravo. Anomalias raras em outros
  anos podem existir.
- **Arquivos grandes não amostrados.** `DENGBR24` (287 MB), `VIOLBR24` e `VIOLBR25`,
  e os ZIPs de documentação (`Docs_TAB_SINAN.zip`, `TAB_SINANNET.zip`).
- **Contagens do PubMed.** São um indicador, não uma medida de uso.
- **Painéis e dados.gov.br.** Painéis (SICLOM) e dados.gov.br autenticado não foram
  explorados além do que está descrito.

## Reproduzir as sondagens principais

```python
import omnisus_db as odb
for p in ("/dissemin/publicos/SINAN/DADOS/FINAIS", "/dissemin/publicos/SINAN/DADOS/PRELIM"):
    print(p, len(odb.browse(p, depth=1, refresh=True)))
```

```bash
curl -sS "https://apidadosabertos.saude.gov.br/saude-indigena/sesai-assistencia-farmaceutica?limit=2&offset=0"
curl -sS -o /dev/null -w "%{http_code}\n" "https://dados.gov.br/dados/api/publico/conjuntos-dados?isPrivado=false&nomeConjuntoDados=farmacia&pagina=1"
curl -sS -I "https://demas-dados-abertos.s3.amazonaws.com/csv/sntpbih.csv.zip"
```
