# Transactional Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Corrigir A01, A04, A06 e A08, preservando dados e tornando os resultados de importação coerentes com commits e rollbacks.

**Architecture:** `Lake` controla a transação, o cache e os snapshots dos resultados pendentes. O runner controla outcomes por posição de entrada e interrompe a execução quando a confirmação não é determinável. CNES prepara os registros antes de agrupar tabela, upsert e visão em uma transação.

**Tech Stack:** Python 3.12/3.13, DuckDB 1.5.5, DuckLake observado `d8a1881e`, Polars 1.44.2, PyArrow 25.0.1, pytest 9.1.1, pytest-asyncio 1.4.0, Ruff 0.16.6 e mypy 2.3.1.

**Spec:** [transactional-ingestion-design.md](/Users/raphael/PycharmProjects/omnisus-db/docs/superpowers/specs/2026-09-09-transactional-ingestion-design.md).

## Global Constraints

- Python mínimo: `>=3.12`; verificar Python 3.12 e 3.13.
- Base validada: DuckDB `1.5.5`, Polars `1.44.2`, PyArrow `25.0.1`; preservar `uv.lock` e os mínimos atualizados do `pyproject.toml`.
- Extensão DuckLake observada nessa base: `d8a1881e`, repositório `core`; verificar capacidades na extensão efetivamente carregada.
- Um escritor por lake é precondição operacional desta entrega; o consumidor deve serializar handles, processos e SQL externo que alterem o mesmo catálogo.
- Uma conexão DuckDB e um consumidor de parsing/escrita por execução; downloads podem permanecer concorrentes.
- `Lake.ingest` continua append; nenhuma deduplicação, substituição de escopo ou migração de tabelas antigas.
- Estados de `ScopeOutcome` permanecem `ok`, `skipped`, `failed`; ordem e multiplicidade das entradas devem ser preservadas.
- `ImportResult.snapshot_id` permanece `int | None`; `None` significa que não há identificação confirmada disponível.
- Não adicionar dependências de execução nesta entrega.
- Não executar FTP/IBGE/CNES ao vivo na suíte de aprovação; usar fixtures para rede e DuckLake real em diretórios temporários.
- Nenhum COMMIT de resultado desconhecido pode ser repetido automaticamente.
- Não implementar coordenação distribuída, idempotência durável, fonte IBGE, promoções de tipos ou manutenção nesta entrega.

---

## Status da execução

Concluída em 2026-09-10, com código funcional em `30ce324` e revisão integral aprovada após correções. Evidências: `reports/2026-09-10-implementacao-ingestao-transacional.md`. Gate final: 429 testes por versão Python 3.12/3.13, 91,97% de cobertura e wheel limpo aprovado. As notas de estado de partida abaixo descrevem o momento anterior à execução.

## Estado de partida e limites

A atualização de dependências foi executada antes deste plano: 386 testes passaram em Python 3.12 e novamente em 3.13, com cobertura de 91,28%. O wheel instalou em Python 3.12 no macOS arm64 com `--only-binary=:all:`. Esses resultados não cobrem os reparos abaixo: **todas as tarefas funcionais deste plano ainda estão pendentes**.

Trabalhar no diretório raiz `/Users/raphael/PycharmProjects/omnisus-db` ou no checkout escolhido para execução. Os comandos abaixo usam caminhos relativos a essa raiz. Antes de começar, ler a spec e verificar `git status --short`; preservar `profile-timings.txt`, relatórios históricos e alterações de dependências existentes. Não executar `git add .`.

O contrato inicial de um escritor é operacional; não há um bloqueio entre processos a ser implementado neste plano. Também não se assume que uma função de snapshot isole conexões compartilhando catálogo. A confirmação deve ocorrer sem outro escritor intercalado.

## Mapa de arquivos e responsabilidades

| Arquivo | Responsabilidade nesta entrega |
|---|---|
| `src/omnisus_db/lake/_transactions.py` — novo | Tipos de recibo e erros de estado transacional |
| `src/omnisus_db/lake/operations.py` | Fronteira de transação, saúde do handle, cache, ingestão e snapshots |
| `src/omnisus_db/lake/__init__.py` | Exportar erros transacionais |
| `src/omnisus_db/sources/_base.py` | Exceção pública com relatório parcial e posições não resolvidas |
| `src/omnisus_db/sources/datasus_ftp/_runner.py` | Contabilidade por índice, falha de lote e encerramento de produtores |
| `src/omnisus_db/sources/cnes/importers/master.py` | Preparação de registros e publicação atômica |
| `src/omnisus_db/__init__.py` | Exportar `ImportAbortedError` e documentar contrato de importação |
| `src/omnisus_db/cli/main.py` | Comunicar execução interrompida e manter exit status correto |
| `tests/helpers/connection_faults.py` — novo | Injetar falhas ao redor de SQL real, sem substituir o mecanismo transacional |
| `tests/unit/lake/test_transactions.py` — novo | Cache, commit, rollback, recibos e uso direto de ingest |
| `tests/unit/sources/datasus_ftp/test_runner_failures.py` — novo | DBC inválido, lote misto, erro fatal, produtor e cancelamento |
| Testes CNES e CLI existentes | Refresh interrompido, duplicidade e apresentação de resultados |

## Task 1: Tornar a fronteira transacional recuperável e explícita

**Files:** Create `src/omnisus_db/lake/_transactions.py`, `tests/helpers/__init__.py`, `tests/helpers/connection_faults.py`, `tests/unit/lake/test_transactions.py`. Modify `src/omnisus_db/lake/operations.py` e `src/omnisus_db/lake/__init__.py`.

**Interfaces:** Consome `Lake.connect()` e `_columns`/`_ensured`. Produz `TransactionReceipt`, `TransactionStateError`, `CommitOutcomeUnknown`, `Lake.in_transaction`, `Lake.is_usable`, `Lake._read_snapshot()` e context manager `Lake.transaction() -> Iterator[TransactionReceipt]`.

- [x] **1. Criar um seam de falha em torno da conexão real.** Criar `tests/helpers/__init__.py` vazio e o helper abaixo. `before`/`after` falham uma única vez por prefixo; outros comandos vão para DuckDB real.

```python
class FaultyConnection:
    def __init__(self, connection, *, before=None, after=None):
        self.connection = connection
        self.before = dict(before or {})
        self.after = dict(after or {})

    def _fail(self, rules, sql):
        normalized = sql.strip().upper()
        for prefix in tuple(rules):
            if normalized.startswith(prefix):
                raise rules.pop(prefix)

    def execute(self, sql, parameters=None):
        self._fail(self.before, sql)
        result = self.connection.execute(sql, parameters)
        self._fail(self.after, sql)
        return result

    def executemany(self, sql, parameters):
        self._fail(self.before, sql)
        result = self.connection.executemany(sql, parameters)
        self._fail(self.after, sql)
        return result

    def __getattr__(self, name):
        return getattr(self.connection, name)
```

