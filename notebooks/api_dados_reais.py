import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", app_title="omnisus-db · SIM com dados reais")


@app.cell
def _():
    import asyncio
    import hashlib
    import io
    import json
    from dataclasses import asdict
    from datetime import UTC, datetime
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from uuid import uuid4

    import marimo as mo
    import polars as pl

    import omnisus_db as odb

    return (
        Path,
        TemporaryDirectory,
        UTC,
        asdict,
        asyncio,
        datetime,
        hashlib,
        io,
        json,
        mo,
        odb,
        pl,
        uuid4,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # SIM · Roraima, 2022 e 2023 — dados reais

    Este roteiro usa **dois arquivos completos do DATASUS**, importados pela API
    `omnisus-db`. Não usa fixtures nem registros inventados. Ao abrir, reutiliza
    a cópia persistida localmente. O botão abaixo baixa uma **nova cópia** e
    registra uma nova proveniência, sem acrescentar novamente ao lake anterior.

    Cenários: inventário → importação em lote → SQL/Polars → qualidade → filtros
    → agregação → exportação → transação de uma tabela derivada.

    Execute pela raiz do repositório. Na ausência de uma cópia local, clique para
    preparar os dados. Os arquivos ficam em `data/lake/marimo-real/`.
    """)
    return


@app.cell
def _(Path, mo):
    project_root = Path(__file__).resolve().parent.parent
    data_root = project_root / "data/lake/marimo-real"
    download_button = mo.ui.run_button(label="Baixar nova cópia real de RR · 2022-2023")
    download_button
    return data_root, download_button, project_root


@app.cell
def preparation_helpers(UTC, asdict, datetime, json, odb, uuid4):
    def prepare_real_data(data_root, project_root):
        """Download via public API; publish latest.json only after validation."""
        dataset = odb.resolve("sim_do")
        scopes = [
            scope
            for scope in odb.available(dataset, years=[2022, 2023], refresh=True)
            if scope.uf == "RR"
        ]
        expected = odb.scopes_for(dataset, years=[2022, 2023], ufs=["RR"])
        if scopes != expected:
            raise RuntimeError(f"Inventário diferente do esperado: {scopes!r}")
        filenames = {"DORR2022.DBC", "DORR2023.DBC"}
        entries = [
            entry
            for entry in odb.browse(dataset.ftp_dir)
            if entry.name.upper() in filenames and not entry.is_dir
        ]
        if len(entries) != 2:
            raise RuntimeError("Não foi possível registrar os dois arquivos de origem")
        run_dir = data_root / uuid4().hex
        run_dir.mkdir(parents=True)
        target = f"ducklake:{run_dir / 'dados.ducklake'}"
        print(f"Importando para {target}", flush=True)
        started = datetime.now(UTC).isoformat()
        try:
            report = odb.import_dataset(
                dataset, scopes=scopes, target=target, concurrency=1, batch_size=2
            )
        except odb.ImportAbortedError as error:
            (run_dir / "aborted.json").write_text(
                json.dumps(
                    {
                        "report": asdict(error.report),
                        "unresolved": error.unresolved,
                    },
                    default=str,
                    indent=2,
                ),
                encoding="utf-8",
            )
            raise
        (run_dir / "import_report.json").write_text(
            json.dumps(asdict(report), indent=2), encoding="utf-8"
        )
        if report.failed or report.skipped or len(report.ok) != 2:
            raise RuntimeError(f"Importação incompleta; inspecione {run_dir}")
        with odb.Lake.local(target) as lake:
            counts = (
                lake.connect()
                .sql(
                    "SELECT ano, uf, count(*) AS registros FROM lake.sim_do "
                    "GROUP BY ano, uf ORDER BY ano, uf"
                )
                .pl()
                .to_dicts()
            )
            actual = {(row["uf"], row["ano"]): row["registros"] for row in counts}
            for outcome in report.ok:
                if actual.get((outcome.scope.uf, outcome.scope.ano)) != outcome.result.rows:
                    raise RuntimeError("Contagem persistida diverge do relatório")
            if sum(actual.values()) != report.rows or report.rows == 0:
                raise RuntimeError("Total persistido inesperado")
            snapshots = lake.snapshots()
        manifest = {
            "dataset": dataset.name,
            "started_at_utc": started,
            "completed_at_utc": datetime.now(UTC).isoformat(),
            "library_version": odb.__version__,
            "run_relative": str(run_dir.relative_to(project_root)),
            "source_directory": dataset.ftp_dir,
            "source_files": [
                {
                    "name": entry.name,
                    "bytes_in_listing": entry.size_bytes,
                    "modified_in_listing": str(entry.modified),
                    "url": f"ftp://ftp.datasus.gov.br{entry.path}",
                }
                for entry in entries
            ],
            "scopes": [asdict(scope) for scope in scopes],
            "report": asdict(report),
            "counts": counts,
            "snapshots": snapshots,
        }
        encoded = json.dumps(manifest, ensure_ascii=False, indent=2)
        (run_dir / "manifest.json").write_text(encoded, encoding="utf-8")
        # Each writer has its own temp file; only the latest pointer is replaced.
        temporary_pointer = data_root / f"latest-{uuid4().hex}.tmp"
        temporary_pointer.write_text(encoded, encoding="utf-8")
        temporary_pointer.replace(data_root / "latest.json")
        return manifest

    return (prepare_real_data,)


@app.cell
async def load_real_data(
    asyncio,
    data_root,
    download_button,
    json,
    mo,
    prepare_real_data,
    project_root,
):
    if download_button.value:
        mo.output.append(
            mo.md(
                "Consultando o FTP e importando dois escopos. O destino aparece no log. "
                "Interromper a célula pode não encerrar a thread; aguarde antes de tentar novamente."
            )
        )
        manifest = await asyncio.to_thread(prepare_real_data, data_root, project_root)
    else:
        mo.stop(
            not (data_root / "latest.json").exists(),
            mo.md("Clique em **Baixar nova cópia** para começar."),
        )
        manifest = json.loads((data_root / "latest.json").read_text(encoding="utf-8"))
    real_directory = (project_root / manifest["run_relative"]).resolve()
    mo.stop(
        not (real_directory / "dados-catalog.sqlite").exists(),
        mo.md("Catálogo local ausente. Baixe uma nova cópia."),
    )
    real_target = f"ducklake:{real_directory / 'dados.ducklake'}"
    mo.vstack(
        [
            mo.md(
                f"**Extração concluída:** {manifest['completed_at_utc']} · **Destino:** `{real_target}`"
            ),
            mo.ui.table(manifest["source_files"], label="Proveniência: inventário FTP real"),
            mo.ui.table(
                manifest["counts"], label="Contagens persistidas e reconciliadas com ImportReport"
            ),
        ]
    )
    return manifest, real_target


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1 · Conferir o resultado da importação

    Foram pedidos dois escopos anuais, com `concurrency=1` e `batch_size=2`.
    O `ImportReport` abaixo vem da execução real registrada no manifesto.
    `bytes_written` mede o Parquet de staging, não o DBC nem o crescimento final
    do lake. As datas `modified_in_listing` vêm do FTP, sem fuso informado.
    """)
    return


