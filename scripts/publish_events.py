"""Publish canonical product events to Redpanda or Kafka."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.event_schema import load_product_source_events  # noqa: E402

DEFAULT_INPUT = PROJECT_ROOT / "data" / "generated" / "synthetic_product_events.jsonl"
DEFAULT_BOOTSTRAP = "localhost:19092"


def build_producer(config: dict[str, Any]) -> Any:
    try:
        from confluent_kafka import Producer  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("Install Kafka support with: .\\.venv\\Scripts\\python.exe -m pip install -e .[kafka]") from exc
    return Producer(config)


def delivery_report(error: Any, message: Any, failures: list[dict[str, str]]) -> None:
    if error is not None:
        failure = {
            "event": "kafka_delivery_failed",
            "error_kind": "retryable",
            "topic": message.topic() if message is not None else "",
            "message": str(error),
        }
        failures.append(failure)
        print(
            json.dumps(failure, sort_keys=True),
            file=sys.stderr,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish canonical product events to Kafka-compatible topics.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Canonical event JSONL file.")
    parser.add_argument("--bootstrap-servers", default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", DEFAULT_BOOTSTRAP))
    return parser.parse_args()


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    args = parse_args()
    events = load_product_source_events(args.input)
    producer = build_producer({"bootstrap.servers": args.bootstrap_servers})
    failures: list[dict[str, str]] = []

    published = 0
    for event in events:
        producer.produce(
            event.topic(),
            key=event.key(),
            value=event.to_json_line().encode("utf-8"),
            on_delivery=lambda error, message: delivery_report(error, message, failures),
        )
        producer.poll(0)
        published += 1
    producer.flush()
    if failures:
        print(f"failed={len(failures)}", file=sys.stderr)
        return 1
    print(f"published={published}")
    print(f"bootstrap_servers={args.bootstrap_servers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
