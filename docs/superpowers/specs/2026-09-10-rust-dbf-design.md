# Extensão Rust para DBF: arquitetura e contrato

Data: 2026-09-10. Estado: implementação local concluída e validada; Rust opcional.
A matriz externa de distribuição e a promoção do default continuam pendentes.
Evidências: [relatório de validação](../../../reports/rust-dbf-validation.md).

## 1. Objetivo e evidências

Acelerar DBF → Arrow sem alterar a API pública de ingestão, a interpretação dos
dados ou as garantias transacionais. Manter Python como caminho de referência e
como alternativa quando a extensão opcional não estiver instalada.

Base examinada: commit `dd4ccef`. O fluxo atual está em
`src/omnisus_db/sources/datasus_ftp/{parse,staging,_runner}.py`:

1. `datasus_dbc` descompacta todo o DBC em memória.
2. `dbfread2` produz dicionários Python por registro.
3. `staging.py` converte lotes em Arrow, reconcilia schemas por IPC e publica
   Parquet com `os.replace` somente após validar a contagem.
4. O runner publica o escopo via `Lake.publish_scope`.

O benchmark da ADR 0001 é histórico. O staging mudou desde aquela medição;
84,2% e a estimativa de 5–10× não são critérios de desempenho comprovados hoje.
O benchmark existente de parsing inclui Parquet e materialização em Polars;
é necessário separar DBF → Arrow, DBC → Parquet e publicação no lake.

As 11 fixtures DBC versionadas incluem SIM, SINASC, SIH, CNES e SIA. Uma inspeção
preliminar dos descritores encontrou sobretudo C/N. O SIA ABO possui uma área de
cabeçalho peculiar: uma varredura ingênua por offsets detecta bytes extras como
descritores. Caracterizar o término real dos descritores antes de aceitar esse
layout; não transformar essa varredura preliminar em especificação de DBF.

## 2. Alternativas e decisão adotada

| Alternativa | Benefício | Custo | Decisão |
|---|---|---|---|
| Extensão opcional no mesmo repositório | Revisão conjunta, fixtures compartilhadas, wheel principal continua Python | Segundo artefato e matriz de build | Recomendada |
| Migrar o pacote principal para Maturin | Um artefato | Acopla todas as instalações à extensão e à matriz nativa | Rejeitada neste escopo |
| Repositório separado para a extensão | Ciclo independente | PRs e testes de integração entre repositórios | Adiar até existir outro consumidor |

O pacote será `omnisus-db-dbf`, importado como `omnisus_db_dbf`, em
`native/omnisus-db-dbf/`. Um crate com módulos internos é suficiente; não criar
workspaces Cargo/uv, framework de plugins ou crates por camada.

**Não adotar diretamente `dbase::FieldValue` como representação intermediária.**
Na documentação consultada de dbase 0.8.0, `Numeric` e `Currency` usam `f64`,
`Float` usa `f32` e texto preenchido apenas com padding pode virar `None`.
O parser atual preserva inteiros e retorna `""` para texto vazio. Isso impede uma
substituição transparente usando somente essa API tipada.

A primeira versão terá um leitor Rust de escopo restrito, sobre bytes e offsets
validados, com conversões C/N compatíveis com `dbfread2`. Outros tipos/layouts
seguirão pelo Python em modo automático. Não escrever um leitor universal de
dBase, nem adicionar uma dependência dbase que depois precise ser contornada.
Se a tarefa de caracterização mostrar que um layout predominante exige suporte
adicional, registrar o caso e ampliar explicitamente o contrato antes de ativá-lo.

## 3. Restrições globais

- Python `>=3.12`; manter o backend Hatchling do pacote principal.
- Preservar mínimos existentes: DuckDB `>=1.5.5,<2.0`, Polars `>=1.44.2,<2.0`,
  PyArrow `>=25.0.1`, datasus-dbc `>=0.1.3,<1.0`, dbfread2 `>=0.1.0,<2.0`.
