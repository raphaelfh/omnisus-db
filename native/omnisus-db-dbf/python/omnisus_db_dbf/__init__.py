"""Optional native DBF to Arrow reader."""

from ._native import (
    API_VERSION,
    DbfBatchReader,
    InvalidDbfError,
    UnsupportedDbfError,
    __version__,
    open_reader,
)

__all__ = [
    "API_VERSION",
    "DbfBatchReader",
    "InvalidDbfError",
    "UnsupportedDbfError",
    "__version__",
    "open_reader",
]