- [x] **2. Adicionar regressões de cache e estado transacional.** Iniciar o arquivo de teste com os imports abaixo; os testes das próximas tarefas serão acrescentados ao mesmo arquivo.

```python
import polars as pl
import pytest

from omnisus_db.lake import Lake
from tests.helpers.connection_faults import FaultyConnection


def test_schema_cache_recovers_after_rollback(tmp_path):
    with Lake.local(f"ducklake:{tmp_path}/cache.ducklake") as lake:
        lake.ingest("sample", pl.DataFrame({"i": [1]}).lazy())
        frame = pl.DataFrame({"i": [2], "new_column": [3]}).lazy()
        with pytest.raises(ValueError, match="abort"):
            with lake.transaction():
                lake.ingest("sample", frame)
                raise ValueError("abort")
        lake.ingest("sample", frame)
        assert lake.connect().execute(
            "SELECT i, new_column FROM lake.sample ORDER BY i"
        ).fetchall() == [(1, None), (2, 3)]


@pytest.mark.parametrize("timing", ["before", "after"])
def test_commit_failure_invalidates_handle(tmp_path, timing):
    from omnisus_db.lake import CommitOutcomeUnknown

    with Lake.local(f"ducklake:{tmp_path}/commit.ducklake") as lake:
        original = lake.connect()
        injected = RuntimeError("commit acknowledgement failed")
        lake._con = FaultyConnection(original, **{timing: {"COMMIT": injected}})
        with pytest.raises(CommitOutcomeUnknown) as caught:
            with lake.transaction():
                lake.connect().execute("CREATE TABLE lake.sample(i INTEGER)")
                lake.connect().execute("INSERT INTO lake.sample VALUES (1)")
        assert caught.value.__cause__ is injected
        assert lake.is_usable is False
        with pytest.raises(RuntimeError, match="unusable"):
            lake.connect()
        for operation in (
            lake.tables,
            lake.snapshots,
            lake.bootstrap_auxiliares,
            lake.ensure_aux_cnes_view,
            lambda: lake.optimize("sample"),
            lake.vacuum,
        ):
            with pytest.raises(RuntimeError, match="unusable"):
                operation()
        if timing == "after":
            assert original.execute("SELECT * FROM lake.sample").fetchall() == [(1,)]


def test_failed_rollback_preserves_original_cause(tmp_path):
    from omnisus_db.lake import TransactionStateError

    with Lake.local(f"ducklake:{tmp_path}/rollback.ducklake") as lake:
        lake._con = FaultyConnection(
            lake.connect(), before={"ROLLBACK": RuntimeError("rollback unavailable")}
        )
        original = ValueError("bad input")
        with pytest.raises(TransactionStateError) as caught:
            with lake.transaction():
                raise original
        assert caught.value.__cause__ is original
        assert lake.is_usable is False


def test_begin_failure_stops_the_handle(tmp_path):
    from omnisus_db.lake import TransactionStateError

    with Lake.local(f"ducklake:{tmp_path}/begin.ducklake") as lake:
        injected = RuntimeError("cannot begin")
        lake._con = FaultyConnection(lake.connect(), before={"BEGIN": injected})
        with pytest.raises(TransactionStateError) as caught:
            with lake.transaction():
                pytest.fail("body must not run")
        assert caught.value.__cause__ is injected
        assert not lake.is_usable
```

- [x] **3. Executar as regressões antes da correção.**

```bash
uv run --locked --extra dev pytest tests/unit/lake/test_transactions.py -q
```

Esperado: falha por cache inválido e pelos novos tipos/interfaces ainda inexistentes. Confirmar a falha de comportamento do cache isoladamente, não apenas ImportError dos tipos novos.

- [x] **4. Criar os tipos em `_transactions.py` e exportar os erros em `lake/__init__.py`.**

```python
from dataclasses import dataclass


@dataclass
class TransactionReceipt:
    committed: bool = False
    snapshot_id: int | None = None


class TransactionStateError(RuntimeError):
    """The handle cannot safely continue its managed transaction workflow."""


class CommitOutcomeUnknown(TransactionStateError):
    """COMMIT raised; do not infer rollback or retry the write automatically."""
```

Usar esta exportação completa em `lake/__init__.py`:

```python
"""Lake — DuckLake bindings."""

from omnisus_db.lake._transactions import CommitOutcomeUnknown, TransactionStateError
from omnisus_db.lake.catalog import DEFAULT_TARGET
from omnisus_db.lake.operations import Lake

__all__ = ["DEFAULT_TARGET", "CommitOutcomeUnknown", "Lake", "TransactionStateError"]
```

Em `operations.py`, importar esses três tipos. Acrescentar no `__init__`, antes de abrir a conexão:

```python
self._in_transaction = False
self._unusable = False
self._closed = False
self._pending_results: list[ImportResult] = []
```

`ImportResult` já é importado sob `TYPE_CHECKING` e o módulo usa anotações futuras. Substituir `connect()` e `close()` e adicionar propriedades/método abaixo:

```python
@property
def in_transaction(self) -> bool:
    return self._in_transaction

@property
def is_usable(self) -> bool:
    return not self._closed and not self._unusable

def connect(self) -> duckdb.DuckDBPyConnection:
    if not self.is_usable:
        raise RuntimeError("Lake handle is unusable; close it and inspect the catalog")
    return self._con

def _read_snapshot(self) -> int | None:
    row = self._con.execute(
        "SELECT id FROM ducklake_last_committed_snapshot(?)", [self._alias]
    ).fetchone()
    return None if row is None or row[0] is None else int(row[0])

def close(self) -> None:
    if self._closed:
        return
    try:
        close_connection(self._con)
    finally:
        self._closed = True
        self._columns.clear()
        self._ensured.clear()
```

Adicionar também esta instrução no início dos corpos de `tables`, `snapshots`, `optimize`, `vacuum`, `bootstrap_auxiliares` e `ensure_aux_cnes_view`, sem alterar os seus algoritmos:

```python
self.connect()
```

Isso impede que um método que usa `_con` diretamente contorne a invalidação do handle. A manutenção continua pendente em D3; aqui muda somente a guarda de uso.

- [x] **5. Substituir `Lake.transaction` pela fronteira abaixo.** O aviso posterior a COMMIT não altera o estado confirmado. Não consultar snapshot anterior como se identificasse uma transação vazia.

