"""Frictionless Table Schema YAML loader with display-time decoders.

The dicionarios YAML is the single source of truth for both ETL ingestion
metadata (column types, partitions, foreign keys, ETL ``x-transform`` hints)
*and* display-time decoding used by the Explorer UI.

Display decoding happens via :meth:`Dicionario.decode_row` in three layers,
applied in this order per field:

1. **``x-display``** — named display transform from ``_DISPLAY_TRANSFORMS``
   (e.g. ``time_hhmm``, ``idade_sim``, ``idade_sih``). These can read the full
   row, so cross-field decoders (SIH ``COD_IDADE`` + ``IDADE``) are supported.
2. **``type: date`` + ``x-format``** — date strings reformatted to ``dd/mm/yyyy``.
   Supported source formats: ``ddMMyyyy`` (SIM/SINASC) and ``yyyyMMdd`` (SIH).
3. **``x-decode``** — small enum lookup map. Lookups are *type-tolerant*:
   string keys match int values and vice versa, so YAMLs and the lake
   (which stores VARCHAR) stay decoupled.

Lookup against the ``x-decode`` map is also whitespace-tolerant — DBF/DBC files
often pad codes with spaces.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from pathlib import Path
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


# ---------------------------------------------------------------------------
# Display-time decoders
# ---------------------------------------------------------------------------

_DATE_RE_DDMMYYYY = re.compile(r"^(\d{2})(\d{2})(\d{4})$")
_DATE_RE_YYYYMMDD = re.compile(r"^(\d{4})(\d{2})(\d{2})$")
_TIME_RE_HHMM = re.compile(r"^(\d{2})(\d{2})$")


def _decode_date_ddmmyyyy(value: Any) -> Any:
    """``01012024`` → ``01/01/2024``. Pass-through on mismatch."""
    if value is None:
        return value
    s = str(value).strip()
    if not s:
        return value
    m = _DATE_RE_DDMMYYYY.match(s)
    if not m:
        return value
    dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
    if dd == "00" or mm == "00" or yyyy == "0000":
        return value
    return f"{dd}/{mm}/{yyyy}"


def _decode_date_yyyymmdd(value: Any) -> Any:
    """``20240101`` → ``01/01/2024``. Pass-through on mismatch."""
    if value is None:
        return value
    s = str(value).strip()
    if not s:
        return value
    m = _DATE_RE_YYYYMMDD.match(s)
    if not m:
        return value
    yyyy, mm, dd = m.group(1), m.group(2), m.group(3)
    if dd == "00" or mm == "00" or yyyy == "0000":
        return value
    return f"{dd}/{mm}/{yyyy}"


def _decode_time_hhmm(value: Any) -> Any:
    """``1040`` → ``10:40``. Pass-through on mismatch."""
    if value is None:
        return value
    s = str(value).strip()
    if not s:
        return value
    m = _TIME_RE_HHMM.match(s)
    if not m:
        return value
    return f"{m.group(1)}:{m.group(2)}"


# DATASUS SIM age unit code → (singular, plural). 0/9 = ignored.
_IDADE_SIM_UNITS: dict[str, tuple[str, str]] = {
    "1": ("minuto", "minutos"),
    "2": ("hora", "horas"),
    "3": ("dia", "dias"),
    "4": ("ano", "anos"),
    "5": ("ano", "anos"),  # 5 = 100+ years
}


def _decode_idade_sim(value: Any) -> Any:
    """SIM 3-digit encoded age → human-readable string.

    Encoding: 1st digit = unit, last 2 digits = numeric value.
    ``469`` → ``69 anos``  ·  ``115`` → ``15 minutos``  ·  ``501`` → ``101 anos``.
    """
    if value is None:
        return value
    s = str(value).strip()
    if not s:
        return value
    s = s.zfill(3)
    if len(s) != 3 or not s.isdigit():
        return value
    unit_code = s[0]
    if unit_code in ("0", "9"):
        return "Ignorada"
    try:
        n = int(s[1:])
    except ValueError:
        return value
    if n == 99:
        return "Ignorada"
    unit = _IDADE_SIM_UNITS.get(unit_code)
    if unit is None:
        return value
    if unit_code == "5":
        n += 100
    singular, plural = unit
    return f"{n} {singular if n == 1 else plural}"


# DATASUS SIH age unit code (COD_IDADE) → (singular, plural). 0/9 = ignored.
_IDADE_SIH_UNITS: dict[str, tuple[str, str]] = {
    "2": ("dia", "dias"),
    "3": ("mes", "meses"),
    "4": ("ano", "anos"),
    "5": ("ano", "anos"),  # 5 = 100+ years
}


def _decode_idade_sih(value: Any, row: dict[str, Any]) -> Any:
    """SIH cross-field age decode: reads ``COD_IDADE`` + ``IDADE`` from row.

    ``COD_IDADE=4`` and ``IDADE=35`` → ``35 anos``.
    """
    cod = row.get("cod_idade") if "cod_idade" in row else row.get("COD_IDADE")
    idade = row.get("idade") if "idade" in row else row.get("IDADE")
    if cod is None or idade is None:
        return value
    cod_str = str(cod).strip()
    try:
        n = int(str(idade).strip())
    except (ValueError, TypeError):
        return value
    if cod_str in ("0", "9") or n == 999:
        return "Ignorada"
    unit = _IDADE_SIH_UNITS.get(cod_str)
    if unit is None:
        return str(n)
    if cod_str == "5":
        n += 100
    singular, plural = unit
    return f"{n} {singular if n == 1 else plural}"


# ``x-display`` registry. Each transform takes (value, row) and returns the
# decoded value. Single-value transforms can ignore ``row``.
_DISPLAY_TRANSFORMS: dict[str, Callable[[Any, dict[str, Any]], Any]] = {
    "time_hhmm": lambda v, row: _decode_time_hhmm(v),
    "idade_sim": lambda v, row: _decode_idade_sim(v),
    "idade_sih": _decode_idade_sih,
}

# ``type: date`` + ``x-format`` → decoder
_DATE_FORMAT_DECODERS: dict[str, Callable[[Any], Any]] = {
    "ddMMyyyy": _decode_date_ddmmyyyy,
    "yyyyMMdd": _decode_date_yyyymmdd,
}


def _lookup_decode(decode_map: dict[Any, Any], value: Any) -> Any:
    """Type-tolerant ``x-decode`` lookup.

    The lake stores VARCHAR but YAMLs may declare ``type: integer`` and use
    int keys. Also DBF/DBC sources frequently pad codes with spaces. Try
    several reasonable normalizations before falling back to the original.
    """
    # Direct hit
    if value in decode_map:
        return decode_map[value]
    # String form, stripped
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return value
        if stripped in decode_map:
            return decode_map[stripped]
        if stripped.isdigit():
            try:
                as_int = int(stripped)
                if as_int in decode_map:
                    return decode_map[as_int]
            except ValueError:
                pass
        return value
    # Non-string scalar → try its str form
    s = str(value)
    if s in decode_map:
        return decode_map[s]
    return value


# ---------------------------------------------------------------------------
# Dicionario
# ---------------------------------------------------------------------------


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

    def field_def(self, name: str) -> dict[str, Any] | None:
        """Return the field definition for ``name`` (case-insensitive)."""
        lname = name.lower() if isinstance(name, str) else name
        for f in self.fields:
            if f["name"] == lname:
                return f
        return None

    def decode(self, field: str, value: Any) -> Any:
        """Decode a single value using ``x-decode`` (type-tolerant).

        Date and ``x-display`` transforms are NOT applied here — they need
        row context or are applied uniformly via :meth:`decode_row`.
        Use this for ad-hoc enum lookups; use ``decode_row`` for full rows.
        """
        f = self.field_def(field)
        if f is None or "x-decode" not in f:
            return value
        return _lookup_decode(f["x-decode"], value)

    def decode_row(self, row: dict[str, Any]) -> dict[str, Any]:
        """Apply all known display decoders to a row.

        Per field declared in the dicionario, applies (in order):

        1. ``x-display`` named transform (cross-field aware)
        2. ``type: date`` + ``x-format`` reformatting
        3. ``x-decode`` map lookup

        Row keys not declared in the dicionario are passed through unchanged.
        Lookups are case-tolerant on the row key (``DTOBITO`` and ``dtobito``
        both work), so this can be called on raw DBF dicts or on lake rows.

        Cross-field transforms (e.g. ``idade_sih``, which reads ``cod_idade``
        + ``idade``) always see the *original* row, never partially decoded
        values from earlier fields in the iteration.
        """
        if not row:
            return row
        result = dict(row)
        for f in self.fields:
            name = f["name"]
            row_key = self._row_key_for(row, name)
            if row_key is None:
                continue
            value = row[row_key]
            if value is None:
                continue
            if isinstance(value, str) and value.strip() == "":
                continue
            new_value = self._decode_field(f, value, row)
            if new_value is not value and new_value != value:
                result[row_key] = new_value
        return result

    @staticmethod
    def _row_key_for(row: dict[str, Any], name: str) -> str | None:
        """Resolve the row dict key for a (lowercase) field name."""
        if name in row:
            return name
        upper = name.upper()
        if upper in row:
            return upper
        return None

    @staticmethod
    def _decode_field(f: dict[str, Any], value: Any, row: dict[str, Any]) -> Any:
        # 1) x-display transform takes precedence
        display = f.get("x-display")
        if isinstance(display, str):
            transform = _DISPLAY_TRANSFORMS.get(display)
            if transform is not None:
                return transform(value, row)
        # 2) Date with declared source format
        if f.get("type") == "date":
            fmt = f.get("x-format")
            if isinstance(fmt, str):
                decoder = _DATE_FORMAT_DECODERS.get(fmt)
                if decoder is not None:
                    return decoder(value)
        # 3) x-decode lookup
        decode_map = f.get("x-decode")
        if isinstance(decode_map, dict):
            return _lookup_decode(decode_map, value)
        return value


@cache
def load_dicionario(name_or_path: str | Path) -> Dicionario:
    """Load and cache a Dicionario.

    ``str`` is a dataset name resolved to the packaged
    ``dicionarios/<name>.yaml``. ``Path`` is an explicit YAML file — how an
    ad-hoc dataset supplies its own schema (spec §3.3).
    """
    if isinstance(name_or_path, Path):
        if not name_or_path.is_file():
            raise FileNotFoundError(f"dicionario not found: {name_or_path}")
        text = name_or_path.read_text(encoding="utf-8")
    else:
        yaml_path = files("omnisus_db.data.dicionarios") / f"{name_or_path}.yaml"
        if not yaml_path.is_file():
            raise FileNotFoundError(f"dicionario not found: {name_or_path}")
        text = yaml_path.read_text(encoding="utf-8")
    raw = yaml.safe_load(text)
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
