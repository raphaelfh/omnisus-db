# SIM · óbitos (`sim_obitos`)

## Em uma frase

Declarações de Óbito do Sistema de Informações sobre Mortalidade (SIM), com estrutura
documentada pela Coordenação-Geral de Informações e Análise Epidemiológicas da
Secretaria de Vigilância em Saúde do Ministério da Saúde e arquivos publicados pelo
DATASUS, um por UF e ano.

## O que um registro representa

- O dicionário da biblioteca descreve a base como declarações de óbito e declara
  `numerodo` (número da DO) como chave primária
  (`src/omnisus_db/data/dicionarios/sim_obitos.yaml`, `title` e `primaryKey`).
- `tipobito` separa óbito fetal (1) de não fetal (2) e é campo obrigatório
  (Estrutura do SIM 2025, p. 1).
- O documento define óbito fetal como a morte antes da expulsão ou extração completa
  do corpo da mãe, independentemente da duração da gravidez
  (Estrutura do SIM 2025, p. 1).
- `causabas` é a causa básica da DO, com 4 caracteres (Estrutura do SIM 2025, p. 5).
- O dicionário liga `causabas` à tabela CID-10 (`aux_cid10`) com o padrão letra + dois
  dígitos, com ponto e dígito opcionais
  (`src/omnisus_db/data/dicionarios/sim_obitos.yaml`), e o
  diretório final é `/dissemin/publicos/SIM/CID10/DORES` ([catálogo](../datasets.md)).
- As linhas A a D e a Parte II guardam os CIDs informados em cada linha da DO
  (Estrutura do SIM 2025, p. 4–5).
- A importação grava as colunas do arquivo com nomes em minúsculas e acrescenta
  `ano`, `uf` e `_source_release` a cada linha
  (`src/omnisus_db/sources/datasus_ftp/staging.py`, `dbc_bytes_to_parquet`).

## Datas e geografia

- `dtobito` é a data em que ocorreu o óbito, no formato ddmmaaaa, e é campo
  obrigatório (Estrutura do SIM 2025, p. 1).
- Em óbito fetal, a data de nascimento (`dtnasc`) e a data do óbito devem ser iguais
  (Estrutura do SIM 2025, p. 1).
- `dtatestado` é a data em que o atestado foi assinado (Estrutura do SIM 2025, p. 5).
- `dtcadastro` é a data do cadastro do óbito, e `dtrecebim` a data do recebimento
  (Estrutura do SIM 2025, p. 6).
- `difdata` é a diferença entre a data do óbito e a data do recebimento original da DO
  (Estrutura do SIM 2025, p. 7).
- As colunas `ano` e `uf` vêm do nome do arquivo (`DOSP2024.dbc` → SP, 2024), não de
  `dtobito` (`tests/unit/sources/datasus_ftp/test_filenames_golden.py`;
  `src/omnisus_db/sources/datasus_ftp/staging.py`).
- Numa importação real de Roraima, nenhum registro de 2022 ou 2023 tinha ano de
  `dtobito` diferente do ano do arquivo
  (`reports/evidence/2026-09-10/marimo-real/verification.json`, `quality`;
  `reports/2026-09-10-notebook-dados-reais.md`, "Validações concluídas").
- `codmunres` é o município de residência, com 7 caracteres; em óbito fetal, vale o
  município de residência da mãe (Estrutura do SIM 2025, p. 3).
- `codmunocor` é o município onde ocorreu o óbito, com 8 caracteres
  (Estrutura do SIM 2025, p. 3).
- `lococor` diz o local de ocorrência: 1 = hospital, 2 = outros estabelecimentos de
  saúde, 3 = domicílio, 4 = via pública, 5 = outros, 6 = aldeia indígena,
  9 = ignorado (Estrutura do SIM 2025, p. 3).
- A importação não ajusta o comprimento dos códigos de município: `lpad_6` está
  definido em `src/omnisus_db/transforms/codes.py`, mas o caminho de importação
  (`staging.py`) não o chama.

## Cobertura e modalidade

Arquivos anuais por UF, de 1996 em diante, no diretório final
`/dissemin/publicos/SIM/CID10/DORES` e no preliminar
`/dissemin/publicos/SIM/PRELIM/DORES`; veja o
[catálogo de datasets](../datasets.md).

Um ano pode estar em só um dos dois diretórios. Para saber qual:

