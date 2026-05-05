"""Optional Kafka/Redpanda consumer path for canonical product ingestion."""

from __future__ import annotations

import json
import logging
import copy
import random
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
RETRYABLE_INDEX_STATUSES = {429, 502, 503, 504}
CONFLICT_INDEX_STATUS = 409


class IndexSink(Protocol):
    def index_product(self, product_id: str, document: dict[str, Any]) -> None: ...


class DlqSink(Protocol):
    def publish_dlq(self, record: dict[str, Any]) -> None: ...


class StateStore(Protocol):
    def get(self, product_id: str) -> ProductSourceState: ...

    def save(self, state: ProductSourceState) -> None: ...


class RetryableIndexError(RuntimeError):
    """Retryable downstream indexing failure, for example 429 or connection loss."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class NonRetryableIndexError(RuntimeError):
    """Non-retryable downstream indexing failure, for example mapping or OCC conflict."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


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
class IndexerCounters:
    processed: int = 0
    indexed: int = 0
    incomplete: int = 0
    stale: int = 0
    duplicate: int = 0
    dlq: int = 0
    retryable_failed: int = 0
    non_retryable_failed: int = 0
    retries: int = 0
    conflicts: int = 0

    def as_dict(self) -> dict[str, int]:
        return dict(self.__dict__)


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


class BulkElasticsearchIndexSink:
    """Idempotent bulk sink for complete canonical product documents."""

    def __init__(
        self,
        client: Any,
        index_name: str,
        *,
        max_retries: int = 3,
        initial_backoff_seconds: float = 0.25,
        jitter_seconds: float = 0.1,
        sleep: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
        counters: IndexerCounters | None = None,
    ) -> None:
        self.client = client
        self.index_name = index_name
        self.max_retries = max_retries
        self.initial_backoff_seconds = initial_backoff_seconds
        self.jitter_seconds = jitter_seconds
        self.sleep = sleep
        self.rng = rng or random.Random()
        self.counters = counters

    def index_product(self, product_id: str, document: dict[str, Any]) -> None:
        operations = [{"index": {"_index": self.index_name, "_id": product_id}}, document]
        attempt = 0
        while True:
            try:
                response = self.client.bulk(operations=operations)
            except Exception as exc:  # noqa: BLE001 - ES client transport errors vary by version.
                status = getattr(exc, "status_code", None)
                if is_retryable_status(status) and attempt < self.max_retries:
                    self._backoff(attempt, product_id, status=status, error=str(exc))
                    attempt += 1
                    continue
                raise RetryableIndexError(str(exc), status=status) from exc

            status, error = bulk_index_status(response)
            if 200 <= status < 300:
                return
            if status in RETRYABLE_INDEX_STATUSES and attempt < self.max_retries:
                self._backoff(attempt, product_id, status=status, error=error)
                attempt += 1
                continue
            if status == CONFLICT_INDEX_STATUS:
                raise NonRetryableIndexError(error or "Elasticsearch version conflict.", status=status)
            if status in RETRYABLE_INDEX_STATUSES:
                raise RetryableIndexError(error or f"Retryable Elasticsearch status {status}.", status=status)
            raise NonRetryableIndexError(error or f"Non-retryable Elasticsearch status {status}.", status=status)

    def _backoff(self, attempt: int, product_id: str, *, status: int | None, error: str | None) -> None:
        delay = self.initial_backoff_seconds * (2**attempt) + self.rng.uniform(0, self.jitter_seconds)
        if self.counters:
            self.counters.retries += 1
        log_event(
            "indexer_bulk_retry",
            product_id=product_id,
            attempt=attempt + 1,
            delay_seconds=delay,
            status=status,
            error=error,
        )
        self.sleep(delay)


