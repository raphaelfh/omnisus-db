"""Tier 3 (spec §6): every registry row, checked against the live server.

Internal agreement is necessary and insufficient — if a row's ftp_dir or
prefix is wrong, every derived surface is consistently wrong. Only this tier
can catch that, and only it detects a DATASUS reorganisation.

Network-bound and upstream-flaky, so it runs on a schedule, never on a PR.

Marked BOTH ``integration`` and ``e2e`` deliberately. CI runs
``-m "not e2e and not perf"``, which does *not* deselect ``integration`` — so
``integration`` alone would put eleven live FTP listings on every pull
request. ``e2e`` is described in pyproject as "slow, manual/cron", which is
exactly this, and it is already deselected. ``probe.yml`` selects with
``-m integration``, which matches regardless of the second marker.

    uv run pytest tests/integration/test_registry_probe.py -m integration

A failure here is a finding about the registry or the server — never a
reason to loosen an assertion.
"""

from __future__ import annotations

import pytest

from omnisus_db.sources.datasus_ftp.datasets import REGISTRY, Dataset
from omnisus_db.sources.datasus_ftp.filenames import decode
from omnisus_db.sources.datasus_ftp.inventory import Listing, list_dir

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

ROWS = [pytest.param(d, id=name) for name, d in sorted(REGISTRY.items())]


@pytest.fixture(scope="module")
def listings() -> dict[str, Listing]:
    """One live LIST per distinct ftp_dir — the SIA rows share a directory."""
    cache: dict[str, Listing] = {}
    for d in REGISTRY.values():
        if d.ftp_dir not in cache:
            cache[d.ftp_dir] = list_dir(d.ftp_dir, timeout_seconds=120.0)
    return cache


@pytest.mark.parametrize("d", ROWS)
def test_ftp_dir_exists_and_parses_cleanly(d: Dataset, listings: dict[str, Listing]) -> None:
    listing = listings[d.ftp_dir]
    assert listing.entries, f"{d.name}: {d.ftp_dir} listed empty"
    assert listing.skipped == 0, (
        f"{d.name}: {listing.skipped} unparseable LIST lines in {d.ftp_dir} — "
        "the MS-DOS parser or the server format changed"
    )


@pytest.mark.parametrize("d", ROWS)
def test_directory_holds_files_with_this_prefix(d: Dataset, listings: dict[str, Listing]) -> None:
    listing = listings[d.ftp_dir]
    mine = [
        e
        for e in listing.files
        if (decoded := decode(e.name)) is not None and decoded[1] == d.name
    ]
    assert mine, (
        f"{d.name}: no file in {d.ftp_dir} decodes to this dataset — "
        f"prefix {d.prefix!r} or ftp_dir is wrong"
    )


@pytest.mark.parametrize("d", ROWS)
def test_coverage_matches_the_earliest_published_file(
    d: Dataset, listings: dict[str, Listing]
) -> None:
    """coverage[0] must be what the server actually publishes first.

    If this fails, fix the row (or investigate a DATASUS reorganisation) —
    do not widen the assertion.
    """
    listing = listings[d.ftp_dir]
    scopes = [
        decoded[0]
        for e in listing.files
        if (decoded := decode(e.name)) is not None and decoded[1] == d.name
    ]
    assert scopes, f"{d.name}: nothing decoded"
    earliest = min((s.ano, s.mes or 1) for s in scopes)
    assert earliest == d.coverage[0], (
        f"{d.name}: registry says coverage starts {d.coverage[0]}, "
        f"server's earliest file is {earliest}"
    )
