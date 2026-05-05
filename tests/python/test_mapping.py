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
        "seller",
        "stock",
        "price_info",
        "offers",
        "merchandising",
        "lifecycle",
        "is_deleted",
        "cohort_tags",
        "source_versions",
        "updated_at",
        "indexed_at",
        "catalog_text",
        "autosuggest",
        "embedding",
        "semantic_embedding",
    }

    assert required_fields.issubset(properties.keys())


def test_embedding_field_is_indexed_dense_vector():
    embedding = load_properties()["embedding"]

    assert embedding["type"] == "dense_vector"
    assert embedding["dims"] == 384
    assert embedding["index"] is True
    assert embedding["similarity"] == "cosine"

    semantic_embedding = load_properties()["semantic_embedding"]
    assert semantic_embedding["type"] == "dense_vector"
    assert semantic_embedding["dims"] == 384


def test_product_id_is_keyword():
    assert load_properties()["product_id"]["type"] == "keyword"


def test_title_has_text_mapping_and_keyword_subfield():
    title = load_properties()["title"]

    assert title["type"] == "text"
    assert title["fields"]["keyword"]["type"] == "keyword"
    assert title["fields"]["shingles"]["type"] == "search_as_you_type"
    assert load_properties()["autosuggest"]["type"] == "search_as_you_type"


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


def test_offers_are_nested_and_attribute_bags_stay_flattened():
    properties = load_properties()

    assert properties["offers"]["type"] == "nested"
    assert properties["offers"]["properties"]["seller_id"]["type"] == "keyword"
    assert properties["offers"]["properties"]["price"]["type"] == "scaled_float"
    assert properties["attributes"]["type"] == "flattened"


def test_seller_stock_price_merchandising_and_lifecycle_shapes():
    properties = load_properties()

    assert properties["seller"]["properties"]["seller_id"]["type"] == "keyword"
    assert properties["stock"]["properties"]["stock_quantity"]["type"] == "integer"
    assert properties["price_info"]["properties"]["amount"]["type"] == "scaled_float"
    assert properties["merchandising"]["properties"]["badges"]["type"] == "keyword"
    assert properties["lifecycle"]["properties"]["is_deleted"]["type"] == "boolean"
    assert properties["is_deleted"]["type"] == "boolean"


def test_cohort_tags_are_keyword_normalized():
    cohort_tags = load_properties()["cohort_tags"]

    assert cohort_tags["type"] == "keyword"
    assert cohort_tags["normalizer"] == "lowercase_normalizer"


def test_search_profile_is_text():
    assert load_properties()["search_profile"]["type"] == "text"
