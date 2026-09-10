"""Physical schemas and bounded, textual samples; no clinical recoding."""

from __future__ import annotations

import csv
import io
import tempfile
import zipfile
from itertools import islice
from pathlib import Path, PurePosixPath

import datasus_dbc
import polars as pl
from dbfread2 import DBF

MAX_EXPANDED_BYTES = 512 * 1024**2
MAX_MEMBERS = 5000


def read_dbf(payload: bytes, directory: Path, *, limit: int = 200):
    """Validate physical rows; preserve raw code/date strings in the sample."""
    if limit < 1:
        raise ValueError("limite de linhas deve ser positivo")
    if len(payload) < 32:
        raise ValueError("DBF truncado: cabeçalho ausente")
    declared = int.from_bytes(payload[4:8], "little")
    header = int.from_bytes(payload[8:10], "little")
    width = int.from_bytes(payload[10:12], "little")
    expected = header + declared * width
    if header < 33 or width < 1 or expected > MAX_EXPANDED_BYTES:
        raise ValueError("geometria DBF inválida ou acima do limite")
    if len(payload) < expected:
        raise ValueError(f"DBF truncado: {len(payload)} bytes, esperados {expected}")
    flags = payload[header:expected:width]
    deleted = flags.count(42)
    if flags.count(32) + deleted != declared:
        raise ValueError("DBF contém marcadores de registro inválidos")
    repaired = payload[header - 1] != 13
    if repaired:
        # DATASUS sometimes leaves a null in the field-descriptor terminator.
        payload = payload[: header - 1] + b"\r" + payload[header:]
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=directory, suffix=".dbf") as tmp:
        tmp.write(payload)
        tmp.flush()
        table = DBF(tmp.name, encoding="latin-1", keep_raw=True, ignore_missing_memo=True)
        columns = [
            {
                "nome": f.name,
                "tipo_origem": f.type,
                "largura": f.length,
                "decimais": f.decimal_count,
                "tipo_amostra": "String",
            }
            for f in table.fields
        ]
        rows = []
        for record in islice(table, limit):
            rows.append({k: v.decode("latin-1").strip(" \x00") or None for k, v in record.items()})
    frame = pl.DataFrame(rows, schema={c["nome"]: pl.String for c in columns})
    if frame.height != min(limit, declared - deleted):
        raise ValueError("DBF terminou antes da amostra esperada")
    for col in columns:
        series = frame[col["nome"]]
        col["nulos_amostra"] = series.null_count()
        col["distintos_amostra"] = series.n_unique()
    return {
        "formato": "DBF",
        "registros_declarados": declared,
        "registros_ativos": declared - deleted,
        "registros_excluidos": deleted,
        "terminador_reparado": repaired,
        "colunas": columns,
    }, frame


def read_csv(payload: bytes, *, limit: int):
    try:
        text = payload.decode("utf-8-sig")
        encoding = "utf-8-sig"
    except UnicodeDecodeError:
        text, encoding = payload.decode("latin-1"), "latin-1"
    dialect = csv.Sniffer().sniff(text[:8192], delimiters=";,\t|")
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    rows = list(islice(reader, limit))
    names = reader.fieldnames
    if not names or len(set(names)) != len(names) or any(None in r for r in rows):
        raise ValueError("cabeçalho CSV inválido ou linha com campos extras")
    frame = pl.DataFrame(rows, schema={n: pl.String for n in names})
    columns = [
        {
            "nome": n,
            "tipo_origem": "texto CSV",
            "largura": None,
            "decimais": None,
            "tipo_amostra": "String",
            "nulos_amostra": frame[n].null_count(),
            "distintos_amostra": frame[n].n_unique(),
        }
        for n in names
    ]
    return {
        "formato": "CSV",
        "encoding": encoding,
        "colunas": columns,
        "registros_declarados": None,
        "registros_ativos": None,
        "registros_excluidos": None,
    }, frame


def inspect_file(source: Path, output: Path, *, limit: int = 200) -> dict:
    """Read ZIP members in memory; never unpack executable or arbitrary paths."""
    output.mkdir(parents=True, exist_ok=True)
    result = {"tabelas": [], "membros": [], "documentos": []}

    def inspect_payload(name, payload):
        ext = PurePosixPath(name).suffix.lower()
        if ext == ".dbc":
            # DBC retains the initial DBF geometry. Bound expansion before decoding.
            if len(payload) < 32:
                raise ValueError("DBC sem cabeçalho")
            predicted = int.from_bytes(payload[4:8], "little") * int.from_bytes(
                payload[10:12], "little"
            )
            if predicted > MAX_EXPANDED_BYTES:
                raise ValueError("DBC excede limite de expansão")
            payload = datasus_dbc.decompress_bytes(payload)
            ext = ".dbf"
        if len(payload) > MAX_EXPANDED_BYTES:
            raise ValueError("arquivo excede limite de expansão")
        if ext not in {".dbf", ".csv"}:
            if ext in {".txt", ".md"}:
                result["documentos"].append(
                    {
                        "arquivo": name,
                        "trecho": payload[:6000].decode("latin-1"),
                        "bytes": len(payload),
                    }
                )
            return
        metadata, frame = (
            read_dbf(payload, output, limit=limit)
            if ext == ".dbf"
            else read_csv(payload, limit=limit)
        )
        table_id = f"t{len(result['tabelas']):03d}_{PurePosixPath(name).stem}"
        sample = output / f"{table_id}.parquet"
        frame.write_parquet(sample)
        frame.write_csv(output / f"{table_id}.csv")
        result["tabelas"].append(
            {
                **metadata,
                "tabela": table_id,
                "membro": name,
                "amostra_parquet": str(sample.resolve()),
                "linhas_amostra": frame.height,
                "n_colunas": frame.width,
            }
        )

    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as archive:
            entries = archive.infolist()
            if (
                len(entries) > MAX_MEMBERS
                or sum(e.file_size for e in entries) > MAX_EXPANDED_BYTES
            ):
                raise ValueError("ZIP excede limite de membros/expansão")
            # Several territorial tables appear in DBF/CSV/XML/TXT: use DBF once.
            dbf_stems = {
                str(PurePosixPath(e.filename).with_suffix("")).lower()
                for e in entries
                if e.filename.lower().endswith(".dbf")
            }
            for entry in entries:
                path = PurePosixPath(entry.filename.replace("\\", "/"))
                if path.is_absolute() or ".." in path.parts or ":" in entry.filename:
                    raise ValueError("ZIP contém caminho inválido")
                result["membros"].append(
                    {
                        "arquivo": entry.filename,
                        "bytes": entry.file_size,
                        "comprimidos": entry.compress_size,
                        "diretorio": entry.is_dir(),
                    }
                )
                if entry.is_dir():
                    continue
                ext = path.suffix.lower()
                if ext == ".csv" and str(path.with_suffix("")).lower() in dbf_stems:
                    continue
                if ext in {".dbf", ".dbc", ".csv", ".txt", ".md"}:
                    inspect_payload(entry.filename, archive.read(entry))
    else:
        inspect_payload(source.name, source.read_bytes())
    return result