```python
@contextlib.contextmanager
def transaction(self) -> Iterator[TransactionReceipt]:
    self.connect()  # Reject closed or invalidated handles.
    if self._in_transaction:
        raise RuntimeError("nested Lake.transaction is not supported")
    self._columns.clear()
    self._ensured.clear()
    try:
        before = self._read_snapshot()
        self._con.execute("BEGIN TRANSACTION")
    except Exception as exc:
        self._unusable = True
        raise TransactionStateError("could not begin managed transaction") from exc

    receipt = TransactionReceipt()
    self._in_transaction = True
    self._pending_results = []
    try:
        try:
            yield receipt
        except BaseException as original:
            try:
                self._con.execute("ROLLBACK")
            except Exception as rollback_error:
                self._unusable = True
                original.add_note(f"rollback also failed: {rollback_error}")
                if isinstance(original, Exception):
                    raise TransactionStateError("rollback failed; handle unusable") from original
            raise
        else:
            try:
                self._con.execute("COMMIT")
            except BaseException as original:
                self._unusable = True
                try:
                    self._con.execute("ROLLBACK")
                except Exception as rollback_error:
                    original.add_note(f"rollback cleanup also failed: {rollback_error}")
                if not isinstance(original, Exception):
                    raise
                raise CommitOutcomeUnknown("commit outcome unknown; inspect before retry") from original

            receipt.committed = True
            try:
                after = self._read_snapshot()
            except Exception:
                logger.warning("lake.snapshot_unavailable_after_commit")
            else:
                receipt.snapshot_id = after if after != before else None
            for result in self._pending_results:
                result.snapshot_id = receipt.snapshot_id
    finally:
        self._in_transaction = False
        self._pending_results = []
        self._columns.clear()
        self._ensured.clear()
```

- [x] **6. Verificar isolamento de uso, fechamento e transação vazia.** Acrescentar:

```python
def test_empty_and_nested_transactions(tmp_path):
    lake = Lake.local(f"ducklake:{tmp_path}/empty.ducklake")
    with lake.transaction() as receipt:
        assert receipt.committed is False
        with pytest.raises(RuntimeError, match="nested"):
            with lake.transaction():
                pass
    assert receipt.committed is True
    assert receipt.snapshot_id is None
    lake.close()
    lake.close()
    assert lake.is_usable is False
```

- [x] **7. Executar testes e checks da tarefa.**

```bash
uv run --locked --extra dev pytest tests/unit/lake/test_transactions.py tests/unit/lake/test_operations.py -q
uv run --locked --extra dev ruff check src/omnisus_db/lake tests/helpers tests/unit/lake/test_transactions.py
uv run --locked --extra dev mypy src
```

Esperado: todos passam; o controle de falha depois de COMMIT deixa dados persistidos e ainda assim comunica confirmação desconhecida, sem retry.

- [x] **8. Revisar e registrar somente os arquivos da tarefa.**

```bash
git add src/omnisus_db/lake/_transactions.py src/omnisus_db/lake/operations.py src/omnisus_db/lake/__init__.py tests/helpers/__init__.py tests/helpers/connection_faults.py tests/unit/lake/test_transactions.py
git commit -m "fix: make managed lake transactions recoverable"
```

## Task 2: Publicar snapshots somente depois do commit

**Files:** Modify `src/omnisus_db/lake/operations.py`; Test `tests/unit/lake/test_transactions.py` e `tests/unit/lake/test_ingest_performance.py`.

**Interfaces:** Consome `Lake.in_transaction`, `_pending_results`, `transaction()` e `_read_snapshot()` da Task 1. Produz `Lake.ingest(table, lazyframe, *, partition_by=()) -> ImportResult` com `snapshot_id=None` durante a transação e preenchido após confirmação.

- [x] **1. Adicionar testes para resultados pendentes, rollback e metadado indisponível.**

```python
def test_ingest_results_receive_the_committed_batch_snapshot(tmp_path):
    with Lake.local(f"ducklake:{tmp_path}/snap.ducklake") as lake:
        direct = lake.ingest("sample", pl.DataFrame({"i": [1]}).lazy())
        assert direct.snapshot_id == lake.snapshots()[-1]["snapshot_id"]
        with lake.transaction() as receipt:
            first = lake.ingest("sample", pl.DataFrame({"i": [2]}).lazy())
            second = lake.ingest("sample", pl.DataFrame({"i": [3]}).lazy())
            assert first.snapshot_id is None
            assert second.snapshot_id is None
        actual = lake.snapshots()[-1]["snapshot_id"]
        assert first.snapshot_id == second.snapshot_id == receipt.snapshot_id == actual
        assert actual > direct.snapshot_id


def test_rolled_back_result_never_gets_a_snapshot(tmp_path):
    with Lake.local(f"ducklake:{tmp_path}/pending.ducklake") as lake:
        with pytest.raises(ValueError):
            with lake.transaction():
                result = lake.ingest("sample", pl.DataFrame({"i": [1]}).lazy())
                raise ValueError("reject")
        assert result.snapshot_id is None
        assert "sample" not in lake.tables()


def test_snapshot_read_failure_does_not_reclassify_a_committed_write(tmp_path, monkeypatch):
    with Lake.local(f"ducklake:{tmp_path}/metadata.ducklake") as lake:
        read = lake._read_snapshot
        calls = 0

        def fail_second_read():
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("snapshot query failed")
            return read()

        monkeypatch.setattr(lake, "_read_snapshot", fail_second_read)
        result = lake.ingest("sample", pl.DataFrame({"i": [1]}).lazy())
        assert result.snapshot_id is None
        assert lake.connect().execute("SELECT * FROM lake.sample").fetchall() == [(1,)]
        assert lake.is_usable
```

- [x] **2. Executar antes da mudança.**

```bash
uv run --locked --extra dev pytest tests/unit/lake/test_transactions.py -k 'snapshot or pending' -q
```

Esperado: resultados dentro de transação ainda contêm o snapshot anterior e falham as assertions de `None`.

- [x] **3. Fazer `ingest` participar ou possuir a transação.** No início do corpo de `Lake.ingest`, antes da criação do staging:

```python
self.connect()
if not self.in_transaction:
    with self.transaction():
        return self.ingest(table, lazyframe, partition_by=partition_by)
```

Manter o corpo de staging, `_ensure_table` e `INSERT BY NAME`. Remover a consulta `SELECT max(snapshot_id)` e substituir a construção final por:

```python
result = ImportResult(
    rows=int(rows),
    bytes_written=int(bytes_written),
    duration_seconds=duration,
    snapshot_id=None,
)
self._pending_results.append(result)
return result
```

A recursão ocorre somente uma vez: a entrada seguinte vê `in_transaction=True`. O retorno do `with` externo só acontece depois que a Task 1 preenche o resultado. Atualizar o docstring com este texto:

```text
Append data in a managed transaction. Direct calls commit before returning.
Inside Lake.transaction(), snapshot_id remains None until that context commits.
Raw SQL BEGIN/COMMIT is outside this managed-transaction contract.
```

- [x] **4. Verificar atomicidade do schema e compatibilidade dos testes existentes.**

```bash
uv run --locked --extra dev pytest tests/unit/lake -q
uv run --locked --extra dev mypy src
```

Esperado: a ingestão direta cria/insere em um commit; dentro de lote, os resultados compartilham o snapshot do lote. Se algum teste antigo exigir contagem de snapshots intermediários de CREATE/ALTER, atualizar somente essa expectativa, preservando assertions de valores e de um snapshot por lote.

- [x] **5. Registrar a mudança.**

```bash
git add src/omnisus_db/lake/operations.py tests/unit/lake/test_transactions.py tests/unit/lake/test_ingest_performance.py
git commit -m "fix: finalize ingestion snapshots after commit"
```

