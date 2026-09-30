"""Schema-check conformance/valid and conformance/invalid. Exit 1 on failure."""

from __future__ import annotations

import sys
from pathlib import Path

from epienv.schema_check import check_suite


def main(argv: list[str] | None = None) -> int:
    """Check the suite at the repository root, or at a root passed on the command line."""
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[0]).resolve() if args else Path.cwd().resolve()
    report = check_suite(root)
    print(f"checked {len(report.documents)} conformance documents")
    if report.ok:
        print("schema check passed")
        return 0
    for problem in report.problems:
        print(problem, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
