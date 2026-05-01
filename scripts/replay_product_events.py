"""Replay deterministic product catalog change events into Elasticsearch."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.create_index import build_client, create_index, ensure_reachable  # noqa: E402
from src.ingestion.events import load_events  # noqa: E402
from src.ingestion.product_event_consumer import apply_events, configure_logging  # noqa: E402

DEFAULT_INDEX = "products-v1"
DEFAULT_EVENTS_PATH = PROJECT_ROOT / "data" / "sample" / "product_events.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay product catalog change events into Elasticsearch.")
    parser.add_argument("--events", type=Path, default=DEFAULT_EVENTS_PATH, help="JSONL product event file.")
    parser.add_argument("--index", default=os.getenv("PRODUCT_INDEX", DEFAULT_INDEX), help="Product index name.")
    return parser.parse_args()


def main() -> int:
    configure_logging()
    args = parse_args()
    client = build_client()

    try:
        ensure_reachable(client)
        create_index(client, args.index, recreate=False)
        events = load_events(args.events)
        summary = apply_events(client, args.index, events)
        client.indices.refresh(index=args.index)
    except Exception as exc:  # noqa: BLE001 - script should print a clear failure and exit non-zero.
        print(f"Product event replay failed: {exc}", file=sys.stderr)
        return 1

    print(f"processed={summary.processed}")
    print(f"updated={summary.updated}")
    print(f"skipped_stale={summary.skipped_stale}")
    print(f"failed={summary.failed}")
    print(f"elapsed_seconds={summary.elapsed_seconds:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
