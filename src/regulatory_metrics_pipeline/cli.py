"""Command-line interface for illustrative regulatory-style metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .metrics import calculate_metrics


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Calculate explicitly illustrative capital and risk metrics from JSON."
    )
    parser.add_argument("input", type=Path, help="JSON input with capital, credit exposures, and gross income")
    parser.add_argument("-o", "--output", type=Path, help="write result JSON to this path (default: stdout)")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        result = calculate_metrics(data)
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
