"""Tests for datasus_ftp.fetch — FTP DBC fetcher."""

from __future__ import annotations

import ftplib
from unittest.mock import patch

import pytest

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.fetch import (
    fetch_dbc_bytes,
    ftp_path_for,
)


def test_ftp_path_for_sim() -> None:
    path, name = ftp_path_for("sim_do", ScopeKey(uf="SP", ano=2024))
    assert path == "/dissemin/publicos/SIM/CID10/DORES"
    assert name == "DOSP2024.dbc"


def test_ftp_path_for_sih_monthly() -> None:
    path, name = ftp_path_for("sih_rd", ScopeKey(uf="SP", ano=2024, mes=1))
    assert path == "/dissemin/publicos/SIHSUS/200801_/Dados"
    assert name == "RDSP2401.dbc"


def test_ftp_path_for_unknown_dataset() -> None:
    with pytest.raises(ValueError):
        ftp_path_for("bogus", ScopeKey(uf="SP", ano=2024))


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
            dataset="sim_do",
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
            dataset="sim_do",
            scope=ScopeKey(uf="SP", ano=2024),
            max_retries=3,
            backoff_seconds=0,
        )
    assert data == payload
    assert call_count == 2


@pytest.mark.asyncio
async def test_fetch_dbc_bytes_does_not_retry_on_perm_error() -> None:
    """ftplib.error_perm (e.g., 550 file not found) should not be retried."""
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
        pytest.raises(ftplib.error_perm),
    ):
        await fetch_dbc_bytes(
            dataset="sim_do",
            scope=ScopeKey(uf="SP", ano=2024),
            max_retries=3,
            backoff_seconds=0,
        )
    assert call_count == 1


@pytest.mark.asyncio
async def test_fetch_dbc_bytes_raises_after_max_retries() -> None:
    def fake_blocking_fetch(*_args: object) -> bytes:
        raise OSError("perma-fail")

    with (
        patch(
            "omnisus_db.sources.datasus_ftp.fetch._blocking_fetch",
            side_effect=fake_blocking_fetch,
        ),
        pytest.raises(OSError, match="perma-fail"),
    ):
        await fetch_dbc_bytes(
            dataset="sim_do",
            scope=ScopeKey(uf="SP", ano=2024),
            max_retries=2,
            backoff_seconds=0,
        )
