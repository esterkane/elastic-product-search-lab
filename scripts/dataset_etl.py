"""Shared deterministic ETL helpers for local dataset samples."""

from __future__ import annotations

import csv
import json
import random
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.ingestion.event_schema import ProductSourceEvent

DEFAULT_SEED = 17
DEFAULT_EVENT_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def read_records(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        with path.open("r", encoding="utf-8-sig") as handle:
            return [json.loads(line) for line in handle if line.strip()]
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    if suffix == ".parquet":
        try:
            import pandas as pd  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("Reading parquet requires pandas and pyarrow installed in the Python environment.") from exc
        return pd.read_parquet(path).to_dict(orient="records")
    raise ValueError(f"Unsupported input format: {path}")


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def as_float(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def stable_price(product_id: str, *, seed: int = DEFAULT_SEED, low: float = 9.99, high: float = 249.99) -> float:
    rng = random.Random(f"{seed}:price:{product_id}")
    return round(rng.uniform(low, high), 2)


def stable_availability(product_id: str, *, seed: int = DEFAULT_SEED) -> str:
    rng = random.Random(f"{seed}:inventory:{product_id}")
    return rng.choices(["in_stock", "limited_stock", "out_of_stock"], weights=[78, 17, 5], k=1)[0]


def stable_rating(product_id: str, *, seed: int = DEFAULT_SEED) -> float:
    rng = random.Random(f"{seed}:rating:{product_id}")
    return round(rng.uniform(3.2, 4.9), 2)


def utc_iso(value: datetime = DEFAULT_EVENT_TIME) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def snapshot_to_events(product: dict[str, Any], sequence: int, *, dataset: str) -> dict[str, ProductSourceEvent]:
    product_id = str(product["product_id"])
    version = str(product.get("updated_at") or utc_iso())
    event_time = datetime.fromisoformat(version.replace("Z", "+00:00"))
    correlation_id = f"{dataset}-{product_id}"
    attributes = dict(product.get("attributes") or {})
    return {
        "price": ProductSourceEvent(
            source="price",
            event_type="snapshot",
            product_id=product_id,
            source_version=version,
            event_time=event_time,
            payload={"price": float(product["price"]), "currency": str(product["currency"])},
            trace_id=f"{dataset}-{sequence:05d}-price",
            correlation_id=correlation_id,
        ),
        "inventory": ProductSourceEvent(
            source="inventory",
            event_type="snapshot",
            product_id=product_id,
            source_version=version,
            event_time=event_time,
            payload={"availability": str(product["availability"])},
            trace_id=f"{dataset}-{sequence:05d}-inventory",
            correlation_id=correlation_id,
        ),
        "reviews": ProductSourceEvent(
            source="reviews",
            event_type="snapshot",
            product_id=product_id,
            source_version=version,
            event_time=event_time,
            payload={
                "average_rating": as_float(attributes.get("average_rating"), stable_rating(product_id)),
                "review_count": int(as_float(attributes.get("review_count"), 0)),
            },
            trace_id=f"{dataset}-{sequence:05d}-reviews",
            correlation_id=correlation_id,
        ),
        "analytics": ProductSourceEvent(
            source="analytics",
            event_type="snapshot",
            product_id=product_id,
            source_version=version,
            event_time=event_time,
            payload={"popularity_score": float(product["popularity_score"])},
            trace_id=f"{dataset}-{sequence:05d}-analytics",
            correlation_id=correlation_id,
        ),
    }


def write_standard_outputs(
    *,
    output_dir: Path,
    products: list[dict[str, Any]],
    judgments: list[dict[str, Any]] | None = None,
    dataset: str,
) -> dict[str, Path]:
    outputs = {
        "product_snapshots": output_dir / "product_snapshots.jsonl",
        "price_events": output_dir / "price_events.jsonl",
        "inventory_events": output_dir / "inventory_events.jsonl",
        "review_events": output_dir / "review_events.jsonl",
        "analytics_events": output_dir / "analytics_events.jsonl",
        "judgments": output_dir / "judgments.jsonl",
    }
    write_jsonl(outputs["product_snapshots"], products)
    event_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    stream_keys = {"price": "price_events", "inventory": "inventory_events", "reviews": "review_events", "analytics": "analytics_events"}
    for sequence, product in enumerate(products, start=1):
        for stream, event in snapshot_to_events(product, sequence, dataset=dataset).items():
            event_rows[stream_keys[stream]].append(event.model_dump(mode="json", exclude_none=True))
    for key in ["price_events", "inventory_events", "review_events", "analytics_events"]:
        write_jsonl(outputs[key], event_rows[key])
    write_jsonl(outputs["judgments"], judgments or [])
    return outputs


def popularity_from_counts(counts: Counter[str], product_id: str) -> float:
    if not counts:
        return 0.0
    max_count = max(counts.values()) or 1
    return round((counts[product_id] / max_count) * 100, 3)
