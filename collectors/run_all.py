"""Run every enabled collector; a failure in one source does not stop the others."""
from __future__ import annotations

import importlib
import sys
import traceback

from collectors.common import log

ORDER = ["pubmed", "arxiv", "edgar", "clinicaltrials", "uspto"]


def main(selected: list[str] | None = None) -> int:
    failures = []
    for name in selected or ORDER:
        log(f"=== {name} ===")
        try:
            importlib.import_module(f"collectors.{name}").main()
        except Exception:  # noqa: BLE001
            failures.append(name)
            traceback.print_exc()
    if failures:
        log(f"collectors with errors: {failures}")
    return 0  # never fail the workflow on a single source; detector runs on what exists


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or None))
