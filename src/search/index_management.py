"""Index, alias, template, and lifecycle helpers for product search builds."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCT_MAPPING_PATH = PROJECT_ROOT / "src" / "search" / "product_mapping.json"

DEFAULT_PRODUCT_INDEX_PREFIX = "products"
DEFAULT_READ_ALIAS = "products-read"
DEFAULT_BUILD_ALIAS = "products-build"
DEFAULT_PRODUCT_PIPELINE = "products-minimal-normalization"
DEFAULT_PRODUCT_TEMPLATE = "products-catalog-template"
DEFAULT_EVENT_TEMPLATE = "product-events-template"
DEFAULT_EVENT_ILM_POLICY = "product-events-retention"
DEFAULT_EVENT_DATA_STREAM = "product-events"
DEFAULT_SUGGEST_INDEX = "product-suggest"
DEFAULT_POLICY_INDEX = "search-policies"


def utc_build_id(now: datetime | None = None) -> str:
    timestamp = now or datetime.now(timezone.utc)
    return timestamp.astimezone(timezone.utc).strftime("%Y%m%d%H%M")


def versioned_product_index_name(build_id: str, prefix: str = DEFAULT_PRODUCT_INDEX_PREFIX) -> str:
    normalized = build_id.strip()
    if not normalized:
        raise ValueError("build_id must not be empty")
    return f"{prefix}-v{normalized}"


def load_product_mapping(path: Path = PRODUCT_MAPPING_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as mapping_file:
        return json.load(mapping_file)


def product_index_body(
    *,
    shards: int = 1,
    replicas: int = 0,
    default_pipeline: str | None = DEFAULT_PRODUCT_PIPELINE,
) -> dict[str, Any]:
    body = load_product_mapping()
    settings = dict(body.get("settings", {}))
    settings["number_of_shards"] = str(shards)
    settings["number_of_replicas"] = str(replicas)
    if default_pipeline:
        settings["index.default_pipeline"] = default_pipeline
    body["settings"] = settings
    return body


def product_ingest_pipeline_body() -> dict[str, Any]:
    return {
        "description": "Minimal last-mile product document normalization. Business merging happens before indexing.",
        "processors": [
            {"uppercase": {"field": "currency", "ignore_missing": True}},
            {"lowercase": {"field": "availability", "ignore_missing": True}},
            {
                "set": {
                    "field": "indexed_at",
                    "value": "{{_ingest.timestamp}}",
                    "if": "ctx.indexed_at == null",
                }
            },
        ],
    }


def product_index_template_body(
    *,
    shards: int = 1,
    replicas: int = 0,
    default_pipeline: str = DEFAULT_PRODUCT_PIPELINE,
    index_patterns: list[str] | None = None,
) -> dict[str, Any]:
    index_body = product_index_body(shards=shards, replicas=replicas, default_pipeline=default_pipeline)
    return {
        "index_patterns": index_patterns or ["products-v*"],
        "priority": 200,
        "template": {
            "settings": index_body["settings"],
            "mappings": index_body["mappings"],
        },
        "_meta": {
            "component": "search_catalog_index",
            "description": "Versioned product search indices built from canonical product snapshots.",
        },
    }


def event_ilm_policy_body(*, retention_days: int = 14) -> dict[str, Any]:
    if retention_days < 1:
        raise ValueError("retention_days must be at least 1")
    return {
        "policy": {
            "phases": {
                "hot": {
                    "actions": {
                        "rollover": {
                            "max_age": "1d",
                            "max_primary_shard_size": "10gb",
                        }
                    }
                },
                "delete": {
                    "min_age": f"{retention_days}d",
                    "actions": {"delete": {}},
                },
            }
        }
    }


def event_data_stream_template_body(
    *,
    ilm_policy: str = DEFAULT_EVENT_ILM_POLICY,
    shards: int = 1,
    replicas: int = 0,
    index_patterns: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "index_patterns": index_patterns or ["product-events*"],
        "data_stream": {},
        "priority": 150,
        "template": {
            "settings": {
                "index.lifecycle.name": ilm_policy,
                "number_of_shards": str(shards),
                "number_of_replicas": str(replicas),
            },
            "mappings": {
                "dynamic": True,
                "properties": {
                    "@timestamp": {"type": "date"},
                    "event_time": {"type": "date"},
                    "product_id": {"type": "keyword"},
                    "source": {"type": "keyword"},
                    "event_type": {"type": "keyword"},
                    "trace_id": {"type": "keyword"},
                    "correlation_id": {"type": "keyword"},
                    "error_kind": {"type": "keyword"},
                    "code": {"type": "keyword"},
                    "payload": {"type": "flattened"},
                    "metadata": {"type": "flattened"},
                    "raw_event": {"type": "text"},
                    "message": {"type": "text"},
                }
            },
        },
        "_meta": {
            "component": "event_audit_data_stream",
            "description": "Time-based event/audit storage kept separate from the product content index.",
        },
    }


def product_suggest_index_body(*, shards: int = 1, replicas: int = 0) -> dict[str, Any]:
    return {
        "settings": {
            "number_of_shards": str(shards),
            "number_of_replicas": str(replicas),
            "analysis": {
                "normalizer": {
                    "lowercase_normalizer": {
                        "type": "custom",
                        "filter": ["lowercase", "asciifolding"],
                    }
                }
            },
        },
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "product_id": {"type": "keyword"},
                "suggest_text": {"type": "search_as_you_type"},
                "title": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
                "brand": {"type": "keyword", "normalizer": "lowercase_normalizer"},
                "category": {"type": "keyword", "normalizer": "lowercase_normalizer"},
                "popularity_score": {"type": "float"},
                "updated_at": {"type": "date"},
            },
        },
    }


def search_policy_index_body(*, shards: int = 1, replicas: int = 0) -> dict[str, Any]:
    return {
        "settings": {
            "number_of_shards": str(shards),
            "number_of_replicas": str(replicas),
        },
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "id": {"type": "keyword"},
                "enabled": {"type": "boolean"},
                "type": {"type": "keyword"},
                "priority": {"type": "integer"},
                "queryMatch": {"type": "keyword"},
                "productIds": {"type": "keyword"},
                "category": {"type": "keyword"},
                "excludeProductIds": {"type": "keyword"},
                "excludeBrands": {"type": "keyword"},
                "boost": {"type": "float"},
                "rewriteQuery": {"type": "text"},
                "routingHint": {"type": "keyword"},
                "reason": {"type": "text"},
                "startsAt": {"type": "date"},
                "endsAt": {"type": "date"},
                "updatedBy": {"type": "keyword"},
                "updatedAt": {"type": "date"},
            },
        },
    }


def install_product_index_resources(
    client: Any,
    *,
    product_template: str = DEFAULT_PRODUCT_TEMPLATE,
    product_pipeline: str = DEFAULT_PRODUCT_PIPELINE,
    event_template: str = DEFAULT_EVENT_TEMPLATE,
    event_ilm_policy: str = DEFAULT_EVENT_ILM_POLICY,
    shards: int = 1,
    replicas: int = 0,
    event_retention_days: int = 14,
) -> None:
    client.ingest.put_pipeline(id=product_pipeline, body=product_ingest_pipeline_body())
    client.indices.put_index_template(
        name=product_template,
        body=product_index_template_body(shards=shards, replicas=replicas, default_pipeline=product_pipeline),
    )
    client.ilm.put_lifecycle(name=event_ilm_policy, body=event_ilm_policy_body(retention_days=event_retention_days))
    client.indices.put_index_template(
        name=event_template,
        body=event_data_stream_template_body(ilm_policy=event_ilm_policy, shards=shards, replicas=replicas),
    )


def create_product_index(
    client: Any,
    index_name: str,
    *,
    recreate: bool = False,
    shards: int = 1,
    replicas: int = 0,
    default_pipeline: str | None = DEFAULT_PRODUCT_PIPELINE,
) -> None:
    exists = client.indices.exists(index=index_name)
    if exists and recreate:
        client.indices.delete(index=index_name)
        exists = False
    if exists:
        return
    client.indices.create(
        index=index_name,
        body=product_index_body(shards=shards, replicas=replicas, default_pipeline=default_pipeline),
    )


def point_build_alias(client: Any, *, build_alias: str, target_index: str) -> None:
    actions: list[dict[str, Any]] = []
    try:
        existing = client.indices.get_alias(name=build_alias)
    except Exception:  # noqa: BLE001 - Elasticsearch raises when the alias does not exist.
        existing = {}
    for index_name in existing:
        actions.append({"remove": {"index": index_name, "alias": build_alias}})
    actions.append({"add": {"index": target_index, "alias": build_alias}})
    client.indices.update_aliases(body={"actions": actions})


def switch_read_alias(client: Any, *, read_alias: str, target_index: str) -> dict[str, Any]:
    if not client.indices.exists(index=target_index):
        raise ValueError(f"Target index '{target_index}' does not exist")

    try:
        existing = client.indices.get_alias(name=read_alias)
    except Exception:  # noqa: BLE001 - Elasticsearch raises when the alias does not exist.
        existing = {}

    actions: list[dict[str, Any]] = [
        {"remove": {"index": index_name, "alias": read_alias}} for index_name in sorted(existing)
    ]
    actions.append({"add": {"index": target_index, "alias": read_alias}})
    client.indices.update_aliases(body={"actions": actions})
    return {"alias": read_alias, "target_index": target_index, "previous_indices": sorted(existing)}
