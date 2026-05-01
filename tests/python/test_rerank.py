from src.search.rerank import PlaceholderTextSimilarityReranker, SearchResult, metric_delta


def test_placeholder_reranker_preserves_candidate_ids():
    candidates = [
        SearchResult(product_id="P1", title="leather wallet", score=2.0),
        SearchResult(product_id="P2", title="wireless mouse", score=1.0),
    ]

    reranked = PlaceholderTextSimilarityReranker().rerank("wireless mouse", candidates)

    assert sorted(candidate.product_id for candidate in reranked) == ["P1", "P2"]
    assert reranked[0].product_id == "P2"


def test_placeholder_reranker_is_deterministic():
    candidates = [
        SearchResult(product_id="P1", title="usb c cable", score=1.0),
        SearchResult(product_id="P2", title="usb c charger", score=1.0),
        SearchResult(product_id="P3", title="running shoes", score=1.0),
    ]
    reranker = PlaceholderTextSimilarityReranker()

    first = reranker.rerank("usb c charger", candidates)
    second = reranker.rerank("usb c charger", candidates)

    assert [candidate.product_id for candidate in first] == [candidate.product_id for candidate in second]


def test_metric_delta_calculation():
    before = {"ndcg_at_10": 0.4, "mrr": 0.5}
    after = {"ndcg_at_10": 0.65, "mrr": 0.25, "precision_at_10": 0.3}

    delta = metric_delta(before, after)

    assert round(delta["ndcg_at_10"], 3) == 0.25
    assert round(delta["mrr"], 3) == -0.25
    assert round(delta["precision_at_10"], 3) == 0.3
