"""Lake — DuckLake bindings."""

from omnisus_db.lake._transactions import CommitOutcomeUnknown, TransactionStateError
from omnisus_db.lake.catalog import DEFAULT_TARGET
from omnisus_db.lake.operations import Lake

__all__ = ["DEFAULT_TARGET", "CommitOutcomeUnknown", "Lake", "TransactionStateError"]