```python
import omnisus_db as odb

publicados = odb.available_releases("sim_obitos", ufs=["RR"], refresh=True)
```

## Armadilhas

- `idade` não está em anos: são 3 caracteres, o primeiro com a unidade e os dois
  seguintes com a quantidade (Estrutura do SIM 2025, p. 2).
- O documento lista as unidades 1 = minuto, 2 = hora, 3 = mês, 4 = ano e
  5 = idade maior que 100 anos, e 9 = ignorado (Estrutura do SIM 2025, p. 2).
- A unidade 3 é mês: o documento dá para ela a faixa "de 1 a menos de 12 meses
  completos", com quantidade de 01 a 11 (Estrutura do SIM 2025, p. 2). Em SIM Roraima
  2022, os 123 registros com unidade 3 tinham quantidade de 01 a 11
  (`reports/2026-09-13-guia-pesquisador-validacao.md`, §4.3).
- Em óbito fetal, `idade` não deve ser preenchida (Estrutura do SIM 2025, p. 2).
- `sexo` usa M ou 1 = masculino, F ou 2 = feminino, e I, 0 ou 9 = ignorado
  (Estrutura do SIM 2025, p. 2).
- O dicionário declara `sexo` como inteiro, embora o documento liste letras; a
  divergência está aberta em `docs/dicionario/exemplos/sim_obitos.sexo.json`
  (questão `legacy-logical-type`).
- `causabas_o` guarda a causa básica informada antes da resseleção
  (Estrutura do SIM 2025, p. 6). Em outro campo, `altcausa` indica se houve correção
  ou alteração da causa do óbito após investigação (Estrutura do SIM 2025, p. 8).
- `tp_altera` traz códigos como "CausaBas em branco", "CausaBas com ausência do 4
  caractere" e "CausaBas inválida para o Sexo Feminino" (Estrutura do SIM 2025, p. 9).
- `codmunres` (residência) e `codmunocor` (ocorrência) respondem a perguntas
  diferentes e têm tamanhos declarados diferentes, 7 e 8 caracteres
  (Estrutura do SIM 2025, p. 3).
- A escolaridade do falecido aparece em mais de um campo: `esc` em anos de estudo
  (Estrutura do SIM 2025, p. 5), `esc2010` pelo nível da última série concluída
  (p. 2) e `escfalagr1` para o formulário a partir de 2010 (p. 7).
- `gestacao` é a faixa de semanas de gestação do formulário antigo
  (Estrutura do SIM 2025, p. 9); `semagestac` traz as semanas com dois algarismos
  (p. 4).
- `peso` é o peso ao nascer em gramas (Estrutura do SIM 2025, p. 4).
- O documento é a edição atualizada em 07/2025 (Estrutura do SIM 2025, p. 1).
- O documento não descreve `numerodo` nem `contador`, que o dicionário da biblioteca
  declara (Estrutura do SIM 2025, p. 1–9;
  `src/omnisus_db/data/dicionarios/sim_obitos.yaml`).
- Os códigos ficam no lake como publicados: o dicionário decodifica rótulos, datas e
  idade na exibição, não na importação (`src/omnisus_db/transforms/dictionaries.py`,
  docstring do módulo; `src/omnisus_db/sources/datasus_ftp/staging.py`, que não
  decodifica).

### Em aberto

- Se os arquivos `DORES` trazem óbitos fetais: o documento define os dois valores de
  `tipobito` (p. 1), mas na importação real de Roraima 2022–2023 nenhum dos 6 557
  registros era fetal (`reports/evidence/2026-09-10/marimo-real/verification.json`,
  `filter_2022_non_fetal` e `empty_fetal_selection`). Não conte óbitos fetais com esta
  base sem conferir `tipobito` nos seus dados.
- A unidade dos dias em `idade`: o documento dá a faixa "de 24 horas e 29 dias", com
  quantidade de 01 a 29, mas nenhum código de unidade para ela (p. 2). O decodificador
  de exibição da biblioteca lê a unidade 3 como dias
  (`src/omnisus_db/transforms/dictionaries.py`, `_IDADE_SIM_UNITS`), o que diverge do
  documento; a correção está registrada fora deste guia
  (`reports/2026-09-13-guia-pesquisador-validacao.md`, §4.3). Confira a distribuição do
  primeiro dígito antes de converter.
