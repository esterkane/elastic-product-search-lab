"""Versioned per-source product state for canonical document assembly."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.ingestion.canonical_types import SOURCE_OWNED_FIELDS, SourceClock, SourceName, SourceUpdate

SOURCE_PRECEDENCE: tuple[SourceName, ...] = (
    "catalog",
    "seller",
    "price",
    "inventory",
    "stock",
    "analytics",
    "reviews",
    "merchandising",
    "lifecycle",
)


@dataclass(frozen=True)
class SourceRecord:
    """Latest accepted state from one source-owned product-data domain."""

    version: SourceClock
    fields: dict[str, Any]
    updated_at: datetime | None = None


@dataclass
class ProductSourceState:
    """Canonical pre-indexing state for one product across upstream sources."""

    product_id: str
    records: dict[SourceName, SourceRecord] = field(default_factory=dict)
    extra_source_versions: dict[str, SourceClock] = field(default_factory=dict)

    def apply(self, update: SourceUpdate) -> bool:
        """Apply a source-owned update when it is newer than current state."""

        if update.product_id != self.product_id:
            raise ValueError(f"update product_id {update.product_id!r} does not match state product_id {self.product_id!r}")

        unknown_fields = set(update.fields) - SOURCE_OWNED_FIELDS[update.source]
        if unknown_fields:
            fields = ", ".join(sorted(unknown_fields))
            raise ValueError(f"{update.source} update contains non-owned field(s): {fields}")

        current = self.records.get(update.source)
        if current and not source_version_is_newer(update.source_version, current.version):
            return False

        self.records[update.source] = SourceRecord(
            version=update.source_version,
            fields=dict(update.fields),
            updated_at=update.updated_at,
        )
        return True

    def source_versions(self) -> dict[str, str]:
        """Return deterministic source clocks for index storage."""

        versions = {source: clock_to_string(record.version) for source, record in self.records.items()}
        for source, version in self.extra_source_versions.items():
            versions[source] = clock_to_string(version)
        return dict(sorted(versions.items()))

    def merged_fields(self) -> dict[str, Any]:
        """Merge source-owned fields with explicit domain precedence."""

        merged: dict[str, Any] = {"product_id": self.product_id}
        for source in SOURCE_PRECEDENCE:
            record = self.records.get(source)
            if record:
                merged.update(record.fields)
        return merged

    def source_attribution(self) -> dict[str, str]:
        """Return field-to-source metadata for reviewable canonical output."""

        attribution: dict[str, str] = {"product_id": "canonical"}
        for source in SOURCE_PRECEDENCE:
            record = self.records.get(source)
            if not record:
                continue
            source_clock = f"{source}@{clock_to_string(record.version)}"
            for field_name in sorted(record.fields):
                attribution[field_name] = source_clock
        return dict(sorted(attribution.items()))

    def latest_updated_at(self) -> datetime | None:
        timestamps = [record.updated_at for record in self.records.values() if record.updated_at]
        return max(timestamps) if timestamps else None


def clock_to_string(value: SourceClock) -> str:
    return str(value)


def source_version_is_newer(candidate: SourceClock, current: SourceClock) -> bool:
    candidate_int = parse_int_clock(candidate)
    current_int = parse_int_clock(current)
    if candidate_int is not None and current_int is not None:
        return candidate_int > current_int
    return clock_to_string(candidate) > clock_to_string(current)


def parse_int_clock(value: SourceClock) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
