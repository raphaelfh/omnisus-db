"""DBF integrity and semantic publication identity shared by both backends."""

import structlog

logger = structlog.get_logger(__name__)

_DELETED_FLAG = 0x2A  # b"*"


class DbfIntegrityError(Exception):
    """Decompressed DBF is inconsistent with its own header record count.

    DATASUS truncation is *silent*: a partial download or partial decompress
    yields a structurally valid DBF that simply stops early — dbfread2 raises
    nothing and 1-2% of records vanish. This error turns that into a hard
    failure. Field-measured on PAAC2401 (-1.0%) and RDAC2401 (-1.8%).
    """


def _read_dbf_geometry(dbf_bytes: bytes) -> tuple[int, int, int] | None:
    """Return (nrec, hdr_len, rec_len) from the DBF header, or None if the
    header is too malformed to interpret (let dbfread2 surface its own error).
    """
    if len(dbf_bytes) < 32:
        return None
    nrec = int.from_bytes(dbf_bytes[4:8], "little")
    hdr_len = int.from_bytes(dbf_bytes[8:10], "little")
    rec_len = int.from_bytes(dbf_bytes[10:12], "little")
    if hdr_len <= 32 or rec_len <= 0:
        return None
    return nrec, hdr_len, rec_len


def _check_dbf_length(dbf_bytes: bytes, *, dataset: str) -> None:
    """Pre-parse gate: the byte payload must hold all declared records."""
    geometry = _read_dbf_geometry(dbf_bytes)
    if geometry is None:
        return
    nrec, hdr_len, rec_len = geometry
    expected = hdr_len + nrec * rec_len
    if len(dbf_bytes) < expected:
        present = max(0, (len(dbf_bytes) - hdr_len) // rec_len)
        raise DbfIntegrityError(
            f"{dataset}: DBF truncated — header declares {nrec} records "
            f"but payload holds only {present} "
            f"({len(dbf_bytes)} bytes < {expected} expected)"
        )


def _check_record_count(dbf_bytes: bytes, parsed: int, *, dataset: str) -> None:
    """Post-parse gate: parsed + deleted must equal the declared count.

    Catches parser early-stops (e.g. an embedded 0x1A EOF marker) that the
    length check cannot see. Deleted rows (flag ``*``) are skipped by
    dbfread2 but occupy slots, so they count toward nrec.
    """
    geometry = _read_dbf_geometry(dbf_bytes)
    if geometry is None:
        return
    nrec, hdr_len, rec_len = geometry
    flags = dbf_bytes[hdr_len : hdr_len + nrec * rec_len : rec_len]
    deleted = flags.count(_DELETED_FLAG)
    if deleted:
        logger.warning(
            "datasus_ftp.deleted_records",
            dataset=dataset,
            deleted=deleted,
        )
    if parsed + deleted != nrec:
        raise DbfIntegrityError(
            f"{dataset}: record count mismatch — header declares {nrec} "
            f"records, parsed {parsed} + {deleted} deleted = {parsed + deleted}"
        )


def _ensure_dbf_terminator(dbf_bytes: bytes) -> bytes:
    """Ensure the DBF field-descriptor area ends with 0x0D.

    Some DATASUS DBC payloads (notably CNES) decompress to a DBF whose
    declared header length leaves a 0x00 in place of the required 0x0D
    field-descriptor terminator. Patch the byte at ``hdr_size - 1`` when
    needed so dbfread2 can parse the file.
    """
    if len(dbf_bytes) < 12:
        return dbf_bytes
    hdr_size = int.from_bytes(dbf_bytes[8:10], "little")
    if hdr_size <= 32 or hdr_size > len(dbf_bytes):
        return dbf_bytes
    if dbf_bytes[hdr_size - 1] == 0x0D:
        return dbf_bytes
    patched = bytearray(dbf_bytes)
    patched[hdr_size - 1] = 0x0D
    return bytes(patched)


def publication_parser_version(dictionary_hash: str) -> str:
    """Execution backend changes do not change the meaning of published rows."""
    return "dbc-staging-v1:" + dictionary_hash
