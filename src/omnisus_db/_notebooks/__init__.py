"""Private helpers for the `notebooks/bases/` marimo notebooks.

Not part of the public import surface (`omnisus_db.__all__`). Notebook cells still
teach `available`, `import_dataset`, `LakeReader`, `publications` and `outdated`.
This package only chooses where a run lives, writes citation JSON, and reconciles
row counts so a lone-file sandbox or molab session does not need a sibling module.
"""

from omnisus_db._notebooks.paths import data_root, default_target
from omnisus_db._notebooks.plan import (
    outcomes_table,
    record_import,
    run_without_buttons,
    save_plan,
    write_json,
)
from omnisus_db._notebooks.provenance import record_provenance
from omnisus_db._notebooks.reconcile import reconcile, scope_filter

__all__ = [
    "data_root",
    "default_target",
    "outcomes_table",
    "reconcile",
    "record_import",
    "record_provenance",
    "run_without_buttons",
    "save_plan",
    "scope_filter",
    "write_json",
]
