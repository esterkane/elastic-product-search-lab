import json

from scripts.prepare_esci_sample import map_esci_label, prepare_esci_sample, read_records, write_jsonl


def test_map_esci_label_supports_codes_and_names():
    assert map_esci_label("E") == 3
    assert map_esci_label("Exact") == 3
    assert map_esci_label("S") == 2
    assert map_esci_label("Substitute") == 2
    assert map_esci_label("C") == 1
    assert map_esci_label("Complement") == 1
    assert map_esci_label("I") == 0
    assert map_esci_label("Irrelevant") == 0


def test_prepare_esci_sample_filters_english_and_transforms_records():
    products = [
        {
            "product_id": "P1",
            "product_title": "Wireless Mouse",
            "product_description": "Quiet wireless mouse",
            "product_bullet_point": "USB receiver included",
            "product_brand": "Contoso",
            "product_color": "Black",
            "product_locale": "us",
        },
        {
            "product_id": "P2",
            "product_title": "Japanese Product",
            "product_description": "Filtered out",
            "product_brand": "Brand",
            "product_locale": "jp",
        },
    ]
    examples = [
        {"query": "wireless mouse", "product_id": "P1", "product_locale": "us", "esci_label": "E"},
        {"query": "wireless mouse", "product_id": "P2", "product_locale": "jp", "esci_label": "S"},
    ]

    transformed_products, judgments = prepare_esci_sample(products, examples, max_queries=100, max_products=1000)

    assert len(transformed_products) == 1
    assert transformed_products[0]["product_id"] == "P1"
    assert transformed_products[0]["title"] == "Wireless Mouse"
    assert transformed_products[0]["attributes"] == {"product_color": "Black", "product_locale": "us"}
    assert judgments == [{"query": "wireless mouse", "product_id": "P1", "label": "E", "grade": 3}]


def test_prepare_esci_sample_caps_queries_and_products():
    products = [
        {"product_id": "P1", "product_title": "Mouse", "product_brand": "A", "product_locale": "us"},
        {"product_id": "P2", "product_title": "Keyboard", "product_brand": "A", "product_locale": "us"},
    ]
    examples = [
        {"query": "mouse", "product_id": "P1", "product_locale": "us", "esci_label": "E"},
        {"query": "keyboard", "product_id": "P2", "product_locale": "us", "esci_label": "E"},
    ]

    transformed_products, judgments = prepare_esci_sample(products, examples, max_queries=1, max_products=1, seed=1)

    assert len(transformed_products) == 1
    assert len(judgments) == 1


def test_read_and_write_jsonl_fixture(tmp_path):
    path = tmp_path / "products.jsonl"
    write_jsonl(path, [{"product_id": "P1", "title": "Mouse"}])

    assert read_records(path) == [{"product_id": "P1", "title": "Mouse"}]
    assert json.loads(path.read_text(encoding="utf-8"))["product_id"] == "P1"