- Extensão opcional; a instalação base não adiciona nova exigência de Cargo.
- API pública de ingestão e contratos de `Lake` permanecem compatíveis.
- `BATCH_ROWS = 100_000` continua definido somente no Python e é passado ao Rust.
- Uma implementação compartilhada de normalização, schema, IPC e Parquet.
- Nenhuma conversão de inteiro para float para acomodar valores incompatíveis.
- Nenhum fallback após começar a consumir registros do backend escolhido.
- Nenhum novo paralelismo de escrita, download ou parsing de escopos.
- A memória ainda inclui DBC e DBF completos; não prometer memória constante.
- PRs usam fixtures locais; DATASUS ao vivo fica fora dos checks obrigatórios.
- Publicação de pacotes é uma etapa posterior, sujeita à infraestrutura existente.

## 4. Organização e responsabilidades

```text
native/omnisus-db-dbf/
  Cargo.toml, Cargo.lock, rust-toolchain.toml
  pyproject.toml                  # Maturin; versão derivada de Cargo.toml
  README.md, LICENSE
  python/omnisus_db_dbf/
    __init__.py, _native.pyi, py.typed
  src/
    lib.rs                       # registro do módulo PyO3
    error.rs                     # erros estruturados
    header.rs                    # geometria, descritores e preflight
    decode.rs                    # C/N e encodings
    reader.rs                    # cursor incremental e fechamento
    arrow.rs                     # builders por coluna/lote
    bindings.rs                  # ownership e conversão Arrow/Python
  tests/                         # testes Rust dos módulos públicos internos
  fuzz/                          # alvo cargo-fuzz e seeds sintéticos pequenos

src/omnisus_db/sources/datasus_ftp/
  parse.py                       # fachada compatível + _stream_records
  dbf_contract.py                # integridade e versão semântica
  dbf_batches.py                 # adaptador Python, seleção e adaptador Rust
  staging.py                     # fluxo único de Arrow até Parquet
  _runner.py                     # publicação; identidade via helper

tests/support/dbf.py              # um construtor de DBF para testes Python
tests/fixtures/dbf/               # corpus sintético compartilhado Python/Rust
tests/fixtures/dbc/               # fixtures existentes, sem duplicação
tests/unit/sources/datasus_ftp/
  test_dbf_contract.py
  test_dbf_backends.py
  test_dbf_parity.py
tests/integration/test_rust_dbf_pipeline.py
tests/perf/bench_dbf_parse.py      # acrescentar medição realmente isolada
scripts/benchmark_resources.py    # ampliar script existente
.github/workflows/native.yml      # checks e artefatos; sem publicação automática
```

Usar módulos na extensão, sem expor detalhes de DuckDB, YAML, partições ou FTP.
`dbf_contract.py` recebe as validações existentes e a correção do terminador;
`parse.py` reexporta os nomes usados hoje. O staging continua chamando as costuras
de compatibilidade de `parse` quando necessário para preservar testes e scripts.
Não criar ciclo entre `dbf_contract`, `dbf_batches` e `staging`.

Mover `_family` e `_table` para `dbf_batches.py`: pertencem ao adaptador de
registros Python, não ao writer. `_merge_schema` e normalização ficam no staging.
Manter `_stream_records` como referência Python, inclusive seu fechamento.

## 5. Interface pequena e DRY

Contrato interno proposto, não uma nova API pública:

```python
from collections.abc import Iterator
from contextlib import AbstractContextManager
from typing import Literal
import pyarrow as pa

Backend = Literal["python", "rust", "auto"]

def open_dbf_batches(
    dbf_bytes: bytes, *, encoding: str, batch_rows: int, backend: Backend
) -> AbstractContextManager[Iterator[pa.RecordBatch]]: ...

def publication_parser_version(dictionary_hash: str) -> str: ...
```

