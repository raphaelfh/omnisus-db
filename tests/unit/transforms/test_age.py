"""Structured age semantics and actual DuckDB parity, independent of a lake."""

from dataclasses import FrozenInstanceError

import duckdb
import pytest

from omnisus_db.transforms.age import Age, age_expressions, decode_age

SIM = {
    "kind": "sim",
    "units": {
        "0": {"unit": "minute"},
        "1": {"unit": "hour"},
        "2": {"unit": "day"},
        "3": {"unit": "month"},
        "4": {"unit": "year"},
        "5": {"unit": "year", "offset": 100},
    },
    "ignored_values": ["000"],
    "ignored_units": ["9"],
    "under_one_year": ["400"],
}
SIH = {
    "kind": "sih",
    "units": {key: value for key, value in SIM["units"].items() if key in "2345"},
    "ignored_units": ["0", "9"],
    "maximum_value": 99,
}


@pytest.mark.parametrize(
    ("raw", "quantity", "unit", "years", "status", "label"),
    [
        ("000", None, None, None, "ignored", "Ignorada"),
        ("045", 45, "minute", 0, "valid", "45 minutos"),
        ("001", 1, "minute", 0, "valid", "1 minuto"),
        ("122", 22, "hour", 0, "valid", "22 horas"),
        ("101", 1, "hour", 0, "valid", "1 hora"),
        ("229", 29, "day", 0, "valid", "29 dias"),
        ("201", 1, "day", 0, "valid", "1 dia"),
        ("310", 10, "month", 0, "valid", "10 meses"),
        ("301", 1, "month", 0, "valid", "1 mês"),
        ("312", 12, "month", 1, "valid", "12 meses"),
        ("399", 99, "month", 8, "valid", "99 meses"),
        ("400", 0, "year", 0, "valid", "Menor de 1 ano"),
        ("401", 1, "year", 1, "valid", "1 ano"),
        ("499", 99, "year", 99, "valid", "99 anos"),
        ("500", 0, "year", 100, "valid", "100 anos"),
        ("501", 1, "year", 101, "valid", "101 anos"),
        ("599", 99, "year", 199, "valid", "199 anos"),
        ("999", None, None, None, "ignored", "Ignorada"),
        ("900", None, None, None, "ignored", "Ignorada"),
        (None, None, None, None, "missing", None),
        ("", None, None, None, "missing", None),
        ("-10", None, None, None, "invalid", None),
        ("abc", None, None, None, "invalid", None),
        ("45", None, None, None, "invalid", None),
        ("0400", None, None, None, "invalid", None),
        ("635", 35, None, None, "unsupported", None),
    ],
)
def test_sim_interprets_quantity_unit_years_and_display(raw, quantity, unit, years, status, label):
    age = decode_age(SIM, raw)
    assert (age.value, age.unit, age.years_completed, age.status) == (
        quantity,
        unit,
        years,
        status,
    )
    assert age.display() == label


@pytest.mark.parametrize(
    ("unit", "raw", "years", "status"),
    [
        ("2", 30, 0, "valid"),
        ("3", 11, 0, "valid"),
        ("3", 24, 2, "valid"),
        ("4", 35, 35, "valid"),
        ("5", 2, 102, "valid"),
        (None, 35, None, "missing"),
        ("", 35, None, "missing"),
        ("8", 35, None, "unsupported"),
        ("04", 35, None, "unsupported"),
        ("4", 999, None, "unsupported"),
        ("5", 999, None, "unsupported"),
        ("0", 999, None, "ignored"),
        ("9", 999, None, "ignored"),
        ("4", 35.5, None, "invalid"),
        ("4", 35.0, None, "invalid"),
        (4.0, 35, None, "invalid"),
        ("4", "-1", None, "invalid"),
        ("4", "0035", 35, "valid"),
    ],
)
def test_sih_requires_declared_unit_and_domain(unit, raw, years, status):
    age = decode_age(SIH, raw, unit)
    assert (age.years_completed, age.status) == (years, status)


RAW_CASES = [
    None,
    "",
    " ",
    "000",
    "045",
    "122",
    "229",
    "310",
    "400",
    "401",
    "499",
    "500",
    "501",
    "599",
    "999",
    "0000",
    " 401 ",
    "\t401\n",
    "\u00a0401\u00a0",
    "\u2003401\u3000",
    "1",
    "0035",
    "-35",
    "+35",
    "35.5",
    "35.0",
    "1e2",
    "4 1",
    "\uff13\uff15",
    "abc",
    "nan",
    "2147483647",
    "2147483648",
    "9223372036854775807",
    "9223372036854775808",
    "9" * 5000,
    "0" * 5000 + "35",
    "0" * 5000,
]
UNIT_CASES = [None, "", "0", "1", "2", "3", "4", "5", "9", "8", "04", "4.0", "x", "-4", " 4 "]


