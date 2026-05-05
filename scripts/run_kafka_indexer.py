"""Run the optional Kafka/Redpanda canonical product indexer."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.create_index import build_client, create_index, ensure_reachable  # noqa: E402
from src.ingestion.kafka_consumer import (  # noqa: E402
    BulkElasticsearchIndexSink,
    InMemoryStateStore,
    KafkaDlqSink,
    build_kafka_consumer,
    consume_forever,
)
from src.ingestion.event_schema import ALL_PRODUCT_TOPICS, DLQ_TOPIC  # noqa: E402
from src.ingestion.bulk_indexer import configure_logging  # noqa: E402

DEFAULT_INDEX = "products-build"


def build_kafka_producer(config: dict[str, str]):
    try:
        from confluent_kafka import Producer  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - optional runtime dependency.
        raise RuntimeError("Install Kafka support with: .\\.venv\\Scripts\\python.exe -m pip install -e .[kafka]") from exc
    return Producer(config)


def parse_args() -> argparse.Namespace:
    load_dotenv(PROJECT_ROOT / ".env")
    parser = argparse.ArgumentParser(description="Consume Kafka product events and index canonical product documents.")
    parser.add_argument("--bootstrap-servers", default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092"))
    parser.add_argument("--group-id", default=os.getenv("KAFKA_INDEXER_GROUP_ID", "product-catalog-indexer"))
    parser.add_argument("--index", default=os.getenv("PRODUCT_INDEX", DEFAULT_INDEX))
    parser.add_argument("--topics", nargs="*", default=list(ALL_PRODUCT_TOPICS), help="Topics to subscribe to.")
    parser.add_argument("--max-retries", type=int, default=int(os.getenv("KAFKA_INDEXER_MAX_RETRIES", "3")))
    parser.add_argument("--initial-backoff-seconds", type=float, default=float(os.getenv("KAFKA_INDEXER_INITIAL_BACKOFF_SECONDS", "0.25")))
    parser.add_argument("--jitter-seconds", type=float, default=float(os.getenv("KAFKA_INDEXER_JITTER_SECONDS", "0.1")))
    parser.add_argument("--no-create-index", action="store_true", help="Do not create the target index before consuming.")
    return parser.parse_args()


def main() -> int:
    configure_logging()
    args = parse_args()
    es_client = build_client()
    try:
        ensure_reachable(es_client)
        if not args.no_create_index:
            create_index(es_client, args.index, recreate=False)

        kafka_config = {
            "bootstrap.servers": args.bootstrap_servers,
            "group.id": args.group_id,
            "enable.auto.commit": False,
            "auto.offset.reset": os.getenv("KAFKA_INDEXER_AUTO_OFFSET_RESET", "earliest"),
        }
        consumer = build_kafka_consumer(kafka_config)
        producer = build_kafka_producer({"bootstrap.servers": args.bootstrap_servers})
        consume_forever(
            consumer=consumer,
            state_store=InMemoryStateStore(),
            index_sink=BulkElasticsearchIndexSink(
                es_client,
                args.index,
                max_retries=args.max_retries,
                initial_backoff_seconds=args.initial_backoff_seconds,
                jitter_seconds=args.jitter_seconds,
            ),
            dlq_sink=KafkaDlqSink(producer, topic=DLQ_TOPIC),
            topics=args.topics,
        )
    except KeyboardInterrupt:
        print("Kafka indexer stopped.")
        return 0
    except Exception as exc:  # noqa: BLE001 - script should print clear structured-ish failure.
        print(f"Kafka indexer failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
