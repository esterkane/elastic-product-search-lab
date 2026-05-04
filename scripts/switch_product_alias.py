"""Atomically switch the product read alias to a staged product index."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.create_index import build_client, ensure_reachable  # noqa: E402
from src.search.index_management import DEFAULT_READ_ALIAS, switch_read_alias  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Switch the product read alias to a validated product index.")
    parser.add_argument("--target-index", required=True, help="Concrete product index to expose through the read alias.")
    parser.add_argument("--read-alias", default=DEFAULT_READ_ALIAS, help="Read alias to switch. Defaults to products-read.")
    parser.add_argument("--skip-count-check", action="store_true", help="Allow switching to an empty target index.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = build_client()

    try:
        ensure_reachable(client)
        if not args.skip_count_check:
            count = client.count(index=args.target_index, query={"match_all": {}})["count"]
            if count < 1:
                raise RuntimeError(f"Target index '{args.target_index}' is empty; pass --skip-count-check to override.")
        result = switch_read_alias(client, read_alias=args.read_alias, target_index=args.target_index)
    except Exception as exc:  # noqa: BLE001 - script should print a clear failure and exit non-zero.
        print(f"Alias switch failed: {exc}", file=sys.stderr)
        return 1

    print(f"alias={result['alias']}")
    print(f"target_index={result['target_index']}")
    print(f"previous_indices={','.join(result['previous_indices'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