## Task 3: Contabilizar o escopo que falha e interromper commits desconhecidos

**Files:** Modify `src/omnisus_db/sources/_base.py`, `src/omnisus_db/sources/datasus_ftp/_runner.py`, `src/omnisus_db/__init__.py`; Create `tests/unit/sources/datasus_ftp/test_runner_failures.py`.

**Interfaces:** Consome `Lake.transaction()`, `Lake.is_usable` e `TransactionStateError`. Produz `ImportAbortedError(report: ImportReport, unresolved: tuple[tuple[int, ScopeKey], ...])`. Preserva `run_scopes(dataset, *, scopes, lake, concurrency=6, batch_size=24) -> ImportReport`.

- [x] **1. Adicionar o teste mínimo de A01 e o lote misto.**

```python
import asyncio

import pytest

from omnisus_db.lake import Lake
from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp._runner import run_scopes
from tests.helpers.connection_faults import FaultyConnection


@pytest.mark.asyncio
@pytest.mark.parametrize("years", [(2022,), (2021, 2022, 2023)])
async def test_bad_dbc_is_never_omitted(tmp_path, monkeypatch, dbc_fixture, years):
    raw = dbc_fixture("sim_rr_2023_mini").read_bytes()

    async def fetch(*, dataset, scope):
        return b"invalid dbc" if scope.ano == 2022 else raw

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fetch)
    scopes = [ScopeKey(uf="RR", ano=year) for year in years]
    with Lake.local(f"ducklake:{tmp_path}/mixed.ducklake") as lake:
        report = await run_scopes(
            "sim_do", scopes=scopes, lake=lake, concurrency=1, batch_size=2
        )
        assert [outcome.scope for outcome in report.outcomes] == scopes
        expected = ["failed"] if len(years) == 1 else ["failed", "failed", "ok"]
        assert [outcome.status for outcome in report.outcomes] == expected
        if len(years) == 1:
            assert report.rows == 0
        else:
            stored = lake.connect().execute(
                "SELECT ano, count(*) FROM lake.sim_do GROUP BY ano"
            ).fetchall()
            assert stored == [(2023, report.rows)]
            assert report.rows > 0


@pytest.mark.asyncio
async def test_repeated_input_positions_are_preserved(tmp_path, monkeypatch, dbc_fixture):
    raw = dbc_fixture("sim_rr_2023_mini").read_bytes()

    async def fetch(**kwargs):
        return raw

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fetch)
    scope = ScopeKey(uf="RR", ano=2023)
    with Lake.local(f"ducklake:{tmp_path}/repeat.ducklake") as lake:
        report = await run_scopes("sim_do", scopes=[scope, scope], lake=lake)
        assert [outcome.scope for outcome in report.outcomes] == [scope, scope]
        assert len(report.ok) == 2
        assert lake.connect().execute("SELECT count(*) FROM lake.sim_do").fetchone()[0] == report.rows
```

- [x] **2. Executar e confirmar a falha de contabilidade.**

```bash
uv run --locked --extra dev pytest tests/unit/sources/datasus_ftp/test_runner_failures.py -q
```

Esperado: o caso inválido único retorna outcomes vazios; o lote misto omite 2022. O controle de posições repetidas deve continuar passando depois da correção.

- [x] **3. Acrescentar a exceção depois de `ImportReport` em `_base.py`.** Importar/exportar o nome na API de topo, na lista existente de imports de `_base` e em `__all__`.

```python
class ImportAbortedError(RuntimeError):
    """Partial progress is known, but the remaining inputs need inspection."""

    def __init__(
        self,
        report: ImportReport,
        unresolved: tuple[tuple[int, ScopeKey], ...],
    ) -> None:
        self.report = report
        self.unresolved = unresolved
        super().__init__(
            f"import aborted: {len(unresolved)} input(s) unresolved; inspect before retry"
        )
```

- [x] **4. Corrigir a fronteira de publicação no loop do runner.** Importar `ImportAbortedError` de `_base` e `TransactionStateError` de `lake._transactions`. Antes de `ingest_raw`, registrar o escopo; somente o resultado depois do `with` será publicado como `ok`.

Inicializar `writing: set[int] = set()` ao lado de `batch` em cada iteração. Esse conjunto distingue erro de fetch de escopo que pode ter alterado a transação.

```python
writing.add(index)
batch[index] = ScopeOutcome(
    scope=scope, status="failed", reason="ingestion did not complete"
)
try:
    result = ingest_raw(d, scope, raw, lake)
except Exception as exc:
    batch[index] = ScopeOutcome(scope=scope, status="failed", reason=str(exc))
    raise
batch[index] = ScopeOutcome(scope=scope, status="ok", result=result)
```

Substituir o handler de exceção do lote pelo bloco abaixo. A checagem de erro fatal acontece antes de transformar resultados provisórios em falha por rollback:

```python
except Exception as exc:
    if isinstance(exc, TransactionStateError) or not lake.is_usable:
        determined = dict(outcomes)
        determined.update(
            (i, outcome)
            for i, outcome in batch.items()
            if outcome.status != "ok" and i not in writing
        )
        partial = ImportReport(tuple(determined[i] for i in sorted(determined)))
        unresolved = tuple((i, scope) for i, scope in enumerate(scopes) if i not in determined)
        raise ImportAbortedError(partial, unresolved) from exc

    logger.warning("run_scopes.batch_failed", dataset=d.name, error=str(exc))
    for i, outcome in batch.items():
        outcomes[i] = (
            outcome
            if outcome.status != "ok"
            else ScopeOutcome(
                scope=outcome.scope,
                status="failed",
                reason=f"batch rolled back: {exc}",
            )
        )
else:
    outcomes.update(batch)
```

Manter `outcomes` por índice e a construção final ordenada. **Exceção importante:** se `ingest_raw` lançar `TransactionStateError`, o registro provisório do escopo não é resultado determinado. No handler interno de `ingest_raw`, adicionar antes de `except Exception`:

```python
except TransactionStateError:
    batch.pop(index, None)
    raise
```

Isso conserva o escopo em `unresolved`, em vez de afirmar rollback de um commit potencialmente confirmado.

Substituir também `produce_all` nesta tarefa, para que as novas saídas fatais não bloqueiem tentando publicar sentinela no cancelamento:

```python
async def produce_all() -> None:
    await asyncio.gather(*(produce(i, s) for i, s in queued))
    await queue.put(None)
```

A sentinela representa conclusão normal; a Task 4 adiciona observação de término anormal do produtor.

- [x] **5. Adicionar teste de confirmação perdida sem retry.**

