import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.search.index_management import (
    DEFAULT_EVENT_ILM_POLICY,
    DEFAULT_PRODUCT_PIPELINE,
    event_data_stream_template_body,
    event_ilm_policy_body,
    install_product_index_resources,
    product_index_body,
    product_index_template_body,
    product_ingest_pipeline_body,
    product_suggest_index_body,
    search_policy_index_body,
    switch_read_alias,
    utc_build_id,
    versioned_product_index_name,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_versioned_index_name_is_deterministic():
    now = datetime(2026, 5, 4, 12, 45, tzinfo=timezone.utc)

    assert utc_build_id(now) == "202605041245"
    assert versioned_product_index_name("202605041245") == "products-v202605041245"


def test_product_index_body_sets_lab_shards_replicas_and_pipeline():
    body = product_index_body(shards=2, replicas=1)

    assert body["settings"]["number_of_shards"] == "2"
    assert body["settings"]["number_of_replicas"] == "1"
    assert body["settings"]["index.default_pipeline"] == DEFAULT_PRODUCT_PIPELINE
    assert body["mappings"]["dynamic"] == "strict"
    assert "catalog_text" in body["mappings"]["properties"]
    json.dumps(body)


def test_product_template_is_separate_from_event_template():
    template = product_index_template_body(shards=1, replicas=0)

    assert template["index_patterns"] == ["products-v*"]
    assert template["template"]["mappings"]["dynamic"] == "strict"
    assert template["_meta"]["component"] == "search_catalog_index"
    json.dumps(template)


def test_product_ingest_pipeline_is_minimal_and_metadata_only():
    pipeline = product_ingest_pipeline_body()

    processors = pipeline["processors"]
    assert processors[0]["uppercase"]["field"] == "currency"
    assert processors[1]["uppercase"]["field"] == "price_info.currency"
    assert processors[2]["foreach"]["field"] == "offers"
    assert processors[3]["lowercase"]["field"] == "availability"
    assert processors[4]["lowercase"]["field"] == "stock.availability"
    assert processors[5]["set"]["field"] == "indexed_at"
    assert processors[5]["set"]["if"] == "ctx.indexed_at == null"
    assert processors[6]["set"]["field"] == "schema_version"
    assert processors[7]["remove"]["field"] == ["raw_event", "debug", "_debug", "_tmp"]
    assert len(processors) == 8
    json.dumps(pipeline)


def test_checked_in_product_pipeline_json_matches_generated_body():
    pipeline_path = PROJECT_ROOT / "config" / "products-minimal-normalization.pipeline.json"

    with pipeline_path.open(encoding="utf-8") as pipeline_file:
        checked_in_pipeline = json.load(pipeline_file)

    assert checked_in_pipeline == product_ingest_pipeline_body()


def test_event_ilm_and_data_stream_template_are_serializable():
    policy = event_ilm_policy_body(retention_days=30)
    template = event_data_stream_template_body(shards=1, replicas=0)

    assert policy["policy"]["phases"]["delete"]["min_age"] == "30d"
    assert template["data_stream"] == {}
    assert template["template"]["settings"]["index.lifecycle.name"] == DEFAULT_EVENT_ILM_POLICY
    assert template["template"]["mappings"]["properties"]["payload"]["type"] == "flattened"
    assert template["_meta"]["component"] == "event_audit_data_stream"
    json.dumps(policy)
    json.dumps(template)


def test_product_suggest_index_body_is_separate_and_serializable():
    body = product_suggest_index_body(shards=1, replicas=0)

    assert body["mappings"]["dynamic"] == "strict"
    assert body["mappings"]["properties"]["suggest_text"]["type"] == "search_as_you_type"
    assert "price" not in body["mappings"]["properties"]
    assert body["settings"]["number_of_replicas"] == "0"
    json.dumps(body)


def test_search_policy_index_body_is_serializable():
    body = search_policy_index_body(shards=1, replicas=0)

    assert body["mappings"]["dynamic"] == "strict"
    assert body["mappings"]["properties"]["type"]["type"] == "keyword"
    assert body["mappings"]["properties"]["priority"]["type"] == "integer"
    assert body["mappings"]["properties"]["productIds"]["type"] == "keyword"
    json.dumps(body)


def test_event_ilm_retention_must_be_positive():
    with pytest.raises(ValueError, match="retention_days"):
        event_ilm_policy_body(retention_days=0)


class FakeIndices:
    def __init__(self):
        self.existing = {"products-v-old", "products-v-new"}
        self.aliases = {"products-v-old": {"aliases": {"products-read": {}}}}
        self.alias_updates = []
        self.templates = []

    def exists(self, index):
        return index in self.existing

    def get_alias(self, name):
        if name != "products-read":
            raise KeyError(name)
        return self.aliases

    def update_aliases(self, body):
        self.alias_updates.append(body)

    def put_index_template(self, name, body):
        self.templates.append((name, body))


class FakeIngest:
    def __init__(self):
        self.pipelines = []

    def put_pipeline(self, id, body):
        self.pipelines.append((id, body))


class FakeIlm:
    def __init__(self):
        self.policies = []

    def put_lifecycle(self, name, body):
        self.policies.append((name, body))


class FakeClient:
    def __init__(self):
        self.indices = FakeIndices()
        self.ingest = FakeIngest()
        self.ilm = FakeIlm()


def test_switch_read_alias_removes_existing_indices_and_adds_target_atomically():
    client = FakeClient()

    result = switch_read_alias(client, read_alias="products-read", target_index="products-v-new")

    assert result == {
        "alias": "products-read",
        "target_index": "products-v-new",
        "previous_indices": ["products-v-old"],
    }
    assert client.indices.alias_updates == [
        {
            "actions": [
                {"remove": {"index": "products-v-old", "alias": "products-read"}},
                {"add": {"index": "products-v-new", "alias": "products-read"}},
            ]
        }
    ]


def test_switch_read_alias_rejects_missing_target():
    client = FakeClient()

    with pytest.raises(ValueError, match="does not exist"):
        switch_read_alias(client, read_alias="products-read", target_index="products-v-missing")


def test_install_product_index_resources_writes_separate_resources():
    client = FakeClient()

    install_product_index_resources(client, shards=1, replicas=0, event_retention_days=21)

    assert client.ingest.pipelines[0][0] == DEFAULT_PRODUCT_PIPELINE
    assert len(client.indices.templates) == 2
    assert client.indices.templates[0][1]["_meta"]["component"] == "search_catalog_index"
    assert client.indices.templates[1][1]["_meta"]["component"] == "event_audit_data_stream"
    assert client.ilm.policies[0][1]["policy"]["phases"]["delete"]["min_age"] == "21d"
