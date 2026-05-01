from src.embeddings.embedder import EMBEDDING_DIMS, build_embedding_text
from src.search.hybrid_search import evaluate_rankings, rrf_fuse


class MockEmbedder:
    dims = EMBEDDING_DIMS

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[1.0 / EMBEDDING_DIMS] * EMBEDDING_DIMS for _ in texts]


def test_rrf_fusion_combines_rankings_and_preserves_consistent_winners():
    fused = rrf_fuse([["A", "B", "C"], ["B", "A", "D"]], size=3, rank_constant=60)

    assert fused == ["A", "B", "C"]


def test_embedding_vector_shape_with_mocked_embedder():
    product = {"title": "Wireless Mouse", "brand": "Contoso", "category": "Accessories", "description": "Quiet mouse"}
    text = build_embedding_text(product)
    vector = MockEmbedder().encode([text])[0]

    assert text == "Wireless Mouse Contoso Accessories Quiet mouse"
    assert len(vector) == EMBEDDING_DIMS


def test_evaluation_comparison_with_fixed_inputs():
    rankings = {
        "wireless mouse": {
            "baseline_lexical": ["B", "A", "C"],
            "boosted_lexical": ["A", "B", "C"],
            "hybrid_rrf": ["A", "C", "B"],
        }
    }
    judgments = {"wireless mouse": {"A": 3, "B": 0, "C": 1}}

    metrics = evaluate_rankings(rankings, judgments, k=3)

    assert metrics["baseline_lexical"]["mrr"] == 0.5
    assert metrics["boosted_lexical"]["mrr"] == 1.0
    assert metrics["hybrid_rrf"]["precision_at_10"] == 2 / 3
    assert metrics["hybrid_rrf"]["ndcg_at_10"] > metrics["baseline_lexical"]["ndcg_at_10"]