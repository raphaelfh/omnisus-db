"""Lake — DuckLake bindings."""

from omnisus_db.lake._transactions import CommitOutcomeUnknown, TransactionStateError
from omnisus_db.lake.catalog import DEFAULT_TARGET
from omnisus_db.lake.connection import CatalogAttachError
from omnisus_db.lake.operations import Lake
from omnisus_db.lake.session import LakeReader

__all__ = [
    "DEFAULT_TARGET",
    "CatalogAttachError",
    "CommitOutcomeUnknown",
    "Lake",
    "LakeReader",
    "TransactionStateError",
]
