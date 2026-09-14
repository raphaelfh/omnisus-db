"""Finite native SQL projections over an explicitly identified source snapshot."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from omnisus_db.lake.publication import scope_from_fields
from omnisus_db.lake.sql import quote_identifier, quote_literal
from omnisus_db.metadata import describe_dataset
from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.datasets import release_from_uri
from omnisus_db.transforms.age import age_expressions


@dataclass(frozen=True)
class SourceContext:
    """Source identity, read from the same snapshot as the queried records."""

    scope: ScopeKey
    release: str | None = None
    source_sha256: str | None = None

    @classmethod
    def from_publication(cls, row: Mapping[str, Any]) -> SourceContext:
        try:
            fields = json.loads(row["scope_json"])
            if not isinstance(fields, dict):
                raise ValueError("Publication scope must be an object")
            scope = scope_from_fields(fields)
            if scope is None:
                raise ValueError("Publication has no supported scope")
            return cls(
                scope,
                release_from_uri(row["dataset"], row.get("source_uri")),
                row.get("source_sha256"),
            )
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Incomplete publication identity") from exc


@dataclass(frozen=True)
class DerivedColumn:
    name: str
    sql_type: str
    expression: str


@dataclass(frozen=True)
class UnavailableField:
    field: str
    reason: str


@dataclass(frozen=True)
class AnalyticalProjection:
    columns: tuple[DerivedColumn, ...]
    unavailable: tuple[UnavailableField, ...]
    rule_version: str | None
    metadata_hash: str


def _confirmed(contexts: Sequence[SourceContext], validated: Sequence[dict[str, Any]]) -> bool:
    return bool(contexts) and all(
        any(
            context.scope == ScopeKey(uf=source["uf"], ano=source["ano"], mes=source.get("mes"))
            and context.release == source["release"]
            and context.source_sha256 == source["source_sha256"]
            for source in validated
        )
        for context in contexts
    )


def _sex_expressions(rule: Mapping[str, Any], expression: str) -> tuple[str, str]:
    raw = f"trim(CAST({expression} AS VARCHAR))"
    cases = []
    statuses = [f"WHEN {raw} IS NULL OR {raw} = '' THEN 'missing'"]
    for code, category in rule["categories"].items():
        predicate = f"{raw} = {quote_literal(code)}"
        if category is not None:
            cases.append(f"WHEN {predicate} THEN {quote_literal(category)}")
        statuses.append(
            f"WHEN {predicate} THEN '{'valid' if category is not None else 'ignored'}'"
        )
    value = "CASE " + " ".join(cases) + " ELSE NULL END"
    status = "CASE " + " ".join(statuses) + " ELSE 'unsupported' END"
    return value, status


def _date_expressions(expression: str, physical_type: str, format_: str) -> tuple[str, str]:
    if physical_type.upper() == "DATE":
        return expression, f"CASE WHEN {expression} IS NULL THEN 'missing' ELSE 'valid' END"
    formats = {"ddMMyyyy": "%d%m%Y", "yyyyMMdd": "%Y%m%d"}
    raw = f"trim(CAST({expression} AS VARCHAR))"
    parsed = f"TRY_STRPTIME({raw}, {quote_literal(formats[format_])})::DATE"
    guard = f"regexp_full_match({raw}, '[0-9]{{8}}')"
    value = f"CASE WHEN {guard} THEN {parsed} ELSE NULL END"
    status = (
        f"CASE WHEN {raw} IS NULL OR {raw} = '' THEN 'missing' "
        f"WHEN ({value}) IS NULL THEN 'invalid' ELSE 'valid' END"
    )
    return value, status


def analytical_projection(
    dataset: str,
    *,
    observed_schema: Mapping[str, str],
    scopes: Sequence[SourceContext],
    rule_version: str | None = None,
) -> AnalyticalProjection:
    """Return SQL expressions without opening a lake or changing stored records.

    Only exact source identities audited with this rules edition are enabled.
    The caller must obtain schema and contexts from the same snapshot as the
    input relation. Unconfirmed/mixed scopes fail closed per analytical field.
    Identifiers are resolved case-insensitively, with ambiguous names rejected.
    """
    metadata = describe_dataset(dataset)
    rules = metadata["analytics"]
    version = rules["version"] if rules else None
    if rule_version is not None and rule_version != version:
        raise ValueError(f"Unavailable analytical rule version: {rule_version}")
    columns: list[DerivedColumn] = []
    unavailable: list[UnavailableField] = []
    names = {name.lower(): name for name in observed_schema}
    if len(names) != len(observed_schema):
        raise ValueError("Ambiguous case-insensitive source columns")
    definitions = {field["name"]: field for field in metadata["schema"]["fields"]}

    def available(output: str, inputs: Sequence[str], rule: Mapping[str, Any]) -> bool:
        if any(name not in names for name in inputs):
            unavailable.append(UnavailableField(output, "missing_source_field"))
            return False
        if not _confirmed(
            scopes, rule.get("validated_sources", rules.get("validated_sources", []))
        ):
            unavailable.append(UnavailableField(output, "unconfirmed_source_scope"))
            return False
        return True

    def add(name: str, dtype: str, expression: str) -> None:
        if name.lower() in names or any(column.name == name for column in columns):
            raise ValueError(f"Analytical column collision: {name}")
        columns.append(DerivedColumn(name, dtype, expression))

    if not rules:
        return AnalyticalProjection(
            (),
            (
                UnavailableField("idade_anos_completos", "unsupported_dataset"),
                UnavailableField("sexo_categoria", "unsupported_dataset"),
            ),
            None,
            metadata["metadata_hash"],
        )
    age = rules.get("age")
    if age is not None:
        inputs = [age["field"]] + ([age["unit_field"]] if age.get("unit_field") else [])
        if available("idade_anos_completos", inputs, age):
            value, status = age_expressions(
                age,
                quote_identifier(names[inputs[0]]),
                quote_identifier(names[inputs[1]]) if len(inputs) > 1 else None,
            )
            add("idade_anos_completos", "INTEGER", value)
            add("idade_status", "VARCHAR", status)
    else:
        unavailable.append(UnavailableField("idade_anos_completos", "unsupported_field"))
    sex = rules.get("sex")
    if sex is not None and available("sexo_categoria", [sex["field"]], sex):
        value, status = _sex_expressions(sex, quote_identifier(names[sex["field"]]))
        add("sexo_categoria", "VARCHAR", value)
        add("sexo_status", "VARCHAR", status)
    for name in rules.get("dates", []):
        output = f"{name}_data"
        if not available(output, [name], rules):
            continue
        definition = definitions[name]
        format_ = definition.get("x-format")
        if format_ not in ("ddMMyyyy", "yyyyMMdd"):
            unavailable.append(UnavailableField(output, "unsupported_date_format"))
            continue
        source_name = names[name]
        value, status = _date_expressions(
            quote_identifier(source_name), observed_schema[source_name], format_
        )
        add(output, "DATE", value)
        add(f"{output}_status", "VARCHAR", status)
    return AnalyticalProjection(
        tuple(columns), tuple(unavailable), version, metadata["metadata_hash"]
    )