`open_dbf_batches` recebe bytes já preparados pela camada de integridade, abre o
backend antes de entregar seu iterador e sempre fecha os recursos ao sair.
Lotes têm 1 a `batch_rows` registros ativos, ordem original de linhas/colunas,
nomes originais e nenhuma partição injetada. Nenhum lote vazio intermediário.
Um arquivo sem registros ativos produz zero lotes; o staging mantém sua regra
atual de schema vazio baseado no dicionário.

Cada lote pode ter schema próprio: coluna inteiramente nula continua `pa.null()`.
O staging existente faz a reconciliação e rejeita famílias incompatíveis.
Por isso a interface inicial é um iterador de RecordBatch, **não** um único
Arrow C Stream com schema fixo e não uma lista contendo todos os lotes.

Interface da extensão:

```python
API_VERSION: int = 1

class UnsupportedDbfError(ValueError): ...
class InvalidDbfError(ValueError): ...

class DbfBatchReader:
    def __iter__(self) -> "DbfBatchReader": ...
    def __next__(self) -> pa.RecordBatch: ...
    def close(self) -> None: ...

def open_reader(
    data: bytes, *, encoding: str, batch_rows: int
) -> DbfBatchReader: ...
```

`open_reader` faz preflight síncrono de cabeçalho, versão DBF, tipos e encoding,
mas decodifica valores por lote. Usar `arrow-rs` e `arrow-pyarrow` para entregar
RecordBatch; não implementar manualmente ponteiros/callbacks de Arrow C Data.
Pinagem compatível de PyO3/Arrow/Maturin e versão mínima do Rust é resultado
obrigatório da primeira tarefa técnica, com `Cargo.lock` e toolchain registradas.
Não escolher números de versões por suposição.

Uma cópia inicial dos bytes para armazenamento Rust proprietário é aceitável na
primeira versão, com custo medido. Não manter referências emprestadas a buffers
Python ao liberar o GIL. Builders/decodificação rodam sem GIL quando o ownership
permitir; criação de objetos Python ocorre com o GIL. Lotes entregues continuam
válidos depois de fechar ou destruir o reader. `close()` é idempotente.

## 6. Semântica obrigatória

| Caso | Resultado exigido |
|---|---|
| Texto C | Remover apenas padding final `NUL`/espaço; preservar espaço inicial, string vazia, zeros à esquerda e bytes significativos |
| latin-1 | Mapeamento byte → code point, inclusive `0x81`; nunca substituir por Windows-1252 |
| cp1252 | Mesmo decoding estrito de Python; bytes indefinidos geram erro |
| Campo N | Reproduzir `strip().strip(b'*\\0')`; tentar inteiro antes de float; vírgula decimal aceita como no Python |
| Inteiro grande | `2**53+1` e `2**60+1` exatos em int64; fora do domínio aceito por Arrow deve falhar sem truncar |
| Decimal textual em N | Float64 quando essa é a semântica atual; não reinterpretar todos os N como float pelo cabeçalho |
| N vazio | Null; lote só com null mantém tipo null até reconciliação |
| Mistura int/float | Rejeição por famílias tanto dentro quanto entre lotes, como staging atual |
| F, D, L, I, Y, memo etc. | Fora da primeira versão; auto seleciona Python antes da primeira linha, rust explícito informa incompatibilidade |
| Registro deletado | Ignorado na saída, contabilizado no contrato de integridade |
| EOF prematuro/truncamento | `DbfIntegrityError`, sem publicar saída parcial |
| Cabeçalho inválido | Rejeição determinística; não usar número de registros declarado para alocar sem limites |
| Colisão de nomes após lowercase | Rejeição compartilhada no staging |
| CNES sem terminador esperado | Aplicar exatamente a correção compatível atual, uma vez antes da seleção |
| SIA ABO | Caracterização explícita dos descritores e terminador; suporte somente depois de paridade comprovada |
| Partições e schema | Mesmo lowercase, sobrescrita de ano/uf/mes, tipos uint16/uint8 e casts seguros do staging atual |

