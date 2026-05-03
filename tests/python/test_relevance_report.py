from pathlib import Path

from src.evaluation.metrics import ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank
from src.evaluation.relevance_report import (
    build_report,
    evaluate_ranking,
    load_product_search_judgments,
    pending_rows,
    write_json_report,
    write_markdown_report,
)


def test_relevance_metrics_include_precision_recall_mrr_and_ndcg():
    judgments = {"P1": 3, "P2": 2, "P3": 0, "P4": 1}
    ranking = ["P3", "P2", "P5", "P1", "P4"]

    assert precision_at_k(ranking, judgments, 5) == 3 / 5
    assert recall_at_k(ranking, judgments, 5) == 1.0
    assert reciprocal_rank(ranking[:10], judgments) == 1 / 2
    assert round(ndcg_at_k(ranking, judgments, 10), 3) == 0.564


def test_report_generation_from_fixture(tmp_path: Path):
    fixture = tmp_path / "judgments.json"
    fixture.write_text(
        '[{"query":"wireless mouse","judgments":{"P1":3,"P2":1}},'
        '{"query":"coffee maker","judgments":{"P3":3}}]',
        encoding="utf-8",
    )
    judgments = load_product_search_judgments(fixture)
    rows = [
        evaluate_ranking("baseline_bm25", judgments[0].query, judgments[0].judgments, ["P1", "P9"]),
        evaluate_ranking("baseline_bm25", judgments[1].query, judgments[1].judgments, ["P8", "P3"]),
        *pending_rows("enriched_profile", judgments, "pending fixture"),
    ]

    report = build_report(rows, query_count=len(judgments))
    json_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"
    write_json_report(report, json_path)
    write_markdown_report(report, markdown_path)

    assert report["query_count"] == 2
    assert json_path.exists()
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "Product Search Relevance Report" in markdown
    assert "baseline_bm25" in markdown
    assert "enriched_profile" in markdown
    assert "pending fixture" in markdown
