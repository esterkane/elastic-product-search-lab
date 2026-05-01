from __future__ import annotations

from typing import Any

VectorMetadata = dict[str, str | int | float | bool | None]

FILTERABLE_METADATA_FIELDS: tuple[str, ...] = (
    "repo",
    "path",
    "heading_path",
    "content_type",
    "license_family",
)

BOOSTABLE_METADATA_FIELDS: tuple[str, ...] = FILTERABLE_METADATA_FIELDS


def normalize_metadata(
    metadata: dict[str, Any] | None,
    *,
    source_url: str | None = None,
    repo: str | None = None,
    path: str | None = None,
) -> VectorMetadata:
    normalized: VectorMetadata = {}
    raw = dict(metadata or {})

    for key, value in raw.items():
        if value is None:
            continue
        normalized_key = str(key).strip()
        if not normalized_key:
            continue
        normalized[normalized_key] = normalize_metadata_value(normalized_key, value)

    normalized["repo"] = normalize_metadata_value("repo", normalized.get("repo") or repo or "unknown")
    normalized["path"] = normalize_metadata_value("path", normalized.get("path") or path or "unknown")
    normalized["content_type"] = normalize_metadata_value("content_type", normalized.get("content_type") or "unknown")
    normalized["license_family"] = normalize_metadata_value(
        "license_family",
        normalized.get("license_family") or "unknown",
    )

    if source_url and not normalized.get("source_url"):
        normalized["source_url"] = source_url.strip()
    if "chunk_index" in normalized:
        normalized["chunk_index"] = normalize_chunk_index(normalized["chunk_index"])
    return normalized


def normalize_metadata_value(key: str, value: Any) -> str | int | float | bool | None:
    if value is None:
        return None
    if key == "chunk_index":
        return normalize_chunk_index(value)
    if isinstance(value, bool | int | float):
        return value

    text = str(value).strip()
    if key == "path":
        return text.replace("\\", "/").strip("/")
    if key == "license_family":
        return text.replace(" ", "-").lower()
    if key in {"repo", "content_type"}:
        return text.replace(" ", "_").lower()
    return text


def normalize_chunk_index(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def normalize_filters(filters: dict[str, Any] | None) -> dict[str, object] | None:
    if not filters:
        return None

    normalized: dict[str, object] = {}
    for key in sorted(filters):
        if key not in FILTERABLE_METADATA_FIELDS:
            continue
        value = filters[key]
        if value is None or value == "":
            continue
        normalized_value = normalize_filter_value(key, value)
        if normalized_value not in (None, "", []):
            normalized[key] = normalized_value
    return normalized or None


def normalize_filter_value(key: str, value: Any) -> object:
    if isinstance(value, list | tuple | set):
        values = [
            normalize_metadata_value(key, item)
            for item in value
            if item is not None and str(item).strip()
        ]
        return sorted({str(item) for item in values if item is not None})
    return normalize_metadata_value(key, value)


def normalize_boosts(boosts: dict[str, dict[str, Any]] | None) -> dict[str, dict[str, float]]:
    if not boosts:
        return {}

    normalized: dict[str, dict[str, float]] = {}
    for field in sorted(boosts):
        if field not in BOOSTABLE_METADATA_FIELDS:
            continue
        values: dict[str, float] = {}
        for raw_value, raw_weight in sorted((boosts.get(field) or {}).items()):
            value = normalize_metadata_value(field, raw_value)
            if value is None or str(value) == "":
                continue
            try:
                weight = max(0.0, float(raw_weight))
            except (TypeError, ValueError):
                continue
            if weight:
                values[str(value)] = weight
        if values:
            normalized[field] = values
    return normalized


def metadata_boost_score(metadata: dict[str, Any], boosts: dict[str, dict[str, float]]) -> float:
    if not boosts:
        return 0.0

    normalized = normalize_metadata(metadata)
    score = 0.0
    for field, values in boosts.items():
        value = normalized.get(field)
        if value is not None:
            score += values.get(str(value), 0.0)
    return score
