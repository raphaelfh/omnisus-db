"""Frictionless Table Schema YAML loader."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from typing import Any

import pyarrow as pa
import yaml

# Frictionless type → Arrow type
_TYPE_MAP: dict[str, pa.DataType] = {
    "string": pa.string(),
    "integer": pa.int64(),
    "number": pa.float64(),
    "boolean": pa.bool_(),
    "date": pa.date32(),
    "datetime": pa.timestamp("us"),
    "year": pa.uint16(),
    "yearmonth": pa.string(),
}


@dataclass(frozen=True)
class Dicionario:
    """Loaded Frictionless schema with omnisus extensions."""

    name: str
    title: str
    encoding: str
    fields: list[dict[str, Any]]
    primary_key: list[str]
    partitions: list[str]
    source_format: str
    version: str
    raw: dict[str, Any]

    @property
    def arrow_schema(self) -> pa.Schema:
        return pa.schema([(f["name"], _TYPE_MAP.get(f["type"], pa.string())) for f in self.fields])

    def decode(self, field: str, value: Any) -> Any:
        for f in self.fields:
            if f["name"] == field and "x-decode" in f:
                return f["x-decode"].get(value, value)
        return value


@cache
def load_dicionario(name: str) -> Dicionario:
    """Load and cache a Dicionario by dataset name (e.g., 'sim_do')."""
    yaml_path = files("omnisus_db.data.dicionarios") / f"{name}.yaml"
    if not yaml_path.is_file():
        raise FileNotFoundError(f"dicionario not found: {name}")
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    schema = raw.get("schema", {})
    return Dicionario(
        name=raw["name"],
        title=raw.get("title", raw["name"]),
        encoding=raw.get("encoding", "utf-8"),
        fields=schema.get("fields", []),
        primary_key=schema.get("primaryKey", []),
        partitions=raw.get("x-partitions", []),
        source_format=raw.get("x-source-format", ""),
        version=raw.get("x-version", "0.0.0"),
        raw=raw,
    )
