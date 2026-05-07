from scripts.search_quality_program import (
    Gates,
    build_report,
    default_esci_cases,
    default_runs,
    markdown_summary,
    reciprocal_rank_fusion_ids,
)


def test_quality_program_separates_good_and_bad_search_changes() -> None:
    report = build_report(default_esci_cases(), default_runs(), Gates())

    assert report["decision_summary"]["shippable_changes"] == ["baseline-bm25", "hybrid-rrf", "candidate-good"]
    assert report["decision_summary"]["blocked_changes"] == ["candidate-bad"]

    baseline, hybrid, good, bad = report["runs"]
    assert baseline["ship"] is True
    assert hybrid["ship"] is True
    assert bad["ship"] is False
    assert hybrid["strategy"] == "hybrid-rrf"
    assert good["relevance"]["ndcg_at_10"] > bad["relevance"]["ndcg_at_10"]
    assert good["performance"]["p95_latency_ms"] < bad["performance"]["p95_latency_ms"]


def test_quality_program_reports_required_metrics_and_resilience_matrix() -> None:
    report = build_report(default_esci_cases(), default_runs()[:1], Gates())
    run = report["runs"][0]

    assert {"ndcg_at_10", "precision_at_5", "mrr_at_10", "recall_at_10", "zero_result_rate"}.issubset(
        run["relevance"]
    )
    assert {"p50_latency_ms", "p95_latency_ms", "p99_latency_ms", "throughput_qps", "shard_scenarios"}.issubset(
        run["performance"]
    )
    assert [item["name"] for item in run["resilience"]["matrix"]] == [
        "replay",
        "idempotency",
        "429/backoff",
        "partial-cluster degradation",
        "alias rollback",
        "soft-delete merge",
    ]


def test_markdown_summary_explains_ship_decision() -> None:
    markdown = markdown_summary(build_report(default_esci_cases(), default_runs(), Gates()))

    assert "hybrid-rrf (hybrid-rrf): SHIPS" in markdown
    assert "candidate-bad (regression): DO NOT SHIP" in markdown
    assert "Before/After" in markdown
    assert "Recovery Matrix" in markdown
    assert "nDCG@10" in markdown


def test_hybrid_rrf_fuses_lexical_and_dense_channels_deterministically() -> None:
    ranked = reciprocal_rank_fusion_ids(
        {
            "lexical": ["doc-b", "doc-a", "doc-c"],
            "dense": ["doc-a", "doc-b", "doc-d"],
        },
        k=60,
    )

    assert ranked[:4] == ["doc-a", "doc-b", "doc-d", "doc-c"]


def test_report_includes_baseline_vs_hybrid_tradeoff() -> None:
    report = build_report(default_esci_cases(), default_runs(), Gates())
    comparison = report["comparisons"][0]

    assert comparison["baseline"] == "baseline-bm25"
    assert comparison["candidate"] == "hybrid-rrf"
    assert comparison["ndcg_at_10_delta"] > 0
    assert comparison["p95_latency_ms_delta"] > 0
