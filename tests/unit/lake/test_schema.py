"""Tests for lake.schema canonical types."""

from __future__ import annotations

import pyarrow as pa
import pytest

from omnisus_db.lake.schema import canonical_type, ddl_for_field


def test_canonical_type_ano_is_uint16() -> None:
    assert canonical_type("ano") == pa.uint16()


def test_canonical_type_uf_is_dictionary() -> None:
    t = canonical_type("uf")
    assert pa.types.is_dictionary(t)
    assert t.value_type == pa.string()


def test_canonical_type_mes_is_uint8() -> None:
    assert canonical_type("mes") == pa.uint8()


def test_canonical_type_unknown_raises() -> None:
    with pytest.raises(KeyError):
        canonical_type("foo_bar")


def test_ddl_for_field_emits_smallint_for_ano() -> None:
    assert ddl_for_field("ano") == "USMALLINT"


def test_ddl_for_field_emits_utinyint_for_mes() -> None:
    assert ddl_for_field("mes") == "UTINYINT"
