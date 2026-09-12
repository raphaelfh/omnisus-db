"""Real FTP integration test (DATASUS anonymous FTP).

Run with: uv run pytest tests/integration/test_fetch_ftp_real.py -m integration

Marked ``e2e`` as well as ``integration`` so CI's ``-m "not e2e and not perf"``
deselects it. ``integration`` alone does not: there is no default ``-m`` in
``addopts``, so before this marker was added the pull-request gate opened a real
FTP connection to a shared public server on every run (spec I5 — the earlier
docstring claimed an exclusion that did not exist).
"""

from __future__ import annotations

import pytest

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.fetch import fetch_dbc_bytes

pytestmark = [pytest.mark.integration, pytest.mark.e2e]


async def test_fetch_real_sim_rr_2023() -> None:
    """Hits real DATASUS FTP. Requires network."""
    data = await fetch_dbc_bytes(
        dataset="sim_obitos",
        scope=ScopeKey(uf="RR", ano=2023),
        timeout_seconds=60.0,
    )
    # SIM RR 2023 DBC is ~280KB
    assert len(data) > 100_000
