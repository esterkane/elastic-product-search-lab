"""Replay deterministic product catalog change events into Elasticsearch."""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.create_index import build_client, create_index, ensure_reachable  # noqa: E402
from src.ingestion.events import load_events  # noqa: E402
from src.ingestion.event_schema import load_product_source_events  # noqa: E402
from src.ingestion.kafka_consumer import (  # noqa: E402
    BulkElasticsearchIndexSink,
    InMemoryStateStore,
    IndexerCounters,
    ListDlqSink,
    ProductEventIndexer,
)
from src.ingestion.product_event_consumer import apply_events, configure_logging  # noqa: E402

DEFAULT_INDEX = "products-v1"
DEFAULT_EVENTS_PATH = PROJECT_ROOT / "data" / "sample" / "product_events.jsonl"


@dataclass(frozen=True)
class CanonicalReplaySummary:
    processed: int
    updated: int
    skipped_stale: int
    failed: int
    elapsed_seconds: float
    duplicates: int = 0
    retries: int = 0
    dlq: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay product catalog change events into Elasticsearch.")
    parser.add_argument("--events", type=Path, default=DEFAULT_EVENTS_PATH, help="JSONL product event file.")
    parser.add_argument(
        "--canonical-events",
        type=Path,
        default=None,
        help="Replay canonical source-owned events through the canonical builder instead of direct partial updates.",
    )
    parser.add_argument("--index", default=os.getenv("PRODUCT_INDEX", DEFAULT_INDEX), help="Product index name.")
    return parser.parse_args()


def main() -> int:
    configure_logging()
    args = parse_args()
    client = build_client()

    try:
        ensure_reachable(client)
        create_index(client, args.index, recreate=False)
        if args.canonical_events:
            started_at = time.perf_counter()
            events = load_product_source_events(args.canonical_events)
            state_store = InMemoryStateStore()
            dlq_sink = ListDlqSink()
            counters = IndexerCounters()
            index_sink = BulkElasticsearchIndexSink(client, args.index, counters=counters)
            indexer = ProductEventIndexer(
                state_store=state_store,
                index_sink=index_sink,
                dlq_sink=dlq_sink,
                counters=counters,
            )
            for event in events:
                indexer.process_event(event, replay=True)
            summary = CanonicalReplaySummary(
                processed=len(events),
                updated=counters.indexed,
                skipped_stale=counters.stale,
                failed=counters.retryable_failed + counters.non_retryable_failed,
                duplicates=counters.duplicate,
                retries=counters.retries,
                dlq=counters.dlq,
                elapsed_seconds=time.perf_counter() - started_at,
            )
        else:
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
    if isinstance(summary, CanonicalReplaySummary):
        print(f"duplicates={summary.duplicates}")
        print(f"retries={summary.retries}")
        print(f"dlq={summary.dlq}")
    print(f"elapsed_seconds={summary.elapsed_seconds:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
