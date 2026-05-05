import argparse
import json
from pathlib import Path

import pytest

from scripts import reindex_and_switch

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class FakeIndices:
    def __init__(self):
        self.created: list[tuple[str, dict]] = []
        self.deleted: list[str] = []
        self.refreshed: list[str] = []
        self.alias_updates: list[dict] = []
        self.indices = {
            "products-v1": {"mappings": {"properties": {"product_id": {}, "catalog_text": {}, "search_profile": {}}}},
        }
        self.aliases = {
            "products-read": {"products-v1": {"aliases": {"products-read": {}}}},
            "products-write": {"products-v1": {"aliases": {"products-write": {}}}},
        }

    def get(self, index, features=None):
        assert index == "products-v*"
        assert features == "_aliases"
        return {name: {} for name in self.indices}

    def exists(self, index):
        return index in self.indices

    def create(self, index, body):
        self.indices[index] = {
            "mappings": body["mappings"],
            "settings": body["settings"],
        }
        self.created.append((index, body))

    def delete(self, index):
        self.deleted.append(index)
        self.indices.pop(index, None)

    def refresh(self, index):
        self.refreshed.append(index)

    def get_alias(self, name):
        if name not in self.aliases:
            raise KeyError(name)
        return self.aliases[name]

    def update_aliases(self, body):
        self.alias_updates.append(body)

    def get_mapping(self, index):
        return {index: self.indices[index]}


class FakeClient:
    def __init__(self, *, count=3):
        self.indices = FakeIndices()
        self.reindex_calls: list[dict] = []
        self.count_value = count

    def reindex(self, **kwargs):
        self.reindex_calls.append(kwargs)
        target = kwargs["body"]["dest"]["index"]
        if target not in self.indices.indices:
            self.indices.indices[target] = self.indices.indices["products-v1"]
        return {"created": self.count_value, "failures": []}

    def count(self, index, query):
        assert query == {"match_all": {}}
        return {"count": self.count_value}


def test_resolve_target_index_defaults_to_next_numeric_version():
    client = FakeClient()
    args = argparse.Namespace(target_index=None, target_version=None, index_prefix="products")

    assert reindex_and_switch.resolve_target_index(args, client) == "products-v2"


def test_reindex_source_uses_idempotent_index_writes():
    client = FakeClient()

    result = reindex_and_switch.reindex_source(client, source_index="products-read", target_index="products-v2")

    assert result == {"created": 3, "failures": []}
    assert client.reindex_calls[0]["body"]["conflicts"] == "proceed"
    assert client.reindex_calls[0]["body"]["dest"] == {"index": "products-v2", "op_type": "index"}
    assert client.reindex_calls[0]["wait_for_completion"] is True
    assert client.reindex_calls[0]["refresh"] is True


def test_smoke_checks_require_minimum_docs_and_mapping_fields():
    client = FakeClient(count=2)

    result = reindex_and_switch.run_smoke_checks(client, target_index="products-v1", min_docs=1)

    assert result["target_index"] == "products-v1"
    assert result["document_count"] == 2
    assert "product_id" in result["required_fields"]


def test_smoke_checks_reject_empty_index():
    client = FakeClient(count=0)

    with pytest.raises(RuntimeError, match="expected at least 1"):
        reindex_and_switch.run_smoke_checks(client, target_index="products-v1", min_docs=1)


def test_checked_in_ilm_json_is_valid_and_has_hot_warm_delete():
    for policy_path in (PROJECT_ROOT / "config" / "ilm").glob("*.json"):
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        phases = policy["policy"]["phases"]
        assert set(phases) == {"hot", "warm", "delete"}
        assert "rollover" in phases["hot"]["actions"]
        assert "delete" in phases["delete"]["actions"]
