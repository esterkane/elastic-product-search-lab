from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from reranker_ablation import evaluate_ablation, evaluate_query, load_cases, markdown_report


def test_reranked_mode_uses_same_top_k_candidate_set() -> None:
    top_k, cases, _ = load_cases(ROOT / "data" / "candidates.json")
    baseline = evaluate_query(cases[0], "baseline", top_k)
    reranked = evaluate_query(cases[0], "reranked", top_k)

    assert set(baseline["ranked_ids"]) == set(reranked["ranked_ids"])
    assert baseline["top_result"] == "p-keyword-only"
    assert reranked["top_result"] == "p-hybrid-guide"


def test_ablation_report_has_quality_and_latency_deltas() -> None:
    top_k, cases, latency_ms = load_cases(ROOT / "data" / "candidates.json")
    report = evaluate_ablation(top_k, cases, latency_ms)
    comparison = report["comparison"]

    assert report["top_k"] == 5
    assert comparison["ndcg_at_5_delta"] > 0
    assert comparison["p95_latency_ms_delta"] > 0
    assert "When Reranking Helps" in markdown_report(report)
