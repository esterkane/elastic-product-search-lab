import json
from pathlib import Path

from scripts.dataset_etl import write_standard_outputs
from scripts.prepare_olist_sample import prepare_olist_sample
from scripts.prepare_retailrocket_sample import prepare_retailrocket_sample
from src.ingestion.event_schema import parse_product_source_event

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = PROJECT_ROOT / "data" / "sample" / "dataset_demo"


def test_write_standard_outputs_are_deterministic_and_event_schema_valid(tmp_path):
    products = [
        {
            "product_id": "P1",
            "title": "Demo Product",
            "description": "Demo",
            "brand": "Demo",
            "category": "Demo",
            "attributes": {"source_dataset": "fixture", "average_rating": 4.5, "review_count": 2},
            "price": 12.5,
            "currency": "USD",
            "availability": "in_stock",
            "popularity_score": 42,
            "seller_id": "seller-1",
            "updated_at": "2026-01-01T00:00:00Z",
        }
    ]

    outputs = write_standard_outputs(output_dir=tmp_path, products=products, judgments=[], dataset="fixture")
    first = {path.name: path.read_text(encoding="utf-8") for path in outputs.values()}
    write_standard_outputs(output_dir=tmp_path, products=products, judgments=[], dataset="fixture")
    second = {path.name: path.read_text(encoding="utf-8") for path in outputs.values()}

    assert first == second
    price_event = parse_product_source_event((tmp_path / "price_events.jsonl").read_text(encoding="utf-8"))
    review_event = parse_product_source_event((tmp_path / "review_events.jsonl").read_text(encoding="utf-8"))
    assert price_event.topic() == "product.price"
    assert review_event.payload == {"average_rating": 4.5, "review_count": 2}


def test_prepare_retailrocket_sample_uses_behavior_for_analytics_and_marks_synthetic_fields():
    events = [
        {"timestamp": "1", "visitorid": "v1", "event": "view", "itemid": "10"},
        {"timestamp": "2", "visitorid": "v1", "event": "addtocart", "itemid": "10"},
        {"timestamp": "3", "visitorid": "v2", "event": "transaction", "itemid": "20"},
    ]
    item_properties = [
        {"timestamp": "1", "itemid": "10", "property": "name", "value": "Trail Shoes"},
        {"timestamp": "2", "itemid": "10", "property": "price", "value": "59.9"},
        {"timestamp": "1", "itemid": "20", "property": "categoryid", "value": "running"},
    ]

    products, judgments = prepare_retailrocket_sample(events=events, item_properties=item_properties, max_products=2)

    assert judgments == []
    assert [product["product_id"] for product in products] == ["RR-20", "RR-10"]
    assert products[0]["popularity_score"] == 100
    assert products[1]["title"] == "Trail Shoes"
    assert products[1]["price"] == 59.9
    assert products[0]["attributes"]["synthetic_catalog_title"] is True
    assert products[0]["attributes"]["synthetic_price"] is True


def test_prepare_olist_sample_joins_orders_reviews_and_marks_synthetic_inventory():
    products = [
        {
            "product_id": "p1",
            "product_category_name": "housewares",
            "product_name_lenght": "10",
            "product_description_lenght": "30",
            "product_photos_qty": "2",
        }
    ]
    order_items = [
        {"order_id": "o1", "product_id": "p1", "seller_id": "s1", "price": "10.00"},
        {"order_id": "o2", "product_id": "p1", "seller_id": "s1", "price": "14.00"},
    ]
    reviews = [{"order_id": "o1", "review_score": "5"}, {"order_id": "o2", "review_score": "3"}]

    transformed, judgments = prepare_olist_sample(products=products, order_items=order_items, reviews=reviews)

    assert judgments == []
    assert transformed[0]["product_id"] == "OLIST-p1"
    assert transformed[0]["price"] == 12
    assert transformed[0]["currency"] == "BRL"
    assert transformed[0]["attributes"]["average_rating"] == 4
    assert transformed[0]["attributes"]["review_count"] == 2
    assert transformed[0]["attributes"]["synthetic_inventory"] is True


def test_standard_outputs_keep_judgments_separate_from_product_docs(tmp_path):
    product = {
        "product_id": "P-label-safe",
        "title": "Safe Product",
        "description": "",
        "brand": "Safe",
        "category": "Safe",
        "attributes": {"source_dataset": "fixture"},
        "price": 1,
        "currency": "USD",
        "availability": "in_stock",
        "popularity_score": 1,
        "seller_id": "seller",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    judgment = {"query": "safe", "product_id": "P-label-safe", "label": "exact", "grade": 3}

    write_standard_outputs(output_dir=tmp_path, products=[product], judgments=[judgment], dataset="fixture")

    product_doc = json.loads((tmp_path / "product_snapshots.jsonl").read_text(encoding="utf-8"))
    judgment_doc = json.loads((tmp_path / "judgments.jsonl").read_text(encoding="utf-8"))
    assert "grade" not in product_doc
    assert "label" not in product_doc
    assert judgment_doc == judgment


def test_tracked_dataset_demo_outputs_are_schema_valid_and_label_safe():
    expected_files = [
        "product_snapshots.jsonl",
        "price_events.jsonl",
        "inventory_events.jsonl",
        "review_events.jsonl",
        "analytics_events.jsonl",
        "judgments.jsonl",
    ]
    for file_name in expected_files:
        path = DEMO_DIR / file_name
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    products = [json.loads(line) for line in (DEMO_DIR / "product_snapshots.jsonl").read_text(encoding="utf-8").splitlines()]
    assert all("label" not in product and "grade" not in product for product in products)
    for file_name in ["price_events.jsonl", "inventory_events.jsonl", "review_events.jsonl", "analytics_events.jsonl"]:
        for line in (DEMO_DIR / file_name).read_text(encoding="utf-8").splitlines():
            parse_product_source_event(line)