Números especiais, sinal, expoente, padding e encoding de nomes também entram na
caracterização. Erros de conteúdo nunca autorizam reiniciar pelo outro backend.
O parser Rust valida limites de offsets por segurança mesmo quando chamado
diretamente; isso não é duplicação indevida das regras de publicação em Python.

## 7. Seleção, falhas e identidade

Uma variável de ambiente, `OMNISUS_DBF_BACKEND=python|rust|auto`, controla a seleção
interna sem propagar argumentos por todos os importadores. Resolver uma vez por
escopo. Valor inválido falha explicitamente. Durante a primeira entrega, o valor
implícito é `python`; a promoção para `auto` ocorre apenas após os gates.

| Situação | auto | rust |
|---|---|---|
| Pacote ausente | Python | Erro claro de instalação |
| Formato/encoding explicitamente não suportado, detectado no preflight | Python, motivo registrado | UnsupportedDbfError |
| Módulo instalado com import quebrado/API incompatível | Erro claro | Erro claro |
| Arquivo inválido, erro de decoding, falha durante iteração | Propagar erro e limpar | Propagar erro e limpar |

Capturar `ModuleNotFoundError` somente se `exc.name == "omnisus_db_dbf"`;
dependência transitiva ausente não é ausência do pacote opcional. A decisão de
fallback ocorre no `__enter__`, antes do spool. Converter `InvalidDbfError` para
`DbfIntegrityError` no adaptador, preservando a causa. Erros de conversão mantêm
TypeError/ValueError/UnicodeDecodeError conforme a categoria. Logs registram
backend, versão do pacote e motivo do fallback, sem valores de registros.

O manifesto atual usa `dbc-staging-v1:<dictionary_hash>`. Essa identidade representa
a **semântica** do processamento. Centralizar sua construção em
`publication_parser_version`; preservar o valor enquanto Rust for comprovadamente
equivalente. Instalar Rust não deve invalidar `skip_same` por si só. Versão física
do backend fica em log. Mudança de interpretação exige nova versão semântica e
segue a política já existente de substituição explícita; sem migração automática.

## 8. Testes e critérios de aceitação

1. **Caracterização independente:** casos pequenos com valores esperados escritos
   à mão; comparação diferencial sozinha poderia reproduzir um erro dos dois lados.
2. **Unitários Rust:** limites do cabeçalho, C/N, encodings e builders; propriedades
   com proptest para offsets, batches e entradas malformadas, sem panic.
3. **Contrato Python:** backend ausente/quebrado, seleção, erros tardios, fechamento,
   tamanho de lote, schema e lifetime dos RecordBatches após GC do reader.
4. **Paridade:** todas as 11 fixtures versionadas, batch sizes 1, 7, 1024, 100000
   nos casos sintéticos; fixtures reais em 7 e 100000. Comparar valores, nulls,
   ordem, tipos e contagem com `polars.testing.assert_frame_equal` usando checks
   exatos. Rust estrito para layouts suportados; fallback esperado explicitamente
   para os restantes. Registrar essa cobertura, sem vender fallback como aceleração.
5. **Staging:** falha após primeiro lote, cancelamento, disco/escrita com erro,
   output anterior preservado e limpeza de temporários, inclusive Windows.
6. **Lake real local:** fonte e rede substituídas por fixtures, DuckDB/DuckLake real;
   rollback, contagem, skip_same cruzando backends e replace preservando outra UF.
7. **Distribuição:** instalar wheels em ambiente limpo e ler fixture fora da raiz
   do projeto. Jobs nativos não aceitam skip se a extensão/fixture estiver ausente.
8. **Fuzzing:** cabeçalhos e registros truncados/mutados; qualquer crash vira seed
   mínimo e regressão. Fuzzing complementa, não prova ausência de bugs.

Manter cobertura Python global mínima de 85%, já exigida pelo CI. Cobertura não
substitui os testes de perda de dados, lifetime, atomicidade e precisão numérica.

## 9. Desempenho, rollout e distribuição

