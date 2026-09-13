# SINAN · hanseníase (`sinan_hanseniase`)

## Em uma frase

Notificações de hanseníase do Sistema de Informação de Agravos de Notificação (SINAN),
com dados de diagnóstico e de acompanhamento do tratamento, que o DATASUS publica em um
arquivo nacional por ano, ora no diretório final, ora no preliminar.

## O que um registro representa

- Uma linha é uma notificação do SINAN: os campos de 1 a 30 vêm da ficha de notificação
  individual, exceto a data de diagnóstico, e os demais do dicionário do agravo
  (Dicionário Hanseníase v5, p. 1).
- `tp_not` é o tipo de notificação: 1 = negativa, 2 = individual, 3 = surto,
  4 = agregado (Dicionário Notificação Individual v5, p. 1).
- `id_agravo` é o código CID-10 do agravo notificado
  (Dicionário Notificação Individual v5, p. 1); a biblioteca espera `A309`
  (`src/omnisus_db/data/dicionarios/sinan_hanseniase.yaml`, `x-identity`).
- `modoentr` é o modo de entrada do paciente no sistema: 1 = caso novo,
  2 = transferência do mesmo município, 3 = transferência de outro município da mesma
  UF, 4 = transferência de outro estado, 5 = transferência de outro país, 6 = recidiva,
  7 = outros reingressos, 9 = ignorado (Dicionário Hanseníase v5, p. 2).
- `classopera` é a classificação operacional no diagnóstico, 1 = paucibacilar,
  2 = multibacilar, para eleição do esquema terapêutico (Dicionário Hanseníase v5, p. 2).
- A tela de acompanhamento traz a situação atual do paciente — UF, município e unidade
  de atendimento, classificação operacional, esquema, doses supervisionadas e tipo de
  saída (Dicionário Hanseníase v5, p. 3–8).
- `tpalta_n` é o tipo de saída: 1 = cura, 2 a 5 = transferências, 6 = óbito,
  7 = abandono, 8 = erro diagnóstico, 9 = transferência não especificada
  (Dicionário Hanseníase v5, p. 7).
- `in_vincula` recebe 1 depois da vinculação de notificações de hanseníase ou
  tuberculose (Dicionário Hanseníase v5, p. 8).
- O arquivo observado tem 63 campos e não tem `classi_fin`, `criterio` nem `evolucao`
  (`src/omnisus_db/data/dicionarios/sinan_hanseniase.yaml`, `x-evidence` e
  `schema.fields`).
- O dicionário da biblioteca é um inventário físico de `HANSBR26.dbc`, sem auditoria
  semântica dos campos nem mapeamento de categorias
  (`src/omnisus_db/data/dicionarios/sinan_hanseniase.yaml`,
  `x-evidence.semantic_status`).
- A importação grava as colunas do arquivo com nomes em minúsculas e acrescenta
  `_source_ano` e `_source_release`; como o arquivo é nacional, não acrescenta `ano`,
  `uf` nem `mes` (`src/omnisus_db/sources/datasus_ftp/_runner.py`, `ingest_raw`;
  `src/omnisus_db/sources/datasus_ftp/staging.py`, `dbc_bytes_to_parquet`).

## Datas e geografia

- `dt_notific` é a data de preenchimento da ficha, e `nu_ano` o ano da notificação,
  preenchido pelo sistema a partir dessa data (Dicionário Notificação Individual v5,
  p. 2).
- O arquivo traz `dt_diag` e `sem_diag`, e não `dt_sin_pri`
  (`src/omnisus_db/data/dicionarios/sinan_hanseniase.yaml`, `schema.fields`); a ficha
  individual usa o mesmo campo 7 para primeiros sintomas no agravo agudo e diagnóstico
  no agravo crônico (Dicionário Notificação Individual v5, p. 3).
- `dtinictrat` é a data do início do tratamento, igual ou posterior à data do diagnóstico
  (Dicionário Hanseníase v5, p. 3).
- `dtultcomp` é a data do último comparecimento do paciente, igual ou posterior ao início
  do tratamento (Dicionário Hanseníase v5, p. 6).