@dataclass
class ProductEventIndexer:
    state_store: StateStore
    index_sink: IndexSink
    dlq_sink: DlqSink
    counters: IndexerCounters = field(default_factory=IndexerCounters)
    seen_message_ids: set[str] = field(default_factory=set)

    def process_raw(
        self,
        raw: bytes | str | dict[str, Any],
        *,
        metadata: dict[str, Any] | None = None,
        replay: bool = False,
    ) -> ConsumerResult:
        self.counters.processed += 1
        message_id = replay_message_id(raw, metadata)
        if message_id in self.seen_message_ids:
            self.counters.duplicate += 1
            log_event("product_event_duplicate_skipped", message_id=message_id, metadata=metadata or {})
            return ConsumerResult(outcome="stale", code="duplicate_message", message="Duplicate message delivery skipped.")

        result = process_raw_event(
            raw,
            state_store=self.state_store,
            index_sink=self.index_sink,
            dlq_sink=self.dlq_sink,
            metadata=metadata,
        )
        if result.outcome != "failed_retryable":
            self.seen_message_ids.add(message_id)
        self.record_result(result)
        if replay:
            log_event("product_event_replay_result", **self.counters.as_dict())
        return result

    def process_event(self, event: ProductSourceEvent, *, replay: bool = False) -> ConsumerResult:
        return self.process_raw(event.model_dump(mode="json", exclude_none=True), replay=replay)

    def record_result(self, result: ConsumerResult) -> None:
        if result.outcome == "indexed":
            self.counters.indexed += 1
        elif result.outcome == "incomplete":
            self.counters.incomplete += 1
        elif result.outcome == "stale":
            self.counters.stale += 1
        elif result.outcome == "dlq":
            self.counters.dlq += 1
            if result.error_kind == "non_retryable":
                self.counters.non_retryable_failed += 1
        elif result.outcome == "failed_retryable":
            self.counters.retryable_failed += 1
        if result.code == "index_conflict":
            self.counters.conflicts += 1


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
    state = copy.deepcopy(state_store.get(event.product_id))
    accepted = state.apply(event.to_source_update())
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
        state_store.save(state)
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
    state_store.save(state)
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
    except NonRetryableIndexError as exc:
        code = "index_conflict" if exc.status == CONFLICT_INDEX_STATUS else "index_non_retryable_failure"
        dlq_record = build_dlq_record(
            raw,
            code=code,
            message=str(exc),
            error_kind="non_retryable",
            product_id=event.product_id,
            metadata={**(metadata or {}), "status": exc.status},
        )
        dlq_sink.publish_dlq(dlq_record)
        log_event("product_event_sent_to_dlq", **dlq_record)
        return ConsumerResult(
            outcome="dlq",
            product_id=event.product_id,
            error_kind="non_retryable",
            code=code,
            message=str(exc),
        )
    except RetryableIndexError as exc:
        log_event("product_event_retryable_failure", product_id=event.product_id, status=exc.status, error=str(exc))
        return ConsumerResult(
            outcome="failed_retryable",
            product_id=event.product_id,
            error_kind="retryable",
            code="index_sink_unavailable",
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


def is_retryable_status(status: Any) -> bool:
    try:
        return int(status) in RETRYABLE_INDEX_STATUSES
    except (TypeError, ValueError):
        return True


def bulk_index_status(response: dict[str, Any]) -> tuple[int, str | None]:
    items = response.get("items") or []
    if not items:
        return 500, "Bulk response did not include item results."
    result = items[0].get("index", {})
    return int(result.get("status", 500)), result.get("error")


def replay_message_id(raw: bytes | str | dict[str, Any], metadata: dict[str, Any] | None = None) -> str:
    if metadata and {"topic", "partition", "offset"}.issubset(metadata):
        return f"{metadata['topic']}:{metadata['partition']}:{metadata['offset']}"
    if isinstance(raw, bytes):
        raw_text = raw.decode("utf-8", errors="replace")
    elif isinstance(raw, str):
        raw_text = raw
    else:
        raw_text = json.dumps(raw, sort_keys=True)
    return raw_text


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
    indexer = ProductEventIndexer(state_store=state_store, index_sink=index_sink, dlq_sink=dlq_sink)
    while True:
        message = consumer.poll(poll_timeout_seconds)
        if message is None:
            continue
        if message.error():
            log_event("kafka_consumer_error", error=str(message.error()))
            sleep(0.2)
            continue
        result = indexer.process_raw(
            message.value(),
            metadata={
                "topic": message.topic(),
                "partition": message.partition(),
                "offset": message.offset(),
            },
        )
        if result.outcome in {"indexed", "incomplete", "stale", "dlq"}:
            consumer.commit(message=message, asynchronous=False)
