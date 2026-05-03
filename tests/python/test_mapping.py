import json
from pathlib import Path

MAPPING_PATH = Path(__file__).resolve().parents[2] / "src" / "search" / "product_mapping.json"


def load_properties():
    with MAPPING_PATH.open(encoding="utf-8") as mapping_file:
        mapping = json.load(mapping_file)
    return mapping["mappings"]["properties"]


def test_required_fields_exist():
    properties = load_properties()
    required_fields = {
        "product_id",
        "title",
        "description",
        "brand",
        "category",
        "attributes",
        "price",
        "currency",
        "availability",
        "popularity_score",
        "seller_id",
        "source_versions",
        "updated_at",
        "indexed_at",
        "catalog_text",
        "embedding",
    }

    assert required_fields.issubset(properties.keys())


def test_embedding_field_is_indexed_dense_vector():
    embedding = load_properties()["embedding"]

    assert embedding["type"] == "dense_vector"
    assert embedding["dims"] == 384
    assert embedding["index"] is True
    assert embedding["similarity"] == "cosine"


def test_product_id_is_keyword():
    assert load_properties()["product_id"]["type"] == "keyword"


def test_title_has_text_mapping_and_keyword_subfield():
    title = load_properties()["title"]

    assert title["type"] == "text"
    assert title["fields"]["keyword"]["type"] == "keyword"


def test_brand_and_category_use_keyword_normalized_fields():
    properties = load_properties()

    assert properties["brand"]["type"] == "keyword"
    assert properties["brand"]["normalizer"] == "lowercase_normalizer"
    assert properties["category"]["type"] == "keyword"
    assert properties["category"]["normalizer"] == "lowercase_normalizer"


def test_attributes_and_source_versions_are_flattened():
    properties = load_properties()

    assert properties["attributes"]["type"] == "flattened"
    assert properties["source_versions"]["type"] == "flattened"


def test_search_profile_is_text():
    assert load_properties()["search_profile"]["type"] == "text"
