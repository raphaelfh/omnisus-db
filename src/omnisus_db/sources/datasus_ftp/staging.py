"""Bounded record staging; DBC decompression still materializes the entire DBF.

Each batch is spooled to Arrow IPC so null-first and absent columns can be
reconciled before a second, bounded pass writes Parquet. Peak disk includes
DBF, IPC and Parquet; no list of frames or lazy references to deleted files.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from omnisus_db.sources.datasus_ftp.datasets import Release
from omnisus_db.sources.datasus_ftp.dbf_batches import open_dbf_batches
from omnisus_db.transforms.dictionaries import load_dicionario


@dataclass(frozen=True)
class StagingResult:
    rows: int
    bytes: int


def _merge_schema(existing: pa.Schema, incoming: pa.Schema) -> pa.Schema:
    fields = {field.name: field for field in existing}
    for field in incoming:
        previous = fields.get(field.name)
        if previous is None or pa.types.is_null(previous.type):
            fields[field.name] = field
        elif pa.types.is_null(field.type) or previous.type == field.type:
            continue
        elif pa.types.is_signed_integer(previous.type) and pa.types.is_signed_integer(field.type):
            fields[field.name] = pa.field(field.name, pa.int64())
        elif pa.types.is_unsigned_integer(previous.type) and pa.types.is_unsigned_integer(
            field.type
        ):
            fields[field.name] = pa.field(field.name, pa.uint64())
        elif pa.types.is_floating(previous.type) and pa.types.is_floating(field.type):
            fields[field.name] = pa.field(field.name, pa.float64())
        else:
            raise TypeError(
                f"Incompatible batch types for {field.name}: {previous.type} / {field.type}"
            )
    return pa.schema(list(fields.values()))


def dbc_bytes_to_parquet(
    raw: bytes,
    path: Path | str,
    *,
    dataset: str,
    ano: int | None = None,
    uf: str | None = None,
    dictionary: Path | None = None,
    mes: int | None = None,
    source_ano: int | None = None,
    release: Release | None = None,
) -> StagingResult:
    """Validate and stage records atomically; leave existing target intact on error.

    Memory is bounded by the compressed payload, full decompressed DBF, and a
    record batch (not by all parsed frames). IPC spool trades extra disk I/O for
    lossless schema reconciliation. Caller owns the resulting Parquet lifetime.
    """
    from omnisus_db.sources.datasus_ftp import parse

    dic = load_dicionario(dictionary if dictionary is not None else dataset)
    dbf_bytes = parse.datasus_dbc.decompress_bytes(raw)
    parse._check_dbf_length(dbf_bytes, dataset=dataset)
    path = Path(path)
    parsed = 0
    batches = 0
    schema = pa.schema([])
    with tempfile.TemporaryDirectory(prefix=".dbc-stage-", dir=path.parent) as directory:
        root = Path(directory)

        def spool(batch: pa.RecordBatch) -> None:
            nonlocal batches, schema
            table = pa.Table.from_batches([batch])
            lowered = [name.lower() for name in table.column_names]
            if len(set(lowered)) != len(lowered):
                raise ValueError("DBF column names collide after lowercasing")
            table = table.rename_columns(lowered)
            if "_source_ano" in lowered:
                raise ValueError("DBF uses reserved source column _source_ano")
            if "_source_release" in lowered:
                raise ValueError("DBF uses reserved source column _source_release")
            for name, value, dtype in [
                ("ano", ano, pa.uint16()),
                ("uf", uf, pa.string()),
                ("mes", mes, pa.uint8()),
                ("_source_ano", source_ano, pa.uint16()),
                ("_source_release", release, pa.string()),
            ]:
                if value is not None:
                    column = pa.array([value] * len(table), type=dtype, safe=True)
                    index = table.schema.get_field_index(name)
                    table = (
                        table.set_column(index, name, column)
                        if index >= 0
                        else table.append_column(name, column)
                    )
            schema = _merge_schema(schema, table.schema)
            with (
                pa.OSFile(str(root / f"{batches}.arrow"), "wb") as sink,
                pa.ipc.new_file(sink, table.schema) as writer,
            ):
                writer.write_table(table)
            batches += 1

        with open_dbf_batches(
            dbf_bytes, encoding=dic.encoding, batch_rows=parse.BATCH_ROWS
        ) as stream:
            for batch in stream:
                parsed += batch.num_rows
                spool(batch)
        parse._check_record_count(dbf_bytes, parsed, dataset=dataset)
        del dbf_bytes
        if not batches:
            schema = pa.schema([(field["name"].lower(), pa.string()) for field in dic.fields])
            for name, value, dtype in [
                ("ano", ano, pa.uint16()),
                ("uf", uf, pa.string()),
                ("mes", mes, pa.uint8()),
                ("_source_ano", source_ano, pa.uint16()),
                ("_source_release", release, pa.string()),
            ]:
                if value is not None:
                    index = schema.get_field_index(name)
                    field = pa.field(name, dtype)
                    schema = schema.set(index, field) if index >= 0 else schema.append(field)
        output = root / "output.parquet"
        with pq.ParquetWriter(output, schema) as writer:
            for number in range(batches):
                with pa.memory_map(str(root / f"{number}.arrow"), "r") as source:
                    table = pa.ipc.open_file(source).read_all()
                    aligned = pa.Table.from_arrays(
                        [
                            table[field.name].cast(field.type, safe=True)
                            if field.name in table.column_names
                            else pa.nulls(len(table), type=field.type)
                            for field in schema
                        ],
                        schema=schema,
                    )
                    writer.write_table(aligned)
                (root / f"{number}.arrow").unlink()
        size = output.stat().st_size
        os.replace(output, path)
    return StagingResult(rows=parsed, bytes=size)
