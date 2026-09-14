"""Finite age semantics shared by display and native DuckDB projections.

Rules come from packaged metadata. This module does not infer a rule from a
column's name, numeric type, dates, or observed distribution.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from omnisus_db.lake.sql import quote_literal

_INTEGER_MAX = 2_147_483_647
# Match Python's whitespace stripping in DuckDB, including padded DBF strings.
# chr() keeps generated SQL free of literal line/control characters, so saving
# or formatting an audit query cannot silently alter the trimming semantics.
_SQL_WHITESPACE = " || ".join(
    f"chr({ord(char)})"
    for char in " \t\n\r\v\f\x1c\x1d\x1e\x1f\x85\xa0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000"
)
_LABELS = {
    "minute": ("minuto", "minutos"),
    "hour": ("hora", "horas"),
    "day": ("dia", "dias"),
    "month": ("mês", "meses"),
    "year": ("ano", "anos"),
}


@dataclass(frozen=True)
class Age:
    """Interpreted source quantity and unit, with nullable completed years."""

    value: int | None
    unit: str | None
    years_completed: int | None
    status: str
    under_one_year: bool = False

    def display(self) -> str | None:
        """Return a Portuguese label, or None when callers should keep raw data."""
        if self.status == "ignored":
            return "Ignorada"
        if self.status != "valid":
            return None
        if self.under_one_year:
            return "Menor de 1 ano"
        quantity = self.years_completed if self.unit == "year" else self.value
        singular, plural = _LABELS[self.unit]  # type: ignore[index]
        return f"{quantity} {singular if quantity == 1 else plural}"


def _units(rule: Mapping[str, Any]) -> Mapping[str, Any]:
    if rule["kind"] not in ("sim", "sih"):
        raise ValueError(f"Unsupported age rule kind: {rule['kind']!r}")
    return rule["units"]  # type: ignore[no-any-return]


def _maximum(rule: Mapping[str, Any], definition: Mapping[str, Any]) -> int:
    offset = int(definition.get("offset", 0))
    maximum = definition.get("maximum_value", rule.get("maximum_value"))
    if maximum is None:
        # SIM's two quantity digits establish a finite domain. For other
        # encodings, subyear conversion requires an explicitly known domain.
        if rule["kind"] == "sim":
            maximum = 99
        elif definition["unit"] != "year":
            return -1
        else:
            maximum = _INTEGER_MAX
    if definition["unit"] in ("minute", "hour", "day"):
        maximum = min(int(maximum), 99)
    return min(int(maximum), _INTEGER_MAX - offset)


def _minimum(rule: Mapping[str, Any], definition: Mapping[str, Any]) -> int:
    return max(0, int(definition.get("minimum_value", rule.get("minimum_value", 0))))


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def decode_age(rule: Mapping[str, Any], value: Any, unit: Any = None) -> Age:
    """Decode a declared SIM or SIH age without truncation.

    Missing and malformed required inputs are checked before sentinels. Numeric
    values outside the declared domain are unsupported, never guessed as ages.
    """
    units = _units(rule)
    raw = _text(value)
    code = raw[:1] if rule["kind"] == "sim" else _text(unit)
    if not raw or (rule["kind"] == "sih" and not code):
        return Age(None, None, None, "missing")
    pattern = r"[0-9]{3}" if rule["kind"] == "sim" else r"[0-9]+"
    if not re.fullmatch(pattern, raw) or (
        rule["kind"] == "sih" and not re.fullmatch(r"[0-9]+", code)
    ):
        return Age(None, None, None, "invalid")
    definition = units.get(code)
    digits = (raw[1:] if rule["kind"] == "sim" else raw).lstrip("0") or "0"
    # Avoid Python's arbitrary-string integer limit and keep SQL INTEGER parity.
    quantity = int(digits) if len(digits) <= 10 else None
    if (
        rule["kind"] == "sih"
        and quantity is not None
        and quantity <= 99
        and f"{code}{quantity:02d}" in rule.get("invalid_composites", ())
    ):
        return Age(quantity, None, None, "invalid")
    if raw in rule.get("ignored_values", ()) or code in rule.get("ignored_units", ()):
        return Age(None, None, None, "ignored")
    if definition is None or definition["unit"] not in _LABELS:
        return Age(quantity, None, None, "unsupported")
    interpreted_unit = definition["unit"]
    if quantity is None or not _minimum(rule, definition) <= quantity <= _maximum(
        rule, definition
    ):
        return Age(quantity, interpreted_unit, None, "unsupported")
    if interpreted_unit == "year":
        years = quantity + int(definition.get("offset", 0))
    elif interpreted_unit == "month":
        years = quantity // 12
    else:
        years = 0
    return Age(quantity, interpreted_unit, years, "valid", raw in rule.get("under_one_year", ()))


def _sql_text(expression: str) -> str:
    return f"trim(CAST(({expression}) AS VARCHAR), ({_SQL_WHITESPACE}))"


def _in(expression: str, values: Any) -> str:
    literals = ", ".join(quote_literal(str(value)) for value in values)
    return f"{expression} IN ({literals})" if literals else "FALSE"


def age_expressions(
    rule: Mapping[str, Any], value_sql: str, unit_sql: str | None = None
) -> tuple[str, str]:
    """Return completed-years and status SQL, evaluated natively by DuckDB.

    The caller supplies escaped column expressions and verifies applicability.
    Rule values are quoted as SQL literals; this function installs no UDFs.
    """
    units = _units(rule)
    raw = _sql_text(value_sql)
    kind = rule["kind"]
    code = f"substring({raw}, 1, 1)" if kind == "sim" else _sql_text(unit_sql or "NULL")
    missing = f"({raw} IS NULL OR {raw} = '')"
    pattern = "[0-9]{3}" if kind == "sim" else "[0-9]+"
    invalid = f"NOT regexp_full_match({raw}, '{pattern}')"
    if kind == "sih":
        missing += f" OR ({code} IS NULL OR {code} = '')"
        invalid += f" OR NOT regexp_full_match({code}, '[0-9]+')"
    ignored = f"({_in(raw, rule.get('ignored_values', ()))}) OR ({_in(code, rule.get('ignored_units', ()))})"
    digits = f"substring({raw}, 2, 2)" if kind == "sim" else raw
    quantity = f"TRY_CAST({digits} AS BIGINT)"
    if kind == "sih" and rule.get("invalid_composites"):
        composite = f"({code} || lpad(CAST({quantity} AS VARCHAR), 2, '0'))"
        invalid += (
            f" OR ({quantity} BETWEEN 0 AND 99 AND {_in(composite, rule['invalid_composites'])})"
        )
    status_parts = [
        f"WHEN {missing} THEN 'missing'",
        f"WHEN {invalid} THEN 'invalid'",
        f"WHEN {ignored} THEN 'ignored'",
    ]
    years_parts = []
    for unit_code, definition in units.items():
        if definition["unit"] not in _LABELS:
            continue
        valid = f"({code} = {quote_literal(str(unit_code))} AND {quantity} BETWEEN {_minimum(rule, definition)} AND {_maximum(rule, definition)})"
        status_parts.append(f"WHEN {valid} THEN 'valid'")
        if definition["unit"] == "year":
            result = f"({quantity} + {int(definition.get('offset', 0))})"
        elif definition["unit"] == "month":
            result = f"({quantity} // 12)"
        else:
            result = "0"
        years_parts.append(f"WHEN {valid} THEN {result}")
    status = "CASE " + " ".join(status_parts) + " ELSE 'unsupported' END"
    # The first guards are essential: TRY_CAST accepts fractional strings and
    # sentinels may overlap a valid unit domain.
    guards = f"WHEN ({missing}) OR ({invalid}) OR ({ignored}) THEN NULL"
    years = f"CAST(CASE {guards} {' '.join(years_parts)} ELSE NULL END AS INTEGER)"
    return years, status
