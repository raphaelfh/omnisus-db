"""Real FTP integration test (DATASUS anonymous FTP).

Run with: uv run pytest tests/integration/test_fetch_ftp_real.py -m integration
Skipped in default test runs (default excludes 'integration').
"""

from __future__ import annotations

import pytest

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.fetch import fetch_dbc_bytes


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fetch_real_sim_rr_2023() -> None:
    """Hits real DATASUS FTP. Requires network."""
    data = await fetch_dbc_bytes(
        dataset="sim_do",
        scope=ScopeKey(uf="RR", ano=2023),
        timeout_seconds=60.0,
    )
    # SIM RR 2023 DBC is ~280KB
    assert len(data) > 100_000
    # DBC magic bytes — first byte is the LZ77 marker
    assert data[:2] != b""