- Se a edição de 07/2025 vale para arquivos de anos anteriores: o exemplo auditado do
  campo `sexo` deixa aberta a confirmação de uma referência aplicável a 2023
  (`docs/dicionario/exemplos/sim_obitos.sexo.json`, questão `edition-applicability`).
- Se um arquivo `DOUFAAAA` reúne óbitos de residentes na UF ou óbitos ocorridos na UF:
  o documento não explica o diretório `DORES`. Compare o prefixo de `codmunres` e de
  `codmunocor` com a UF do arquivo; a consulta `residencia_e_ocorrencia` do notebook faz
  isso.
- O comprimento do código de município nos dados: o documento declara 7 e 8
  caracteres (p. 3), e o dicionário liga esses campos a `aux_municipios` com a
  indicação `lpad_6`. Confira nos seus dados antes de juntar com a população do IBGE.

## Como usar

```python
import omnisus_db as odb

alvo = "ducklake:./data/lake/pesquisa/dados.ducklake"
escopos = odb.available("sim_obitos", years=[2022], ufs=["RR"], refresh=True)
relatorio = odb.import_dataset(
    "sim_obitos", scopes=escopos, target=alvo, policy="skip_same", run_id="sim-rr-2022"
)
with odb.LakeReader(alvo) as leitor:
    print(leitor.connect().sql("SELECT ano, count(*) AS obitos FROM lake.sim_obitos GROUP BY ano").pl())
```

Passo a passo com análise e proveniência:
[notebooks/bases/sim_obitos.py](https://github.com/raphaelfh/omnisus-db/blob/main/notebooks/bases/sim_obitos.py)
[![Open in molab](https://molab.marimo.io/molab-shield.svg)](https://molab.marimo.io/github/raphaelfh/omnisus-db/blob/main/notebooks/bases/sim_obitos.py).

## Fontes

- Estrutura do SIM (`Estrutura_do_SIM_2025.pdf`), CGIAE/DASNT/SVS/MS, arquivo
  atualizado em 07/2025:
  <ftp://ftp.datasus.gov.br/dissemin/publicos/SIM/CID10/DOCS/Estrutura_do_SIM_2025.pdf>
  — consultado em 2026-09-10; SHA-256
  `b4195ac8e0f825a794cb487df93db41601a2f430a708172f494f1251b55eeeb1`, conferido de novo
  em 2026-09-13. Registro: `docs/dicionario/fontes/registro.json`.
- Catálogo gerado do registro da biblioteca: [Datasets](../datasets.md).
- Exemplo auditado do campo `sexo`, com as questões abertas citadas acima:
  [sim_obitos.sexo.json](../dicionario/exemplos/sim_obitos.sexo.json).

## Detalhes técnicos

### Linha de comando

```bash
omnisus-db inventory sim_obitos --refresh
omnisus-db import sim_obitos --plan inventory --years 2020-2024 --ufs RR
```

As importações acrescentam linhas a `lake.sim_obitos`. Ao terminar, a importação
devolve um `ImportReport`; o estado de uma transação interrompida aparece em
`ImportAbortedError`. Veja
[resultados e transações](../guides/inventory.md#transactions-and-interrupted-imports).

### Dicionário

As definições de campo, os metadados de chave estrangeira e as regras de decodificação
ficam em `src/omnisus_db/data/dicionarios/sim_obitos.yaml`. O parser aplica o
dicionário e preserva os campos não listados; por isso as colunas físicas da tabela
podem ser mais numerosas que as do dicionário. A validação do dicionário, sozinha, não
certifica todos os registros recebidos.

### Dados preliminares

O DATASUS também publica `sim_obitos` em `/dissemin/publicos/SIM/PRELIM/DORES`, ao
lado do diretório final. Um ano pode estar disponível apenas em um dos dois;
`available_releases()` (em [Cobertura e modalidade](#cobertura-e-modalidade)) mostra
qual.

Cada linha carrega `_source_release` (`final` ou `prelim`), então um ano preliminar
convive na mesma tabela com anos finais sem se confundir com eles. Quando o DATASUS
republica um ano preliminar como final:

```python
with odb.LakeReader(odb.DEFAULT_TARGET) as leitor:
    movidos = odb.outdated("sim_obitos", lake=leitor)
odb.import_dataset("sim_obitos", scopes=movidos, target=odb.DEFAULT_TARGET,
                   policy="replace", run_id="sim-final-2026")
```