Gates para promoção a `auto`, incluindo a matriz de distribuição abaixo e
desempenho mensurado na mesma máquina com Rust release:

- Paridade e todas as garantias acima aprovadas.
- Mediana DBF → Arrow pelo menos 2× mais rápida em dois corpora amplificados,
  um predominantemente C e outro C/N; não extrapolar para DATASUS nacional.
- DBC → Parquet sem regressão superior a 10% no agregado dos corpora medidos;
  pico RSS sem regressão superior a 20% em relação ao Python atual.
- Um aquecimento e sete medições em processos novos por backend/corpus, ordem
  alternada. Registrar CPU, SO, Python, crates, hash do corpus, lotes, mediana,
  dispersão, RSS, disco temporário e equivalência. Os limiares são critérios de aceitação; os resultados locais estão no
  relatório de validação. Gates de tempo rodam em máquina controlada.
- Publicação no lake medida à parte, com lake novo por rodada; rede medida
  separadamente quando pertinente, nunca embutida no alegado ganho do parser.

Manter Rust opt-in enquanto qualquer gate estiver pendente, inclusive a execução
da matriz de distribuição. Os gates locais de desempenho passaram; isso não
substitui os checks de outras plataformas. Não enfraquecer paridade ou coerções
para produzir um benchmark favorável.

Build inicial: CPython normal 3.12 e 3.13, Linux x86_64 manylinux, Windows x86_64,
macOS arm64 e x86_64. Fixar runner/target compatível, testar cada arquitetura que
for anunciada. Preferir wheels por versão de Python inicialmente; só usar abi3
depois de confirmar que todas as dependências da ponte Arrow o suportam.
Free-threaded, PyPy, musl e outras arquiteturas não são metas iniciais.

O wheel principal permanece `py3-none-any`. A extensão tem versão independente
em Cargo.toml, extraída pelo Maturin, e `API_VERSION` próprio. Construir e testar
sdist incluindo fontes/stubs/licença; `target/`, wheels e ambientes não entram
no Git. `Cargo.lock` e `rust-toolchain.toml` entram.

A lacuna preexistente de wheels de `datasus-dbc` em Python 3.13 é independente:
gate da extensão isolada em todas as plataformas deve bloquear; instalação da
stack inteira sem compilar continua obrigatória em 3.12, e a limitação 3.13 fica
visível. Não atribuir a essa extensão uma correção do descompactador.

Antes de publicação, instalar a extensão diretamente do wheel local. Somente após
disponibilidade validada no índice, acrescentar extra `rust` ao pacote principal
e atualizar `uv.lock`. Nunca introduzir uma dependência opcional irresolvível no
lockfile para uma versão ainda não publicada. Tags da extensão usam `dbf-v*` e
não acionam o release `v*` do pacote principal. Release nativo deve consumir os
mesmos artefatos testados, com publisher próprio, quando sua publicação for pedida.

## 10. Fontes e execução

- Contexto histórico: `docs/decisions/0001-rust-dbf.md`.
- Plano executável: `../plans/2026-09-10-rust-dbf.md`.
- [dbase FieldValue](https://docs.rs/dbase/0.8.0/dbase/enum.FieldValue.html): tipos
  intermediários e semântica de texto vazio que motivam evitar a API tipada.
- [arrow-pyarrow](https://docs.rs/arrow-pyarrow/latest/arrow_pyarrow/): ponte oficial
  entre Arrow Rust e PyArrow.
- [Arrow PyCapsule](https://arrow.apache.org/docs/format/CDataInterface/PyCapsuleInterface.html):
  protocolo de interoperabilidade e ownership.
- [Maturin layout](https://www.maturin.rs/project_layout.html): pacote misto isolado.

Não há promessa de que testes garantam ausência absoluta de defeitos. A aprovação
depende de evidências reproduzíveis de equivalência, falhas seguras, distribuição
e ganho mensurado, com fallback operacional conhecido.
