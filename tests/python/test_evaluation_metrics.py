import math

import pytest

from src.evaluation.judgments import label_to_grade, load_judgments
from src.evaluation.metrics import dcg_at_k, ndcg_at_k, precision_at_k, reciprocal_rank


def test_label_to_grade():
    assert label_to_grade("exact") == 3
    assert label_to_grade("substitute") == 2
    assert label_to_grade("complement") == 1
    assert label_to_grade("irrelevant") == 0


def test_precision_at_k_counts_relevant_documents():
    ranked = ["A", "B", "C", "D"]
    judgments = {"A": 3, "B": 0, "C": 1, "D": 0}

    assert precision_at_k(ranked, judgments, 4) == 0.5
    assert precision_at_k(ranked, judgments, 2) == 0.5


def test_precision_at_k_handles_empty_results_and_large_k():
    assert precision_at_k([], {"A": 3}, 10) == 0.0
    assert precision_at_k(["A"], {"A": 3}, 10) == 1.0


def test_precision_at_k_rejects_invalid_k():
    with pytest.raises(ValueError):
        precision_at_k(["A"], {"A": 3}, 0)


def test_mrr_uses_first_relevant_result():
    assert reciprocal_rank(["A", "B", "C"], {"C": 3}) == 1 / 3
    assert reciprocal_rank(["A", "B"], {"C": 3}) == 0.0
    assert reciprocal_rank([], {"A": 3}) == 0.0


def test_dcg_known_values():
    relevances = [3, 2, 1]
    expected = 7 / math.log2(2) + 3 / math.log2(3) + 1 / math.log2(4)

    assert dcg_at_k(relevances, 3) == pytest.approx(expected)


def test_ndcg_known_values():
    ranked = ["B", "A", "C"]
    judgments = {"A": 3, "B": 2, "C": 1}
    actual = dcg_at_k([2, 3, 1], 3)
    ideal = dcg_at_k([3, 2, 1], 3)

    assert ndcg_at_k(ranked, judgments, 3) == pytest.approx(actual / ideal)


def test_ndcg_handles_no_relevant_docs_empty_results_and_large_k():
    assert ndcg_at_k(["A", "B"], {"A": 0, "B": 0}, 10) == 0.0
    assert ndcg_at_k([], {"A": 3}, 10) == 0.0
    assert ndcg_at_k(["A"], {"A": 3}, 10) == 1.0


def test_load_judgments(tmp_path):
    path = tmp_path / "judgments.jsonl"
    path.write_text(
        '{"query":"mouse","product_id":"P1","label":"exact"}\n'
        '{"query":"mouse","product_id":"P2","label":"substitute","grade":2}\n',
        encoding="utf-8",
    )

    assert load_judgments(path) == {"mouse": {"P1": 3, "P2": 2}}