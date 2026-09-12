"""Tests for datasus_ftp.fetch — FTP DBC fetcher."""

from __future__ import annotations

import ftplib
from unittest.mock import patch

import pytest

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.datasets import REGISTRY
from omnisus_db.sources.datasus_ftp.fetch import (
    FtpFileNotFound,
    FtpUnavailable,
    fetch_dbc_bytes,
    ftp_path_for,
)


def test_ftp_path_for_sim() -> None:
    path, name = ftp_path_for("sim_obitos", ScopeKey(uf="SP", ano=2024))
    assert path == "/dissemin/publicos/SIM/CID10/DORES"
    assert name == "DOSP2024.dbc"


def test_ftp_path_for_sih_monthly() -> None:
    path, name = ftp_path_for("sih_aih_reduzida", ScopeKey(uf="SP", ano=2024, mes=1))
    assert path == "/dissemin/publicos/SIHSUS/200801_/Dados"
    assert name == "RDSP2401.dbc"


def test_ftp_path_for_unknown_dataset() -> None:
    with pytest.raises(ValueError):
        ftp_path_for("bogus", ScopeKey(uf="SP", ano=2024))


def test_ftp_path_for_uses_the_release_directory() -> None:
    d = REGISTRY["sim_obitos"]
    scope = ScopeKey(uf="SP", ano=2025)
    assert ftp_path_for(d, scope) == (d.ftp_dir, "DOSP2025.dbc")
    assert ftp_path_for(d, scope, "prelim") == (d.prelim_dir, "DOSP2025.dbc")


def test_ftp_path_for_prelim_on_a_row_without_prelim_dir_is_a_caller_bug() -> None:
    with pytest.raises(ValueError, match="has no prelim directory"):
        ftp_path_for(
            REGISTRY["sia_bpa_individualizado"], ScopeKey(uf="RR", ano=2024, mes=1), "prelim"
        )


@pytest.mark.asyncio
async def test_fetch_dbc_bytes_returns_payload() -> None:
    payload = b"\x00\x01FAKE_DBC_BYTES"

    def fake_blocking_fetch(remote_dir: str, filename: str, timeout: float) -> bytes:
        assert remote_dir == "/dissemin/publicos/SIM/CID10/DORES"
        assert filename == "DOSP2024.dbc"
        return payload

    with patch(
        "omnisus_db.sources.datasus_ftp.fetch._blocking_fetch",
        side_effect=fake_blocking_fetch,
    ):
        data = await fetch_dbc_bytes(
            dataset="sim_obitos",
            scope=ScopeKey(uf="SP", ano=2024),
        )
    assert data == payload


@pytest.mark.asyncio
async def test_fetch_dbc_bytes_retries_on_transient_error() -> None:
    payload = b"OK"
    call_count = 0

    def fake_blocking_fetch(*_args: object) -> bytes:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise OSError("connection reset")
        return payload

    with patch(
        "omnisus_db.sources.datasus_ftp.fetch._blocking_fetch",
        side_effect=fake_blocking_fetch,
    ):
        data = await fetch_dbc_bytes(
            dataset="sim_obitos",
            scope=ScopeKey(uf="SP", ano=2024),
            max_retries=3,
            backoff_seconds=0,
        )
    assert data == payload
    assert call_count == 2


@pytest.mark.asyncio
async def test_a_550_is_terminal_and_typed() -> None:
    """550 means DATASUS does not publish this scope. Never retried, and it
    arrives as FtpFileNotFound so the caller can skip rather than string-match."""
    call_count = 0

    def fake_blocking_fetch(*_args: object) -> bytes:
        nonlocal call_count
        call_count += 1
        raise ftplib.error_perm("550 No such file")

    with (
        patch(
            "omnisus_db.sources.datasus_ftp.fetch._blocking_fetch",
            side_effect=fake_blocking_fetch,
        ),
        pytest.raises(FtpFileNotFound),
    ):
        await fetch_dbc_bytes(
            dataset="sim_obitos",
            scope=ScopeKey(uf="SP", ano=2024),
            max_retries=3,
            backoff_seconds=0,
        )
    assert call_count == 1


@pytest.mark.asyncio
async def test_a_530_throttle_is_retried_not_mistaken_for_a_missing_file() -> None:
    """The defect this contract replaces.

    ``ftplib.error_perm`` is *any* 5xx, and DATASUS answers 530 when its
    anonymous-connection pool is full. Treating the whole class as permanent
    made a busy server indistinguishable from an absent dataset — so a wide
    import would report scopes as missing that exist and were merely throttled.
    """
    call_count = 0

    def fake_blocking_fetch(*_args: object) -> bytes:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ftplib.error_perm("530 maximum number of allowed clients")
        return b"OK"

    with patch(
        "omnisus_db.sources.datasus_ftp.fetch._blocking_fetch",
        side_effect=fake_blocking_fetch,
    ):
        data = await fetch_dbc_bytes(
            dataset="sim_obitos",
            scope=ScopeKey(uf="SP", ano=2024),
            max_retries=3,
            backoff_seconds=0,
        )
    assert data == b"OK"
    assert call_count == 3, "530 must be retried to the full budget, not treated as terminal"


@pytest.mark.asyncio
async def test_a_530_that_never_clears_is_unavailable_not_not_found() -> None:
    """Exhausting the budget on a throttle is 'failed', never 'skipped'."""

    def fake_blocking_fetch(*_args: object) -> bytes:
        raise ftplib.error_perm("530 maximum number of allowed clients")

    with (
        patch(
            "omnisus_db.sources.datasus_ftp.fetch._blocking_fetch",
            side_effect=fake_blocking_fetch,
        ),
        pytest.raises(FtpUnavailable) as exc_info,
    ):
        await fetch_dbc_bytes(
            dataset="sim_obitos",
            scope=ScopeKey(uf="SP", ano=2024),
            max_retries=2,
            backoff_seconds=0,
        )
    assert not isinstance(exc_info.value, FtpFileNotFound)


@pytest.mark.asyncio
async def test_exhausted_retries_raise_unavailable_preserving_the_cause() -> None:
    def fake_blocking_fetch(*_args: object) -> bytes:
        raise OSError("perma-fail")

    with (
        patch(
            "omnisus_db.sources.datasus_ftp.fetch._blocking_fetch",
            side_effect=fake_blocking_fetch,
        ),
        pytest.raises(FtpUnavailable) as exc_info,
    ):
        await fetch_dbc_bytes(
            dataset="sim_obitos",
            scope=ScopeKey(uf="SP", ano=2024),
            max_retries=2,
            backoff_seconds=0,
        )
    # The original error is not swallowed — it is the __cause__.
    assert isinstance(exc_info.value.__cause__, OSError)
    assert "perma-fail" in str(exc_info.value.__cause__)
