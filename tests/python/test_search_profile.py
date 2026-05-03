from src.ingestion.search_profile import build_search_profile
from scripts.evaluate_relevance import enriched_profile_query


def test_search_profile_enrichment_uses_product_fields_and_inferred_use_cases():
    product = {
        "title": "Sony WH-CH720N Wireless Noise Canceling Headphones",
        "brand": "Sony",
        "category": "Electronics > Headphones",
        "description": "Bluetooth headphones with active noise canceling.",
        "attributes": {"color": "black", "connectivity": "bluetooth", "style": "over-ear"},
    }

    profile = build_search_profile(product)

    assert "Product: Sony WH-CH720N Wireless Noise Canceling Headphones." in profile
    assert "Brand: Sony." in profile
    assert "Category: Electronics > Headphones." in profile
    assert "Useful for: travel, office, commuting, music." in profile
    assert "Attributes: black, bluetooth, over-ear." in profile


def test_search_profile_handles_missing_fields_safely():
    profile = build_search_profile({"title": "Minimal Product", "attributes": None})

    assert profile == "Product: Minimal Product."


def test_enriched_profile_strategy_builds_valid_es_query():
    query = enriched_profile_query("wireless headphones", 5)

    assert query["size"] == 5
    multi_match = query["query"]["multi_match"]
    assert multi_match["query"] == "wireless headphones"
    assert "search_profile^3" in multi_match["fields"]
    assert "title^2" in multi_match["fields"]
    assert multi_match["operator"] == "or"