```python
@pytest.mark.asyncio
async def test_commit_unknown_aborts_without_retry(tmp_path, monkeypatch, dbc_fixture):
    from omnisus_db import ImportAbortedError

    raw = dbc_fixture("sim_rr_2023_mini").read_bytes()

    async def fetch(**kwargs):
        return raw

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fetch)
    scopes = [ScopeKey(uf="RR", ano=year) for year in (2021, 2022)]
    with Lake.local(f"ducklake:{tmp_path}/unknown.ducklake") as lake:
        real = lake.connect()
        lake._con = FaultyConnection(real, after={"COMMIT": RuntimeError("ack lost")})
        with pytest.raises(ImportAbortedError) as caught:
            await run_scopes("sim_do", scopes=scopes, lake=lake, batch_size=1, concurrency=1)
        assert caught.value.report.rows == 0
        assert caught.value.unresolved == tuple(enumerate(scopes))
        assert real.execute("SELECT DISTINCT ano FROM lake.sim_do").fetchall() == [(2021,)]
        assert not lake.is_usable
```

Acrescentar o controle de preservação de um lote anterior. Nesse controle, a segunda confirmação falha, após a primeira ter sido publicada:

```python
@pytest.mark.asyncio
async def test_abort_keeps_previously_committed_progress(tmp_path, monkeypatch, dbc_fixture):
    from omnisus_db import ImportAbortedError

    raw = dbc_fixture("sim_rr_2023_mini").read_bytes()

    async def fetch(**kwargs):
        return raw

    class FailSecondCommit(FaultyConnection):
        commits = 0

        def execute(self, sql, parameters=None):
            if sql.strip().upper() == "COMMIT":
                self.commits += 1
                if self.commits == 2:
                    raise RuntimeError("second commit unavailable")
            return super().execute(sql, parameters)

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fetch)
    scopes = [ScopeKey(uf="RR", ano=year) for year in (2021, 2022, 2023)]
    with Lake.local(f"ducklake:{tmp_path}/partial.ducklake") as lake:
        lake._con = FailSecondCommit(lake.connect())
        with pytest.raises(ImportAbortedError) as caught:
            await run_scopes("sim_do", scopes=scopes, lake=lake, batch_size=1, concurrency=1)
        assert [outcome.scope for outcome in caught.value.report.ok] == scopes[:1]
        assert caught.value.report.rows > 0
        assert caught.value.unresolved == ((1, scopes[1]), (2, scopes[2]))
```

- [x] **6. Executar regressões e testes de tolerância existentes.**

```bash
uv run --locked --extra dev pytest tests/unit/sources/datasus_ftp/test_runner_failures.py tests/unit/sources/datasus_ftp/test_tolerance.py tests/unit/sources/datasus_ftp/test_runner_concurrency.py tests/unit/test_public_api.py -q
```

Esperado: nenhuma omissão; contagem corresponde a dados confirmados; falha de COMMIT interrompe com exceção e progresso parcial, sem bloquear na limpeza do produtor.

- [x] **7. Registrar.**

```bash
git add src/omnisus_db/sources/_base.py src/omnisus_db/sources/datasus_ftp/_runner.py src/omnisus_db/__init__.py tests/unit/sources/datasus_ftp/test_runner_failures.py
git commit -m "fix: account for failed scopes and unknown commits"
```

## Task 4: Encerrar produtores sem bloquear a importação

**Files:** Modify `src/omnisus_db/sources/datasus_ftp/_runner.py`; Test `tests/unit/sources/datasus_ftp/test_runner_failures.py`.

**Interfaces:** Consome a fila `asyncio.Queue[_Fetched | None]`, o produtor `asyncio.Task[None]` e `ImportAbortedError`. Produz `_next_fetched(queue, producer) -> _Fetched | None` e `_ProducerStoppedError(RuntimeError)` privados.

- [x] **1. Adicionar teste de produtor encerrado sem sentinela.**

```python
@pytest.mark.asyncio
async def test_dead_producer_does_not_leave_queue_waiter():
    from omnisus_db.sources.datasus_ftp import _runner

    baseline = asyncio.all_tasks()

    async def fail():
        raise ValueError("producer stopped")

    producer = asyncio.create_task(fail())
    queue = asyncio.Queue(maxsize=1)
    with pytest.raises(_runner._ProducerStoppedError):
        await asyncio.wait_for(_runner._next_fetched(queue, producer), timeout=2)
    assert not (asyncio.all_tasks() - baseline)
```

- [x] **2. Executar antes de implementar.**

```bash
uv run --locked --extra dev pytest tests/unit/sources/datasus_ftp/test_runner_failures.py::test_dead_producer_does_not_leave_queue_waiter -q
```

Esperado: helper inexistente. Esse teste especifica que a espera deve observar produtor e fila, não somente a disponibilidade de um item.

- [x] **3. Adicionar o helper e substituir `await queue.get()` do consumidor por `await _next_fetched(queue, producer)`.**

```python
class _ProducerStoppedError(RuntimeError):
    """The producer exited without completing the input stream."""


async def _next_fetched(
    queue: asyncio.Queue[_Fetched | None],
    producer: asyncio.Task[None],
) -> _Fetched | None:
    waiting = asyncio.create_task(queue.get())
    try:
        done, _ = await asyncio.wait(
            {waiting, producer}, return_when=asyncio.FIRST_COMPLETED
        )
        if waiting in done:
            return waiting.result()
        if producer.cancelled():
            raise _ProducerStoppedError("producer cancelled")
        error = producer.exception()
        if error is not None:
            raise _ProducerStoppedError("producer failed") from error
        return await waiting  # Normal completion has queued the sentinel.
    finally:
        if not waiting.done():
            waiting.cancel()
        await asyncio.gather(waiting, return_exceptions=True)
```

No handler do lote, substituir o bloco fatal da Task 3 por este. Quando o produtor falha e rollback funciona, os escopos já escritos no lote são falhas determinadas; somente commits/rollbacks desconhecidos tornam essas posições não resolvidas.

```python
if isinstance(exc, (TransactionStateError, _ProducerStoppedError)) or not lake.is_usable:
    rollback_known = not isinstance(exc, TransactionStateError) and lake.is_usable
    determined = dict(outcomes)
    for i, outcome in batch.items():
        if i in writing and not rollback_known:
            continue
        determined[i] = (
            outcome
            if outcome.status != "ok"
            else ScopeOutcome(
                scope=outcome.scope,
                status="failed",
                reason=f"batch rolled back: {exc}",
            )
        )
    partial = ImportReport(tuple(determined[i] for i in sorted(determined)))
    unresolved = tuple((i, scope) for i, scope in enumerate(scopes) if i not in determined)
    raise ImportAbortedError(partial, unresolved) from exc
```

- [x] **4. Acrescentar teste de cancelamento com fila cheia após um commit.** O evento sincroniza o ponto de cancelamento; não usar um sleep de duração arbitrária para adivinhar quando a fila encheu.

