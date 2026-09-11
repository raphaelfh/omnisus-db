import pytest

from omnisus_db.sources.ibge.products import CENSUS_YEARS, resolve_product


def test_census_years_are_the_verified_editions():
    assert CENSUS_YEARS == (2010, 2022)
    assert all(resolve_product("census", year).name == "census" for year in CENSUS_YEARS)


def test_non_census_year_is_rejected():
    with pytest.raises(ValueError, match="census years: 2010, 2022"):
        resolve_product("census", 2015)