@pytest.mark.parametrize("rule", [SIM, SIH])
def test_native_duckdb_matches_scalar_for_malformed_and_boundary_values(rule):
    cases = [(raw, unit) for raw in RAW_CASES for unit in UNIT_CASES]
    years_sql, status_sql = age_expressions(rule, '"raw"', '"unit"')
    with duckdb.connect() as con:
        con.execute("CREATE TABLE cases (i INTEGER, raw VARCHAR, unit VARCHAR)")
        con.executemany(
            "INSERT INTO cases VALUES (?, ?, ?)", [(i, *case) for i, case in enumerate(cases)]
        )
        rows = con.execute(f"SELECT {years_sql}, {status_sql} FROM cases ORDER BY i").fetchall()
    expected = [
        (age.years_completed, age.status)
        for raw, unit in cases
        for age in [decode_age(rule, raw, unit)]
    ]
    assert rows == expected


@pytest.mark.parametrize("raw", [35, 35.0, 35.5, True, False, None])
def test_duckdb_typed_values_match_scalar(raw):
    years, status = age_expressions(SIH, "raw", "unit")
    with duckdb.connect() as con:
        actual = con.execute(
            f"SELECT {years}, {status} FROM (SELECT ? AS raw, 4 AS unit)", [raw]
        ).fetchone()
    age = decode_age(SIH, raw, 4)
    assert actual == (age.years_completed, age.status)


def test_rule_changes_apply_to_both_executors():
    rule = {
        **SIH,
        "units": {"5": {"unit": "year", "offset": 90, "maximum_value": 2}},
        "ignored_values": ["1"],
    }
    years, status = age_expressions(rule, "raw", "'5'")
    with duckdb.connect() as con:
        for raw, expected in [
            ("0", (90, "valid")),
            ("1", (None, "ignored")),
            ("2", (92, "valid")),
            ("3", (None, "unsupported")),
        ]:
            scalar = decode_age(rule, raw, "5")
            assert (scalar.years_completed, scalar.status) == expected
            assert (
                con.execute(f"SELECT {years}, {status} FROM (SELECT ? AS raw)", [raw]).fetchone()
                == expected
            )


def test_subyear_without_confirmed_domain_is_unsupported():
    rule = {key: value for key, value in SIH.items() if key != "maximum_value"}
    years, status = age_expressions(rule, "'30'", "'2'")
    assert decode_age(rule, "30", "2").status == "unsupported"
    with duckdb.connect() as con:
        assert con.execute(f"SELECT {years}, {status}").fetchone() == (None, "unsupported")


def test_missing_unit_sql_and_unknown_rule():
    years, status = age_expressions(SIH, "'35'")
    with duckdb.connect() as con:
        assert con.execute(f"SELECT {years}, {status}").fetchone() == (None, "missing")
    for operation in (
        lambda: decode_age({"kind": "unknown"}, 35),
        lambda: age_expressions({"kind": "unknown"}, "raw"),
    ):
        with pytest.raises(ValueError, match="Unsupported age rule kind"):
            operation()


def test_age_is_immutable():
    age = Age(35, "year", 35, "valid")
    with pytest.raises(FrozenInstanceError):
        age.value = 40


@pytest.mark.parametrize(
    ("unit", "raw", "expected"),
    [
        ("0", "0", (None, "invalid")),
        ("0", "000", (None, "invalid")),
        ("9", "99", (None, "invalid")),
        ("9", "099", (None, "invalid")),
        ("4", "999", (None, "unsupported")),
        ("9", "999", (None, "unsupported")),
        ("3", "0", (None, "unsupported")),
        ("4", "0", (None, "unsupported")),
        ("2", "0", (0, "valid")),
        ("2", "30", (0, "valid")),
        ("2", "31", (None, "unsupported")),
        ("3", "11", (0, "valid")),
        ("3", "12", (None, "unsupported")),
        ("4", "1", (1, "valid")),
        ("5", "0", (100, "valid")),
        ("5", "30", (130, "valid")),
        ("5", "31", (None, "unsupported")),
        ("0", "0.0", (None, "invalid")),
        ("9", "99.0", (None, "invalid")),
    ],
)
def test_packaged_sih_domains_and_invalid_composites(unit, raw, expected):
    from omnisus_db.transforms.dictionaries import load_dicionario

    rule = load_dicionario("sih_aih_reduzida").raw["x-analytics"]["age"]
    age = decode_age(rule, raw, unit)
    assert (age.years_completed, age.status) == expected
    years, status = age_expressions(rule, "raw", "unit")
    with duckdb.connect() as con:
        assert (
            con.execute(
                f"SELECT {years}, {status} FROM (SELECT ? AS raw, ? AS unit)", [raw, unit]
            ).fetchone()
            == expected
        )


def test_minimum_domain_from_rule_and_unit_override():
    rule = {
        **SIH,
        "minimum_value": 2,
        "units": {
            "4": {"unit": "year"},
            "5": {"unit": "year", "offset": 100, "minimum_value": 0},
        },
    }
    years, status = age_expressions(rule, "raw", "unit")
    with duckdb.connect() as con:
        for unit, raw, expected in [
            ("4", "1", (None, "unsupported")),
            ("4", "2", (2, "valid")),
            ("5", "0", (100, "valid")),
        ]:
            age = decode_age(rule, raw, unit)
            assert (age.years_completed, age.status) == expected
            assert (
                con.execute(
                    f"SELECT {years}, {status} FROM (SELECT ? AS raw, ? AS unit)", [raw, unit]
                ).fetchone()
                == expected
            )
