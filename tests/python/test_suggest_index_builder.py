import json

import pytest

from scripts.build_product_suggest_index import build_operations, iter_snapshots, suggest_document


def test_suggest_document_uses_canonical_snapshot_fields():
    document = suggest_document(
        {
            "product_id": "P1",
            "title": "Wireless Mouse",
            "brand": "Contoso",
            "category": "Accessories",
            "popularity_score": 12.5,
            "updated_at": "2026-01-01T00:00:00Z",
        }
    )

    assert document == {
        "product_id": "P1",
        "suggest_text": "Wireless Mouse Contoso Accessories",
        "title": "Wireless Mouse",
        "brand": "Contoso",
        "category": "Accessories",
        "popularity_score": 12.5,
        "updated_at": "2026-01-01T00:00:00Z",
    }


def test_build_operations_targets_suggest_index():
    operations = build_operations([{"product_id": "P1", "title": "Mouse"}], "product-suggest")

    assert operations == [
        {"index": {"_index": "product-suggest", "_id": "P1"}},
        {
            "product_id": "P1",
            "suggest_text": "Mouse",
            "title": "Mouse",
            "brand": "",
            "category": "",
            "popularity_score": 0,
            "updated_at": "1970-01-01T00:00:00Z",
        },
    ]


def test_iter_snapshots_reports_bad_json_line(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text(json.dumps({"product_id": "P1"}) + "\n{bad json}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="line 2"):
        iter_snapshots(path)