@app.cell
def _(manifest, mo):
    mo.vstack(
        [
            mo.ui.table(
                [
                    {
                        "escopo": f"{outcome['scope']['uf']}/{outcome['scope']['ano']}",
                        "status": outcome["status"],
                        **(outcome["result"] or {}),
                        "motivo": outcome["reason"],
                    }
                    for outcome in manifest["report"]["outcomes"]
                ]
            ),
            mo.ui.table(manifest["snapshots"], label="Snapshots registrados após a importação"),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2 · Consultar e interpretar os campos

    A biblioteca preserva vários campos DBF como texto. O SQL converte `dtobito`
    com `TRY_STRPTIME`, mantendo datas inválidas como `NULL`. `ano` e `uf` vêm do
    escopo solicitado; `codmunres` informa residência e `codmunocor`, ocorrência.
    `tipobito` distingue fetal e não fetal. Não convertemos `idade` diretamente
    em anos: esse campo usa codificação própria.

    Referências: [dicionário oficial SIM](https://svs.aids.gov.br/download/Dicionario_de_Dados_SIM_tabela_DO.pdf)
    e [transferência de arquivos DATASUS](https://datasus.saude.gov.br/transferencia-de-arquivos/).
    """)
    return


@app.cell
def read_real_lake(manifest, odb, real_target):
    with odb.Lake.local(real_target) as _lake:
        assert _lake.snapshots() == manifest["snapshots"], (
            "Histórico do lake alterado desde a extração; prepare nova cópia antes de analisar"
        )
        real_schema = _lake.connect().sql("DESCRIBE lake.sim_do").pl()
        real_data = (
            _lake.connect()
            .sql("""
            SELECT ano AS ano_arquivo, uf AS uf_arquivo,
                NULLIF(trim(cast(dtobito AS VARCHAR)), '') AS dtobito_original,
                TRY_STRPTIME(NULLIF(trim(cast(dtobito AS VARCHAR)), ''), '%d%m%Y')::DATE AS data_obito,
                NULLIF(trim(cast(sexo AS VARCHAR)), '') AS sexo_codigo,
                CASE upper(trim(cast(sexo AS VARCHAR)))
                    WHEN '1' THEN 'Masculino' WHEN 'M' THEN 'Masculino'
                    WHEN '2' THEN 'Feminino' WHEN 'F' THEN 'Feminino'
                    WHEN '0' THEN 'Ignorado' WHEN '9' THEN 'Ignorado'
                    WHEN 'I' THEN 'Ignorado' ELSE 'Ausente/outro' END AS sexo,
                CASE trim(cast(tipobito AS VARCHAR)) WHEN '1' THEN 'Fetal'
                    WHEN '2' THEN 'Não fetal' ELSE 'Ausente/outro' END AS tipo_obito,
                NULLIF(trim(cast(codmunres AS VARCHAR)), '') AS municipio_residencia,
                NULLIF(trim(cast(codmunocor AS VARCHAR)), '') AS municipio_ocorrencia,
                NULLIF(upper(trim(cast(causabas AS VARCHAR))), '') AS causa_basica,
                NULLIF(trim(cast(idade AS VARCHAR)), '') AS idade_codificada
            FROM lake.sim_do
            ORDER BY ano, dtobito, codmunres, causabas, sexo
        """)
            .pl()
        )
        current_counts = (
            _lake.connect()
            .sql(
                "SELECT ano, uf, count(*) AS registros FROM lake.sim_do GROUP BY ano, uf ORDER BY ano, uf"
            )
            .pl()
            .to_dicts()
        )
    assert current_counts == manifest["counts"], (
        "Lake alterado desde a extração; confira antes de analisar"
    )
    assert real_data.height == sum(row["registros"] for row in current_counts)
    return real_data, real_schema


@app.cell
def _(mo, real_schema):
    mo.ui.table(
        real_schema, label="Esquema efetivamente armazenado, antes das conversões analíticas"
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 3 · Verificar qualidade antes de filtrar
    """)
    return


@app.cell
def _(mo, pl, real_data):
    quality = (
        real_data.group_by("ano_arquivo")
        .agg(
            pl.len().alias("registros"),
            pl.col("dtobito_original").is_null().sum().alias("data_ausente"),
            (pl.col("dtobito_original").is_not_null() & pl.col("data_obito").is_null())
            .sum()
            .alias("data_invalida"),
            (pl.col("data_obito").dt.year() != pl.col("ano_arquivo"))
            .fill_null(False)
            .sum()
            .alias("ano_divergente"),
            pl.col("causa_basica").is_null().sum().alias("causa_ausente"),
            pl.col("municipio_residencia").is_null().sum().alias("municipio_ausente"),
            (pl.col("sexo") == "Ausente/outro").sum().alias("sexo_ausente_ou_outro"),
            (pl.col("sexo") == "Ignorado").sum().alias("sexo_ignorado"),
        )
        .sort("ano_arquivo")
    )
    mo.ui.table(quality, label="Contagens de qualidade, calculadas sobre todos os registros")
    return


@app.cell
def _(mo):
    year_filter = mo.ui.dropdown(["Todos", "2022", "2023"], value="Todos", label="Ano do arquivo")
    type_filter = mo.ui.dropdown(
        ["Todos", "Não fetal", "Fetal", "Ausente/outro"], value="Todos", label="Tipo de óbito"
    )
    residency_filter = mo.ui.checkbox(
        value=False, label="Somente município de residência com prefixo 14 (RR)"
    )
    mo.hstack([year_filter, type_filter, residency_filter], wrap=True)
    return residency_filter, type_filter, year_filter


@app.cell
def filter_real_data(
    pl,
    real_data,
    residency_filter,
    type_filter,
    year_filter,
):
    filtered = real_data
    if year_filter.value != "Todos":
        filtered = filtered.filter(pl.col("ano_arquivo") == int(year_filter.value))
    if type_filter.value != "Todos":
        filtered = filtered.filter(pl.col("tipo_obito") == type_filter.value)
    if residency_filter.value:
        filtered = filtered.filter(pl.col("municipio_residencia").str.starts_with("14"))
    return (filtered,)


@app.cell(hide_code=True)
def _(filtered, mo):
    mo.md(f"""
    ## 4 · Explorar {filtered.height:,} registros selecionados

    As tabelas seguintes respondem aos filtros acima. São contagens dos registros
    encontrados nos arquivos importados; não representam taxas, pessoas únicas ou
    garantia de completude de uma população. O filtro por residência não procura
    registros de RR em arquivos de outras UFs. Não usamos o importador IBGE como
    denominador, pois sua seleção de origem ainda requer correção.
    """)
    return


@app.cell
def _(filtered, mo, pl):
    annual_summary = (
        filtered.group_by("ano_arquivo", "sexo", "tipo_obito")
        .agg(pl.len().alias("registros"))
        .sort("ano_arquivo", "sexo", "tipo_obito")
    )
    month_summary = (
        filtered.with_columns(
            pl.col("data_obito")
            .dt.strftime("%Y-%m")
            .fill_null("Sem data válida")
            .alias("mes_obito")
        )
        .group_by("ano_arquivo", "mes_obito")
        .agg(pl.len().alias("registros"))
        .sort("ano_arquivo", "mes_obito")
    )
    municipality_summary = (
        filtered.with_columns(pl.col("municipio_residencia").fill_null("Ausente"))
        .group_by("municipio_residencia")
        .agg(pl.len().alias("registros"))
        .sort("registros", descending=True)
    )
    cause_summary = (
        filtered.with_columns(
            pl.col("causa_basica").str.slice(0, 3).fill_null("Ausente").alias("categoria_cid10")
        )
        .group_by("categoria_cid10")
        .agg(pl.len().alias("registros"))
        .sort("registros", descending=True)
    )
    assert annual_summary["registros"].sum() == filtered.height
    assert month_summary["registros"].sum() == filtered.height
    mo.ui.tabs(
        {
            "Ano, sexo e tipo": mo.ui.table(annual_summary),
            "Mês do óbito": mo.ui.table(month_summary),
            "Município de residência": mo.ui.table(municipality_summary),
            "Categoria CID-10 (3 caracteres)": mo.ui.table(cause_summary),
            "Amostra dos dados reais": mo.ui.table(filtered.head(50)),
        }
    )
    return (annual_summary,)


@app.cell
def _(annual_summary, hashlib, io, mo):
    _buffer = io.BytesIO()
    annual_summary.write_parquet(_buffer)
    summary_parquet = _buffer.getvalue()
    summary_sha256 = hashlib.sha256(summary_parquet).hexdigest()
    mo.vstack(
        [
            mo.md("## 5 · Exportar a agregação selecionada"),
            mo.download(summary_parquet, filename="sim_rr_resumo.parquet", label="Baixar Parquet"),
            mo.download(
                annual_summary.write_csv().encode(),
                filename="sim_rr_resumo.csv",
                label="Baixar CSV",
            ),
            mo.md(
                f"SHA-256 do **Parquet derivado**: `{summary_sha256}`. Este não é o hash dos DBC originais."
            ),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 6 · Transação de uma tabela derivada real

    Copiamos a agregação selecionada para um lake temporário. A primeira transação
    confirma a tabela; a segunda tenta acrescentar a mesma agregação e lança um
    erro proposital para demonstrar rollback. **Os dados são reais; o erro é
    induzido para ensinar o contrato.** O lake de origem não é alterado.
    """)
    return


@app.cell
def derived_transaction(Path, TemporaryDirectory, annual_summary, mo, odb):
    mo.stop(
        annual_summary.is_empty(),
        mo.md("Seleção vazia: altere os filtros para testar a transação."),
    )
    with (
        TemporaryDirectory(prefix="omnisus-real-derived-") as _temporary,
        odb.Lake.local(f"ducklake:{Path(_temporary) / 'derived.ducklake'}") as _lake,
    ):
        with _lake.transaction() as _receipt:
            _result = _lake.ingest("resumo_sim", annual_summary.lazy())
            assert _result.snapshot_id is None
        assert _receipt.committed
        _before = _lake.snapshots()
        _rollback_signal = ValueError("Rollback demonstrativo: não publicar a repetição")
        try:
            with _lake.transaction():
                _lake.ingest("resumo_sim", annual_summary.lazy())
                raise _rollback_signal
        except ValueError as _error:
            assert _error is _rollback_signal
        _rows = _lake.connect().sql("SELECT count(*) FROM lake.resumo_sim").fetchone()[0]
        assert _rows == annual_summary.height
        assert _lake.snapshots() == _before
        transaction_evidence = {
            "committed": _receipt.committed,
            "snapshot_id": _receipt.snapshot_id,
            "linhas_derivadas": _rows,
            "rollback_sem_duplicacao": True,
        }
    mo.json(transaction_evidence)
    return


if __name__ == "__main__":
    app.run()