```python
@pytest.mark.asyncio
async def test_cancel_with_full_queue_preserves_previous_commit(
    tmp_path, monkeypatch, dbc_fixture
):
    from omnisus_db.sources.datasus_ftp import _runner

    raw = dbc_fixture("sim_rr_2023_mini").read_bytes()

    async def fetch(**kwargs):
        return raw

    real_next = _runner._next_fetched
    paused = asyncio.Event()
    hold = asyncio.Event()
    calls = 0

    async def pause_second_item(queue, producer):
        nonlocal calls
        item = await real_next(queue, producer)
        calls += 1
        if calls == 2:
            while not queue.full():
                await asyncio.sleep(0)
            paused.set()
            await hold.wait()
        return item

    monkeypatch.setattr(_runner, "fetch_dbc_bytes", fetch)
    monkeypatch.setattr(_runner, "_next_fetched", pause_second_item)
    scopes = [ScopeKey(uf="RR", ano=year) for year in range(2015, 2024)]
    baseline = asyncio.all_tasks()
    with Lake.local(f"ducklake:{tmp_path}/cancel.ducklake") as lake:
        task = asyncio.create_task(
            _runner.run_scopes("sim_do", scopes=scopes, lake=lake, concurrency=1, batch_size=1)
        )
        try:
            await asyncio.wait_for(paused.wait(), timeout=5)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, timeout=2)
            assert lake.is_usable
            assert lake.connect().execute("SELECT DISTINCT ano FROM lake.sim_do").fetchall() == [(2015,)]
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    assert not (asyncio.all_tasks() - baseline)
```

- [x] **5. Rodar testes de falha, concorrência e limites.**

```bash
uv run --locked --extra dev pytest tests/unit/sources/datasus_ftp/test_runner_failures.py tests/unit/sources/datasus_ftp/test_runner_concurrency.py -q
uv run --locked --extra dev ruff check src/omnisus_db/sources/datasus_ftp/_runner.py tests/unit/sources/datasus_ftp/test_runner_failures.py
uv run --locked --extra dev mypy src
```

Esperado: os testes terminam, sem tarefas pendentes; os limites de fetch existentes continuam passando e o lote confirmado antes do cancelamento permanece íntegro.

- [x] **6. Registrar.**

```bash
git add src/omnisus_db/sources/datasus_ftp/_runner.py tests/unit/sources/datasus_ftp/test_runner_failures.py
git commit -m "fix: stop ingestion producers without queue deadlocks"
```

## Task 5: Publicar refresh CNES de forma atômica

**Files:** Modify `src/omnisus_db/sources/cnes/importers/master.py`; Test `tests/unit/sources/cnes/test_master.py`.

**Interfaces:** Consome `Lake.in_transaction` e `Lake.transaction()`. Produz `_prepare_master_rows(records: list[dict]) -> list[tuple[str, str, str | None, str | None]]`. Preserva `_upsert_master(lake, records) -> None` e retorno inteiro do importador público.

- [x] **1. Acrescentar imports e regressões de perda de registro e conflito.** O arquivo existente já importa `httpx`, `respx`, `Lake` e `import_cnes_master`; adicionar `pytest` e `FaultyConnection`.

```python
import pytest
from tests.helpers.connection_faults import FaultyConnection


def test_upsert_failure_preserves_previous_record(tmp_path):
    from omnisus_db.sources.cnes.importers.master import _ensure_master_table, _upsert_master

    with Lake.local(f"ducklake:{tmp_path}/atomic.ducklake") as lake:
        _ensure_master_table(lake)
        lake.connect().execute(
            "INSERT INTO lake.cnes_master VALUES ('1234567', 'OLD', 'OLD', NULL)"
        )
        lake._con = FaultyConnection(
            lake.connect(), before={"INSERT INTO": RuntimeError("insert failed")}
        )
        records = [{"cnes": "1234567", "nome": "NEW", "nome_fantasia": "NEW", "razao_social": None}]
        with pytest.raises(RuntimeError, match="insert failed"):
            _upsert_master(lake, records)
        assert lake.connect().execute("SELECT nome FROM lake.cnes_master").fetchall() == [("OLD",)]


def test_conflicting_records_are_rejected_before_delete(tmp_path):
    from omnisus_db.sources.cnes.importers.master import _ensure_master_table, _upsert_master

    with Lake.local(f"ducklake:{tmp_path}/conflict.ducklake") as lake:
        _ensure_master_table(lake)
        lake.connect().execute(
            "INSERT INTO lake.cnes_master VALUES ('1234567', 'OLD', 'OLD', NULL)"
        )
        records = [
            {"cnes": "1234567", "nome": "A", "nome_fantasia": "A", "razao_social": None},
            {"cnes": "1234567", "nome": "B", "nome_fantasia": "B", "razao_social": None},
        ]
        with pytest.raises(ValueError, match="conflicting"):
            _upsert_master(lake, records)
        assert lake.connect().execute("SELECT nome FROM lake.cnes_master").fetchall() == [("OLD",)]
```

- [x] **2. Executar e confirmar a regressão de atomicidade.**

```bash
uv run --locked --extra dev pytest tests/unit/sources/cnes/test_master.py -k 'preserves_previous_record or conflicting_records' -q
```

Esperado: implementação antiga perde OLD no primeiro teste e não rejeita conflito no segundo.

- [x] **3. Preparar todos os valores antes da primeira mutação.** Adicionar `from contextlib import nullcontext` e este helper ao módulo CNES:

```python
def _prepare_master_rows(
    records: list[dict],
) -> list[tuple[str, str, str | None, str | None]]:
    prepared: dict[str, tuple[str, str, str | None, str | None]] = {}
    for record in records:
        code = record.get("cnes")
        name = record.get("nome")
        if not isinstance(code, str) or len(code) != 7 or not code.isascii() or not code.isdigit():
            raise ValueError("CNES code must contain seven ASCII digits")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("CNES record must contain a usable name")
        fantasia = record.get("nome_fantasia")
        razao = record.get("razao_social")
        if any(value is not None and not isinstance(value, str) for value in (fantasia, razao)):
            raise ValueError("CNES optional names must be strings or None")
        row = (code, name, fantasia, razao)
        if code in prepared and prepared[code] != row:
            raise ValueError(f"conflicting CNES records for {code}")
        prepared[code] = row
    return list(prepared.values())
```

Substituir `_upsert_master`:

```python
def _upsert_master(lake: Lake, records: list[dict]) -> None:
    rows = _prepare_master_rows(records)
    if not rows:
        return
    context = nullcontext() if lake.in_transaction else lake.transaction()
    with context:
        con = lake.connect()
        codes = [row[0] for row in rows]
        placeholders = ", ".join("?" for _ in codes)
        con.execute(
            f"DELETE FROM {lake.alias}.cnes_master WHERE cnes IN ({placeholders})",
            codes,
        )
        con.executemany(
            f"INSERT INTO {lake.alias}.cnes_master VALUES (?, ?, ?, ?)", rows
        )
```

- [x] **4. Agrupar a publicação pública depois do fetch.** Substituir o corpo de `with Lake.local(target) as lake:` em `import_cnes_master` pelo seguinte; manter assinatura e docstring, atualizando a descrição de atomicidade.

