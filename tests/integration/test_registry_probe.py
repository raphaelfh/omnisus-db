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

from datetime import date

import pytest

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.datasets import REGISTRY, Dataset
from omnisus_db.sources.datasus_ftp.filenames import decode_for
from omnisus_db.sources.datasus_ftp.inventory import Listing, list_dir

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

ROWS = [pytest.param(d, id=name) for name, d in sorted(REGISTRY.items())]


@pytest.fixture(scope="module")
def listings() -> dict[str, Listing]:
    """One live LIST per distinct directory — rows share directories (SIA) and
    a row may have two (final + preliminary)."""
    cache: dict[str, Listing] = {}
    for d in REGISTRY.values():
        for directory in d.directories().values():
            if directory not in cache:
                cache[directory] = list_dir(directory, timeout_seconds=120.0)
    return cache


def _scopes(d: Dataset, listings: dict[str, Listing]) -> list[ScopeKey]:
    return [
        scope
        for directory in d.directories().values()
        for e in listings[directory].files
        if (scope := decode_for(d, e.name)) is not None
    ]


@pytest.mark.parametrize("d", ROWS)
def test_every_directory_exists_and_parses_cleanly(
    d: Dataset, listings: dict[str, Listing]
) -> None:
    for release, directory in d.directories().items():
        listing = listings[directory]
        assert listing.entries, f"{d.name}: {release} directory {directory} listed empty"
        assert listing.skipped == 0, (
            f"{d.name}: {listing.skipped} unparseable LIST lines in {directory}"
        )


@pytest.mark.parametrize("d", ROWS)
def test_some_directory_holds_files_with_this_prefix(
    d: Dataset, listings: dict[str, Listing]
) -> None:
    assert _scopes(d, listings), (
        f"{d.name}: no file in {list(d.directories().values())} decodes to this row"
    )


@pytest.mark.parametrize("d", ROWS)
def test_no_scope_is_published_in_two_directories(
    d: Dataset, listings: dict[str, Listing]
) -> None:
    scopes = _scopes(d, listings)
    assert len(scopes) == len(set(scopes)), (
        f"{d.name}: a scope appears in more than one release directory"
    )


@pytest.mark.parametrize("d", ROWS)
def test_coverage_matches_the_earliest_published_file(
    d: Dataset, listings: dict[str, Listing]
) -> None:
    """coverage[0] must be what the server actually publishes first.

    If this fails, fix the row (or investigate a DATASUS reorganisation) —
    do not widen the assertion.
    """
    scopes = _scopes(d, listings)
    assert scopes, f"{d.name}: nothing decoded"
    earliest = min((s.ano, s.mes or 1) for s in scopes)
    assert earliest == d.coverage[0], (
        f"{d.name}: registry says coverage starts {d.coverage[0]}, "
        f"server's earliest file is {earliest}"
    )


# A monthly dataset silent for 18 months is dead. A yearly one 18 months
# behind is just yearly: DATASUS publishes SIM and SINASC definitive data
# years in arrears (SINASC's newest file was 2022 when this was written, 45
# months old, and the row is still perfectly truthful). One grace period
# cannot serve both, and the row already declares which it is.
_ONGOING_GRACE_MONTHS = {"monthly": 18, "yearly": 48}


@pytest.mark.parametrize("d", ROWS)
def test_coverage_end_is_not_a_stale_claim(d: Dataset, listings: dict[str, Listing]) -> None:
    """coverage[1] is a claim too (spec I5).

    A closed window must not be contradicted by newer files on the server. An
    open window — ``None``, meaning "still published" — is the stronger claim,
    and it goes stale silently: nothing else in this suite would notice a
    dataset DATASUS quietly stopped publishing. The grace period is wide
    because DATASUS publishing lag is normal and this runs weekly on a cron,
    where a false alarm costs a notification rather than a blocked pull
    request.
    """
    scopes = _scopes(d, listings)
    assert scopes, f"{d.name}: nothing decoded"
    latest = max((s.ano, s.mes or 12) for s in scopes)

    declared_end = d.coverage[1]
    if declared_end is not None:
        assert latest <= declared_end, (
            f"{d.name}: registry closes coverage at {declared_end}, "
            f"but the server publishes {latest}"
        )
        return

    today = date.today()
    months_stale = (today.year - latest[0]) * 12 + (today.month - latest[1])
    grace = _ONGOING_GRACE_MONTHS[d.cadence]
    assert months_stale <= grace, (
        f"{d.name}: registry claims coverage is open-ended, but the server's "
        f"newest file is {latest}, {months_stale} months old "
        f"(grace for a {d.cadence} dataset is {grace})"
    )