- `dtalta_n` é a data da alta, obrigatória quando o tipo de saída está preenchido,
  não posterior à data do sistema e não anterior ao início do tratamento
  (Dicionário Hanseníase v5, p. 8).
- `dt_noti_at` é a data de notificação pela unidade atualmente responsável pelo
  tratamento (Dicionário Hanseníase v5, p. 4).
- `_source_ano` é o ano do arquivo (`HANSBR23.dbc` → 2023), não uma data dos registros
  (`src/omnisus_db/sources/datasus_ftp/_runner.py`, `ingest_raw`).
- A biblioteca rejeita o arquivo inteiro quando o valor mais frequente de `nu_ano` não é
  o ano do arquivo, e mantém no lake os registros isolados de outro ano
  (`src/omnisus_db/sources/datasus_ftp/identity.py`, docstring do módulo e
  `validate_identity`).
- Em `HANSBR23` (30.114 registros) e `HANSBR25` (31.268), nenhum registro tinha `nu_ano`
  diferente do ano do arquivo ([relatório de 2026-09-12](https://github.com/raphaelfh/omnisus-db/blob/main/reports/2026-09-12-sinan-e-dispensacao.md),
  §1.3).
- `sg_uf_not` e `id_municip` são a UF e o município da unidade que notificou
  (Dicionário Notificação Individual v5, p. 2); `sg_uf` e `id_mn_resi` são a UF e o
  município de residência na notificação (p. 6).
- `ufatual` e `id_muni_at` são a UF e o município da unidade responsável pelo tratamento
  atual (Dicionário Hanseníase v5, p. 3–4).
- `ufresat` e `muniresat` são a UF e o município de residência atual, preenchidos da
  residência na notificação e atualizáveis no acompanhamento
  (Dicionário Hanseníase v5, p. 5).

## Cobertura e modalidade

Um arquivo nacional por ano, de 2001 em diante, no diretório final
`/dissemin/publicos/SINAN/DADOS/FINAIS` ou no preliminar
`/dissemin/publicos/SINAN/DADOS/PRELIM`; veja o [catálogo de datasets](../datasets.md).
Em 2026-09-11, 2001–2023 estavam em `FINAIS` e 2024–2026 em `PRELIM`, e nenhum ano
estava nos dois (relatório de 2026-09-12, §1.1 e §1.2). A importação não aceita filtro
de UF nem de mês.

Para saber em qual diretório cada ano está hoje:

```python
import omnisus_db as odb

publicados = odb.available_releases("sinan_hanseniase", refresh=True)
```

## Armadilhas

- Uma notificação não é um caso novo: `modoentr` separa caso novo (1) de transferências
  (2 a 5), recidiva (6) e outros reingressos (7) (Dicionário Hanseníase v5, p. 2). Filtre
  `modoentr` antes de contar casos novos.
- O modo de detecção (`mododetect`) só é habilitado para caso novo, `modoentr` = 1
  (Dicionário Hanseníase v5, p. 2).
- Quando o paciente muda de unidade de tratamento e é notificado de novo, os campos de
  atendimento atual são atualizados pela rotina de vinculação entre as duas notificações
  (Dicionário Hanseníase v5, p. 3–4); `in_vincula` = 1 marca a notificação vinculada
  (p. 8).
- Duplicidades marcadas com 2 em `nduplic_n` não devem ser computadas na incidência
  (Dicionário Notificação Individual v5, p. 8–9).
- `tpalta_n` não é só alta: a partir da versão 2.0, situação administrativa e tipo de
  alta foram unificados no tipo de saída (Dicionário Hanseníase v5, p. 7).
- A categoria 9 de `tpalta_n` não está disponível para digitação e só aparece em casos
  migrados do Sinan Windows ou notificados até a versão 1.3
  (Dicionário Hanseníase v5, p. 8).
- O Anexo I do dicionário da notificação dá para hanseníase a classificação final
  descartado "se o campo tp_administiva = 5 erro diagnostico" (Dicionário Notificação
  Individual v5, p. 20), enquanto o tipo de saída usa 8 = erro diagnóstico
  (Dicionário Hanseníase v5, p. 7), e o anexo começa com a nota "Falta concluir revisão"
  (Dicionário Notificação Individual v5, p. 17).
- A coluna é `classopera`, não `classoper`: é o nome DBF do documento
  (Dicionário Hanseníase v5, p. 2) e o do dicionário da biblioteca
  (`src/omnisus_db/data/dicionarios/sinan_hanseniase.yaml`).
- O documento pede renomear `BACILOSCOP` para `BACILOSCO` (Dicionário Hanseníase v5,
  p. 2), e o arquivo observado ainda traz `baciloscop`
  (`src/omnisus_db/data/dicionarios/sinan_hanseniase.yaml`).
- `nu_lesoes` era limitado a 20 lesões até a versão 1.3 (Dicionário Hanseníase v5, p. 2).
- `dose_receb` é o número de doses supervisionadas recebidas, não o total de doses
  (Dicionário Hanseníase v5, p. 7).
- O documento descreve número do prontuário, número de notificação atual e CEP
  (Dicionário Hanseníase v5, p. 1, 4 e 5), que não estão no arquivo observado
  (`src/omnisus_db/data/dicionarios/sinan_hanseniase.yaml`).
- Os dois diretórios são reescritos, e a data de modificação no FTP prova reescrita, não
  mudança de conteúdo (relatório de 2026-09-12, §1.2, item 4).
- Os códigos ficam no lake como publicados: o dicionário da biblioteca não mapeia
  categorias (`src/omnisus_db/data/dicionarios/sinan_hanseniase.yaml`,
  `x-evidence.semantic_status`).

### Em aberto

- Como selecionar casos confirmados: o arquivo não tem `classi_fin`
  (`sinan_hanseniase.yaml`), e o Anexo I só a descreve para hanseníase com uma nota de
  revisão pendente (p. 17 e p. 20). Declare no estudo que usou `modoentr` e `tpalta_n`.
- Como identificar pessoas únicas: transferências geram nova notificação vinculada
  (p. 3–4), e o arquivo não tem o número de notificação atual
  (`sinan_hanseniase.yaml`). Não trate linhas como pessoas.
- Em que data os campos de acompanhamento foram lidos: o documento diz que são
  atualizados ao longo do tratamento (p. 3–8), mas não diz quando o DATASUS extrai o
  arquivo. Um ano preliminar pode mudar quando for republicado.
- Se o ano do arquivo segue a notificação ou o diagnóstico: nas duas amostras `nu_ano`
  coincide com o ano do arquivo (relatório de 2026-09-12, §1.3), o que não separa as
  duas hipóteses; na tuberculose, o ano do arquivo segue `DT_DIAG` (mesmo relatório,
  §1.3).

## Como usar

```python
import omnisus_db as odb

alvo = "ducklake:./data/lake/pesquisa/dados.ducklake"
print(odb.available_releases("sinan_hanseniase", refresh=True))  # ano -> final ou prelim
escopos = odb.available("sinan_hanseniase", years=[2023])
relatorio = odb.import_dataset(
    "sinan_hanseniase", scopes=escopos, target=alvo, policy="skip_same", run_id="hanseniase-2023"
)
with odb.LakeReader(alvo) as leitor:
    print(leitor.connect().sql("SELECT _source_ano, _source_release, count(*) FROM lake.sinan_hanseniase GROUP BY ALL").pl())
```

Passo a passo com Chagas e hanseníase, análise e proveniência:
[notebooks/bases/sinan.py](https://github.com/raphaelfh/omnisus-db/blob/main/notebooks/bases/sinan.py).

## Fontes

- Sistema de Informação de Agravos de Notificação, Dicionário de Dados – SINAN NET –
  Versão 5.0, agravo hanseníase (`DIC_DADOS_Hanseniase_v5.pdf`), Ministério da Saúde /
  SVS / GT-SINAN:
  <https://portalsinan.saude.gov.br/images/documentos/Agravos/Hanseniase/DIC_DADOS_Hanseniase_v5.pdf>
  — consultado em 2026-09-13; 103.221 bytes; SHA-256
  `81f8f7919b15c84ce75129a55d8a18de241c11281920eb7c4c7c19f4337f3e16`, calculado em
  2026-09-13, não arquivado em `docs/dicionario/fontes/registro.json`.
- Dicionário de Dados – SINAN NET – Versão 5.0, Notificação Individual
  (`DIC_DADOS_Notificacao_Individual_v5.pdf`), Ministério da Saúde / SVS / GT-SINAN,
  revisado em julho de 2010:
  <https://portalsinan.saude.gov.br/images/documentos/Agravos/NINDIV/DIC_DADOS_Notificacao_Individual_v5.pdf>
  — consultado em 2026-09-10; SHA-256
  `b3e0561c7a2d0a83d717286e07d01ca75b0d4499a38d3b3ba2b602a4fc983004`, conferido de novo
  em 2026-09-13. Registro: `docs/dicionario/fontes/registro.json`.
- Relatório "SINAN além de Chagas e fontes públicas de dispensação", revisado em
  2026-09-12, §1.1–1.3:
  <https://github.com/raphaelfh/omnisus-db/blob/main/reports/2026-09-12-sinan-e-dispensacao.md>.
- Catálogo gerado do registro da biblioteca: [Datasets](../datasets.md).

## Detalhes técnicos

### Linha de comando

```bash
omnisus-db inventory sinan_hanseniase
omnisus-db import sinan_hanseniase --years 2023 --plan inventory --policy skip_same
```

O recorte nacional é `ScopeKey(uf=None, ano=2023)`; filtros de UF ou mês na aquisição
são rejeitados. Filtre a geografia na consulta, por `sg_uf_not` ou pelos campos de
residência, conforme a pergunta.

### Final e preliminar

`available_releases` lê os dois diretórios e diz de qual deles cada ano veio;
`available()` devolve só os recortes, sem a modalidade. Cada arquivo é buscado no
diretório em que foi listado, e a linha registra a modalidade em `_source_release`
(`final` ou `prelim`), ao lado de `_source_ano`. Anos finais e preliminares convivem na
mesma tabela; a coluna diz qual é qual, e `publications()` repete a modalidade por
publicação. Comparar um ano preliminar com um ano final compara duas coisas diferentes;
use `_source_release` para separá-los. A biblioteca não converte uma modalidade na outra
em silêncio. Quando o DATASUS republica um ano preliminar como final:

```python
with odb.LakeReader(alvo) as leitor:
    movidos = odb.outdated("sinan_hanseniase", lake=leitor)
print(movidos)  # escopos cuja modalidade mudou no servidor
if movidos:
    odb.import_dataset("sinan_hanseniase", scopes=movidos, target=alvo,
                       policy="replace", run_id="hanseniase-final-2024")
```

`outdated()` compara a modalidade publicada no lake com a listada hoje no servidor e
devolve só os escopos que mudaram. A substituição é sempre explícita: `replace` valida
antes de substituir exatamente aquele ano nacional, e dados e manifesto são publicados
atomicamente. Nada é atualizado por conta própria.

### Contrato de integridade e publicação

- O arquivo inteiro passa pela verificação de tamanho e contagem DBF, pelo staging
  Arrow/Parquet e pela mesma transação dos importadores estaduais.
- A identidade da fonte é declarada no YAML (`x-identity`) e verificada pela moda: o
  `nu_ano` mais frequente deve ser o ano do arquivo e, se a coluna existir, o
  `id_agravo` mais frequente deve ser `A309`. Um erro rejeita o arquivo inteiro; não há
  descarte silencioso de linhas.
- `_source_ano` e `_source_release` são reservados à biblioteca e não sobrescrevem
  campos originais.
- `skip_same` verifica a fonte de novo. Se o hash, o parser ou o dicionário mudou, exige
  uma decisão explícita de substituição.
- O manifesto guarda SHA-256, versão, URL de origem, IDs de execução e de publicação e
  situação ativa.

### Dicionário

Os 63 campos de `src/omnisus_db/data/dicionarios/sinan_hanseniase.yaml` são um
inventário físico observado em `HANSBR26.dbc`, não uma auditoria semântica. Campos
adicionais são preservados; incompatibilidades de tipo seguem a política geral de
esquema.

### Notebook

```bash
uv run --locked --extra notebooks marimo edit notebooks/bases/sinan.py
```

Abrir ou exportar o notebook não usa rede nem grava nada. Interromper uma célula não
cancela a thread do importador; espere a conclusão antes de reabrir o mesmo destino.
