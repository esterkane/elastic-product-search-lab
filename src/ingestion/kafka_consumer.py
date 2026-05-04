"""Optional Kafka/Redpanda consumer path for canonical product ingestion."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from pydantic import ValidationError

from src.ingestion.canonical_builder import build_canonical_product_document
from src.ingestion.event_schema import ALL_PRODUCT_TOPICS, DLQ_TOPIC, ProductSourceEvent, parse_product_source_event
from src.ingestion.source_state import ProductSourceState

LOGGER = logging.getLogger(__name__)
ErrorKind = Literal["retryable", "non_retryable"]
ConsumerOutcome = Literal["indexed", "incomplete", "stale", "dlq", "failed_retryable"]


class IndexSink(Protocol):
    def index_product(self, product_id: str, document: dict[str, Any]) -> None: ...


class DlqSink(Protocol):
    def publish_dlq(self, record: dict[str, Any]) -> None: ...


class StateStore(Protocol):
    def get(self, product_id: str) -> ProductSourceState: ...

    def save(self, state: ProductSourceState) -> None: ...


@dataclass
class InMemoryStateStore:
    states: dict[str, ProductSourceState] = field(default_factory=dict)

    def get(self, product_id: str) -> ProductSourceState:
        return self.states.setdefault(product_id, ProductSourceState(product_id=product_id))

    def save(self, state: ProductSourceState) -> None:
        self.states[state.product_id] = state


@dataclass(frozen=True)
class ConsumerResult:
    outcome: ConsumerOutcome
    product_id: str | None = None
    error_kind: ErrorKind | None = None
    code: str | None = None
    message: str | None = None


@dataclass
class ListDlqSink:
    records: list[dict[str, Any]] = field(default_factory=list)

    def publish_dlq(self, record: dict[str, Any]) -> None:
        self.records.append(record)


class ElasticsearchIndexSink:
    def __init__(self, client: Any, index_name: str) -> None:
        self.client = client
        self.index_name = index_name

    def index_product(self, product_id: str, document: dict[str, Any]) -> None:
        self.client.index(index=self.index_name, id=product_id, document=document)


class KafkaDlqSink:
    def __init__(self, producer: Any, topic: str = DLQ_TOPIC) -> None:
        self.producer = producer
        self.topic = topic

    def publish_dlq(self, record: dict[str, Any]) -> None:
        key = str(record.get("product_id") or "")
        value = json.dumps(record, sort_keys=True).encode("utf-8")
        self.producer.produce(self.topic, key=key, value=value)
        self.producer.poll(0)


def process_event(
    event: ProductSourceEvent,
    *,
    state_store: StateStore,
    index_sink: IndexSink,
) -> ConsumerResult:
    state = state_store.get(event.product_id)
    accepted = state.apply(event.to_source_update())
    state_store.save(state)
    if not accepted:
        log_event(
            "product_event_skipped_stale",
            product_id=event.product_id,
            source=event.source,
            source_version=event.source_version,
        )
        return ConsumerResult(outcome="stale", product_id=event.product_id)

    result = build_canonical_product_document(state)
    if not result.emitted or result.document is None:
        issue = result.issues[0] if result.issues else None
        log_event(
            "canonical_product_incomplete",
            product_id=event.product_id,
            source=event.source,
            issue=issue.model_dump(mode="json") if issue else None,
        )
        return ConsumerResult(
            outcome="incomplete",
            product_id=event.product_id,
            error_kind="retryable",
            code=issue.code if issue else "canonical_product_incomplete",
            message=issue.message if issue else "Canonical product is incomplete.",
        )

    index_sink.index_product(event.product_id, result.document)
    log_event("canonical_product_indexed", product_id=event.product_id, source=event.source)
    return ConsumerResult(outcome="indexed", product_id=event.product_id)


def process_raw_event(
    raw: bytes | str | dict[str, Any],
    *,
    state_store: StateStore,
    index_sink: IndexSink,
    dlq_sink: DlqSink,
    metadata: dict[str, Any] | None = None,
) -> ConsumerResult:
    try:
        event = parse_product_source_event(raw)
    except (json.JSONDecodeError, UnicodeDecodeError, ValidationError, ValueError) as exc:
        dlq_record = build_dlq_record(
            raw,
            code="malformed_product_event",
            message=str(exc),
            error_kind="non_retryable",
            metadata=metadata,
        )
        dlq_sink.publish_dlq(dlq_record)
        log_event("product_event_sent_to_dlq", **dlq_record)
        return ConsumerResult(outcome="dlq", error_kind="non_retryable", code="malformed_product_event", message=str(exc))

    try:
        return process_event(event, state_store=state_store, index_sink=index_sink)
    except ValueError as exc:
        dlq_record = build_dlq_record(
            raw,
            code="invalid_source_update",
            message=str(exc),
            error_kind="non_retryable",
            product_id=event.product_id,
            metadata=metadata,
        )
        dlq_sink.publish_dlq(dlq_record)
        log_event("product_event_sent_to_dlq", **dlq_record)
        return ConsumerResult(
            outcome="dlq",
            product_id=event.product_id,
            error_kind="non_retryable",
            code="invalid_source_update",
            message=str(exc),
        )
    except Exception as exc:  # noqa: BLE001 - classify downstream sink errors for retry.
        log_event("product_event_retryable_failure", product_id=event.product_id, error=str(exc))
        return ConsumerResult(
            outcome="failed_retryable",
            product_id=event.product_id,
            error_kind="retryable",
            code="index_sink_unavailable",
            message=str(exc),
        )


def build_dlq_record(
    raw: bytes | str | dict[str, Any],
    *,
    code: str,
    message: str,
    error_kind: ErrorKind,
    product_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if isinstance(raw, bytes):
        raw_text = raw.decode("utf-8", errors="replace")
    elif isinstance(raw, str):
        raw_text = raw
    else:
        raw_text = json.dumps(raw, sort_keys=True)
    return {
        "code": code,
        "message": message,
        "error_kind": error_kind,
        "product_id": product_id,
        "raw_event": raw_text,
        "metadata": metadata or {},
    }


def log_event(event: str, **fields: Any) -> None:
    LOGGER.info(json.dumps({"event": event, **fields}, sort_keys=True))


def build_kafka_consumer(config: dict[str, Any]) -> Any:
    try:
        from confluent_kafka import Consumer  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - optional runtime dependency.
        raise RuntimeError("Install Kafka support with: python -m pip install -e .[kafka]") from exc
    return Consumer(config)


def consume_forever(
    *,
    consumer: Any,
    state_store: StateStore,
    index_sink: IndexSink,
    dlq_sink: DlqSink,
    topics: Iterable[str] = ALL_PRODUCT_TOPICS,
    poll_timeout_seconds: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    consumer.subscribe(list(topics))
    while True:
        message = consumer.poll(poll_timeout_seconds)
        if message is None:
            continue
        if message.error():
            log_event("kafka_consumer_error", error=str(message.error()))
            sleep(0.2)
            continue
        result = process_raw_event(
            message.value(),
            state_store=state_store,
            index_sink=index_sink,
            dlq_sink=dlq_sink,
            metadata={
                "topic": message.topic(),
                "partition": message.partition(),
                "offset": message.offset(),
            },
        )
        if result.outcome in {"indexed", "incomplete", "stale", "dlq"}:
            consumer.commit(message=message, asynchronous=False)