```python
if codes is None:
    codes = _codes_from_lake(lake, only_missing=only_missing)
codes = list(dict.fromkeys(str(code).zfill(7) for code in codes))
if any(len(code) != 7 or not code.isascii() or not code.isdigit() for code in codes):
    raise ValueError("CNES codes must contain seven ASCII digits")
logger.info("cnes_master.start", codes=len(codes), only_missing=only_missing)

records = asyncio.run(_fetch_all(codes, concurrency=concurrency, progress=progress))
_prepare_master_rows(records)  # Validate before table creation or DELETE.
with lake.transaction():
    _ensure_master_table(lake)
    _upsert_master(lake, records)
    lake.ensure_aux_cnes_view()

logger.info("cnes_master.done", fetched=len(records), requested=len(codes))
return len(records)
```

A validação repetida no helper protege também chamadores diretos de `_upsert_master`; não há consulta de rede adicional. O callback passa a contar códigos únicos, o que deve ser documentado.

- [x] **5. Adicionar controles de duplicidade e falha da visão.** Reutilizar `_api_url` e `_api_response` já definidos no arquivo de testes existente.

```python
@respx.mock
def test_duplicate_codes_fetch_once(tmp_path):
    route = respx.get(_api_url("1234567")).mock(
        return_value=httpx.Response(
            200, json=_api_response(1234567, nome_fantasia="NEW", razao="NEW SA")
        )
    )
    target = f"ducklake:{tmp_path}/dedup.ducklake"
    assert import_cnes_master(codes=["1234567", "1234567"], target=target) == 1
    assert route.call_count == 1
    with Lake.local(target) as lake:
        assert lake.connect().execute("SELECT count(*) FROM lake.cnes_master").fetchone()[0] == 1


@respx.mock
def test_view_failure_rolls_back_master_refresh(tmp_path, monkeypatch):
    from omnisus_db.sources.cnes.importers.master import _ensure_master_table

    target = f"ducklake:{tmp_path}/view.ducklake"
    with Lake.local(target) as lake:
        _ensure_master_table(lake)
        lake.connect().execute(
            "INSERT INTO lake.cnes_master VALUES ('1234567', 'OLD', 'OLD', NULL)"
        )
    respx.get(_api_url("1234567")).mock(
        return_value=httpx.Response(
            200, json=_api_response(1234567, nome_fantasia="NEW", razao="NEW SA")
        )
    )

    def fail_view(self):
        raise RuntimeError("view unavailable")

    monkeypatch.setattr(Lake, "ensure_aux_cnes_view", fail_view)
    with pytest.raises(RuntimeError, match="view unavailable"):
        import_cnes_master(codes=["1234567"], target=target)
    with Lake.local(target) as lake:
        assert lake.connect().execute("SELECT nome FROM lake.cnes_master").fetchall() == [("OLD",)]
```

- [x] **6. Executar a suíte CNES e os testes de transação.**

```bash
uv run --locked --extra dev pytest tests/unit/sources/cnes/test_master.py tests/unit/lake/test_transactions.py -q
uv run --locked --extra dev mypy src
```

Esperado: refresh completo ou preservação de OLD; falhas HTTP continuam sem apagar dados anteriores; duplicidades não ampliam a tabela. Não alterar a regra temporal da visão.

- [x] **7. Registrar.**

```bash
git add src/omnisus_db/sources/cnes/importers/master.py tests/unit/sources/cnes/test_master.py
git commit -m "fix: publish CNES master refresh atomically"
```

## Task 6: Comunicar falha e progresso parcial pela CLI

**Files:** Modify `src/omnisus_db/cli/main.py`, docstrings de `src/omnisus_db/__init__.py`, `docs/guides/inventory.md` e `CHANGELOG.md`; Test `tests/unit/cli/test_main.py` e `tests/unit/test_public_api.py`.

**Interfaces:** Consome `odb.ImportAbortedError.report` e `.unresolved`. Preserva comando `omnisus-db import`, retorno `ImportReport` em conclusão normal e código de saída 1 para falha/interrupção.

- [x] **1. Adicionar um teste real de CLI com DBC inválido e um teste do novo erro público.** O arquivo existente já contém `runner = CliRunner()` e `app`.

```python
def test_import_invalid_dbc_exits_nonzero(monkeypatch, tmp_path):
    async def fetch(**kwargs):
        return b"invalid dbc"

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fetch)
    result = runner.invoke(
        app,
        ["import", "sim_do", "--year", "2023", "--ufs", "RR",
         "--target", f"ducklake:{tmp_path}/bad.ducklake"],
    )
    assert result.exit_code == 1
    assert "1 failed" in result.stdout
    assert "0 rows" in result.stdout


def test_import_abort_prints_partial_progress(monkeypatch, tmp_path):
    import omnisus_db as odb

    def abort(*args, **kwargs):
        report = odb.ImportReport(outcomes=())
        unresolved = ((0, odb.ScopeKey(uf="RR", ano=2023)),)
        raise odb.ImportAbortedError(report, unresolved)

    monkeypatch.setattr(odb, "import_dataset", abort)
    result = runner.invoke(
        app,
        ["import", "sim_do", "--year", "2023", "--ufs", "RR",
         "--target", f"ducklake:{tmp_path}/partial.ducklake"],
    )
    assert result.exit_code == 1
    assert "import interrupted" in result.stdout
    assert "1 unresolved" in result.stdout
    assert "inspect before retry" in result.stdout
    assert "imported" not in result.stdout
```

- [x] **2. Rodar os testes antes de tratar a exceção na CLI.**

```bash
uv run --locked --extra dev pytest tests/unit/cli/test_main.py -k 'invalid_dbc or abort_prints' -q
```

Esperado: o controle DBC passa pela Task 3; o teste de texto de interrupção falha, pois a CLI ainda não apresenta progresso parcial.

- [x] **3. Envolver somente a chamada dos importadores FTP em `try/except`.** Substituir o bloco `if d.name == "cnes_st"` imediatamente antes do resumo:

```python
try:
    if d.name == "cnes_st":
        report = odb.import_cnes_st(scopes=scopes, target=target)
    else:
        report = odb.import_dataset(d, scopes=scopes, target=target)
except odb.ImportAbortedError as exc:
    console.print(
        "[red]import interrupted[/red]: "
        f"{exc.report.rows:,} confirmed rows, "
        f"{len(exc.report.failed)} failed, "
        f"{len(exc.unresolved)} unresolved; inspect before retry"
    )
    raise typer.Exit(1) from exc
```

Preservar a checagem de `report.failed` que já existe depois do resumo normal. Usar marcador vermelho para execução concluída com falhas, evitando a marca verde atual:

```python
marker = "[red]failed[/red]" if report.failed else "[green]:heavy_check_mark:[/green]"
console.print(
    f"{marker} imported [bold]{report.rows:,}[/bold] rows "
    f"({len(report.ok)} ok, {len(report.skipped)} skipped, {len(report.failed)} failed)"
)
```

- [x] **4. Documentar o contrato onde o usuário lê os resultados.** Acrescentar ao guia `docs/guides/inventory.md`:

````markdown
## Transactions and interrupted imports

Use one writer per lake. Serialize write handles, processes and external SQL
clients that target the same catalog. This release does not provide a
cross-process writer lock or distributed retry coordination.

A completed import returns one outcome for every requested input position.
Repeated input scopes remain repeated append operations. `ok` means committed;
`failed` means an unsuccessful scope; `skipped` means a documented absence.

If commit acknowledgement or rollback fails, the import raises
`ImportAbortedError`. Its `report` contains determined outcomes and its
`unresolved` contains `(input_index, scope)` pairs that need inspection or were
not processed. Do not retry the whole import automatically: an unacknowledged
commit may already have written data.

```python
import omnisus_db as odb

try:
    report = odb.import_dataset(
        "sim_do", scopes=[odb.ScopeKey(uf="RR", ano=2023)]
    )
except odb.ImportAbortedError as exc:
    print(exc.report.rows, exc.unresolved)
    raise
```

For lower-level writes, use `Lake.transaction()`. An `ImportResult` created
inside that context has `snapshot_id=None` until commit. Direct `Lake.ingest`
commits before returning. If snapshot metadata cannot be read after a successful
commit, the write remains successful and its snapshot stays `None`.

Do not combine managed transactions with raw SQL `BEGIN` or `COMMIT` on
`Lake.connect()`. After a transaction-state failure, close the handle and inspect
the catalog before starting a new write.

CNES Master refresh validates records before changing stored values and commits
the table update and view refresh together. Repeated explicit CNES codes are
fetched once; progress counts unique codes.
````

Atualizar a frase da docstring de `import_dataset` que diz que falhas nunca abortam:

```text
Ordinary scope failures are reported and later batches continue. A transaction
state failure raises ImportAbortedError with partial progress; inspect before retry.
Use one writer per lake and managed Lake.transaction contexts for writes.
```

Em `CHANGELOG.md`, registrar o efeito concreto:

```markdown
- Failed DBC scopes are included in import reports. Rolled-back batches no longer
  leave missing outcomes, and unknown commits abort with inspectable partial progress.
- Schema caches are cleared at transaction boundaries. Ingestion snapshots are
  finalized after commit; direct ingestion groups schema and data changes atomically.
- CNES Master refresh commits records and the derived view together. Duplicate
  explicit codes are fetched once, and conflicting prepared records are rejected.
```

- [x] **5. Verificar CLI, API e documentação.**

```bash
uv run --locked --extra dev pytest tests/unit/cli tests/unit/test_public_api.py -q
uv run --locked --extra docs mkdocs build --strict
uv run --locked python scripts/gen_datasets_doc.py --check
```

Esperado: nenhuma mudança nas assinaturas de importação; erro novo exportado; documentação compila e contagens da CLI refletem outcomes.

- [x] **6. Registrar.**

```bash
git add src/omnisus_db/cli/main.py src/omnisus_db/__init__.py docs/guides/inventory.md CHANGELOG.md tests/unit/cli/test_main.py tests/unit/test_public_api.py
git commit -m "fix: expose interrupted import progress in CLI and API"
```

## Verificação final da entrega

Esta seção é o gate de integração das seis tarefas, não uma tarefa de refatoração adicional. Só marcar concluída depois de executar os comandos sobre o estado final.

- [x] Confirmar RED/GREEN das novas regressões, distinguindo controles de comportamento já implementado que devem permanecer verdes; não usar os diagnósticos históricos como substitutos das regressões.
- [x] Executar os checks globais:

```bash
uv sync --locked --all-extras
uv run --locked --extra dev ruff check .
uv run --locked --extra dev ruff format --check .
uv run --locked --extra dev mypy src
uv run --locked python scripts/gen_datasets_doc.py --check
uv run --locked --extra docs mkdocs build --strict
uv run --locked --extra dev frictionless validate src/omnisus_db/data/dicionarios/*.yaml
uv run --locked --extra dev pytest -m "not e2e and not perf" --cov=omnisus_db --cov-fail-under=85
uv build
uv lock --check
git diff --check
```

- [x] Executar a mesma seleção em Python 3.12, mantendo o ambiente principal em 3.13:

```bash
UV_PROJECT_ENVIRONMENT=/private/tmp/omnisus-d1-py312 uv sync --locked --all-extras --python 3.12
/private/tmp/omnisus-d1-py312/bin/pytest -m "not e2e and not perf" --cov=omnisus_db --cov-fail-under=85
```

- [x] Validar wheel limpo no Python 3.12:

```bash
uv venv --python 3.12 /private/tmp/omnisus-d1-wheel312
uv pip install --python /private/tmp/omnisus-d1-wheel312 --only-binary=:all: dist/omnisus_db-0.1.0-py3-none-any.whl
uv pip check --python /private/tmp/omnisus-d1-wheel312
/private/tmp/omnisus-d1-wheel312/bin/python -I -c "import omnisus_db; print(omnisus_db.__file__)"
```

O nome 0.1.0 é a versão atual em `src/omnisus_db/_version.py`; se outra entrega tiver alterado esse arquivo, usar o nome efetivamente produzido por `uv build`, sem alterar a versão para satisfazer este comando. Não certificar Windows/Linux a partir da execução macOS: os jobs existentes devem passar nos respectivos sistemas.

- [x] Registrar commit, hashes de `src`, `pyproject.toml` e `uv.lock`, versões carregadas, comandos, contagem de testes, falhas e skips em novo arquivo de evidência. Preservar os anexos anteriores.
- [x] Revisar o diff final para garantir que não alterou append, fontes IBGE, tipos canônicos, retenção ou política de múltiplos escritores.

## Cobertura da especificação e revisão do plano

| Critério da spec | Tarefa e evidência planejada |
|---|---|
| 1–3: DBC inválido, lote misto e posições repetidas | Task 3; teste real pela CLI na Task 6 |
| 4: cache após ALTER revertido | Task 1, `test_schema_cache_recovers_after_rollback` |
| 5–6: COMMIT/ROLLBACK falhos | Task 1; progresso parcial e ausência de retry na Task 3 |
| 7–9: snapshots pendentes, indisponíveis e transação vazia | Tasks 1–2 |
| 10: produtor/cancelamento | Task 4 com eventos e timeouts |
| 11–13: CNES atômico e duplicidades | Task 5 |
| 14: compatibilidade e checks | Task 6 e gate de integração |

Interfaces entre tarefas usam os mesmos nomes da spec. Os códigos apresentados eram propostas durante o planejamento; a execução foi concluída e revisada, com ajustes registrados no relatório de implementação. A atualização de dependências antecedeu este plano. O código efetivamente validado e as evidências finais prevalecem sobre os exemplos originais.

Próximos planos independentes: D2 para produto populacional IBGE; D3 para manutenção e URIs; D4 para tipos e visão CNES; D5 para reprocessamento/proveniência e eventual exclusividade entre processos; D6 para memória e desempenho. Não incorporar essas frentes durante a execução desta entrega sem rever seu escopo.
